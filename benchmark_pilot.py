"""Short-audio experimental ASR benchmark runner, sequential by model.

The normal transcription workflow is not modified. Optional observational
pyannote overlap analysis can perform diarisation, separately from scoring.
Only raw WER/CER is calculated; approved normalisation remains on HOLD.
"""
from datetime import datetime, timezone
from pathlib import Path
from hashlib import sha256
from uuid import uuid4
import csv
import gc
import json
import time
import traceback

from benchmark_config import BenchmarkConfig
from benchmark_metrics import raw_wer, raw_cer
from benchmark_reference import sha256_file, verify_reference
from model_options import ASR_MODEL_LABELS, preflight_model
from asr_backends import EXTRA_MODELS, LocalASR

MAX_PILOT_SECONDS = 180
FIELDS = (
    "model_key", "model", "status", "wer", "cer", "substitutions",
    "deletions", "insertions", "reference_words", "reference_characters",
    "loading_seconds", "transcription_seconds", "rtf", "audio_seconds",
    "device", "precision", "timing_note", "error",
    "gpu_util_peak_percent", "gpu_memory_peak_mb", "gpu_temp_peak_c",
    "cpu_peak_percent", "system_ram_peak_mb",
)


class PilotCancelled(Exception):
    pass


def _atomic_json(path, value):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
                    + "\n", encoding="utf-8")
    temp.replace(path)


def _whisper_model(key):
    # Reuse existing Faster-Whisper loading strategy, only when invoked.
    from redscribe_gpu import create_whisper_model
    return create_whisper_model(key)


def _cleanup(model):
    try:
        if model is not None and hasattr(model, "close"):
            model.close()
    finally:
        del model
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except (ImportError, RuntimeError):
            pass


def _decode_duration(path):
    from faster_whisper.audio import decode_audio
    waveform = decode_audio(str(path), sampling_rate=16000)
    seconds = len(waveform) / 16000
    if not 0 < seconds <= MAX_PILOT_SECONDS:
        raise ValueError(
            f"Pilot audio must be between 0 and {MAX_PILOT_SECONDS} seconds; got {seconds:.1f}s")
    return seconds


def _transcribe(key, audio_path, language, stopped):
    model = None
    try:
        stopped()
        if key in EXTRA_MODELS:
            # Optional ASR uses lazy model load at segment iteration.
            model = LocalASR(key, language=language, check_stop=stopped)
            load_started = time.perf_counter()
            # Preflight is intentionally before timing the transcription, but
            # optional adapters perform lazy loading; separate loading time is
            # unavailable without refactoring their internal generator.
            segments, info = model.transcribe(str(audio_path))
            transcription_started = time.perf_counter()
            text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
            elapsed = time.perf_counter() - transcription_started
            return text, None, elapsed, "cuda", "float16", "lazy model load included in inference"
        load_started = time.perf_counter()
        model, device, precision = _whisper_model(key)
        loading = time.perf_counter() - load_started
        stopped()
        transcription_started = time.perf_counter()
        segments, info = model.transcribe(str(audio_path), language=language, task="transcribe",
                                          beam_size=5, vad_filter=False)
        text = " ".join(s.text.strip() for s in segments if s.text.strip())
        elapsed = time.perf_counter() - transcription_started
        stopped()
        return text, loading, elapsed, device, precision, ""
    finally:
        _cleanup(model)


def run_single_pilot(audio_path, reference_manifest, selected_models, output_root,
                     *, language="ms", notify=None, cancel=None,
                     gpu_monitor=False, vad=False, osd=False, hf_token=None):
    """Sequential pilot; each result saved as JSON and transcript TXT.

    notify(event, detail): worker-thread callback; caller marshals into GUI.
    cancel: threading.Event. Cancel is checked between models/segments.
    """
    config = BenchmarkConfig(mode="single", models=tuple(selected_models))
    if language not in ("ms", "en", None):
        raise ValueError("Invalid language")
    if cancel is None:
        from threading import Event
        cancel = Event()
    notify = notify or (lambda event, detail: None)

    audio = Path(audio_path).resolve()
    if not audio.is_file():
        raise FileNotFoundError("Audio file not found")
    refpath = Path(reference_manifest).resolve()
    ref = verify_reference(refpath)
    reference_path = refpath.parent / ref["scoring_text_file"]
    reference = reference_path.read_text(encoding="utf-8")
    if not reference.strip():
        raise ValueError("Approved reference is empty")
    seconds = _decode_duration(audio)
    audio_hash = sha256_file(audio)
    results_folder = Path(output_root).resolve() / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8])
    results_folder.mkdir(parents=True, exist_ok=False)

    manifest = {
        "pilot": True, "status": "running", "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_audio": audio.name, "audio_sha256": audio_hash,
        "audio_seconds": seconds, "reference_id": ref["reference_id"],
        "reference_sha256": ref["approved_text_sha256"],
        "reference_source_sha256": ref["source_sha256"],
        "selected_models": list(config.models), "language": language,
        "scoring": "raw whitespace WER / raw Unicode-codepoint CER; no normalisation",
        "max_pilot_seconds": MAX_PILOT_SECONDS,
        "diarization": "disabled",
        "notes": "Exploratory test only; model-specific decoding and compute fallback may differ.",
        "model_results": {},
    }
    manifest["analysis_options"] = {"gpu_monitor": bool(gpu_monitor),
                                    "silero_vad": bool(vad), "pyannote_osd": bool(osd)}
    _atomic_json(results_folder / "manifest.json", manifest)
    notify("start", f"Pilot: {len(config.models)} models, {seconds:.1f}s audio")

    def stopped():
        if cancel.is_set():
            raise PilotCancelled("Cancelled by researcher")

    try:
        if vad or osd:
            from benchmark_speech import analyse_audio
            notify("analysis", "Running optional VAD/OSD analysis...")
            manifest["speech_analysis"] = analyse_audio(
                audio, seconds, vad=vad, osd=osd, hf_token=hf_token, notify=notify)
            _atomic_json(results_folder / "manifest.json", manifest)
        for i, key in enumerate(config.models, 1):
            stopped()
            name = ASR_MODEL_LABELS[key]
            notify("model", f"{i}/{len(config.models)}: {name}")
            row = {field: None for field in FIELDS}
            row.update(model_key=key, model=name, status="failed",
                       audio_seconds=round(seconds, 4), timing_note="", error="")
            try:
                # Optional models may reject unsupported language or unavailable CUDA.
                preflight_model(key, language)
                from contextlib import nullcontext
                monitoring = nullcontext()
                resource_monitor_active = False
                if gpu_monitor:
                    try:
                        from benchmark_resources import ResourceMonitor
                        monitoring = ResourceMonitor()
                        resource_monitor_active = True
                    except Exception as monitor_exc:
                        notify("warning", f"{name}: resource monitoring unavailable: {monitor_exc}")
                with monitoring:
                    transcript, loading, transcription, device, precision, note = _transcribe(
                        key, audio, language, stopped)
                if resource_monitor_active:
                    try:
                        resource_summary = monitoring.summary()
                        row.update(
                            gpu_util_peak_percent=resource_summary.get("gpu_util_percent_peak"),
                            gpu_memory_peak_mb=resource_summary.get("gpu_memory_used_mb_peak"),
                            gpu_temp_peak_c=resource_summary.get("gpu_temperature_c_peak"),
                            cpu_peak_percent=resource_summary.get("cpu_percent_peak"),
                            system_ram_peak_mb=resource_summary.get("ram_used_mb_peak"),
                        )
                        safe_monitor_name = f"{i:02d}_{key.replace(' ', '_').replace('/', '_')}"
                        monitoring.save_csv(results_folder / (safe_monitor_name + "_resources.csv"))
                    except Exception as monitor_exc:
                        notify("warning", f"{name}: monitor results unavailable: {monitor_exc}")
                word = raw_wer(reference, transcript)
                char = raw_cer(reference, transcript)
                safe_name = f"{i:02d}_{key.replace(' ', '_').replace('/', '_')}"
                (results_folder / (safe_name + ".txt")).write_text(
                    transcript + "\n", encoding="utf-8")
                row.update(status="completed", wer=word.rate, cer=char.rate,
                           substitutions=word.substitutions, deletions=word.deletions,
                           insertions=word.insertions,
                           reference_words=word.reference_units,
                           reference_characters=char.reference_units,
                           loading_seconds=round(loading, 4) if loading is not None else None,
                           transcription_seconds=round(transcription, 4),
                           rtf=round(transcription / seconds, 5),
                           device=device, precision=precision, timing_note=note, error="")
            except PilotCancelled:
                row.update(status="cancelled", error="Cancelled by researcher")
                raise
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
                notify("warning", f"{name}: {row['error']}")
            finally:
                manifest["model_results"][key] = row
                _atomic_json(results_folder / "manifest.json", manifest)
                with (results_folder / "results.csv").open(
                        "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDS)
                    writer.writeheader()
                    writer.writerows(manifest["model_results"].values())
            notify("progress", f"{i}/{len(config.models)} completed; results saved")
        manifest["status"] = (
            "completed" if all(row.get("status") == "completed"
                               for row in manifest["model_results"].values())
            else "completed_with_errors"
        )
    except PilotCancelled:
        manifest["status"] = "cancelled"
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        _atomic_json(results_folder / "manifest.json", manifest)
        notify("finished", str(results_folder))
    return results_folder, manifest
