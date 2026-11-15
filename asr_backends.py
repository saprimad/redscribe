"""Optional local ASR adapters. Importing this module never downloads weights.

Desktop chunk/turn timing is approximate, not alignment or a scored benchmark.
The original Faster-Whisper route remains in redscribe_gpu.py.
"""
from dataclasses import dataclass
import math
from types import SimpleNamespace


@dataclass(frozen=True)
class ModelSpec:
    checkpoint: str
    engine: str
    default_language: str | None = None


EXTRA_MODELS = {
    "Mesolitica Whisper v3": ModelSpec("mesolitica/Malaysian-whisper-large-v3-turbo-v3", "whisper"),
    "Mesolitica XLS-R 300M": ModelSpec("mesolitica/wav2vec2-xls-r-300m-mixed", "ctc", "ms"),
    "Meta MMS 1B (Malay)": ModelSpec("facebook/mms-1b-all", "mms", "ms"),
    "Qwen3-ASR 1.7B": ModelSpec("Qwen/Qwen3-ASR-1.7B", "qwen"),
    "BuzzASR Malay": ModelSpec("BuzzASR/malay", "whisper", "ms"),
}
CHUNK_SECONDS = 30.0
TIMING_NOTE = ("Approximate audio chunk/diarisation-turn boundaries; sentence times are distributed estimates, "
               "not model alignment. Segment-based speech/silence statistics are not measured speech activity.")


def validate_language(spec, language):
    # XLS-R has a fixed mixed-language decoder; MMS here deliberately uses Malay.
    if spec.default_language and language not in (None, "ms"):
        raise ValueError("This model option is configured for Bahasa Melayu. Select Bahasa Melayu or Auto detect.")


def chunk_ranges(duration, turns=(), max_seconds=CHUNK_SECONDS):
    """Cover the entire recording once, splitting at every diarisation boundary.

    Keep gaps so unrecognised speech is not discarded. No overlap/duplication,
    even for overlapping speaker turns. Splitting at boundaries limits mixed
    speaker chunks; overlap identity still needs human verification.
    """
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("The recording contains no decodable audio.")
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("Chunk size must be positive.")
    boundaries = {0.0, duration}
    for turn in turns:
        for field in ("start", "end"):
            point = float(turn[field])
            if math.isfinite(point) and 0 < point < duration:
                boundaries.add(point)
    boundaries = sorted(boundaries)
    for start, end in zip(boundaries, boundaries[1:]):
        count = max(1, math.ceil((end - start) / max_seconds))
        for index in range(count):
            yield start + index * (end - start) / count, start + (index + 1) * (end - start) / count


class LocalASR:
    """Lazy CUDA FP16, batch-one inference after pyannote has released its model."""
    timing_note = TIMING_NOTE

    def __init__(self, selected, language=None, check_stop=lambda: None):
        self.spec = EXTRA_MODELS[selected]
        validate_language(self.spec, language)
        self.language = language or self.spec.default_language
        self.check_stop = check_stop
        self.model = self.processor = None
        self.turns = ()
        self.revision = "not loaded"
        try:
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("Additional ASR models require an NVIDIA CUDA GPU for FP16. No CPU/precision fallback is used.")
            if self.spec.engine == "qwen":
                import qwen_asr  # noqa: F401
            else:
                import transformers  # noqa: F401
        except ImportError as exc:
            requirement = "requirements-qwen.txt" if self.spec.engine == "qwen" else "requirements-models.txt"
            raise RuntimeError(f"Install the optional runtime first: python -m pip install -r {requirement}") from exc

    def _load(self):
        import torch
        self.check_stop()
        if self.spec.engine == "qwen":
            from qwen_asr import Qwen3ASRModel
            self.model = Qwen3ASRModel.from_pretrained(
                self.spec.checkpoint, dtype=torch.float16, device_map="cuda:0",
                max_inference_batch_size=1, max_new_tokens=448,
            )
        else:
            from transformers import AutoProcessor, AutoModelForCTC, WhisperForConditionalGeneration
            self.processor = AutoProcessor.from_pretrained(self.spec.checkpoint, trust_remote_code=False)
            if self.spec.engine == "whisper":
                self.model = WhisperForConditionalGeneration.from_pretrained(
                    self.spec.checkpoint, torch_dtype=torch.float16, trust_remote_code=False)
                # Text-only chunks use the standard transcription task. Mesolitica's
                # optional transcribeprecise task is not invoked or globally patched.
                self.model.generation_config.forced_decoder_ids = None
            else:
                options = {"target_lang": "zsm", "ignore_mismatched_sizes": True} if self.spec.engine == "mms" else {}
                self.model = AutoModelForCTC.from_pretrained(
                    self.spec.checkpoint, torch_dtype=torch.float16, trust_remote_code=False, **options)
                if self.spec.engine == "mms":
                    self.processor.tokenizer.set_target_lang("zsm")
                    self.model.load_adapter("zsm")
            # Also cast newly loaded MMS adapter weights to the requested dtype.
            self.model.to(device="cuda", dtype=torch.float16).eval()
        inner = getattr(self.model, "model", self.model) if self.spec.engine == "qwen" else self.model
        self.revision = getattr(getattr(inner, "config", None), "_commit_hash", None) or "unavailable"
        self.check_stop()

    def _decode(self, audio):
        import torch
        self.check_stop()
        with torch.inference_mode():
            if self.spec.engine == "qwen":
                language = {"ms": "Malay", "en": "English"}.get(self.language)
                result = self.model.transcribe(audio=(audio, 16000), language=language)
                return result[0].text.strip()
            batch = self.processor(audio, sampling_rate=16000, return_tensors="pt")
            batch = {key: value.to(device="cuda", dtype=torch.float16) if value.is_floating_point()
                     else value.to("cuda") for key, value in batch.items()}
            if self.spec.engine == "whisper":
                result = self.model.generate(**batch, language=self.language, task="transcribe",
                                             return_timestamps=False, num_beams=5, max_new_tokens=440)
            else:
                logits = self.model(**batch).logits
                if not torch.isfinite(logits).all():
                    raise RuntimeError("Non-finite FP16 CTC output. Run stopped without changing precision.")
                result = logits.argmax(dim=-1)
            return self.processor.batch_decode(result, skip_special_tokens=True)[0].strip()

    def transcribe(self, audio_path, **_kwargs):
        from faster_whisper.audio import decode_audio
        self.check_stop()
        audio = decode_audio(audio_path, sampling_rate=16000)
        duration = len(audio) / 16000
        if not duration:
            raise ValueError("The recording contains no decodable audio.")
        info = SimpleNamespace(duration=duration, language=self.language, timing_note=self.timing_note)

        def segments():
            try:
                self._load()
                for start, end in chunk_ranges(duration, self.turns):
                    self.check_stop()
                    chunk = audio[round(start * 16000):round(end * 16000)]
                    if not len(chunk):
                        continue
                    text = self._decode(chunk)
                    self.check_stop()
                    yield SimpleNamespace(start=start, end=end, text=text)
            finally:
                self.close()
        return segments(), info

    def close(self):
        self.model = self.processor = None
        import gc
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
