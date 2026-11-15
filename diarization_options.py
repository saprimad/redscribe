"""Local pyannote pipeline choices; no imports or downloads of model runtimes."""
DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"
DIARIZATION_MODELS = {
    "Community-1 (Recommended)": DEFAULT_DIARIZATION_MODEL,
    "3.1 (Legacy / comparison)": "pyannote/speaker-diarization-3.1",
}
DEFAULT_DIARIZATION_CHOICE = next(iter(DIARIZATION_MODELS))


def describe_diarization(choice):
    if DIARIZATION_MODELS[choice] == DEFAULT_DIARIZATION_MODEL:
        return "Recommended local pipeline. Accept Community-1 conditions on Hugging Face. Automatic or expected speaker count."
    return ("Older local pipeline for comparison. Accept both speaker-diarization-3.1 and segmentation-3.0 conditions "
            "on Hugging Face. Uses the same token; runtime compatibility still needs testing.")


class DiarizationDependencyError(RuntimeError):
    """The local runtime must be repaired before model download can start."""


def load_pyannote_pipeline_class():
    """Check imports without downloading models or modifying installed packages."""
    import importlib
    import sys
    try:
        return importlib.import_module("pyannote.audio").Pipeline
    except ModuleNotFoundError as exc:
        if exc.name in ("pyannote", "pyannote.audio"):
            raise DiarizationDependencyError(
                "pyannote.audio is not installed in the active Python environment.\n"
                "Install it with: python -m pip install pyannote.audio\n"
                f"Python interpreter: {sys.executable}\nNo diarisation model was downloaded."
            ) from exc
        error = exc
    except Exception as exc:
        error = exc
    detail = str(error)
    if "_ExtendedAttributes" in detail and "opentelemetry" in detail.lower():
        repair = (
            "OpenTelemetry dependencies are incompatible; this is not a missing pyannote model.\n"
            "In the RedScribe environment, run:\n"
            "python -m pip install --upgrade opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp\n"
            "python -m pip check\nRestart RedScribe after repairing the environment."
        )
    else:
        repair = (
            "A pyannote.audio dependency could not be imported.\n"
            "Check the active environment with: python -m pip check\n"
            "Install missing dependencies in the RedScribe environment and restart the app."
        )
    raise DiarizationDependencyError(
        f"{repair}\nPython interpreter: {sys.executable}\n"
        "No diarisation model was downloaded. Dependency repair is separate from automatic model downloads."
    ) from error
