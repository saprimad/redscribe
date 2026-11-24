import unittest
from types import SimpleNamespace
from redscribe.benchmark.benchmark_whisper_session import WhisperSession
from redscribe.benchmark.benchmark_model_major import run_model_major

class WhisperSessionTests(unittest.TestCase):
    def test_reuses_model(self):
        loads, calls, rows = [], [], []
        class Fake:
            model = SimpleNamespace(device="cuda", compute_type="float16")
            def transcribe(self, audio, **kw):
                calls.append((audio,kw))
                return iter([SimpleNamespace(text=" hmm kawe ")]), None
        def loader(key, **kw):
            loads.append((key,kw))
            return Fake(), "cuda", "float16"
        run_model_major(["whisper"], ["p1","p2"],
            open_model=lambda k:WhisperSession(k,loader=loader),
            infer=lambda s,r:s.transcribe(r), close_model=lambda s:s.close(),
            checkpoint=lambda *r:rows.append(r))
        self.assertEqual(len(loads),1)
        self.assertTrue(loads[0][1]["strict_benchmark"])
        self.assertEqual([x[0] for x in calls],["p1","p2"])
        self.assertEqual([r[2]["result"] for r in rows],["hmm kawe"]*2)
        self.assertEqual(calls[0][1]["beam_size"],5)
        self.assertFalse(calls[0][1]["vad_filter"])
