"""Approved, immutable-by-convention local scoring references and audit hashes.

Artifacts live beside an explicitly chosen local output folder, never in GitHub.
Approval is manual; optional label removal affects only the scoring copy.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import json
import os
import tempfile


def sha256_file(path, chunk_bytes=1024 * 1024):
    digest = sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_bytes), b""):
            digest.update(chunk)
    return digest.hexdigest()


def approve_reference(source_path, approved_text, output_dir, *, reviewer_acknowledged=False,
                      expected_source_sha256=None, verification=None, label_removal_history=None):
    """Freeze a researcher-reviewed text file and metadata with exclusive filenames.

    Explicit approval is required. Never modifies the original DOCX. Resulting
    files should be treated as private researcher data and never committed.
    """
    if not reviewer_acknowledged:
        raise ValueError("Researcher approval is required")
    source = Path(source_path)
    if source.suffix.lower() != ".docx" or not source.is_file():
        raise ValueError("Source must be an existing DOCX")
    if not approved_text or not approved_text.strip():
        raise ValueError("Approved reference is empty")
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    reference_id = uuid4().hex
    text_path = destination / (reference_id + ".txt")
    manifest_path = destination / (reference_id + ".json")
    source_hash = sha256_file(source)
    if expected_source_sha256 is not None and source_hash != expected_source_sha256:
        raise ValueError("Original DOCX changed since extraction preview; reload and review again")
    verification = dict(verification or {})
    if verification:
        required = ("audio_verified", "coverage_verified", "speaker_labels_reviewed",
                    "non_speech_reviewed")
        if any(verification.get(field) is not True for field in required):
            raise ValueError("All reference verification checks must be confirmed")
    text_hash = sha256(approved_text.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": 2,
        "reference_id": reference_id,
        "approved_utc": datetime.now(timezone.utc).isoformat(),
        "source_filename": source.name,
        "source_path": str(source.resolve()),
        "source_sha256": source_hash,
        "approved_text_sha256": text_hash,
        "scoring_text_file": text_path.name,
        "approval": "researcher_confirmed",
        "extraction_policy": ("optional_rule_based_label_removal_then_manual_review" if label_removal_history else "manual_review_no_automatic_label_removal"),
        "speaker_label_removal_history": list(label_removal_history or []),
        "verification": verification,
        "normalisation_policy": "raw_unmodified_no_automatic_normalisation",
        "scoring_scope": "researcher_verified_audio_span" if verification else "unspecified",
    }
    # Creation is exclusive; failures must not erase pre-existing references.
    with text_path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(approved_text)
    try:
        with manifest_path.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except BaseException:
        text_path.unlink(missing_ok=True)
        raise
    return manifest_path, text_path, manifest


def verify_reference(manifest_path):
    manifest_path = Path(manifest_path)
    with manifest_path.open(encoding="utf-8") as f:
        info = json.load(f)
    reference = (manifest_path.parent / info["scoring_text_file"]).resolve()
    if reference.parent != manifest_path.parent.resolve():
        raise ValueError("Invalid scoring reference path in manifest")
    if not reference.is_file() or sha256_file(reference) != info["approved_text_sha256"]:
        raise ValueError("Frozen scoring reference missing or modified")
    # Older manifests do not include a source path; callers should not treat
    # them as provenance-verified until re-approved with the current version.
    source_path = info.get("source_path")
    if source_path:
        source = Path(source_path)
        if not source.is_file() or sha256_file(source) != info["source_sha256"]:
            raise ValueError("Original DOCX source is missing or has changed since approval")
    else:
        raise ValueError("Legacy reference manifest lacks source integrity information; re-approve DOCX")
    return info
