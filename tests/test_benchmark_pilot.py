"""Mocked smoke tests: no model weights downloaded, no participant data."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docx import Document
from benchmark_reference import approve_reference
from benchmark_pilot import run_single_pilot


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.audio = self.directory / "audio.wav"
        self.audio.write_bytes(b"dummy test audio")
        self.reference_doc = self.directory / "reference.docx"
        doc = Document()
        doc.add_paragraph("dia makan ikan")
        doc.save(self.reference_doc)
        self.manifest, _, _ = approve_reference(
            str(self.reference_doc), "dia makan ikan",
            self.directory / "private", reviewer_acknowledged=True)

    @patch("benchmark_pilot._decode_duration", return_value=10.)
    @patch("benchmark_pilot.preflight_model", return_value="mock-ready")
    @patch("benchmark_pilot._transcribe", return_value=(
        "dia makan ikang", 0.5, 1.5, "cuda", "float16", ""))
    def test_one_model_scores_and_saves(self, transcribe, preflight, duration):
        folder, summary = run_single_pilot(
            self.audio, self.manifest, ("large-v3",), self.directory / "results")
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["model_results"]["large-v3"]["status"], "completed")
        self.assertAlmostEqual(summary["model_results"]["large-v3"]["wer"], 1 / 3)
        self.assertAlmostEqual(summary["model_results"]["large-v3"]["rtf"], .15)
        self.assertTrue((folder / "results.csv").is_file())
        self.assertTrue((folder / "01_large-v3.txt").is_file())
        self.assertTrue((folder / "manifest.json").is_file())

    @patch("benchmark_pilot._decode_duration", return_value=10.)
    @patch("benchmark_pilot.preflight_model", return_value="mock-ready")
    @patch("benchmark_pilot._transcribe", return_value=(
        "dia makan ikan", 0.5, 1.5, "cuda", "float16", ""))
    def test_monitor_export_failure_does_not_invalidate_accuracy(
            self, transcribe, preflight, duration):
        class FaultyMonitor:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def summary(self):
                return {"gpu_util_percent_peak": 30}

            def save_csv(self, _path):
                raise OSError("monitor export failure")

        with patch("benchmark_resources.ResourceMonitor", FaultyMonitor):
            folder, summary = run_single_pilot(
                self.audio, self.manifest, ("large-v3",),
                self.directory / "results", gpu_monitor=True)
        result = summary["model_results"]["large-v3"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["wer"], 0)
        self.assertTrue((folder / "results.csv").exists())

    @patch("benchmark_pilot._decode_duration", return_value=10.)
    @patch("benchmark_pilot.preflight_model", side_effect=RuntimeError("missing CUDA"))
    def test_failed_model_is_not_assigned_fake_wer(self, preflight, duration):
        _, summary = run_single_pilot(
            self.audio, self.manifest, ("Qwen3-ASR 1.7B",),
            self.directory / "results")
        item = summary["model_results"]["Qwen3-ASR 1.7B"]
        self.assertEqual(item["status"], "failed")
        self.assertIsNone(item["wer"])
        self.assertIn("missing CUDA", item["error"])


if __name__ == "__main__":
    unittest.main()
