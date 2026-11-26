"""Local export integrity manifest; detects subsequent byte changes."""
import json
from pathlib import Path
from .benchmark_reference import sha256_file

FIGURES=("corpus_accuracy","wer_distribution","cer_distribution","accuracy_speed","participant_wer_heatmap")
TABLES=("matrix.json","model_summary.csv","recording_results.csv","efficiency_summary.csv","scientific_results.xlsx")

def write_export_manifest(directory):
    directory=Path(directory)
    files=list(TABLES)+[n+"."+ext for n in FIGURES for ext in ("svg","png")]
    hashes={n:sha256_file(directory/n) for n in files if (directory/n).is_file()}
    if not all(n in hashes for n in TABLES):
        raise ValueError("Missing required reporting artefacts")
    state=json.loads((directory/"matrix.json").read_text(encoding="utf-8"))
    manifest={"schema":1,"scoring_engine":state["identity"].get("scoring_engine"),
              "rapidfuzz_version":state["identity"].get("rapidfuzz_version"),
              "sha256":hashes}
    path=directory/"export_integrity.json"
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    temp.replace(path)
    return manifest

def verify_export_manifest(directory):
    directory=Path(directory)
    manifest=json.loads((directory/"export_integrity.json").read_text(encoding="utf-8"))
    if manifest["schema"]!=1:
        raise ValueError("Unknown export integrity schema")
    allowed=set(TABLES)|{n+"."+ext for n in FIGURES for ext in ("svg","png")}
    if not set(TABLES)<=set(manifest["sha256"])<=allowed:
        raise ValueError("Invalid export inventory")
    return {n: (directory/n).is_file() and sha256_file(directory/n)==h
            for n,h in manifest["sha256"].items()}
