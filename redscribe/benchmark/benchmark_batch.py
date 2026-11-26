"""Researcher-paired sequential pilot with auditable per-recording outcomes.

Never auto-match source audio and references. A failed recording is retained in
both the batch manifest and flat CSV, even when no model started.
"""
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from uuid import uuid4
import csv
import os
import json
from redscribe.benchmark.benchmark_rescore import rescore

from benchmark_config import BenchmarkConfig
from benchmark_reference import sha256_file, verify_reference
from benchmark_pilot import run_single_pilot, _atomic_json
from benchmark_reporting import export_reporting
from benchmark_excel import export_excel


BATCH_COLUMNS = (
    "audio", "audio_sha256", "reference_sha256", "recording_status",
    "recording_error", "model_key", "status", "wer", "cer",
    "transcription_seconds", "rtf", "gpu_util_peak_percent",
    "gpu_memory_peak_mb", "error",
)


def _write_batch_results(directory, state):
    """Replace CSV atomically; keep a row for failed or unattempted audio."""
    target = directory / "batch_results.csv"
    temporary = target.with_name(target.name + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=BATCH_COLUMNS)
            writer.writeheader()
            for item in state["items"]:
                common = {
                    "audio": item["audio"],
                    "audio_sha256": item["audio_sha256"],
                    "reference_sha256": item["reference_sha256"],
                    "recording_status": item["status"],
                    "recording_error": item.get("error", ""),
                }
                if not item["model_results"]:
                    writer.writerow({
                        **common, "model_key": "", "status": item["status"],
                        "error": item.get("error", ""),
                    })
                else:
                    for key, record in item["model_results"].items():
                        writer.writerow({
                            **common,
                            "model_key": key,
                            **{field: record.get(field) for field in BATCH_COLUMNS
                               if field not in common and field != "model_key"},
                        })
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _checkpoint(directory, state):
    _atomic_json(directory / "batch_manifest.json", state)
    for name, exporter in (("CSV", _write_batch_results), ("reporting", export_reporting)):
        try:
            exporter(directory, state)
        except Exception as exc:
            state.setdefault("reporting_warnings", []).append(
                f"{name}: {type(exc).__name__}: {exc}")
            _atomic_json(directory / "batch_manifest.json", state)


def run_batch_pilot(pairs, models, output_root, *, language="ms", notify=None,
                    cancel=None, gpu_monitor=False, vad=False, osd=False, hf_token=None, resume_directory=None):
    """Run explicit audio/reference pairs, preserving failures and cancellation.

    Resume is recording-level; verified complete recordings are skipped.
    Every audio is re-hashed when its turn begins; a modified recording is
    rejected rather than compared against stale preflight metadata.
    """
    config = BenchmarkConfig(mode="batch", models=tuple(models))
    if language not in ("ms", "en", None):
        raise ValueError("Invalid language")
    pairs = tuple(pairs)
    if not pairs:
        raise ValueError("Batch contains no confirmed audio/reference pairs")
    if len({str(Path(a).resolve()) for a, _ in pairs}) != len(pairs):
        raise ValueError("Audio selected more than once")
    if len({str(Path(r).resolve()) for _, r in pairs}) != len(pairs):
        raise ValueError("Reference selected more than once")

    notify = notify or (lambda *_: None)
    if cancel is None:
        cancel = Event()

    preflight = []
    for audio, reference in pairs:
        audio = Path(audio).resolve()
        refpath = Path(reference).resolve()
        if not audio.is_file():
            raise FileNotFoundError(f"Audio missing: {audio.name}")
        approved = verify_reference(refpath)
        preflight.append((audio, refpath, sha256_file(audio),
                          approved["approved_text_sha256"]))

    directory = Path(output_root).resolve() / (
        "batch_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid4().hex[:8])
    if resume_directory is None:
        directory.mkdir(parents=True, exist_ok=False)

    state = {
        "schema_version": 3, "mode": "batch", "status": "running",
        "models": list(config.models), "language": language,
        "gpu_monitor": bool(gpu_monitor), "vad": bool(vad), "osd": bool(osd),
        "resume_supported": True,
        "items": [
            {"audio": p[0].name, "audio_sha256": p[2],
             "reference_manifest": p[1].name, "reference_sha256": p[3],
             "status": "pending", "error": "", "result_folder": None,
             "model_results": {}}
            for p in preflight
        ],
    }
    if resume_directory is not None:
        directory = Path(resume_directory).resolve()
        previous = json.loads((directory / 'batch_manifest.json').read_text(encoding='utf-8'))
        state = validate_resume(directory, previous, state, preflight)
    _checkpoint(directory, state)

    try:
        for index, (audio, ref, approved_audio_hash, approved_reference_hash) in enumerate(preflight):
            if cancel.is_set():
                state["status"] = "cancelled"
                break
            item = state["items"][index]
            if item["status"] == "completed":
                continue
            if item.get("result_folder"):
                item.setdefault("prior_result_folders", []).append(item["result_folder"])
            item.update(status="running", error="", result_folder=None, model_results={})
            _checkpoint(directory, state)
            notify("batch", f"Recording {index + 1}/{len(preflight)}: {audio.name}")
            try:
                # Defensive second check before launching any model weights.
                if not audio.is_file() or sha256_file(audio) != approved_audio_hash:
                    raise ValueError("Audio recording changed since batch preflight")
                if verify_reference(ref)['approved_text_sha256'] != approved_reference_hash:
                    raise ValueError('Ground truth changed since batch preflight')
                result_dir, result = run_single_pilot(
                    audio, ref, config.models, directory, language=language,
                    cancel=cancel, notify=notify, gpu_monitor=gpu_monitor,
                    vad=vad, osd=osd, hf_token=hf_token,
                    expected_audio_sha256=approved_audio_hash)
                item["status"] = result["status"]
                item["result_folder"] = result_dir.name
                item["model_results"] = result["model_results"]
                item["speech_analysis"] = result.get("speech_analysis")
                if result["status"] == "cancelled":
                    state["status"] = "cancelled"
                    break
            except Exception as exc:
                item["status"] = "failed"
                item["error"] = f"{type(exc).__name__}: {exc}"
                notify("warning", f"{audio.name}: {item['error']}")
            finally:
                _checkpoint(directory, state)
        else:
            state["status"] = (
                "completed_with_errors"
                if any(item["status"] != "completed" for item in state["items"])
                else "completed")
    except BaseException:
        state["status"] = "failed"
        raise
    finally:
        _checkpoint(directory, state)
        try:
            export_excel(directory, state)
        except Exception as excel_exc:
            # Spreadsheet output is secondary; retain valid CSV and manifest.
            state.setdefault("reporting_warnings", []).append(
                f"Excel: {type(excel_exc).__name__}: {excel_exc}")
            _atomic_json(directory / "batch_manifest.json", state)
            notify("warning", f"Excel summary unavailable: {excel_exc}")
        notify("batch_finished", str(directory))
    return directory, state


def validate_resume(directory, previous, requested, preflight):
    """Fail closed on changed inputs/settings or corrupt completed artifacts."""
    for key in ("schema_version", "models", "language", "gpu_monitor", "vad", "osd"):
        if previous.get(key) != requested.get(key):
            raise ValueError(f"Resume configuration mismatch: {key}")
    if len(previous["items"]) != len(requested["items"]):
        raise ValueError("Resume dataset count mismatch")
    for old, new, (_, ref, _, _) in zip(previous["items"], requested["items"], preflight):
        for key in ("audio", "audio_sha256", "reference_manifest", "reference_sha256"):
            if old.get(key) != new.get(key):
                raise ValueError(f"Resume pairing mismatch: {key}")
        if old["status"] == "completed":
            folder = (directory / old["result_folder"]).resolve()
            if folder.parent != directory.resolve():
                raise ValueError("Invalid resume artifact folder")
            manifest_path = folder / "manifest.json"
            run = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (run["audio_sha256"] != new["audio_sha256"] or run["selected_models"] != requested["models"]
                or run["language"] != requested["language"] or run["model_results"] != old["model_results"]):
                raise ValueError("Resume artifact metadata mismatch")
            report = rescore(manifest_path, ref)
            if len(report["results"]) != len(requested["models"]) or any(r["status"] != "verified" for r in report["results"]):
                raise ValueError("Completed recording failed resume integrity verification")
    previous["status"] = "running"
    previous["resume_count"] = previous.get("resume_count", 0) + 1
    return previous
