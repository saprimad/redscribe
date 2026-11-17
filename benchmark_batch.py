"""Explicitly paired, sequential short-audio benchmark with durable batch checkpoints."""
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from uuid import uuid4
import csv

from benchmark_config import BenchmarkConfig
from benchmark_reference import sha256_file, verify_reference
from benchmark_pilot import run_single_pilot, _atomic_json, PilotCancelled


def run_batch_pilot(pairs, models, output_root, *, language="ms", notify=None,
                    cancel=None, gpu_monitor=False, vad=False, osd=False, hf_token=None):
    """Run validated, researcher-paired audio/reference items in selection order.

    Each file is a separate run with per-model CSV and atomic JSON. No
    unreviewed automatic filename or speaker-label matching is performed.
    """
    config = BenchmarkConfig(mode="batch", models=tuple(models))
    pairs = tuple(pairs)
    if not pairs:
        raise ValueError("Batch contains no confirmed audio/reference pairs")
    if len({str(Path(a).resolve()) for a, _ in pairs}) != len(pairs):
        raise ValueError("Audio selected more than once")
    if len({str(Path(r).resolve()) for _, r in pairs}) != len(pairs):
        raise ValueError("Reference selected more than once")
    notify = notify or (lambda *_: None)
    cancel = cancel or Event()
    preflight = []
    # Validate ALL pairs before any model weights are loaded.
    for audio, reference in pairs:
        audio = Path(audio).resolve()
        refpath = Path(reference).resolve()
        if not audio.is_file():
            raise FileNotFoundError(f"Audio missing: {audio.name}")
        approved = verify_reference(refpath)
        preflight.append((audio, refpath, sha256_file(audio), approved["approved_text_sha256"]))
    directory = Path(output_root).resolve() / (
        "batch_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    state = {"schema_version": 1, "mode": "batch", "status": "running",
             "models": list(config.models), "language": language,
             "gpu_monitor": gpu_monitor, "vad": vad, "osd": osd,
             "items": [{"audio": p[0].name, "audio_sha256": p[2],
                        "reference_manifest": p[1].name, "reference_sha256": p[3],
                        "status": "pending", "result_folder": None,
                        "model_results": {}} for p in preflight]}
    _atomic_json(directory / "batch_manifest.json", state)
    try:
        for index, (audio, ref, _, _) in enumerate(preflight):
            if cancel.is_set():
                state["status"] = "cancelled"
                break
            item = state["items"][index]
            item["status"] = "running"
            _atomic_json(directory / "batch_manifest.json", state)
            notify("batch", f"Recording {index+1}/{len(preflight)}: {audio.name}")
            try:
                result_dir, result = run_single_pilot(
                    audio, ref, config.models, directory, language=language,
                    cancel=cancel, notify=notify, gpu_monitor=gpu_monitor,
                    vad=vad, osd=osd, hf_token=hf_token)
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
                _atomic_json(directory / "batch_manifest.json", state)
        else:
            state["status"] = "completed_with_errors" if any(
                entry["status"] != "completed" for entry in state["items"]) else "completed"
    finally:
        # One flat CSV for quick per-audio/per-model inspection; other reports
        # remain within each original per-file experiment folder.
        with (directory / "batch_results.csv").open(
                "w", newline="", encoding="utf-8-sig") as stream:
            columns = ["audio", "audio_sha256", "reference_sha256",
                       "model_key", "status", "wer", "cer", "transcription_seconds",
                       "rtf", "gpu_util_peak_percent", "gpu_memory_peak_mb",
                       "error"]
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for item in state["items"]:
                for key, record in item["model_results"].items():
                    writer.writerow({
                        "audio": item["audio"], "audio_sha256": item["audio_sha256"],
                        "reference_sha256": item["reference_sha256"],
                        "model_key": key,
                        **{c: record.get(c) for c in columns if c not in
                           ("audio", "audio_sha256", "reference_sha256", "model_key")}})
        _atomic_json(directory / "batch_manifest.json", state)
    notify("batch_finished", str(directory))
    return directory, state
