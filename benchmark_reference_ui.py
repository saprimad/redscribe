"""Interactive manual review of DOCX reference transcripts."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from benchmark_ground_truth import extract_docx
from benchmark_reference import approve_reference


class GroundTruthReview:
    def __init__(self, parent, paths, on_approved=None):
        self.parent = parent
        self.paths = tuple(paths)
        self.on_approved = on_approved
        if not self.paths:
            raise ValueError("Select a DOCX file before opening review")
        self.window = tk.Toplevel(parent)
        self.window.title("Ground Truth — Review & Freeze")
        self.window.geometry("840x680")
        self.window.minsize(600, 450)
        self.index = tk.StringVar(master=self.window, value=self.paths[0])
        self.acknowledged = tk.BooleanVar(master=self.window, value=False)
        self.status = tk.StringVar(master=self.window, value="Reference not approved")
        self.current_draft = None
        self.build()
        self.load_selected()

    def build(self):
        frame = ttk.Frame(self.window, padding=14)
        frame.pack(fill="both", expand=True)
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

        self.text = scrolledtext.ScrolledText(frame, wrap="word", undo=True, font=("TkDefaultFont", 11))
        self.text.pack(fill="both", expand=True, pady=(4, 8))
        ttk.Label(frame, text="NOTE: Extracted text may contain speaker labels, headings, "
                  "tables, fillers and comments. No automatic speaker-label removal is performed.",
                  wraplength=770, foreground="#845a26").pack(anchor="w", pady=(0, 8))
        ttk.Checkbutton(frame, variable=self.acknowledged,
                        text="I have reviewed this complete reference and approve this scoring text.").pack(
            anchor="w", pady=(0, 7))
        ttk.Label(frame, textvariable=self.status, wraplength=770).pack(anchor="w")
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Reload extracted DOCX (discard edits)",
                   command=self.reload_confirm).pack(side="left")
        ttk.Button(actions, text="Close", command=self.window.destroy).pack(side="right")
        ttk.Button(actions, text="Approve & Freeze locally",
                   command=self.approve).pack(side="right", padx=(0, 8))

    def reload_confirm(self):
        if messagebox.askyesno("Discard edits?", "Reload extracted text from the original DOCX? "
                               "Unsaved edits in this window will be lost.", parent=self.window):
            self.load_selected()

    def load_selected(self):
        self.acknowledged.set(False)
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
        self.status.set(f"{len(self.current_draft.blocks)} text blocks extracted; not approved")

    def approve(self):
        if self.current_draft is None:
            messagebox.showwarning("No reference", "Choose a readable DOCX.", parent=self.window)
            return
        if not self.acknowledged.get():
            messagebox.showwarning("Approval required", "Review the content and tick the confirmation.",
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
        folder = filedialog.askdirectory(parent=self.window, title="Choose PRIVATE output folder for approved references")
        if not folder:
            return
        try:
            manifest_path, text_path, info = approve_reference(
                self.current_draft.source_path, text, folder, reviewer_acknowledged=True)
        except Exception as exc:
            messagebox.showerror("Approval failed", str(exc), parent=self.window)
            return
        self.status.set("Approved and frozen: " + Path(manifest_path).name)
        self.acknowledged.set(False)
        if self.on_approved:
            self.on_approved(self.current_draft.source_path, str(manifest_path))
        messagebox.showinfo("Reference saved",
                            f"Scoring text: {text_path}\nManifest: {manifest_path}\n"
                            "Keep these files private. Changing the text requires a NEW approval.",
                            parent=self.window)


def open_ground_truth_review(parent, paths, on_approved=None):
    return GroundTruthReview(parent, paths, on_approved=on_approved)
