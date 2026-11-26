"""Local researcher-approved dataset pairing manifest."""
import json
from pathlib import Path
from datetime import datetime, timezone
from .benchmark_reference import sha256_file, verify_reference

def inspect_pairs(pairs):
    rows = []
    ids, audio_hashes, reference_hashes = set(), set(), set()
    for pair in pairs:
        pid = pair["participant_id"].strip()
        if not pid or pid.casefold() in ids:
            raise ValueError("Missing or duplicate participant ID")
        audio = Path(pair["audio"]).resolve()
        refpath = Path(pair["reference_manifest"]).resolve()
        ref = verify_reference(refpath)
        ah = sha256_file(audio)
        rh = ref["source_sha256"]
        if ah in audio_hashes or rh in reference_hashes:
            raise ValueError("Duplicate audio or source DOCX content")
        ids.add(pid.casefold())
        audio_hashes.add(ah)
        reference_hashes.add(rh)
        rows.append({"participant_id": pid, "audio": str(audio), "audio_sha256": ah,
                     "reference_manifest": str(refpath), "reference_manifest_sha256": sha256_file(refpath),
                     "reference_id": ref["reference_id"], "reference_source_sha256": rh,
                     "reference_sha256": ref["approved_text_sha256"]})
    if not rows:
        raise ValueError("Empty dataset")
    return rows

def approve_dataset(pairs, output, *, researcher_acknowledged=False, expected_count=None):
    if not researcher_acknowledged:
        raise ValueError("Explicit researcher pairing approval required")
    rows = inspect_pairs(pairs)
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError("Dataset count mismatch")
    manifest = {"schema_version": 1, "approved_utc": datetime.now(timezone.utc).isoformat(),
                "approval": "researcher_confirmed", "count": len(rows), "pairs": rows}
    with Path(output).open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
    return manifest

def verify_dataset(path):
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1 or manifest["approval"] != "researcher_confirmed":
        raise ValueError("Dataset is not approved")
    rows = inspect_pairs(manifest["pairs"])
    if rows != manifest["pairs"] or len(rows) != manifest["count"]:
        raise ValueError("Dataset integrity mismatch")
    return manifest
