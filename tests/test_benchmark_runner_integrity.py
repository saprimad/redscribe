"""Failure/cancellation regression tests for the experimental single/batch runners.

Uses private synthetic DOCX and fake audio bytes. No ASR weights or GPU needed.
"""
import csv
import tempfile
import unittest
import warnings
from pathlib import Path
from threading import Event
from unittest.mock import patch

from docx import Document

from benchmark_reference import approve_reference
from benchmark_pilot import run_single_pilot, PilotCancelled, _cleanup
from benchmark_batch import run_batch_pilot


class RunnerIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pairs = []
        for number in range(2):
            docx = self.root / f"ref{number}.docx"
            doc = Document()
            doc.add_paragraph(f"short synthetic text {number}")
            doc.save(docx)
            manifest, _, _ = approve_reference(
                docx, f"short synthetic text {number}", self.root / "private",
                reviewer_acknowledged=True)
            audio = self.root / f"audio{number}.wav"
            audio.write_bytes(b"mock audio - not an actual recording")
            self.pairs.append((audio, manifest))

    def test_batch_records_failure_without_model_results(self):
        completed = {"status": "completed", "model_results": {
            "tiny": {"status": "completed", "wer": 0.0, "cer": 0.0,
                     "transcription_seconds": 0.5, "rtf": 0.05, "error": ""}}}
        class DirectoryResult:
            name = "synthetic_child"
        with patch("benchmark_batch.run_single_pilot", side_effect=[
            RuntimeError("synthetic first-audio failure"),
            (DirectoryResult(), completed),
        ]) as mocked:
            folder, state = run_batch_pilot(self.pairs, ("tiny",), self.root / "out")
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(state["status"], "completed_with_errors")
        self.assertEqual([item["status"] for item in state["items"]],
                         ["failed", "completed"])
        with (folder / "batch_results.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["recording_status"], "failed")
        self.assertEqual(rows[0]["model_key"], "")
        self.assertIn("synthetic first-audio failure", rows[0]["recording_error"])
        self.assertEqual(rows[1]["model_key"], "tiny")
        self.assertEqual(rows[1]["recording_status"], "completed")

    def test_batch_cancel_before_start_keeps_pending_rows(self):
        cancel = Event()
        cancel.set()
        with patch("benchmark_batch.run_single_pilot") as mocked:
            folder, state = run_batch_pilot(
                self.pairs, ("tiny",), self.root / "out", cancel=cancel)
        mocked.assert_not_called()
        self.assertEqual(state["status"], "cancelled")
        self.assertTrue(all(item["status"] == "pending" for item in state["items"]))
        with (folder / "batch_results.csv").open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["recording_status"] == "pending" for row in rows))
        self.assertTrue(all(not row["wer"] for row in rows))

    def test_audio_modification_after_preflight_is_rejected(self):
        with patch("benchmark_batch.sha256_file", side_effect=["original", "changed"]), \\
             patch("benchmark_batch.run_single_pilot") as runner:
            folder, state = run_batch_pilot(
                self.pairs[:1], ("tiny",), self.root / "out")
        runner.assert_not_called()
        self.assertEqual(state["items"][0]["status"], "failed")
        self.assertIn("changed since batch preflight", state["items"][0]["error"])
        self.assertEqual(state["status"], "completed_with_errors")
        self.assertTrue((folder / "batch_results.csv").is_file())

    def test_cancelled_single_run_does_not_fake_metric(self):
        with patch("benchmark_pilot._decode_duration", return_value=10.0), \\
             patch("benchmark_pilot.preflight_model", return_value="ready"), \\
             patch("benchmark_pilot._transcribe", side_effect=PilotCancelled("stop")):
            folder, state = run_single_pilot(
                self.pairs[0][0], self.pairs[0][1], ("tiny",),
                self.root / "out")
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(state["model_results"]["tiny"]["status"], "cancelled")
        self.assertIsNone(state["model_results"]["tiny"]["wer"])
        self.assertTrue((folder / "results.csv").is_file())

    def test_failed_model_cleanup_does_not_override_valid_output(self):
        class BadClose:
            def close(self):
                raise RuntimeError("synthetic teardown failure")
        with warnings.catch_warnings(record=True) as found:
            warnings.simplefilter("always")
            _cleanup(BadClose())
        self.assertTrue(any("cleanup warning" in str(w.message) for w in found))

    def test_single_checks_expected_batch_hash(self):
        with patch("benchmark_pilot._decode_duration", return_value=10.0):
            with self.assertRaisesRegex(ValueError, "changed since batch preflight"):
                run_single_pilot(
                    self.pairs[0][0], self.pairs[0][1], ("tiny",),
                    self.root / "out", expected_audio_sha256="not-the-real-hash")


if __name__ == "__main__":
    unittest.main()
