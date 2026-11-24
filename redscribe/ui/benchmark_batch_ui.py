"""Researcher-controlled batch pairing: explicit audio-to-approved-DOCX mapping."""
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path


class PairingWindow:
    def __init__(self, parent, audio_files, reference_files, approved, on_confirm):
        self.window = tk.Toplevel(parent)
        self.window.title("Verify batch audio / ground truth pairings")
        self.window.geometry("850x550")
        self.window.transient(parent)
        self.audio_files = tuple(audio_files)
        self.approved = dict(approved)
        self.on_confirm = on_confirm
        self.references = [path for path in reference_files if path in approved]
        self.rows = []
        if len(self.references) < len(self.audio_files):
            raise ValueError("Approve at least one distinct DOCX reference per audio before pairing")
        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Manually confirm each audio → approved reference",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(outer, wraplength=780,
                  text="No automatic matching. Select a different approved DOCX for each recording; "
                       "the chosen mapping is stored with the batch. Each source must describe "
                       "the exact corresponding audio; check content before starting.").pack(
            anchor="w", pady=(7, 10))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        canvas = tk.Canvas(body, highlightthickness=0)
        scroller = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroller.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroller.pack(side="right", fill="y")
        inner = ttk.Frame(canvas, padding=4)
        item = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item, width=e.width))
        labels = [f"{Path(x).name}  [{i+1}]" for i, x in enumerate(self.references)]
        for i, audio in enumerate(self.audio_files):
            ttk.Label(inner, text=f"Audio {i+1}: {Path(audio).name}", wraplength=730).pack(
                anchor="w", pady=(12, 3))
            selection = tk.StringVar(master=self.window, value="")
            ttk.Combobox(inner, textvariable=selection, values=labels,
                         state="readonly", width=85).pack(anchor="w")
            self.rows.append(selection)
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(side="right")
        ttk.Button(footer, text="Confirm pairing", command=self.confirm).pack(
            side="right", padx=(0, 8))

    def confirm(self):
        labels = [f"{Path(x).name}  [{i+1}]" for i, x in enumerate(self.references)]
        chosen = [x.get() for x in self.rows]
        if any(x not in labels for x in chosen) or len(set(chosen)) != len(chosen):
            messagebox.showwarning("Invalid pairing",
                                   "Choose one unique approved reference for every audio.",
                                   parent=self.window)
            return
        pairs = [(a, self.approved[self.references[labels.index(c)]])
                 for a, c in zip(self.audio_files, chosen)]
        pretty = "\n".join(f"{Path(a).name} → {Path(self.references[labels.index(c)]).name}"
                            for a, c in zip(self.audio_files, chosen))
        if not messagebox.askyesno("Confirm batch mapping",
                                   "Confirm these pairs are correct:\n\n" + pretty,
                                   parent=self.window):
            return
        self.on_confirm(tuple(pairs))
        self.window.destroy()


def open_batch_pairing(parent, audio_files, reference_files, approved, on_confirm):
    return PairingWindow(parent, audio_files, reference_files, approved, on_confirm)
