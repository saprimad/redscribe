"""Experimental RedScribe benchmark UI.

Runs isolated single/batch trials on worker threads. Results stay local;
ordinary transcription settings and workflow are not altered.
"""
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from benchmark_config import ALL_MODELS, CORE_MODELS, BenchmarkConfig, ordered_selection
from model_options import ASR_MODEL_LABELS

AUDIO_TYPES = [("Audio recordings", "*.wav *.mp3 *.m4a *.mp4"), ("All files", "*.*")]
WORD_TYPES = [("Microsoft Word", "*.docx"), ("All files", "*.*")]


class BenchmarkWindow:
    """A Toplevel window that never takes over the existing application flow."""

    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("RedScribe — Benchmarking Mode")
        self.window.geometry("820x740")
        self.window.minsize(620, 510)
        self.window.transient(parent)
        self.mode = tk.StringVar(master=self.window, value="single")
        self.selected = {key: tk.BooleanVar(master=self.window, value=key in CORE_MODELS)
                         for key in ALL_MODELS}
        self.audio_files = ()
        self.reference_files = ()
        self.approved_references = {}
        self.batch_pairs = ()
        self.gpu_monitor = tk.BooleanVar(master=self.window, value=True)
        self.silero_vad = tk.BooleanVar(master=self.window, value=False)
        self.pyannote_osd = tk.BooleanVar(master=self.window, value=False)
        self.hf_token = tk.StringVar(master=self.window, value="")
        self.pilot_thread = None
        self.pilot_cancel = threading.Event()
        self.worker_events = queue.Queue()
        self.window.protocol("WM_DELETE_WINDOW", self.request_close)
        self.language = tk.StringVar(master=self.window, value="Bahasa Melayu")
        self.pilot_status = tk.StringVar(master=self.window, value="Ready to configure benchmark")
        self.audio_summary = tk.StringVar(master=self.window, value="No audio selected")
        self.reference_summary = tk.StringVar(master=self.window, value="No ground truth selected")
        self.model_summary = tk.StringVar(master=self.window)
        self.build()
        self.refresh_models()

    def build(self):
        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Benchmarking Mode", font=("TkDefaultFont", 17, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Full-length single / batch ASR evaluation; scientific validation pending.").pack(
            anchor="w", pady=(3, 12))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        canvas = tk.Canvas(body, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas, padding=(4, 0, 14, 6))
        item = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item, width=e.width))
        mode_frame = ttk.LabelFrame(inner, text="1. Processing mode", padding=12)
        mode_frame.pack(fill="x", pady=(0, 10))
        for value, title in (("single", "Single audio + DOCX"),
                             ("batch", "Batch audio + DOCX")):
            ttk.Radiobutton(mode_frame, text=title, value=value, variable=self.mode,
                            command=self.reset_files).pack(anchor="w", pady=2)

        files = ttk.LabelFrame(inner, text="2. Dataset files", padding=12)
        files.pack(fill="x", pady=(0, 10))
        ttk.Button(files, text="Select audio", command=self.pick_audio).pack(anchor="w")
        ttk.Label(files, textvariable=self.audio_summary, wraplength=660).pack(anchor="w", pady=(4, 10))
        ttk.Button(files, text="Select ground truth DOCX", command=self.pick_references).pack(anchor="w")
        ttk.Label(files, textvariable=self.reference_summary, wraplength=660).pack(anchor="w", pady=(4, 3))
        ttk.Button(files, text="Review / Approve / Freeze DOCX",
                   command=self.open_reference_review).pack(anchor="w", pady=(7, 0))
        ttk.Label(files, text="References are approved individually; selection alone is not approval.",
                  wraplength=660).pack(anchor="w", pady=(3, 0))
        self.pairing_button = ttk.Button(files, text="Verify batch audio / DOCX pairing",
                   command=self.open_batch_pairing)
        ttk.Label(files, text="DOCX speaker labels and file matching must be verified before scoring.",
                  foreground="#805b33", wraplength=660).pack(anchor="w", pady=(6, 0))

        models = ttk.LabelFrame(inner, text="3. ASR model selection", padding=12)
        models.pack(fill="x", pady=(0, 10))
        buttons = ttk.Frame(models)
        buttons.pack(fill="x", pady=(0, 5))
        for title, keys in (("Default 7", CORE_MODELS),
                            ("Select All", ALL_MODELS), ("Clear All", ())):
            ttk.Button(buttons, text=title, command=lambda keys=keys: self.set_models(keys)).pack(
                side="left", padx=(0, 8))
        ttk.Label(models, textvariable=self.model_summary).pack(anchor="w", pady=(4, 8))
        ttk.Label(models, text="Core study models (selected by default)").pack(anchor="w")
        for key in CORE_MODELS:
            self.add_model_checkbox(models, key)
        ttk.Separator(models).pack(fill="x", pady=9)
        ttk.Label(models, text="Optional legacy comparison").pack(anchor="w")
        for key in ALL_MODELS[len(CORE_MODELS):]:
            self.add_model_checkbox(models, key)

        options = ttk.LabelFrame(inner, text="4. Benchmark settings", padding=12)
        options.pack(fill="x", pady=(0, 10))
        ttk.Label(options, text="Full audio duration; no three-minute trial limit.",
                  wraplength=650).pack(anchor="w")
        ttk.Label(options, text="Language").pack(anchor="w", pady=(8, 1))
        ttk.Combobox(options, textvariable=self.language, state="readonly",
                     values=["Bahasa Melayu", "English", "Auto detect"]).pack(anchor="w")
        ttk.Checkbutton(options, text="GPU / CPU / RAM monitoring", variable=self.gpu_monitor).pack(anchor="w", pady=5)
        ttk.Label(options, text="Selected models may require CUDA and download weights.", wraplength=650).pack(anchor="w")
        safety = ttk.LabelFrame(inner, text="5. Experiment management", padding=12)
        safety.pack(fill="x", pady=(0, 10))
        ttk.Label(safety, wraplength=660, text="Choose a private master folder once. References, manifests and experiment folders are managed automatically. Review scientific limitations before using results.").pack(anchor="w")
        ttk.Button(safety, text="Resume Experiment", command=self.resume_experiment).pack(anchor="w", pady=4)
        ttk.Button(safety, text="Regenerate Reports", command=self.regenerate_experiment).pack(anchor="w", pady=4)
        ttk.Button(safety, text="Change Master Output Folder", command=lambda: self.master_folder(change=True)).pack(anchor="w", pady=4)
        advanced = ttk.LabelFrame(safety, text="Advanced — legacy imports", padding=6)
        advanced.pack(fill="x", pady=4)
        ttk.Button(advanced, text="Load approved reference (JSON)", command=self.load_approved_reference).pack(anchor="w")
        ttk.Button(advanced, text="Load approved dataset (JSON)", command=self.load_approved_dataset).pack(anchor="w")
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Close", command=self.request_close).pack(side="right")
        ttk.Button(footer, text="Benchmark", command=self.open_full_matrix).pack(side="right", padx=(0, 10))
        # Legacy pilot callbacks remain available for regression tests, not primary UI.
        self.start_pilot_button = ttk.Button(footer, command=self.start_pilot)
        self.stop_pilot_button = ttk.Button(footer, command=self.stop_pilot, state="disabled")
        ttk.Label(outer, textvariable=self.pilot_status, wraplength=720).pack(
            anchor="w", pady=(7, 0))

    def open_full_matrix(self):
        if self.pilot_thread is not None and self.pilot_thread.is_alive():
            messagebox.showwarning("Running","Stop the pilot first.",parent=self.window)
            return
        models=ordered_selection(k for k,v in self.selected.items() if v.get())
        if not models:
            messagebox.showwarning("Models","Select at least one model.",parent=self.window)
            return
        from .benchmark_matrix_ui import open_matrix_window
        lang={"Bahasa Melayu":"ms","English":"en","Auto detect":None}[self.language.get()]
        from .benchmark_dataset_ui import approve_pairs_dialog
        if self.mode.get() == "single":
            if len(self.audio_files) != 1 or len(self.reference_files) != 1:
                messagebox.showwarning("Inputs", "Select one audio and one DOCX first.", parent=self.window)
                return
            reference = self.approved_references.get(self.reference_files[0])
            if not reference:
                messagebox.showwarning("Approval", "Review / Approve / Freeze the DOCX, or load an approved reference.", parent=self.window)
                return
            pairs = ((self.audio_files[0], reference),)
        else:
            if not self.audio_files or len(self.batch_pairs) != len(self.audio_files):
                messagebox.showwarning("Pairing", "Verify batch audio / DOCX pairing first.", parent=self.window)
                return
            pairs = self.batch_pairs
        master = self.master_folder()
        if not master:
            return
        from redscribe.benchmark.benchmark_experiments import new_experiment
        monitor = self.gpu_monitor.get()
        prepared = approve_pairs_dialog(self.window, pairs, prepare_experiment=lambda rows:
            new_experiment(master, rows, models, lang, monitor, researcher_acknowledged=True))
        if not prepared:
            return
        output, manifest = prepared
        open_matrix_window(self.window, models, lang, monitor, manifest=str(manifest), output=str(output))

    def master_folder(self, change=False):
        from redscribe.benchmark.benchmark_experiments import saved_master, save_master
        master = saved_master()
        if master and not change:
            return master
        folder = filedialog.askdirectory(parent=self.window, title="Choose PRIVATE master benchmark folder", initialdir=str(master) if master else None)
        if not folder:
            return None
        try:
            master = save_master(folder)
            self.pilot_status.set("Master output folder: " + str(master))
            return master
        except Exception as exc:
            messagebox.showerror("Master folder", str(exc), parent=self.window)
            return None

    def choose_experiment(self):
        master = self.master_folder()
        if not master:
            return None
        return filedialog.askdirectory(parent=self.window, title="Choose existing experiment folder", initialdir=str(master))

    def resume_experiment(self):
        from redscribe.benchmark.benchmark_experiments import load_experiment
        from .benchmark_matrix_ui import open_matrix_window
        root = self.choose_experiment()
        if not root:
            return
        try:
            manifest, models, language, monitor = load_experiment(root)
        except Exception as exc:
            messagebox.showerror("Experiment integrity", str(exc), parent=self.window)
            return
        open_matrix_window(self.window, models, language, monitor, manifest=str(manifest), output=root)

    def regenerate_experiment(self):
        from redscribe.benchmark.benchmark_structured_output import regenerate
        from .operation_guard import start_exclusive
        root = self.choose_experiment()
        if not root:
            return
        events = queue.Queue()
        def worker():
            try:
                regenerate(root)
                events.put((True, "Scientific reports regenerated without ASR."))
            except Exception as exc:
                events.put((False, str(exc)))
        thread = start_exclusive(worker)
        if thread is None:
            messagebox.showwarning("Operation active", "Finish the active operation first.", parent=self.window)
            return
        self.pilot_status.set("Regenerating scientific reports...")
        def poll():
            try:
                ok, detail = events.get_nowait()
            except queue.Empty:
                self.window.after(150, poll)
                return
            self.pilot_status.set(detail)
            (messagebox.showinfo if ok else messagebox.showerror)("Report regeneration", detail, parent=self.window)
        self.window.after(150, poll)

    def load_approved_reference(self):
        if not self.reference_files:
            messagebox.showwarning("Inputs", "Select the original DOCX first.", parent=self.window)
            return
        path = filedialog.askopenfilename(parent=self.window, title="Load frozen reference manifest (JSON)", filetypes=[("JSON", "*.json")])
        if not path:
            return
        from redscribe.benchmark.benchmark_reference import verify_reference, sha256_file
        try:
            ref = verify_reference(path)
            matches = [p for p in self.reference_files if sha256_file(p) == ref["source_sha256"]]
            if len(matches) != 1:
                raise ValueError("Frozen reference must match exactly one selected DOCX by SHA-256.")
        except Exception as exc:
            messagebox.showerror("Reference integrity", str(exc), parent=self.window)
            return
        self.mark_reference_approved(matches[0], path)

    def load_approved_dataset(self):
        from .benchmark_matrix_ui import open_matrix_window
        models = ordered_selection(k for k, v in self.selected.items() if v.get())
        if not models:
            messagebox.showwarning("Models", "Select at least one model.", parent=self.window)
            return
        lang = {"Bahasa Melayu": "ms", "English": "en", "Auto detect": None}[self.language.get()]
        open_matrix_window(self.window, models, lang, self.gpu_monitor.get())

    def open_batch_pairing(self):
        if self.mode.get() != "batch":
            messagebox.showwarning("Pairing", "Choose Batch mode first.", parent=self.window)
            return
        from benchmark_batch_ui import open_batch_pairing
        try:
            open_batch_pairing(self.window, self.audio_files, self.reference_files,
                               self.approved_references, self.confirm_batch_pairs)
        except ValueError as exc:
            messagebox.showwarning("Pairing", str(exc), parent=self.window)

    def confirm_batch_pairs(self, pairs):
        self.batch_pairs = pairs
        self.pilot_status.set(f"Confirmed {len(pairs)} audio/reference pairs")

    def start_pilot(self):
        if self.pilot_thread is not None and self.pilot_thread.is_alive():
            messagebox.showwarning("Running", "A trial is already active.", parent=self.window)
            return
        selected_models = ordered_selection(k for k, v in self.selected.items() if v.get())
        if not selected_models:
            messagebox.showwarning("Models", "Select at least one model.", parent=self.window)
            return
        batch = self.mode.get() == "batch"
        if batch:
            if not self.audio_files or len(self.batch_pairs) != len(self.audio_files):
                messagebox.showwarning("Pairing required", "Approve all DOCXs and confirm each audio/reference pair.",
                                       parent=self.window)
                return
            pairs = tuple(self.batch_pairs)
        else:
            if len(self.audio_files) != 1 or len(self.reference_files) != 1:
                messagebox.showwarning("Inputs", "Select one audio and one reference DOCX.",
                                       parent=self.window)
                return
            manifest = self.approved_references.get(self.reference_files[0])
            if not manifest:
                messagebox.showwarning("Approval", "Review / Approve / Freeze the DOCX first.",
                                       parent=self.window)
                return
            pairs = ((self.audio_files[0], manifest),)
        from benchmark_reference import verify_reference
        try:
            for audio, reference in pairs:
                if not os.path.isfile(audio):
                    raise FileNotFoundError(audio)
                verify_reference(reference)
        except Exception as exc:
            messagebox.showerror("Input integrity", str(exc), parent=self.window)
            return
        if not messagebox.askyesno(
            "Run experimental benchmark?",
            f"Run {len(selected_models)} model(s) on {len(pairs)} recording(s)?\n\n"
            "Models may download weights and consume substantial resources. "
            "VAD/OSD are descriptive only. Pilot limit: 3 minutes per audio. "
            "Proceed?", parent=self.window):
            return
        self.pilot_cancel.clear()
        self.start_pilot_button.configure(state="disabled")
        self.stop_pilot_button.configure(state="normal")
        self.pilot_status.set("Running sequential benchmark; saving per-model results")
        lang = {"Bahasa Melayu": "ms", "English": "en", "Auto detect": None}[self.language.get()]
        output = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output", "benchmark_pilot")
        # Snapshot Tk variables on the GUI thread; worker must never read Tk state.
        opts = dict(language=lang, cancel=self.pilot_cancel,
                    gpu_monitor=self.gpu_monitor.get(), vad=self.silero_vad.get(),
                    osd=self.pyannote_osd.get(), hf_token=self.hf_token.get().strip() or None)

        def notify(event, detail):
            # Thread-safe hand-off; schedule UI updates only on the Tk thread.
            self.worker_events.put((event, str(detail)))

        def worker():
            try:
                if batch:
                    from benchmark_batch import run_batch_pilot
                    folder, result = run_batch_pilot(pairs, selected_models, output,
                                                     notify=notify, **opts)
                else:
                    from benchmark_pilot import run_single_pilot
                    folder, result = run_single_pilot(pairs[0][0], pairs[0][1],
                                                      selected_models, output,
                                                      notify=notify, **opts)
                notify("finished", f"{result['status']} — {folder}")
            except Exception as exc:
                notify("error", f"{type(exc).__name__}: {exc}")
            finally:
                self.worker_events.put(("worker_done", ""))

        from .operation_guard import start_exclusive
        self.pilot_thread = start_exclusive(worker)
        if self.pilot_thread is None:
            self.pilot_complete()
            messagebox.showwarning("Operation active","Wait for the current ASR operation to finish.",parent=self.window)
            return
        self.window.after(150, self.drain_worker_events)

    def drain_worker_events(self):
        if not self.window.winfo_exists():
            return
        finished = False
        while True:
            try:
                event, detail = self.worker_events.get_nowait()
            except queue.Empty:
                break
            if event == "worker_done":
                finished = True
            else:
                self.set_pilot_status(event, detail)
        if finished:
            self.pilot_complete()
        elif self.pilot_thread is not None and self.pilot_thread.is_alive():
            self.window.after(150, self.drain_worker_events)
        else:
            self.pilot_complete()

    def request_close(self):
        from .operation_guard import operation_active
        if operation_active():
            messagebox.showwarning("Operation active", "Wait for the active operation to finish before closing.", parent=self.window)
            return
        if self.pilot_thread is not None and self.pilot_thread.is_alive():
            messagebox.showwarning(
                "Benchmark running",
                "Stop the benchmark first and wait until the worker has finished. "
                "Closing now could interrupt result saving.",
                parent=self.window,
            )
            return
        self.window.destroy()

    def stop_pilot(self):
        self.pilot_cancel.set()
        self.pilot_status.set("Stop requested; waiting for current model operation to yield...")

    def set_pilot_status(self, event, detail):
        if not self.window.winfo_exists():
            return
        self.pilot_status.set(f"{event}: {detail}")

    def pilot_complete(self):
        if self.window.winfo_exists():
            self.start_pilot_button.configure(state="normal")
            self.stop_pilot_button.configure(state="disabled")

    def open_reference_review(self):
        if not self.reference_files:
            messagebox.showwarning("No DOCX selected", "Choose ground-truth DOCX file(s) first.",
                                   parent=self.window)
            return
        try:
            from .benchmark_reference_ui import open_ground_truth_review
            from redscribe.benchmark.benchmark_experiments import reference_cache
            def storage():
                master = self.master_folder()
                return str(reference_cache(master)) if master else None
            open_ground_truth_review(self.window, self.reference_files, self.mark_reference_approved,
                                     output_provider=storage)
        except Exception as exc:
            messagebox.showerror("Ground truth review", f"{type(exc).__name__}: {exc}", parent=self.window)

    def mark_reference_approved(self, source_path, manifest_path):
        key = str(Path(source_path).resolve())
        if key not in self.reference_files:
            raise ValueError("Approved DOCX is no longer selected")
        self.approved_references[key] = manifest_path
        self.batch_pairs = ()
        self.reference_summary.set(self.describe_files(self.reference_files) +
                                   f" | {len(self.approved_references)} locally approved")

    def add_model_checkbox(self, parent, key):
        ttk.Checkbutton(parent, text=ASR_MODEL_LABELS[key], variable=self.selected[key],
                        command=self.refresh_models).pack(anchor="w", pady=2)

    def set_models(self, keys):
        selected = set(keys)
        for key, variable in self.selected.items():
            variable.set(key in selected)
        self.refresh_models()

    def refresh_models(self):
        count = sum(bool(var.get()) for var in self.selected.values())
        self.model_summary.set(f"{count} of {len(ALL_MODELS)} models selected")

    def reset_files(self):
        if self.mode.get() == "batch":
            self.pairing_button.pack(anchor="w", pady=(6, 0))
        else:
            self.pairing_button.pack_forget()
        self.audio_files = ()
        self.reference_files = ()
        self.approved_references = {}
        self.batch_pairs = ()
        self.audio_summary.set("No audio selected")
        self.reference_summary.set("No ground truth selected")

    def pick_audio(self):
        if self.mode.get() == "single":
            value = filedialog.askopenfilename(parent=self.window, title="Select audio",
                                               filetypes=AUDIO_TYPES)
            if not value:
                return
            self.audio_files = (value,)
        else:
            value = filedialog.askopenfilenames(parent=self.window, title="Select recordings",
                                                filetypes=AUDIO_TYPES)
            if not value:
                return
            self.audio_files = tuple(value)
        self.batch_pairs = ()
        self.audio_summary.set(self.describe_files(self.audio_files))

    def pick_references(self):
        if self.mode.get() == "single":
            value = filedialog.askopenfilename(parent=self.window, title="Select DOCX reference",
                                               filetypes=WORD_TYPES)
            if not value:
                return
            self.reference_files = (str(Path(value).resolve()),)
        else:
            value = filedialog.askopenfilenames(parent=self.window, title="Select DOCX references",
                                                filetypes=WORD_TYPES)
            if not value:
                return
            self.reference_files = tuple(str(Path(p).resolve()) for p in value)
        self.approved_references = {}
        self.batch_pairs = ()
        self.reference_summary.set(self.describe_files(self.reference_files))
        self.restore_approved_references()

    def restore_approved_references(self):
        """Restore only unambiguous, verified frozen references after DOCX selection."""
        from redscribe.benchmark.benchmark_experiments import saved_master
        from redscribe.benchmark.benchmark_reference import verify_reference, sha256_file
        master = saved_master()
        if not master:
            return
        cache = master / "_PRIVATE Frozen References"
        if not cache.is_dir():
            return
        candidates = {}
        for manifest in cache.glob("*.json"):
            try:
                info = verify_reference(manifest)
                checks = info.get("verification", {})
                if info.get("approval") != "researcher_confirmed" or not all(
                    checks.get(k) is True for k in ("audio_verified", "coverage_verified",
                        "speaker_labels_reviewed", "non_speech_reviewed")
                ):
                    continue
                candidates.setdefault(str(Path(info["source_path"]).resolve()), []).append(
                    (manifest, info["source_sha256"]))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        for source in self.reference_files:
            try:
                digest = sha256_file(source)
                matches = [p for p, h in candidates.get(source, []) if h == digest]
                if len(matches) == 1:
                    self.approved_references[source] = str(matches[0])
            except OSError:
                continue
        self.reference_summary.set(self.describe_files(self.reference_files) +
                                   f" | {len(self.approved_references)} locally approved")

    @staticmethod
    def describe_files(files):
        if len(files) == 1:
            return os.path.basename(files[0])
        return f"{len(files)} selected files"

    def review(self):
        models = ordered_selection(k for k, v in self.selected.items() if v.get())
        if not models:
            messagebox.showwarning("No models selected", "Select at least one model.", parent=self.window)
            return
        if not self.audio_files or not self.reference_files:
            messagebox.showwarning("Missing dataset", "Choose audio and DOCX reference files.",
                                   parent=self.window)
            return
        if self.mode.get() == "single" and (len(self.audio_files) != 1 or len(self.reference_files) != 1):
            messagebox.showwarning("Invalid single mode", "Single mode needs one audio and one DOCX.",
                                   parent=self.window)
            return
        # This validates model/mode settings only: it MUST NOT imply DOCX parsing
        # and audio/reference matching have already been checked.
        config = BenchmarkConfig(mode=self.mode.get(), models=models)
        messagebox.showinfo(
            "Benchmark configuration preview",
            f"Mode: {config.mode}\n"
            f"Audio files: {len(self.audio_files)}\n"
            f"DOCX files: {len(self.reference_files)}\n"
            f"Selected models: {len(config.models)}\n\n"
            f"Approved references (local): {len(self.approved_references)}/{len(self.reference_files)}\\n"
            "Audio/reference file matching has NOT been validated.\\n"
            "Review and verify all pairings before starting a real experimental run.",
            parent=self.window,
        )


def open_benchmark_window(parent):
    """Open an isolated, non-modal experimental benchmark window."""
    return BenchmarkWindow(parent)
