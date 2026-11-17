"""Standalone RedScribe Benchmarking Mode configuration window.

UI-only scaffold. Does NOT start transcription, load models, alter existing
transcription settings, or send recordings anywhere.
"""
import os
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
        self.window.title("RedScribe — Benchmarking Mode (Design Preview)")
        self.window.geometry("820x740")
        self.window.minsize(620, 510)
        self.window.transient(parent)
        self.mode = tk.StringVar(master=self.window, value="single")
        self.selected = {key: tk.BooleanVar(master=self.window, value=key in CORE_MODELS)
                         for key in ALL_MODELS}
        self.audio_files = ()
        self.reference_files = ()
        self.approved_references = {}
        self.pilot_thread = None
        self.pilot_cancel = threading.Event()
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
        ttk.Label(outer, text="Configuration preview — benchmark execution is not connected yet.").pack(
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

        options = ttk.LabelFrame(inner, text="4. Short-audio pilot settings", padding=12)
        options.pack(fill="x", pady=(0, 10))
        ttk.Label(options, text="Pilot supports Single mode only, with one approved DOCX and audio up to 3 minutes.",
                  wraplength=650).pack(anchor="w")
        ttk.Label(options, text="Language").pack(anchor="w", pady=(8, 1))
        ttk.Combobox(options, textvariable=self.language, state="readonly",
                     values=["Bahasa Melayu", "English", "Auto detect"]).pack(anchor="w")
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
                  text="Planned but not active: Batch runner, normalised scores, VAD/OSD, "
                       "resource monitoring, full error analysis and Excel reports.").pack(
            anchor="w", pady=(8, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Close", command=self.window.destroy).pack(side="right")
        self.stop_pilot_button = ttk.Button(footer, text="Stop pilot",
                                             command=self.stop_pilot, state="disabled")
        self.stop_pilot_button.pack(side="right", padx=(0, 10))
        self.start_pilot_button = ttk.Button(footer, text="Start short-audio pilot",
                                              command=self.start_pilot)
        self.start_pilot_button.pack(side="right", padx=(0, 10))
        ttk.Button(footer, text="Review configuration",
                   command=self.review).pack(side="left")
        ttk.Label(outer, textvariable=self.pilot_status, wraplength=720).pack(
            anchor="w", pady=(7, 0))

    def start_pilot(self):
        if self.pilot_thread is not None and self.pilot_thread.is_alive():
            messagebox.showwarning("Already running", "A benchmark pilot is already running.",
                                   parent=self.window)
            return
        if self.mode.get() != "single":
            messagebox.showwarning("Pilot scope", "Only Single mode runs in this pilot. "
                                   "Batch stays available as a design preview.",
                                   parent=self.window)
            return
        if len(self.audio_files) != 1 or len(self.reference_files) != 1:
            messagebox.showwarning("Missing dataset", "Select one audio and one DOCX.",
                                   parent=self.window)
            return
        ref = self.reference_files[0]
        manifest_path = self.approved_references.get(ref)
        if not manifest_path:
            messagebox.showwarning("Reference not approved",
                                   "Open Review / Approve / Freeze DOCX first, then approve the scoring text.",
                                   parent=self.window)
            return
        models = ordered_selection(k for k, v in self.selected.items() if v.get())
        if not models:
            messagebox.showwarning("No models", "Select at least one model.", parent=self.window)
            return
        audio = self.audio_files[0]
        if not os.path.isfile(audio) or not os.path.isfile(manifest_path):
            messagebox.showerror("Missing input", "Audio or approved reference no longer exists.",
                                 parent=self.window)
            return
        from benchmark_reference import verify_reference
        try:
            verify_reference(manifest_path)
        except Exception as exc:
            messagebox.showerror("Reference integrity", str(exc), parent=self.window)
            return
        if not messagebox.askyesno("Start REAL benchmark pilot?",
                f"Run {len(models)} model(s) sequentially on one short audio?\\n\\n"
                "First-time model downloads may be large. This is exploratory raw "
                "WER/CER scoring without diarization. Keep RedScribe running.\\n\\n"
                "Continue?", parent=self.window):
            return
        from benchmark_pilot import run_single_pilot
        self.pilot_cancel.clear()
        self.start_pilot_button.configure(state="disabled")
        self.stop_pilot_button.configure(state="normal")
        self.pilot_status.set("Pilot running. Results are saved after every model.")
        language = {"Bahasa Melayu": "ms", "English": "en",
                    "Auto detect": None}[self.language.get()]
        output_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output", "benchmark_pilot")

        def notify(event, detail):
            try:
                self.window.after(0, lambda e=event, d=detail: self.set_pilot_status(e, d))
            except (RuntimeError, tk.TclError):
                pass

        def worker():
            try:
                result_path, summary = run_single_pilot(
                    audio, manifest_path, models, output_folder,
                    language=language, notify=notify, cancel=self.pilot_cancel)
                notify("finished", str(result_path) + " | " + summary["status"])
            except Exception as exc:
                notify("error", f"{type(exc).__name__}: {exc}")
            finally:
                try:
                    self.window.after(0, self.pilot_complete)
                except (RuntimeError, tk.TclError):
                    pass
        self.pilot_thread = threading.Thread(target=worker, daemon=True)
        self.pilot_thread.start()

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
            "No benchmark has started. Execution remains disabled pending implementation.",
            parent=self.window,
        )


def open_benchmark_window(parent):
    """Open an isolated, non-modal preview window."""
    return BenchmarkWindow(parent)
