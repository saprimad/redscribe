"""Interactive manual review of DOCX reference transcripts."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from benchmark_ground_truth import extract_docx, remove_speaker_labels
from benchmark_reference import approve_reference, verify_reference


class GroundTruthReview:
    def __init__(self, parent, paths, on_approved=None, output_dir=None, output_provider=None):
        self.parent = parent
        self.paths = tuple(paths)
        self.on_approved = on_approved
        self.output_dir = output_dir
        self.output_provider = output_provider
        if not self.paths:
            raise ValueError("Select a DOCX file before opening review")
        self.window = tk.Toplevel(parent)
        self.window.title("Ground Truth — Review & Freeze")
        self.window.transient(parent)
        self.window.grab_set()
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        self.window.geometry(f"{min(1000, int(screen_w * .85))}x{min(820, int(screen_h * .80))}")
        self.window.minsize(600, 450)
        self.window.resizable(True, True)
        self.index = tk.StringVar(master=self.window, value=self.paths[0])
        self.acknowledged = tk.BooleanVar(master=self.window, value=False)
        self.verification = {
            "audio_verified": tk.BooleanVar(master=self.window, value=False),
            "coverage_verified": tk.BooleanVar(master=self.window, value=False),
            "speaker_labels_reviewed": tk.BooleanVar(master=self.window, value=False),
            "non_speech_reviewed": tk.BooleanVar(master=self.window, value=False),
        }
        self.status = tk.StringVar(master=self.window, value="Reference not approved")
        self.current_draft = None
        self.label_removal_history = []
        self.build()
        self.load_selected()

    def build(self):
        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill="both", expand=True)
        # Reserve footer space before allocating the scrollable body.
        actions = ttk.Frame(outer)
        actions.pack(side="bottom", fill="x", pady=(8, 0))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        canvas = tk.Canvas(body, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        frame = ttk.Frame(canvas, padding=(0, 0, 8, 0))
        item = canvas.create_window((0, 0), window=frame, anchor="nw")
        def fit_body(_event=None):
            # Fill the viewport when space is available; scroll only when needed.
            width = max(1, canvas.winfo_width())
            height = max(canvas.winfo_height(), frame.winfo_reqheight())
            canvas.itemconfigure(item, width=width, height=height)
            canvas.configure(scrollregion=(0, 0, width, height))

        frame.bind("<Configure>", fit_body)
        canvas.bind("<Configure>", fit_body)
        ttk.Label(frame, text="Ground Truth DOCX — Manual Review",
                  font=("TkDefaultFont", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Original Word documents stay unchanged. Edit the scoring copy below; "
                  "do not delete actual spoken words.", wraplength=780).pack(anchor="w", pady=(6, 10))
        chooser = ttk.Frame(frame)
        chooser.pack(fill="x", pady=(0, 8))
        ttk.Label(chooser, text="Document:").pack(side="left")
        combo = ttk.Combobox(chooser, textvariable=self.index, values=self.paths, state="readonly")
        combo.pack(side="left", fill="x", expand=True, padx=(8, 0))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.load_selected())

        self.text = scrolledtext.ScrolledText(frame, wrap="word", undo=True, height=10, font=("TkDefaultFont", 11))
        self.text.pack(fill="both", expand=True, pady=(4, 8))
        ttk.Label(frame, text="NOTE: Extracted text may contain speaker labels, headings, "
                  "tables, fillers and comments. Optional removal supports P1–P25, Penemu duga and Interviewer with : or ;. Review the result.",
                  wraplength=770, foreground="#845a26").pack(anchor="w", pady=(0, 8))
        self.issues_summary = tk.StringVar(master=self.window, value="")
        ttk.Label(frame, textvariable=self.issues_summary, wraplength=770,
                  foreground="#9a4b24").pack(anchor="w", pady=(0, 5))
        checks = (
            ("audio_verified", "I checked this transcript against the corresponding audio."),
            ("coverage_verified", "I verified the reference covers exactly the selected audio span."),
            ("speaker_labels_reviewed", "I reviewed speaker labels, headings and non-spoken metadata."),
            ("non_speech_reviewed", "I reviewed fillers, overlaps, interruptions and non-speech notes."),
        )
        self.check_widgets = []
        for key, label in checks:
            flag = self.verification[key]
            check = tk.Checkbutton(frame, variable=flag, text=label, anchor="w", bg="white",
                                   selectcolor="white", activebackground="white")
            check.pack(fill="x")
            self.check_widgets.append((check, flag))
        check = tk.Checkbutton(frame, variable=self.acknowledged,
            text="I have reviewed and approve the complete reference for scoring.",
            anchor="w", bg="white", selectcolor="white", activebackground="white")
        check.pack(fill="x", pady=(0, 7))
        self.check_widgets.append((check, self.acknowledged))
        ttk.Label(frame, textvariable=self.status, wraplength=770).pack(anchor="w")
        ttk.Separator(actions, orient="horizontal").pack(fill="x", pady=(0, 9))
        toolbar = ttk.Frame(actions)
        toolbar.pack(fill="x")
        reload_button = ttk.Button(toolbar, text="Reload DOCX", command=self.reload_confirm)
        remove_button = ttk.Button(toolbar, text="Remove speaker labels", command=self.remove_labels)
        close_button = ttk.Button(toolbar, text="Close", command=self.window.destroy)
        approve_button = tk.Button(toolbar, text="Approve & freeze reference", command=self.approve,
                                   state="disabled", bg="#eeeeee", disabledforeground="#999999", padx=10, pady=6)
        self.approve_button = approve_button
        for _, flag in self.check_widgets:
            flag.trace_add("write", self.refresh_approval)
        self.refresh_approval()
        self.text.bind("<<Modified>>", self.reference_edited)
        self.text.edit_modified(False)
        buttons = (reload_button, remove_button, close_button, approve_button)
        compact = None

        def fit_toolbar(event=None):
            nonlocal compact
            width = toolbar.winfo_width()
            narrow = width < sum(button.winfo_reqwidth() for button in buttons) + 30
            if compact == narrow:
                return
            compact = narrow
            for button in buttons:
                button.grid_forget()
            for column in range(5):
                toolbar.columnconfigure(column, weight=0)
            if narrow:
                toolbar.columnconfigure(0, weight=1)
                toolbar.columnconfigure(1, weight=1)
                for i, button in enumerate(buttons):
                    button.grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=2)
            else:
                toolbar.columnconfigure(2, weight=1)
                for button, column in zip(buttons, (0, 1, 3, 4)):
                    button.grid(row=0, column=column, padx=3, pady=2)

        toolbar.bind("<Configure>", fit_toolbar)
        fit_toolbar()


    def refresh_approval(self, *_):
        for widget, flag in self.check_widgets:
            widget.configure(fg="#247a46" if flag.get() else "#202332")
        ready = self.current_draft is not None and all(flag.get() for _, flag in self.check_widgets)
        self.approve_button.configure(state="normal" if ready else "disabled",
                                      bg="#247a46" if ready else "#eeeeee", fg="white" if ready else "#999999")

    def reference_edited(self, _event=None):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.acknowledged.set(False)
        for flag in self.verification.values():
            flag.set(False)
        self.refresh_approval()

    def remove_labels(self):
        current = self.text.get("1.0", "end-1c")
        proposed, counts = remove_speaker_labels(current)
        if not counts:
            messagebox.showinfo("Speaker labels", "No supported line-start labels found. Review manually.", parent=self.window)
            return
        if not messagebox.askyesno("Remove speaker labels?", f"Remove {sum(counts.values())} explicit prefixes from the scoring copy only? Review all changes before approval.", parent=self.window):
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", proposed)
        self.label_removal_history.append(counts)
        self.acknowledged.set(False)
        for flag in self.verification.values():
            flag.set(False)
        self.status.set(f"Removed {sum(counts.values())} speaker labels; review required")

    def reload_confirm(self):
        if messagebox.askyesno("Discard edits?", "Reload extracted text from the original DOCX? "
                               "Unsaved edits in this window will be lost.", parent=self.window):
            self.load_selected()

    def load_selected(self):
        self.label_removal_history = []
        self.acknowledged.set(False)
        for flag in self.verification.values():
            flag.set(False)
        self.issues_summary.set("")
        self.status.set("Reference not approved; review required")
        try:
            self.current_draft = extract_docx(self.index.get())
        except Exception as exc:
            self.current_draft = None
            self.text.delete("1.0", "end")
            messagebox.showerror("DOCX import error", str(exc), parent=self.window)
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.current_draft.text)
        issues = self.current_draft.issues
        self.issues_summary.set(
            "DOCX review flags: " + " | ".join(issues)
            if issues else "No flagged advanced DOCX features; still verify all spoken content."
        )
        self.status.set(f"{len(self.current_draft.blocks)} text blocks extracted; not approved")
        self.text.edit_modified(False)
        self.refresh_approval()

    def approve(self):
        if self.current_draft is None:
            messagebox.showwarning("No reference", "Choose a readable DOCX.", parent=self.window)
            return
        if not self.acknowledged.get():
            messagebox.showwarning("Approval required", "Review the content and tick the confirmation.",
                                   parent=self.window)
            return
        verification = {name: flag.get() for name, flag in self.verification.items()}
        if not all(verification.values()):
            messagebox.showwarning("Verification required",
                                   "Confirm all four audio/reference review checks before freezing.",
                                   parent=self.window)
            return
        text = self.text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("Empty reference", "Reference cannot be empty.",
                                   parent=self.window)
            return
        if not messagebox.askyesno("Freeze this reference?",
                "Save a PRIVATE, immutable-by-convention reference text and its SHA-256 manifest? "
                "This does not run any ASR model.", parent=self.window):
            return
        try:
            folder = self.output_dir
            if folder is None:
                folder = (self.output_provider() if self.output_provider is not None
                          else filedialog.askdirectory(parent=self.window, title="Choose PRIVATE output folder for approved references"))
            if not folder:
                return
            manifest_path, text_path, info = approve_reference(
                self.current_draft.source_path, text, folder, reviewer_acknowledged=True,
                expected_source_sha256=self.current_draft.source_sha256,
                verification=verification, label_removal_history=self.label_removal_history)
            verify_reference(manifest_path)
            if self.on_approved:
                self.on_approved(self.current_draft.source_path, str(manifest_path))
        except Exception as exc:
            messagebox.showerror("Approval failed", str(exc), parent=self.window)
            return
        self.status.set("Ground truth approved and frozen")
        if len(self.paths) == 1:
            self.window.destroy()
        else:
            self.acknowledged.set(False)
            for flag in self.verification.values():
                flag.set(False)


def open_ground_truth_review(parent, paths, on_approved=None, output_dir=None, output_provider=None):
    return GroundTruthReview(parent, paths, on_approved=on_approved, output_dir=output_dir, output_provider=output_provider)
