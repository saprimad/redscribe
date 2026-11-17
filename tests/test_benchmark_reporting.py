"""Synthetic tests for reporting: no participant audio, model weights or GPU."""
import csv
import tempfile
import unittest
from pathlib import Path

from benchmark_reporting import build_summary, build_error_breakdown, export_reporting


def result(sw=0, dw=0, iw=0, nw=10, sc=0, dc=0, ic=0, nc=50):
    return {
        "status": "completed",
        "substitutions": sw, "deletions": dw, "insertions": iw,
        "word_substitutions": sw, "word_deletions": dw, "word_insertions": iw,
        "reference_words": nw, "wer": (sw + dw + iw) / nw,
        "char_substitutions": sc, "char_deletions": dc, "char_insertions": ic,
        "reference_characters": nc, "cer": (sc + dc + ic) / nc,
    }


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "models": ["large-v3", "tiny"],
            "items": [
                {
                    "audio": "a.wav", "audio_sha256": "hashA", "status": "completed",
                    "model_results": {
                        "large-v3": result(sw=2, nw=10, sc=3, nc=50),
                        "tiny": result(sw=4, nw=10, sc=10, nc=50),
                    },
                },
                {
                    "audio": "b.wav", "audio_sha256": "hashB",
                    "status": "completed_with_errors",
                    "model_results": {
                        "large-v3": result(sw=0, nw=90, sc=0, nc=450),
                        "tiny": {"status": "failed", "wer": None, "cer": None,
                                 "error": "synthetic CUDA unavailable"},
                    },
                },
            ],
        }

    def test_micro_macro_distinct_and_common_cohort(self):
        rows = build_summary(self.state)
        self.assertEqual(len(rows), 4)
        all_large, all_tiny, common_large, common_tiny = rows
        self.assertEqual((all_large["word_scored"], all_tiny["word_scored"]), (2, 1))
        self.assertAlmostEqual(all_large["corpus_wer"], 0.02)
        self.assertAlmostEqual(all_large["macro_wer"], 0.10)
        self.assertAlmostEqual(all_large["corpus_cer"], 3 / 500)
        self.assertEqual(all_tiny["recordings_failed"], 1)
        self.assertEqual(all_tiny["word_scored"], 1)
        self.assertEqual(common_large["recordings_total"], 1)
        self.assertEqual(common_tiny["recordings_total"], 1)
        self.assertAlmostEqual(common_large["corpus_wer"], 0.2)
        self.assertAlmostEqual(common_tiny["corpus_wer"], 0.4)

    def test_missing_character_components_not_fabricated(self):
        self.state["items"][0]["model_results"]["large-v3"].pop("char_insertions")
        rows = build_summary(self.state)
        all_large = rows[0]
        self.assertEqual(all_large["word_scored"], 2)
        self.assertEqual(all_large["character_scored"], 1)
        self.assertAlmostEqual(all_large["corpus_cer"], 0.0)
        self.assertEqual(rows[2]["recordings_total"], 0)
        self.assertIsNone(rows[2]["corpus_wer"])
        self.assertIsNone(rows[2]["corpus_cer"])

    def test_invalid_count_or_rate_is_excluded_not_zeroed(self):
        self.state["items"][0]["model_results"]["large-v3"]["wer"] = 0.001
        self.state["items"][1]["model_results"]["large-v3"]["word_substitutions"] = -1
        self.state["items"][1]["model_results"]["large-v3"]["substitutions"] = -1
        rows = build_summary(self.state)
        self.assertEqual(rows[0]["recordings_completed"], 2)
        self.assertEqual(rows[0]["word_scored"], 0)
        self.assertIsNone(rows[0]["corpus_wer"])
        breakdown = build_error_breakdown(self.state)
        self.assertIsNone(breakdown[0]["wer"])
        self.assertEqual(breakdown[1]["status"], "completed")

    def test_failed_recording_cannot_appear_as_perfect_accuracy(self):
        self.state["items"].append({
            "audio": "c.wav", "audio_sha256": "hashC", "status": "failed",
            "error": "bad reference", "model_results": {},
        })
        rows = build_summary(self.state)
        self.assertEqual(rows[0]["recordings_total"], 3)
        self.assertEqual(rows[0]["recordings_unavailable"], 1)
        breakdown = build_error_breakdown(self.state)
        self.assertEqual(len(breakdown), 6)
        self.assertEqual(breakdown[-1]["status"], "unavailable")
        self.assertIsNone(breakdown[-1]["wer"])

    def test_export_columns_and_rates_are_fractions(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            export_reporting(folder, self.state)
            with (folder / "model_summary.csv").open(
                    newline="", encoding="utf-8-sig") as stream:
                summaries = list(csv.DictReader(stream))
            with (folder / "error_breakdown.csv").open(
                    newline="", encoding="utf-8-sig") as stream:
                errors = list(csv.DictReader(stream))
            self.assertEqual(len(summaries), 4)
            self.assertEqual(len(errors), 4)
            self.assertEqual(summaries[0]["corpus_wer"], "0.02")
            self.assertEqual(errors[1]["model_key"], "tiny")
            self.assertEqual(errors[1]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
