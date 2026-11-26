import unittest
from pathlib import Path
from redscribe.benchmark.benchmark_batch import validate_resume

class ResumeTests(unittest.TestCase):
    def test_pending_and_configuration(self):
        state = dict(schema_version=3, models=["tiny"], language="ms", gpu_monitor=False, vad=False, osd=False,
                     items=[dict(audio="a", audio_sha256="a", reference_manifest="r", reference_sha256="r", status="pending")])
        self.assertEqual(validate_resume(Path("."), state, state, [(None,None,None,None)])["resume_count"], 1)
        with self.assertRaises(ValueError):
            validate_resume(Path("."), state, dict(state, language="en"), [])
