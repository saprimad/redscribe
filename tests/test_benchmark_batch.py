"""Synthetic tests for overlap counting and confirmed batch execution."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docx import Document

from benchmark_reference import approve_reference
from benchmark_speech import overlap_intervals, union_duration
from benchmark_batch import run_batch_pilot


class BenchmarkBatchTest(unittest.TestCase):
    def test_overlap_distinct_speakers_only(self):
        turns = [
            {"start": 0, "end": 4, "speaker": "A"},
            {"start": 1, "end": 3, "speaker": "A"},
            {"start": 2, "end": 5, "speaker": "B"},
            {"start": 4, "end": 6, "speaker": "C"},
        ]
        self.assertEqual(overlap_intervals(turns), [(2., 5.)])
        self.assertEqual(union_duration([(0, 1), (0.5, 2), (3, 4)]), 3.)

    def test_batch_creates_separate_results_and_aggregate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pairs = []
            for i in range(2):
                docx = root / f"ref{i}.docx"
                document = Document()
                document.add_paragraph(f"sample {i}")
                document.save(docx)
                manifest, _, _ = approve_reference(
                    docx, f"sample {i}", root / "private",
                    reviewer_acknowledged=True)
                audio = root / f"audio{i}.wav"
                audio.write_bytes(b"mock audio")
                pairs.append((audio, manifest))
            with patch("benchmark_pilot._decode_duration", return_value=10.), \
                 patch("benchmark_pilot.preflight_model", return_value="ok"), \
                 patch("benchmark_pilot._transcribe",
                       side_effect=[("sample 0", .2, .4, "cpu", "int8", ""),
                                    ("sample 1", .2, .4, "cpu", "int8", "")]):
                result_dir, result = run_batch_pilot(
                    pairs, ("tiny",), root / "out", gpu_monitor=False, vad=False, osd=False)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(result["items"]), 2)
            self.assertTrue((result_dir / "batch_manifest.json").is_file())
            self.assertTrue((result_dir / "batch_results.csv").is_file())
            self.assertTrue((result_dir / "model_summary.csv").is_file())
            self.assertTrue((result_dir / "error_breakdown.csv").is_file())
            self.assertTrue((result_dir / "benchmark_summary.xlsx").is_file())
            with __import__("zipfile").ZipFile(result_dir / "benchmark_summary.xlsx") as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(len([name for name in archive.namelist() if name.startswith("xl/worksheets/sheet")]), 4)
            self.assertTrue(all(item["status"] == "completed" for item in result["items"]))

    def test_secondary_export_failures_preserve_completed_batch(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            document = Document()
            document.add_paragraph("sample")
            word = root / "ref.docx"
            document.save(word)
            manifest, _, _ = approve_reference(
                word, "sample", root / "private", reviewer_acknowledged=True)
            audio = root / "audio.wav"
            audio.write_bytes(b"mock audio")
            with patch("benchmark_pilot._decode_duration", return_value=10.), \
                 patch("benchmark_pilot.preflight_model", return_value="ok"), \
                 patch("benchmark_pilot._transcribe",
                       return_value=("sample", .2, .4, "cpu", "int8", "")), \
                 patch("benchmark_batch._write_batch_results",
                       side_effect=PermissionError("CSV locked")), \
                 patch("benchmark_batch.export_reporting",
                       side_effect=OSError("report unavailable")), \
                 patch("benchmark_batch.export_excel",
                       side_effect=PermissionError("Excel locked")):
                directory, state = run_batch_pilot(
                    [(audio, manifest)], ("tiny",), root / "out")
            saved = json.loads((directory / "batch_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, state)
            self.assertEqual(saved["status"], "completed")
            self.assertEqual(saved["items"][0]["model_results"]["tiny"]["status"], "completed")
            for prefix in ("CSV:", "reporting:", "Excel:"):
                self.assertTrue(any(w.startswith(prefix) for w in saved["reporting_warnings"]))
            self.assertTrue((directory / saved["items"][0]["result_folder"] / "manifest.json").is_file())

    def test_no_duplicate_references(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            document = Document()
            document.add_paragraph("test")
            word = root / "t.docx"
            document.save(word)
            manifest, _, _ = approve_reference(word, "test", root / "approved",
                                                reviewer_acknowledged=True)
            a, b = root / "a.wav", root / "b.wav"
            a.write_bytes(b"a")
            b.write_bytes(b"b")
            with self.assertRaises(ValueError):
                run_batch_pilot([(a, manifest), (b, manifest)], ("tiny",), root / "out")


if __name__ == "__main__":
    unittest.main()
