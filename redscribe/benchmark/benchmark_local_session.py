"""Reusable benchmark-only session for existing local Transformers ASR adapters."""
from asr_backends import LocalASR, chunk_ranges

class LocalBenchmarkSession:
    def __init__(self, key, language="ms", check_stop=lambda: None, factory=None, decoder=None):
        self.adapter = (factory or LocalASR)(key, language=language, check_stop=check_stop)
        self.adapter.strict_benchmark = True
        self.check_stop = check_stop
        self.decoder = decoder
        try:
            self.adapter._load()
            self.device = self.adapter.verified_device
            self.precision = self.adapter.verified_precision
            self.provenance={"model_key":key,"checkpoint":getattr(getattr(self.adapter,"spec",None),"checkpoint",None),"revision":getattr(self.adapter,"revision",None),"decoding":{"language":language,"chunking":"existing chunk_ranges"}}
        except Exception:
            self.close()
            raise

    def transcribe(self, audio_path):
        if self.adapter is None:
            raise RuntimeError("Session closed")
        decoder = self.decoder
        if decoder is None:
            from faster_whisper.audio import decode_audio
            decoder = decode_audio
        self.check_stop()
        audio = decoder(str(audio_path), sampling_rate=16000)
        texts = []
        for start, end in chunk_ranges(len(audio)/16000):
            self.check_stop()
            chunk = audio[round(start*16000):round(end*16000)]
            if len(chunk):
                text = self.adapter._decode(chunk).strip()
                if text:
                    texts.append(text)
            self.check_stop()
        return " ".join(texts)

    def close(self):
        adapter, self.adapter = self.adapter, None
        if adapter is not None:
            adapter.close()
