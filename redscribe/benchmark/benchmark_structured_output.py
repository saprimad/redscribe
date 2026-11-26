"""Structured benchmark output; private working state remains resumable.

Folder segregation is not encryption. Never move or delete original research files.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

PRIVATE = "04 - SENSITIVE DATA"
SUPPORT = "03 - Supporting Material"
PDF = "01 - Scientific Report.pdf"
EXCEL = "02 - Scientific Results.xlsx"
NOTICE = """CONFIDENTIAL RESEARCH DATA
This folder may contain transcripts, source paths, identifiers, checkpoints and
diagnostic logs. Restrict access to authorised researchers. Do not distribute,
upload or publish without appropriate authorisation. Folder segregation is
not encryption. Retention and disposal remain the researcher's responsibility.
Original source files are not deleted or modified by this workflow.
"""
FIGURES = ("corpus_accuracy", "wer_distribution", "cer_distribution",
           "accuracy_speed", "participant_wer_heatmap")
NUMERIC = ("wer","cer","word_substitutions","word_deletions","word_insertions",
           "reference_words","char_substitutions","char_deletions","char_insertions",
           "reference_characters","audio_seconds","inference_seconds","rtf","worker_exit_code")
RESOURCES = ("gpu_util_percent_peak","gpu_memory_used_mb_peak","gpu_temperature_c_peak",
             "cpu_percent_peak","ram_used_mb_peak","sample_count")

def _numeric(value):
    return value if type(value) in (int,float) and math.isfinite(value) else None

def _public_state(state):
    """Allowlist numbers and fixed enums; replace source participant identifiers."""
    identity = state["identity"]
    models = identity["models"]
    from .benchmark_config import ALL_MODELS
    if not models or any(not isinstance(m,str) or m not in ALL_MODELS for m in models):
        raise ValueError("Unexpected model identifier: expected a registered RedScribe model")
    if len(set(models)) != len(models):
        raise ValueError("Duplicate model identifiers")
    ids = {p:f"R{i:03d}" for i,p in enumerate(identity["recordings"],1)}
    out = {"identity":{"models":models,"recordings":list(ids.values())},"results":{}}
    for m in models:
        out["results"][m] = {}
        for p,alias in ids.items():
            row = state["results"].get(m,{}).get(p,{})
            status = row.get("status")
            clean = {k:_numeric(row.get(k)) for k in NUMERIC}
            clean["status"] = status if status in ("completed","failed","cancelled","not_run") else "not_run"
            for k,allowed in (
                ("device",("cuda","cpu")),("precision",("float16","float32","int8","fp16","fp32")),
                ("cleanup_status",("completed","failed")),
                ("shutdown_strategy",("normal_destructor","controlled_process_exit"))):
                clean[k] = row.get(k) if row.get(k) in allowed else None
            resources = row.get("resources") or {}
            clean["resources"] = {k:_numeric(resources.get(k)) for k in RESOURCES}
            out["results"][m][alias] = clean
    return out

def _safe_root(root):
    root = Path(root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    allowed = {PRIVATE,SUPPORT,PDF,EXCEL}
    if any(p.name not in allowed or p.is_symlink() for p in root.iterdir()):
        raise ValueError("Choose an empty or existing structured output folder; legacy output is not moved automatically.")
    private = root / PRIVATE
    private.mkdir(exist_ok=True)
    (private/"CONFIDENTIAL - READ ME.txt").write_text(NOTICE,encoding="utf-8")
    return root,private

def _publish(root,private,state):
    from .benchmark_matrix_reporting import export_matrix_reporting
    from .benchmark_publication import export_publication
    with tempfile.TemporaryDirectory(prefix="report-staging-",dir=private) as temp:
        stage = Path(temp)
        public = _public_state(state)
        export_matrix_reporting(stage,public)
        export_publication(stage,public)
        # Keep staging and all unfiltered data inside the sensitive workspace.
        supporting = stage/"support"
        figures = supporting/"Scientific Figures"
        statistics = supporting/"Statistical Data"
        integrity = supporting/"Reproducibility and Integrity"
        for p in (figures,statistics,integrity,
                  supporting/"Corpus Analysis",supporting/"Performance and Diagnostics"):
            p.mkdir(parents=True,exist_ok=True)
        (supporting/"Corpus Analysis"/"README.txt").write_text(
            "Numerical corpus results are in Statistical Data. Textual corpus analysis requires authorised access to sensitive data. No automatic linguistic classification is claimed.",encoding="utf-8")
        (supporting/"Performance and Diagnostics"/"README.txt").write_text(
            "Numerical resource and exit-code records are in Statistical Data. Unfiltered logs remain in SENSITIVE DATA.",encoding="utf-8")
        for name in ("model_summary.csv","recording_results.csv","efficiency_summary.csv"):
            shutil.copy2(stage/name,statistics/name)
        for name in FIGURES:
            for ext in ("png","svg"):
                p=stage/(name+"."+ext)
                if p.is_file():
                    shutil.copy2(p,figures/p.name)
        (integrity/"README.txt").write_text(
            "Recording labels are sequential aliases. Raw checkpoint and source manifests remain sensitive. Hashes below cover published files only; they do not establish anonymity or audio coverage.",encoding="utf-8")
        files = {PDF:stage/"scientific_report.pdf",EXCEL:stage/"scientific_results.xlsx"}
        files.update({str(Path(SUPPORT)/p.relative_to(supporting)).replace(os.sep,"/"):p for p in supporting.rglob("*") if p.is_file()})
        hashes={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files.items()}
        manifest=integrity/"export_integrity.json"
        manifest.write_text(json.dumps({"schema":1,"scope":"structured_publication","sha256":hashes},indent=2),encoding="utf-8")
        # Invalidate old certification before replacing outputs. Preserve previous
        # supporting material in the private workspace if a replacement is needed.
        old=root/SUPPORT
        if old.exists():
            from uuid import uuid4
            old.rename(private/("previous-support-"+uuid4().hex))
        os.replace(stage/"scientific_report.pdf",root/PDF)
        os.replace(stage/"scientific_results.xlsx",root/EXCEL)
        supporting.rename(old)
        verify_publication(root)

def verify_publication(root):
    root=Path(root).resolve()
    manifest=json.loads((root/SUPPORT/"Reproducibility and Integrity"/"export_integrity.json").read_text(encoding="utf-8"))
    if manifest.get("schema")!=1 or manifest.get("scope")!="structured_publication":
        raise ValueError("Unknown publication manifest")
    hashes=manifest["sha256"]
    if not {PDF,EXCEL} <= set(hashes):
        raise ValueError("Missing required publication hashes")
    for name,digest in hashes.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or path.is_relative_to(root/PRIVATE) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError("Publication integrity failure")
    return True

def run_structured_batch(dataset_path,models,output,**kwargs):
    from .benchmark_output_lock import output_lock
    from .benchmark_model_major_batch import _run_model_major_batch
    root,private=_safe_root(output)
    with output_lock(private):
        state=_run_model_major_batch(dataset_path,models,private,**kwargs)
        _publish(root,private,state)
        return state

def regenerate(output):
    from .benchmark_output_lock import output_lock
    from .benchmark_export_integrity import verify_export_manifest
    root,private=_safe_root(output)
    with output_lock(private):
        if not all(verify_export_manifest(private).values()):
            raise ValueError("Source export integrity failure")
        state=json.loads((private/"matrix.json").read_text(encoding="utf-8"))
        _publish(root,private,state)

def publish_legacy(source,output):
    """Non-destructive offline publication from a verified legacy run.
    Private source stays in its original directory; no transcript is copied."""
    from .benchmark_output_lock import output_lock
    from .benchmark_export_integrity import verify_export_manifest
    source=Path(source).resolve()
    dest=Path(output).resolve()
    if source==dest or source.is_relative_to(dest) or dest.is_relative_to(source):
        raise ValueError("Choose a separate output folder")
    root,private=_safe_root(dest)
    with output_lock(source),output_lock(private):
        if not all(verify_export_manifest(source).values()):
            raise ValueError("Legacy export integrity failure")
        state=json.loads((source/"matrix.json").read_text(encoding="utf-8"))
        _publish(root,private,state)
        (private/"LEGACY SOURCE.txt").write_text(
            "Original checkpoint, transcripts and logs remain in the original legacy run folder. This publication is not a resumable copy. Keep the original folder restricted.",encoding="utf-8")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("--legacy-source")
    args=parser.parse_args()
    if args.legacy_source:
        publish_legacy(args.legacy_source,args.output)
    else:
        regenerate(args.output)
    print("Structured scientific reports generated and verified.")
