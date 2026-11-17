"""Standalone RedScribe Benchmarking Mode configuration window.

UI-only scaffold. Does NOT start transcription, load models, alter existing
transcription settings, or send recordings anywhere.
"""
import os
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

        safety = ttk.LabelFrame(inner, text="4. Before starting", padding=12)
        safety.pack(fill="x", pady=(0, 10))
        ttk.Label(safety, wraplength=660,
                  text="Warning: benchmarking may run for hours, download large models, "
                       "use considerable GPU/CPU/RAM and disk space, and generate "
                       "research outputs. Save results after each model. This is "
                       "currently a UI preview: no model will be run.").pack(anchor="w")
        ttk.Label(safety, wraplength=660,
                  text="Planned: sequential execution, WER/CER, error analysis, "
                       "audio/VAD descriptives, resource monitoring and Excel reports.").pack(
            anchor="w", pady=(8, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Close", command=self.window.destroy).pack(side="right")
        ttk.Button(footer, text="Review configuration (no run)",
                   command=self.review).pack(side="right", padx=(0, 10))

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
            "Ground-truth content and file matching have NOT been validated.\n"
            "No benchmark has started. Execution remains disabled pending implementation.",
            parent=self.window,
        )


def open_benchmark_window(parent):
    """Open an isolated, non-modal preview window."""
    return BenchmarkWindow(parent)
