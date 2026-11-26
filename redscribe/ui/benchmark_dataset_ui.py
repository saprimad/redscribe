"""Explicit participant identifiers and dataset approval from confirmed pairs."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path

def approve_pairs_dialog(parent,pairs):
    from redscribe.benchmark.benchmark_dataset import approve_dataset
    rows=[]
    for audio,reference in pairs:
        pid=simpledialog.askstring("Participant ID",
            f"Confirm participant ID for:\n{Path(audio).name}\nReference: {Path(reference).parent.name}",
            initialvalue=Path(audio).stem,parent=parent)
        if pid is None:
            return None
        rows.append({"participant_id":pid,"audio":audio,"reference_manifest":reference})
    if not messagebox.askyesno("Freeze dataset",f"Approve these {len(rows)} participant/audio/reference pairs? Confirm that all identifiers and pairings are correct.",parent=parent):
        return None
    path=filedialog.asksaveasfilename(parent=parent,title="Save new approved dataset manifest",defaultextension=".json",filetypes=[("JSON","*.json")],initialfile="approved_dataset.json")
    if not path:
        return None
    try:
        approve_dataset(rows,path,researcher_acknowledged=True,expected_count=len(pairs))
    except Exception as exc:
        messagebox.showerror("Dataset approval",str(exc),parent=parent)
        return None
    return path
