import tempfile
import unittest
import json
from pathlib import Path
from threading import Event
from unittest.mock import patch
from redscribe.benchmark import benchmark_batch as batch
from redscribe.benchmark.benchmark_reference import approve_reference

class RecoveryTests(unittest.TestCase):
    def test_checkpoint_cancel_and_reporting_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pairs = []
            for i in range(2):
                a = root / f"a{i}.wav"
                a.write_bytes(str(i).encode())
                d = root / f"d{i}.docx"
                d.write_bytes(str(i).encode())
                ref, _, _ = approve_reference(d, f"kawe {i}", root, reviewer_acknowledged=True)
                pairs.append((a, ref))
            cancel = Event()
            def fake(*args, **kwargs):
                cancel.set()
                return root / "synthetic_result", {"status":"completed", "model_results":{}}
            with patch.object(batch, "run_single_pilot", side_effect=fake), patch.object(batch, "export_reporting", side_effect=RuntimeError("synthetic report failure")):
                folder, state = batch.run_batch_pilot(pairs, ["tiny"], root / "runs", cancel=cancel)
            saved = json.loads((folder / "batch_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "cancelled")
            self.assertEqual([i["status"] for i in saved["items"]], ["completed","pending"])
            self.assertTrue(saved["reporting_warnings"])
            self.assertTrue((folder / "batch_results.csv").exists())
            self.assertTrue(saved["resume_supported"])
