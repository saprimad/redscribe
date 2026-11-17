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

from benchmark_config import BenchmarkConfig
from benchmark_reference import sha256_file, verify_reference
from benchmark_pilot import run_single_pilot, _atomic_json


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
    _write_batch_results(directory, state)


def run_batch_pilot(pairs, models, output_root, *, language="ms", notify=None,
                    cancel=None, gpu_monitor=False, vad=False, osd=False, hf_token=None):
    """Run explicit audio/reference pairs, preserving failures and cancellation.

    Checkpointing is durable but **resume is not implemented**.
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
    directory.mkdir(parents=True, exist_ok=False)

    state = {
        "schema_version": 2, "mode": "batch", "status": "running",
        "models": list(config.models), "language": language,
        "gpu_monitor": bool(gpu_monitor), "vad": bool(vad), "osd": bool(osd),
        "resume_supported": False,
        "items": [
            {"audio": p[0].name, "audio_sha256": p[2],
             "reference_manifest": p[1].name, "reference_sha256": p[3],
             "status": "pending", "error": "", "result_folder": None,
             "model_results": {}}
            for p in preflight
        ],
    }
    _checkpoint(directory, state)

    try:
        for index, (audio, ref, approved_audio_hash, _) in enumerate(preflight):
            if cancel.is_set():
                state["status"] = "cancelled"
                break
            item = state["items"][index]
            item["status"] = "running"
            _checkpoint(directory, state)
            notify("batch", f"Recording {index + 1}/{len(preflight)}: {audio.name}")
            try:
                # Defensive second check before launching any model weights.
                if not audio.is_file() or sha256_file(audio) != approved_audio_hash:
                    raise ValueError("Audio recording changed since batch preflight")
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
        notify("batch_finished", str(directory))
    return directory, state
