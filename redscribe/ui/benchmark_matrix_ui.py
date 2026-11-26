"""Separate full-length benchmark window; all worker updates via queue."""
import json
import queue
import threading
import traceback
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from pathlib import Path

def open_matrix_window(parent,models,language,monitor=True,manifest=None):
    from redscribe.benchmark.benchmark_dataset import verify_dataset
    from redscribe.benchmark.benchmark_structured_output import run_structured_batch, validate_output_root
    from redscribe.benchmark.benchmark_resources import ResourceMonitor
    manifest=manifest or filedialog.askopenfilename(parent=parent,title="Select approved dataset manifest",filetypes=[("JSON","*.json")])
    if not manifest:
        return
    output=filedialog.askdirectory(parent=parent,title="Select new or existing benchmark output folder")
    if not output:
        return
    try:
        validate_output_root(output)
        dataset=verify_dataset(manifest)
    except Exception as exc:
        messagebox.showerror("Benchmark preflight",str(exc),parent=parent)
        return
    ids=[p["participant_id"] for p in dataset["pairs"]]
    if not messagebox.askyesno("Full-length benchmark",f"Run {len(models)} models on {len(ids)} recordings? Existing compatible checkpoints will be resumed. CUDA FP16 required.",parent=parent):
        return
    win=tk.Toplevel(parent)
    win.title("RedScribe — Full-length Benchmark")
    win.geometry("1000x650")
    win.transient(parent)
    win.grab_set()
    status=tk.StringVar(master=win,value="Preparing benchmark")
    ttk.Label(win,textvariable=status).pack(fill="x",padx=12,pady=8)
    frame=ttk.Frame(win)
    frame.pack(fill="both",expand=True,padx=12)
    tree=ttk.Treeview(frame,columns=tuple(models),show="tree headings")
    tree.heading("#0",text="Participant")
    tree.column("#0",width=100,stretch=False)
    for m in models:
        tree.heading(m,text=m)
        tree.column(m,width=135,anchor="center",stretch=False)
    for pid in ids:
        tree.insert("", "end",iid=pid,text=pid,values=["pending"]*len(models))
    sy=ttk.Scrollbar(frame,orient="vertical",command=tree.yview)
    sx=ttk.Scrollbar(frame,orient="horizontal",command=tree.xview)
    tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
    sy.pack(side="right",fill="y")
    sx.pack(side="bottom",fill="x")
    tree.pack(fill="both",expand=True)
    bar=ttk.Progressbar(win,maximum=len(ids)*len(models))
    bar.pack(fill="x",padx=12,pady=8)
    cancel=threading.Event()
    events=queue.Queue()
    cells={}
    def update(m,p,s):
        if p is not None and p in ids and m in models:
            cells[m,p]=s
            tree.set(p,m,s)
        terminal=sum(s in ("completed","failed","not_run","cancelled") for s in cells.values())
        bar["value"]=terminal
        status.set(f"{terminal}/{len(ids)*len(models)} resolved — {m}: {s}")
    def worker():
        def progress(m,p,s):
            print(f"[Benchmark] {m}: {s}",flush=True)
            events.put(("cell",m,p,s))
        try:
            result=run_structured_batch(manifest,models,output,language=language,
                stopped=cancel.is_set,monitor_factory=ResourceMonitor if monitor else None,
                progress=progress)
            for m,records in result["results"].items():
                for p,r in records.items():
                    events.put(("cell",m,p,r["status"]))
            events.put(("published","Stopped — partial reports generated" if cancel.is_set() else "Run ended — inspect failures and reports"))
        except Exception as exc:
            traceback.print_exc()
            events.put(("error",f"{type(exc).__name__}: {exc}"))
    from .operation_guard import start_exclusive
    thread=start_exclusive(worker)
    if thread is None:
        win.destroy()
        messagebox.showwarning("Operation active","Wait for the current ASR operation to finish.",parent=parent)
        return
    def close():
        if thread.is_alive():
            cancel.set()
            status.set("Stop requested; waiting for current operation")
        else:
            win.destroy()
    win.protocol("WM_DELETE_WINDOW",close)
    ttk.Button(win,text="Stop / Close",command=close).pack(pady=8)
    def drain():
        while True:
            try:
                event=events.get_nowait()
            except queue.Empty:
                break
            if event[0]=="cell":
                update(*event[1:])
            else:
                status.set(event[1])
                if event[0]=="error":
                    messagebox.showerror("Benchmark failed",event[1],parent=win)
                if event[0]=="published":
                    messagebox.showwarning("Confidential research data retained",
                        "Scientific reports are in the selected output folder. The 04 - SENSITIVE DATA folder contains confidential transcripts, checkpoints and diagnostic materials. Do not distribute or upload it without authorisation. Folder segregation is not encryption. Review run failures before interpreting results.",parent=win)
        if thread.is_alive() or not events.empty():
            win.after(150,drain)
    win.after(150,drain)
