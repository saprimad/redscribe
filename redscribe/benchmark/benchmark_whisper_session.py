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
            if model is not None:
                # Release native weights explicitly before destroying the wrapper.
                # The isolated worker still contains any native abort here.
                native = getattr(model, "model", None)
                unload = getattr(native, "unload_model", None)
                if callable(unload):
                    print("NATIVE UNLOAD START", flush=True)
                    unload(to_cpu=False)
                    if getattr(native, "model_is_loaded", False):
                        raise RuntimeError("CTranslate2 model remains loaded")
                    print("NATIVE UNLOAD PASS", flush=True)
                del unload, native
                if hasattr(model, "close"):
                    model.close()
        finally:
            print("WRAPPER RELEASE START", flush=True)
            del model
            collect()
            print("WRAPPER RELEASE PASS", flush=True)

    def prepare_controlled_shutdown(self):
        """Unload weights while retaining the wrapper until isolated process exit."""
        if self.model is None:
            raise RuntimeError("Session closed")
        native = self.model.model
        print("NATIVE UNLOAD START", flush=True)
        native.unload_model(to_cpu=False)
        if native.model_is_loaded:
            raise RuntimeError("CTranslate2 model remains loaded")
        print("NATIVE UNLOAD PASS", flush=True)
