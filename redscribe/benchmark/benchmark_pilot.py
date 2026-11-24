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
import warnings

from benchmark_config import BenchmarkConfig
from benchmark_metrics import raw_wer, raw_cer
from benchmark_reporting import export_reporting
from benchmark_excel import export_excel
from benchmark_reference import sha256_file, verify_reference
from model_options import ASR_MODEL_LABELS, preflight_model
from asr_backends import EXTRA_MODELS, LocalASR

MAX_PILOT_SECONDS = 180
FIELDS = (
    "model_key", "model", "status", "wer", "cer", "substitutions",
    "deletions", "insertions", "reference_words", "reference_characters",
    "word_substitutions", "word_deletions", "word_insertions",
    "char_substitutions", "char_deletions", "char_insertions",
    "loading_seconds", "transcription_seconds", "rtf", "audio_seconds",
    "device", "precision", "timing_note", "error",
    "prediction_file", "prediction_sha256", "prediction_bytes",
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


def _write_results_csv(folder, manifest):
    """Write current model statuses using atomic file replacement."""
    destination = folder / "results.csv"
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(manifest["model_results"].values())
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _persist_prediction(folder, name, transcript):
    """Freeze exact scoring input as UTF-8 bytes, without newline conversion."""
    payload = transcript.encode("utf-8")
    path = folder / (name + ".txt")
    with path.open("xb") as stream:
        stream.write(payload)
    saved = path.read_bytes()
    if saved != payload:
        raise ValueError("Prediction persistence verification failed")
    return saved.decode("utf-8"), {
        "prediction_file": path.name,
        "prediction_sha256": sha256(saved).hexdigest(),
        "prediction_bytes": len(saved),
    }


def _whisper_model(key):
    # Reuse existing Faster-Whisper loading strategy, only when invoked.
    from redscribe_gpu import create_whisper_model
    return create_whisper_model(key)


def _cleanup(model):
    """Best-effort teardown; cleanup must not erase a valid ASR result."""
    try:
        if model is not None and hasattr(model, "close"):
            model.close()
    except Exception as exc:
        warnings.warn(f"ASR model cleanup warning: {type(exc).__name__}", RuntimeWarning)
    finally:
        del model
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:
            warnings.warn(f"CUDA cache cleanup warning: {type(exc).__name__}", RuntimeWarning)


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
                     gpu_monitor=False, vad=False, osd=False, hf_token=None,
                     expected_audio_sha256=None):
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
    if expected_audio_sha256 is not None and audio_hash != expected_audio_sha256:
        raise ValueError("Audio recording changed since batch preflight")
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
        "reference_scoring_scope": ref.get("scoring_scope", "unspecified"),
        "reference_verification": ref.get("verification", {}),
        "selected_models": list(config.models), "language": language,
        "scoring": "raw verbatim WER / raw Unicode-codepoint CER; all spoken fillers retained; no normalisation",
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
                monitoring = None
                if gpu_monitor:
                    try:
                        from benchmark_resources import ResourceMonitor
                        candidate = ResourceMonitor()
                        candidate.__enter__()
                        monitoring = candidate
                    except Exception as monitor_exc:
                        notify("warning", f"{name}: resource monitor start unavailable: {monitor_exc}")
                try:
                    transcript, loading, transcription, device, precision, note = _transcribe(
                        key, audio, language, stopped)
                finally:
                    if monitoring is not None:
                        try:
                            monitoring.__exit__(None, None, None)
                        except Exception as monitor_exc:
                            notify("warning", f"{name}: resource monitor stop unavailable: {monitor_exc}")
                if monitoring is not None:
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
                safe_name = f"{i:02d}_{key.replace(' ', '_').replace('/', '_')}"
                transcript, prediction_metadata = _persist_prediction(
                    results_folder, safe_name, transcript)
                row.update(prediction_metadata)
                word = raw_wer(reference, transcript)
                char = raw_cer(reference, transcript)
                row.update(status="completed", wer=word.rate, cer=char.rate,
                           substitutions=word.substitutions, deletions=word.deletions,
                           insertions=word.insertions,
                           word_substitutions=word.substitutions,
                           word_deletions=word.deletions,
                           word_insertions=word.insertions,
                           char_substitutions=char.substitutions,
                           char_deletions=char.deletions,
                           char_insertions=char.insertions,
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
                _write_results_csv(results_folder, manifest)
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
        # Make unattempted models visible instead of omitting them from CSV.
        for key in config.models:
            if key not in manifest["model_results"]:
                pending = {field: None for field in FIELDS}
                pending.update(
                    model_key=key, model=ASR_MODEL_LABELS[key], status="not_run",
                    audio_seconds=round(seconds, 4), timing_note="",
                    error="Run cancelled before model execution" if manifest["status"] == "cancelled"
                    else "Run stopped before model execution",
                )
                manifest["model_results"][key] = pending
        _atomic_json(results_folder / "manifest.json", manifest)
        _write_results_csv(results_folder, manifest)
        try:
            reporting_state = {
                "models": list(config.models),
                "items": [{
                    "audio": audio.name,
                    "audio_sha256": audio_hash,
                    "status": manifest["status"],
                    "error": manifest.get("error", ""),
                    "model_results": manifest["model_results"],
                }],
            }
            export_reporting(results_folder, reporting_state)
            export_excel(results_folder, reporting_state)
        except Exception as report_exc:
            # A secondary report must not invalidate a valid frozen result.
            notify("warning", f"Summary reporting unavailable: {report_exc}")
        notify("finished", str(results_folder))
    return results_folder, manifest
