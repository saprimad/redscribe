"""Experimental RedScribe benchmark UI.

Runs isolated single/batch trials on worker threads. Results stay local;
ordinary transcription settings and workflow are not altered.
"""
import os
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
        self.window.title("RedScribe — Benchmarking Mode (Experimental)")
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
        self.pilot_status = tk.StringVar(master=self.window, value="Pilot not started")
        self.audio_summary = tk.StringVar(master=self.window, value="No audio selected")
        self.reference_summary = tk.StringVar(master=self.window, value="No ground truth selected")
        self.model_summary = tk.StringVar(master=self.window)
        self.build()
        self.refresh_models()

    def build(self):
        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Benchmarking Mode", font=("TkDefaultFont", 17, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Single / batch experimental benchmarking; not publication validated.").pack(
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
        ttk.Button(files, text="Load approved reference (JSON)", command=self.load_approved_reference).pack(anchor="w", pady=(6, 0))
        ttk.Label(files, text="References are approved individually; selection alone is not approval.",
                  wraplength=660).pack(anchor="w", pady=(3, 0))
        ttk.Button(files, text="Verify batch audio / DOCX pairing",
                   command=self.open_batch_pairing).pack(anchor="w", pady=(6, 0))
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

        options = ttk.LabelFrame(inner, text="4. Benchmark trial options", padding=12)
        options.pack(fill="x", pady=(0, 10))
        ttk.Label(options, text="Single or paired batch: max 3 minutes per recording (trial limit).",
                  wraplength=650).pack(anchor="w")
        ttk.Label(options, text="Language").pack(anchor="w", pady=(8, 1))
        ttk.Combobox(options, textvariable=self.language, state="readonly",
                     values=["Bahasa Melayu", "English", "Auto detect"]).pack(anchor="w")
        ttk.Checkbutton(options, text="GPU / CPU / RAM monitoring", variable=self.gpu_monitor).pack(anchor="w", pady=5)
        ttk.Checkbutton(options, text="Silero VAD (speech / non-speech estimates)", variable=self.silero_vad).pack(anchor="w")
        ttk.Checkbutton(options, text="pyannote Community-1 OSD (overlap estimate)", variable=self.pyannote_osd).pack(anchor="w")
        ttk.Label(options, text="HF token (OSD only; optional if already logged in)").pack(anchor="w", pady=(6, 0))
        ttk.Entry(options, textvariable=self.hf_token, show="*", width=40).pack(anchor="w")
        ttk.Label(options, text="This pilot scores raw WER/CER only; optional ASR models may need CUDA.",
                  wraplength=650).pack(anchor="w", pady=(8, 0))

        safety = ttk.LabelFrame(inner, text="5. Before starting", padding=12)
        safety.pack(fill="x", pady=(0, 10))
        ttk.Label(safety, wraplength=660,
                  text="Warning: a pilot run WILL load/download selected ASR models and consume "
                       "GPU/CPU/RAM, disk and power. It processes models sequentially "
                       "and saves intermediate results. This is an unvalidated pilot, not a "
                       "publication-ready benchmark. Do not run alongside ordinary transcription."
                       ).pack(anchor="w")
        ttk.Label(safety, wraplength=660,
                  text="Still pending: normalised scoring, NIST validation, resume, full error analysis and Excel.").pack(
            anchor="w", pady=(8, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(safety, text="Full-length model-major benchmark", command=self.open_full_matrix).pack(anchor="w", pady=8)
        ttk.Button(safety, text="Resume from approved dataset (JSON)", command=self.load_approved_dataset).pack(anchor="w", pady=(0, 8))
        ttk.Button(footer, text="Close", command=self.request_close).pack(side="right")
        self.stop_pilot_button = ttk.Button(footer, text="Stop pilot",
                                             command=self.stop_pilot, state="disabled")
        self.stop_pilot_button.pack(side="right", padx=(0, 10))
        self.start_pilot_button = ttk.Button(footer, text="Start benchmark trial",
                                              command=self.start_pilot)
        self.start_pilot_button.pack(side="right", padx=(0, 10))
        ttk.Button(footer, text="Review configuration",
                   command=self.review).pack(side="left")
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
        manifest = approve_pairs_dialog(self.window, pairs)
        if not manifest:
            return
        open_matrix_window(self.window, models, lang, self.gpu_monitor.get(), manifest=manifest)

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
        from benchmark_reference_ui import open_ground_truth_review
        open_ground_truth_review(self.window, self.reference_files, self.mark_reference_approved)

    def mark_reference_approved(self, source_path, manifest_path):
        self.approved_references[source_path] = manifest_path
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
            self.reference_files = (value,)
        else:
            value = filedialog.askopenfilenames(parent=self.window, title="Select DOCX references",
                                                filetypes=WORD_TYPES)
            if not value:
                return
            self.reference_files = tuple(value)
        self.approved_references = {}
        self.batch_pairs = ()
        self.reference_summary.set(self.describe_files(self.reference_files))

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
