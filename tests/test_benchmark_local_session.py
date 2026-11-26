import unittest
from redscribe.benchmark.benchmark_local_session import LocalBenchmarkSession

class LocalSessionTests(unittest.TestCase):
    def test_reuse(self):
        for key in ("Mesolitica Whisper v3", "Mesolitica XLS-R 300M", "Meta MMS 1B (Malay)"):
            events = []
            class Fake:
                def _load(self):
                    assert self.strict_benchmark
                    events.append("load")
                    self.verified_device = "cuda"
                    self.verified_precision = "float16"
                def _decode(self, audio):
                    events.append(len(audio))
                    return " hmm kawe "
                def close(self):
                    events.append("close")
            s = LocalBenchmarkSession(key, factory=lambda *a,**k:Fake(),
                decoder=lambda *a,**k:range(16000))
            self.assertEqual(s.transcribe("p1"), "hmm kawe")
            self.assertEqual(s.transcribe("p2"), "hmm kawe")
            s.close()
            s.close()
            self.assertEqual(events, ["load",16000,16000,"close"])
            with self.assertRaises(RuntimeError):
                s.transcribe("p3")
