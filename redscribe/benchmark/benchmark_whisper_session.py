"""Reusable strict Faster-Whisper session for experimental model-major runs."""
from redscribe.benchmark.benchmark_configuration import verify_configuration

class WhisperSession:
    def __init__(self, key, language="ms", loader=None):
        if loader is None:
            from redscribe_gpu import create_whisper_model
            loader = create_whisper_model
        self.language = language
        self.model, _, _ = loader(key, strict_benchmark=True)
        try:
            self.device, self.precision = verify_configuration(
                getattr(self.model.model, "device", None),
                getattr(self.model.model, "compute_type", None))
            self.provenance={"model_key":key,"revision":getattr(self.model,"benchmark_revision",None),"decoding":{"language":language,"task":"transcribe","beam_size":5,"vad_filter":False,"condition_on_previous_text":True}}
        except Exception:
            self.close()
            raise

    def transcribe(self, audio):
        if self.model is None:
            raise RuntimeError("Session closed")
        segments, _ = self.model.transcribe(str(audio), language=self.language,
            task="transcribe", beam_size=5, vad_filter=False,
            condition_on_previous_text=True)
        return " ".join(s.text.strip() for s in segments if s.text.strip())

    def close(self):
        model, self.model = self.model, None
        from gc import collect
        try:
            if model is not None and hasattr(model, "close"):
                model.close()
        finally:
            del model
            collect()
