"""Benchmark model-selection contract. No model loading on import."""
from dataclasses import dataclass

CORE_MODELS = (
    "large-v3", "turbo", "Mesolitica Whisper v3",
    "Mesolitica XLS-R 300M", "Meta MMS 1B (Malay)",
    "Qwen3-ASR 1.7B", "BuzzASR Malay",
)
OPTIONAL_MODELS = ("medium", "small", "base", "tiny")
ALL_MODELS = CORE_MODELS + OPTIONAL_MODELS
BENCHMARK_WARNING = (
    "Benchmarking can take substantial time and consume GPU/CPU resources, "
    "disk space and power. Keep RedScribe running until completion."
)

@dataclass(frozen=True)
class BenchmarkConfig:
    mode: str = "single"
    models: tuple[str, ...] = CORE_MODELS

    def __post_init__(self):
        if self.mode not in ("single", "batch"):
            raise ValueError("Expected single or batch mode")
        if not self.models:
            raise ValueError("Select at least one model")
        if len(set(self.models)) != len(self.models):
            raise ValueError("Duplicate model selection")
        unknown = set(self.models) - set(ALL_MODELS)
        if unknown:
            raise ValueError("Unknown model keys: " + ", ".join(sorted(unknown)))

def ordered_selection(keys):
    keys = tuple(keys)
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate model selection")
    unknown = set(keys) - set(ALL_MODELS)
    if unknown:
        raise ValueError("Unknown model keys: " + ", ".join(sorted(unknown)))
    return tuple(k for k in ALL_MODELS if k in keys)
