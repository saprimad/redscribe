"""Experimental RedScribe benchmark UI.

Runs isolated single/batch trials on worker threads. Results stay local;
ordinary transcription settings and workflow are not altered.
"""
import os
import subprocess
import sys
from datetime import datetime, timezone
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

    def __init__(self, parent, on_live=None, *, sidebar=None, controls=None):
        self.parent = parent
        self.on_live = on_live
        self.embedded = sidebar is not None and controls is not None
        self.sidebar = sidebar
        self.controls = controls
        self.window = parent if self.embedded else tk.Toplevel(parent)
        if not self.embedded:
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
        if not self.embedded:
            self.window.protocol("WM_DELETE_WINDOW", self.request_close)
        self.language = tk.StringVar(master=self.window, value="Bahasa Melayu")
        self.pilot_status = tk.StringVar(master=self.window, value="Ready to configure benchmark")
        self.audio_summary = tk.StringVar(master=self.window, value="No audio selected")
        self.reference_summary = tk.StringVar(master=self.window, value="No ground truth selected")
        self.model_summary = tk.StringVar(master=self.window)
        self.confirmed_configuration = None
        self.active_run = None
        self.last_output = None
        self.build()
        self.refresh_models()
        for variable in (self.language, self.gpu_monitor, *self.selected.values()):
            variable.trace_add('write', lambda *_: self.invalidate_review())
        self.invalidate_review()

    def build(self):
        outer = ttk.Frame(self.sidebar if self.embedded else self.window, padding=4 if self.embedded else 16)
        outer.pack(fill="both", expand=True)
        if self.embedded:
            inner = outer
        else:
            ttk.Label(outer, text="Benchmarking Mode", font=("TkDefaultFont", 17, "bold")).pack(anchor="w")
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
        wrap = 300 if self.embedded else 660
        self.setup_widgets = []
        self.model_checks = {}
        self.output_summary = tk.StringVar(master=self.window)
        overview = ttk.LabelFrame(inner, text="Scientific Benchmarking", padding=12)
        overview.pack(fill="x", pady=(0, 10))
        ttk.Label(overview, text="Evaluation of automatic speech recognition (ASR) performance against researcher-approved reference transcripts.", wraplength=wrap, justify="left").pack(fill="x", pady=(0, 8))
        for heading, detail in (("Evaluation metrics", "Word Error Rate (WER)\nCharacter Error Rate (CER)"), ("Scoring engine", "RapidFuzz — Levenshtein edit distance"), ("Evaluation protocol", "Raw verbatim scoring")):
            ttk.Label(overview, text=heading, foreground="#667085").pack(anchor="w")
            ttk.Label(overview, text=detail, wraplength=wrap, justify="left").pack(fill="x", pady=(0, 6))
        self.setup_panel = outer
        def action(parent, text, command):
            button = tk.Button(parent, text=text, command=command, bg="white", fg="#202332",
                               disabledforeground="#999999", padx=10, pady=7, relief="groove", bd=1)
            button.pack(fill="x", pady=3)
            self.setup_widgets.append((button, "normal"))
            return button

        files = ttk.LabelFrame(inner, text="01. Dataset", padding=12)
        files.pack(fill="x", pady=(0, 10))
        self.audio_button = action(files, "Select audio recording", self.pick_audio)
        self.audio_label = ttk.Label(files, textvariable=self.audio_summary, wraplength=wrap)
        self.audio_label.pack(fill="x", pady=(0, 6))
        self.reference_button = action(files, "Select reference transcript", self.pick_references)
        self.reference_label = ttk.Label(files, textvariable=self.reference_summary, wraplength=wrap)
        self.reference_label.pack(fill="x", pady=(0, 6))
        self.ground_button = action(files, "Review ground truth", self.open_reference_review)
        self.ground_status = ttk.Label(files, wraplength=wrap)
        self.ground_status.pack(fill="x")
        self.pairing_button = ttk.Button(files, text="Verify batch audio / DOCX pairing", command=self.open_batch_pairing)

        models = ttk.LabelFrame(inner, text="02. ASR models", padding=12)
        models.pack(fill="x", pady=(0, 10))
        for title, keys in (("Default 7", CORE_MODELS), ("Select all", ALL_MODELS), ("Clear all", ())):
            action(models, title, lambda keys=keys: self.set_models(keys))
        ttk.Label(models, textvariable=self.model_summary).pack(anchor="w", pady=(4, 8))
        ttk.Label(models, text="Default models").pack(anchor="w")
        for key in CORE_MODELS:
            self.add_model_checkbox(models, key)
        ttk.Separator(models).pack(fill="x", pady=9)
        ttk.Label(models, text="Legacy models").pack(anchor="w")
        for key in ALL_MODELS[len(CORE_MODELS):]:
            self.add_model_checkbox(models, key)

        options = ttk.LabelFrame(inner, text="03. Benchmark settings", padding=12)
        options.pack(fill="x", pady=(0, 10))
        ttk.Label(options, text="Language").pack(anchor="w")
        language = ttk.Combobox(options, textvariable=self.language, state="readonly",
                                values=["Bahasa Melayu", "English", "Auto detect"])
        language.pack(fill="x")
        self.setup_widgets.append((language, "readonly"))
        self.monitor_check = tk.Checkbutton(options, text="Resource monitoring", variable=self.gpu_monitor,
                                           anchor="w", bg="white", activebackground="white", selectcolor="white")
        self.monitor_check.pack(fill="x", pady=5)
        self.setup_widgets.append((self.monitor_check, "normal"))
        location = ttk.LabelFrame(inner, text="04. Output location", padding=12)
        location.pack(fill="x", pady=(0, 10))
        ttk.Label(location, textvariable=self.output_summary, wraplength=wrap).pack(fill="x")
        self.folder_button = action(location, "Choose output folder", lambda: self.master_folder(change=True))
        footer = self.controls if self.embedded else ttk.Frame(outer)
        if not self.embedded:
            footer.pack(fill="x", pady=(12, 0))
        self.review_button = tk.Button(footer, text="Review configuration", bg="#247a46", fg="white",
                                      command=self.review, disabledforeground="#999999")
        self.review_button.configure(padx=10, pady=7)
        self.review_button.pack(side="left", padx=4)
        self.start_button = tk.Button(footer, text="Start benchmark", command=self.open_full_matrix,
                                     bg="#eeeeee", disabledforeground="#999999", state="disabled")
        self.start_button.configure(padx=10, pady=7)
        self.start_button.pack(side="right", padx=4)
        self.stop_button = ttk.Button(footer, text="Stop benchmark", command=self.stop_benchmark, state="disabled")
        self.stop_button.pack(side="right", padx=4)
        ttk.Button(footer, text="Open output folder", command=self.open_output_folder).pack(side="right", padx=4)
        # Legacy pilot callbacks remain available for regression tests, not primary UI.
        self.start_pilot_button = ttk.Button(footer, command=self.start_pilot)
        self.stop_pilot_button = ttk.Button(footer, command=self.stop_pilot, state="disabled")
        if not self.embedded:
            ttk.Label(outer, textvariable=self.pilot_status, wraplength=720).pack(anchor="w", pady=(7, 0))

    def configuration(self):
        from redscribe.benchmark.benchmark_experiments import saved_master
        from redscribe.benchmark.benchmark_reference import verify_reference, sha256_file
        if len(self.audio_files) != 1 or len(self.reference_files) != 1:
            raise ValueError("Select one audio and one DOCX.")
        audio, source = self.audio_files[0], self.reference_files[0]
        manifest = self.approved_references.get(source)
        if not manifest:
            raise ValueError("Review and freeze the ground truth first.")
        info = verify_reference(manifest)
        if Path(info["source_path"]).resolve() != Path(source).resolve():
            raise ValueError("Approved reference does not match selected DOCX.")
        if not all(info.get("verification", {}).get(k) is True for k in
                   ("audio_verified", "coverage_verified", "speaker_labels_reviewed", "non_speech_reviewed")):
            raise ValueError("Complete all ground truth verification checks.")
        models = ordered_selection(k for k,v in self.selected.items() if v.get())
        master = saved_master()
        if not models or not master:
            raise ValueError("Choose models and a private output folder.")
        return dict(audio=audio, audio_sha256=sha256_file(audio), source=source,
                    manifest=manifest, reference_sha256=info["approved_text_sha256"],
                    manifest_sha256=sha256_file(manifest), models=list(models),
                    language={"Bahasa Melayu":"ms","English":"en","Auto detect":None}[self.language.get()],
                    monitor=bool(self.gpu_monitor.get()), master=str(master))

    def invalidate_review(self):
        self.confirmed_configuration = None
        if not hasattr(self, "start_button"):
            return
        self.start_button.configure(state="disabled", bg="#eeeeee", fg="#777777")
        ready = (len(self.audio_files) == 1 and len(self.reference_files) == 1
                 and self.reference_files[0] in self.approved_references
                 and any(v.get() for v in self.selected.values()))
        self.review_button.configure(state="normal" if ready and not self.active_run else "disabled",
                                     bg="#247a46" if ready and not self.active_run else "#eeeeee", text="Review configuration")
        if hasattr(self, "setup_widgets"):
            self.refresh_setup()
        if not self.active_run:
            self.pilot_status.set("Configuration review required")

    def refresh_setup(self):
        from redscribe.benchmark.benchmark_experiments import saved_master
        locked = bool(self.active_run)
        for widget, normal in self.setup_widgets:
            widget.configure(state="disabled" if locked else normal)
        def status_button(widget, selected, available=True):
            widget.configure(state="normal" if available and not locked else "disabled",
                             bg="#247a46" if selected and not locked else "#eeeeee" if not available or locked else "white",
                             fg="white" if selected and not locked else "#202332")
        audio = bool(self.audio_files)
        reference = bool(self.reference_files)
        frozen = reference and all(p in self.approved_references for p in self.reference_files)
        status_button(self.audio_button, audio)
        status_button(self.reference_button, reference)
        status_button(self.ground_button, audio and reference, audio and reference)
        self.audio_label.configure(foreground="#247a46" if audio else "#667085")
        self.reference_label.configure(foreground="#247a46" if reference else "#667085")
        self.ground_status.configure(text="Ground truth approved and frozen" if frozen else "Awaiting verification",
                                     foreground="#247a46" if frozen else "#667085")
        for key, widget in self.model_checks.items():
            widget.configure(fg="#247a46" if self.selected[key].get() else "#667085")
        self.monitor_check.configure(fg="#247a46" if self.gpu_monitor.get() else "#667085")
        master = saved_master()
        self.output_summary.set(str(master) if master else "No master output folder configured")
        self.folder_button.configure(text="Change output folder" if master else "Choose output folder")
        self.refresh_models()

    def open_full_matrix(self):
        from .operation_guard import operation_active
        from .benchmark_matrix_ui import open_matrix_window
        from redscribe.benchmark.benchmark_experiments import new_experiment
        if self.active_run or operation_active():
            return
        try:
            current = self.configuration()
            approval = self.confirmed_configuration
            if not approval or approval["configuration"] != current:
                raise ValueError("Configuration changed or not confirmed. Review again.")
            row = dict(participant_id=approval["participant_id"], audio=current["audio"],
                       reference_manifest=current["manifest"])
            output, manifest = new_experiment(current["master"], [row], current["models"],
                current["language"], current["monitor"], researcher_acknowledged=True,
                configuration_confirmation=approval)
        except Exception as exc:
            self.invalidate_review()
            messagebox.showerror("Benchmark preflight", str(exc), parent=self.window)
            return
        self.last_output = output
        self.active_run = True
        if hasattr(self, "setup_widgets"):
            self.refresh_setup()
        self.start_button.configure(state="disabled", bg="#eeeeee", fg="#777777")
        self.review_button.configure(state="disabled", bg="#eeeeee")
        self.stop_button.configure(state="normal")
        self.pilot_status.set("Benchmark running")
        try:
            handle = open_matrix_window(self.window, current["models"], current["language"],
                current["monitor"], manifest=str(manifest), output=str(output),
                confirmed=True, on_finished=self.finish_benchmark,
                on_live=self.on_live)
            if handle is None:
                self.finish_benchmark()
            elif self.active_run:
                self.active_run = handle
                if self.on_live is not None:
                    self.on_live('begin', None, None, dict(models=current['models'], participant=approval['participant_id']))
                    if not self.embedded:
                        self.window.transient('')
                        self.parent.lift()
        except Exception as exc:
            self.finish_benchmark()
            messagebox.showerror("Benchmark", str(exc), parent=self.window)

    def stop_benchmark(self):
        if callable(self.active_run):
            self.active_run()
            self.pilot_status.set("Stop requested; waiting for safe checkpoint")
            self.stop_button.configure(state="disabled")

    def finish_benchmark(self):
        self.active_run = None
        if getattr(self, 'on_live', None) is not None:
            self.on_live('finished', None, None, None)
        self.stop_button.configure(state="disabled")
        self.invalidate_review()
        self.pilot_status.set("Run ended — inspect results; review before another run")

    def open_output_folder(self):
        from redscribe.benchmark.benchmark_experiments import saved_master
        path = self.last_output or saved_master()
        if not path:
            messagebox.showinfo("Output folder", "Choose an output folder first.", parent=self.window)
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("Output folder", str(exc), parent=self.window)

    def master_folder(self, change=False):
        if change and self.active_run:
            return None
        from redscribe.benchmark.benchmark_experiments import saved_master, save_master
        master = saved_master()
        if master and not change:
            return master
        folder = filedialog.askdirectory(parent=self.window, title="Choose PRIVATE master benchmark folder", initialdir=str(master) if master else None)
        if not folder:
            return None
        try:
            master = save_master(folder)
            self.invalidate_review()
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
        if not self.embedded:
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
        if getattr(self, "active_run", None):
            return
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
        if hasattr(self, "start_button"):
            self.invalidate_review()
        self.reference_summary.set(self.describe_files(self.reference_files) +
                                   f" | {len(self.approved_references)} locally approved")

    def add_model_checkbox(self, parent, key):
        widget = tk.Checkbutton(parent, text=ASR_MODEL_LABELS[key], variable=self.selected[key],
                                anchor="w", justify="left", wraplength=278 if self.embedded else 600,
                                bg="white", activebackground="white", selectcolor="white")
        widget.pack(fill="x", pady=2)
        self.model_checks[key] = widget
        self.setup_widgets.append((widget, "normal"))

    def set_models(self, keys):
        if self.active_run:
            return
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
        if self.active_run:
            return
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
        self.approved_references = {}
        if self.reference_files:
            self.reference_summary.set(self.describe_files(self.reference_files))
        self.audio_summary.set(self.describe_files(self.audio_files))
        self.invalidate_review()

    def pick_references(self):
        if self.active_run:
            return
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
        self.invalidate_review()

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
        if self.active_run:
            return
        self.invalidate_review()
        if not self.master_folder():
            return
        try:
            config = self.configuration()
        except Exception as exc:
            messagebox.showwarning("Review configuration", str(exc), parent=self.window)
            return
        dialog = tk.Toplevel(self.window)
        dialog.title("Benchmark Configuration Review")
        dialog.transient(self.window)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        participant = tk.StringVar(master=dialog, value=Path(config["audio"]).stem)
        ttk.Label(frame, text="Recording ID").pack(anchor="w")
        ttk.Entry(frame, textvariable=participant).pack(fill="x")
        details = [
            "Audio: " + Path(config["audio"]).name,
            "Ground truth: " + Path(config["source"]).name,
            "Reference: approved and SHA-256 verified",
            "Models: " + ", ".join(ASR_MODEL_LABELS[m] for m in config["models"]),
            "Language: " + self.language.get(),
            "Evaluation method: Raw WER and CER using RapidFuzz Levenshtein alignment.",
            "Requested device / precision: CUDA / FP16",
            "Resource monitoring: " + ("Enabled" if config["monitor"] else "Disabled"),
            "Master output folder: " + config["master"],
            "An experiment subfolder will be created automatically.",
        ]
        ttk.Label(frame, text="\n".join(details), wraplength=640, justify="left").pack(anchor="w", pady=10)
        labels = (
            "I confirm that the selected audio corresponds to the approved ground truth.",
            "I confirm the selected ASR models, benchmark settings and output location.",
            "I acknowledge the limitations of automatic speech recognition and the need for independent verification of benchmark results.",
        )
        flags = [tk.BooleanVar(master=dialog, value=False) for _ in labels]
        widgets = []
        def update(*_):
            for widget, flag in zip(widgets, flags):
                widget.configure(fg="#247a46" if flag.get() else "#202332")
            ready = all(v.get() for v in flags) and bool(participant.get().strip())
            confirm.configure(state="normal" if ready else "disabled", bg="#247a46" if ready else "#eeeeee", fg="white" if ready else "#999999")
        def approve():
            try:
                if not all(v.get() for v in flags) or config != self.configuration():
                    raise ValueError("Configuration changed. Review again.")
                pid = participant.get().strip()
                if not pid:
                    raise ValueError("Enter a participant pseudonym.")
                self.confirmed_configuration = dict(configuration=config, participant_id=pid,
                    confirmed_utc=datetime.now(timezone.utc).isoformat(),
                    checks=dict(zip(("audio_reference_match", "settings_correct", "interpretation_acknowledged"), [True]*3)))
                self.start_button.configure(state="normal", bg="#8f1037", fg="white", activebackground="#74102d", activeforeground="white")
                self.review_button.configure(text="Review configuration ✓", bg="#247a46")
                self.pilot_status.set("Configuration confirmed — Ready to benchmark")
                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Configuration review", str(exc), parent=dialog)
        for label, flag in zip(labels, flags):
            widget = tk.Checkbutton(frame, text=label, variable=flag, command=update, anchor="w",
                                    wraplength=620, justify="left", bg="white", activebackground="white", selectcolor="white")
            widget.pack(fill="x", pady=3)
            widgets.append(widget)
        confirm = tk.Button(frame, text="Confirm configuration", command=approve, state="disabled",
                            bg="#eeeeee", disabledforeground="#999999", padx=10, pady=7)
        confirm.pack(anchor="e", pady=8)
        participant.trace_add("write", update)
        update()


def open_benchmark_window(parent, on_live=None, **kwargs):
    """Open an isolated, non-modal experimental benchmark window."""
    return BenchmarkWindow(parent, on_live=on_live, **kwargs)
