"""Desktop model descriptions, stable output folders and no-download checks."""
import importlib
from pathlib import Path

from asr_backends import EXTRA_MODELS, validate_language

LEGACY_MODELS = ("large-v3", "turbo", "medium", "small", "base")
MODEL_FOLDERS = {
    **{name: f"whisper_{name.replace('-', '_')}" for name in LEGACY_MODELS},
    "Mesolitica Whisper v3": "mesolitica_whisper_turbo_v3",
    "Mesolitica XLS-R 300M": "mesolitica_xlsr_300m",
    "Meta MMS 1B (Malay)": "meta_mms_1b_malay",
    "Qwen3-ASR 1.7B": "qwen3_asr_1_7b",
    "BuzzASR Malay": "buzzasr_malay",
}


def describe_model(selected):
    if selected in LEGACY_MODELS:
        return ("Multilingual / Auto detect. CUDA FP16; CPU INT8 fallback.\n"
                "Model segment timestamps; sentence times estimated.")
    spec = EXTRA_MODELS[selected]
    language = ("Fixed Malay adapter (zsm)" if spec.engine == "mms" else
                "Fixed Malay / mixed decoder" if spec.engine == "ctc" else
                "Malay-specific" if spec.default_language == "ms" else "Auto detect / Malay / English")
    return f"{language}. CUDA FP16 required.\nApproximate chunk timestamps. First use downloads model."


def model_output_folder(base_directory, period, selected):
    """Known stable names keep both exports for each model together."""
    return str(Path(base_directory) / period / MODEL_FOLDERS[selected])


class ModelPreflightError(RuntimeError):
    """Actionable runtime failure, before downloads, diarisation or exports."""


def preflight_model(selected, language=None):
    if selected in LEGACY_MODELS:
        # Faster-Whisper is already imported by the desktop; retain CPU support.
        return "Faster-Whisper runtime ready; CUDA FP16 / CPU INT8 fallback remains enabled."
    if selected not in EXTRA_MODELS:
        raise ModelPreflightError("Unknown ASR model. Select a model from the dropdown.")
    spec = EXTRA_MODELS[selected]
    try:
        validate_language(spec, language)
    except ValueError as exc:
        raise ModelPreflightError(str(exc)) from exc
    try:
        torch = importlib.import_module("torch")
    except ImportError as exc:
        raise ModelPreflightError("PyTorch is missing. Install CUDA-enabled PyTorch in the RedScribe virtual environment first.") from exc
    if not torch.cuda.is_available():
        raise ModelPreflightError("This model requires an NVIDIA CUDA GPU with FP16. CUDA is unavailable in this Python environment. Check CUDA-enabled PyTorch; no model was downloaded or diarisation started.")
    runtime = "qwen_asr" if spec.engine == "qwen" else "transformers"
    requirements = "requirements-qwen.txt" if spec.engine == "qwen" else "requirements-models.txt"
    required_classes = ("Qwen3ASRModel",) if spec.engine == "qwen" else (
        "AutoProcessor", "WhisperForConditionalGeneration" if spec.engine == "whisper" else "AutoModelForCTC")
    try:
        module = importlib.import_module(runtime)
        for name in required_classes:
            getattr(module, name)
    except Exception as exc:
        # Do not expose arbitrary dependency exception contents (tokens/URLs).
        raise ModelPreflightError(
            f"The optional {runtime} runtime is missing or cannot load.\n\n"
            f"In the active RedScribe environment, run:\npython -m pip install -r {requirements}\n"
            "python -m pip check\n\nNo model was downloaded or diarisation started."
        ) from exc
    return "Runtime and CUDA availability checks passed. FP16 inference will be checked when the model runs."
