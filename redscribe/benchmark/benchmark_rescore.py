"""CPU-only offline verification of saved pilot predictions."""
import argparse
import json
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
from .benchmark_metrics import raw_wer, raw_cer
from .benchmark_reference import verify_reference

def checked_text(folder, filename, digest):
    path = (folder / filename).resolve()
    if path.parent != folder.resolve():
        raise ValueError("Invalid artifact path")
    data = path.read_bytes()
    if sha256(data).hexdigest() != digest:
        raise ValueError("Artifact hash mismatch")
    return data.decode("utf-8")

def rescore(run_manifest, reference_manifest, model_key=None):
    path = Path(run_manifest)
    run = json.loads(path.read_text(encoding="utf-8"))
    ref = verify_reference(reference_manifest)
    if run["reference_sha256"] != ref["approved_text_sha256"] or run["reference_id"] != ref["reference_id"]:
        raise ValueError("Reference does not match original run")
    reference = checked_text(Path(reference_manifest).parent, ref["scoring_text_file"], ref["approved_text_sha256"])
    rows = []
    models = run["model_results"]
    if model_key is not None and model_key not in models:
        raise ValueError("Unknown model")
    for key, row in models.items():
        if model_key is not None and key != model_key:
            continue
        if row["status"] != "completed":
            rows.append({"model_key": key, "status": "skipped", "original_status": row["status"]})
            continue
        try:
            prediction = checked_text(path.parent, row["prediction_file"], row["prediction_sha256"])
            if len(prediction.encode("utf-8")) != row["prediction_bytes"]:
                raise ValueError("Prediction byte count mismatch")
            w, c = raw_wer(reference, prediction), raw_cer(reference, prediction)
            expected = {"wer": w.rate, "cer": c.rate, "word_substitutions": w.substitutions,
                        "word_deletions": w.deletions, "word_insertions": w.insertions,
                        "char_substitutions": c.substitutions, "char_deletions": c.deletions,
                        "char_insertions": c.insertions, "reference_words": w.reference_units,
                        "reference_characters": c.reference_units}
            differences = {k: {"original": row.get(k), "recomputed": v} for k,v in expected.items() if row.get(k) != v}
            rows.append({"model_key": key, "status": "mismatch" if differences else "verified",
                         "wer": w.as_dict(), "cer": c.as_dict(), "differences": differences,
                         "prediction_sha256": row["prediction_sha256"]})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            rows.append({"model_key": key, "status": "unverifiable", "error": str(exc)})
    return {"created_utc": datetime.now(timezone.utc).isoformat(), "reference_sha256": ref["approved_text_sha256"],
            "run_manifest_sha256": sha256(path.read_bytes()).hexdigest(), "results": rows}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_manifest")
    parser.add_argument("reference_manifest")
    parser.add_argument("output")
    parser.add_argument("--model")
    args = parser.parse_args()
    report = rescore(args.run_manifest, args.reference_manifest, args.model)
    with Path(args.output).open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return int(not report["results"] or any(r["status"] != "verified" for r in report["results"]))

if __name__ == "__main__":
    raise SystemExit(main())
