"""Derived reporting counts without changing benchmark scoring or legacy exports."""
import unittest
from redscribe.benchmark.benchmark_metrics import ErrorCounts, raw_wer, raw_cer


class ExtendedErrorCountsTests(unittest.TestCase):
    def test_absolute_counts(self):
        score = ErrorCounts(2, 3, 4, 10)
        self.assertEqual(score.hits, 5)
        self.assertEqual(score.hypothesis_units, 11)
        self.assertEqual(score.total_errors, 9)
        self.assertEqual(score.as_extended_dict(), {
            "substitutions": 2, "deletions": 3, "insertions": 4,
            "reference_units": 10, "rate": .9, "hypothesis_units": 11,
            "hits": 5, "total_errors": 9,
        })
        self.assertEqual(set(score.as_dict()), {
            "substitutions", "deletions", "insertions", "reference_units", "rate",
        })

    def test_word_and_character_counts(self):
        for scorer, ref, hyp, n, m in (
            (raw_wer, "a b c", "a x", 3, 2),
            (raw_cer, "é a", "é b!", 3, 4),
            (raw_wer, "a", "a b c", 1, 3),
            (raw_wer, "a b", "", 2, 0),
            (raw_cer, "", "abc", 0, 3),
            (raw_cer, "", "", 0, 0),
        ):
            with self.subTest(ref=ref, hyp=hyp):
                score = scorer(ref, hyp)
                result = score.as_extended_dict()
                self.assertEqual(result["reference_units"], n)
                self.assertEqual(result["hypothesis_units"], m)
                self.assertEqual(result["hits"] + score.substitutions + score.deletions, n)
                self.assertEqual(result["hits"] + score.substitutions + score.insertions, m)
                if n == 0:
                    self.assertIsNone(result["rate"])
                else:
                    self.assertEqual(result["rate"], result["total_errors"] / n)
        self.assertEqual(raw_wer("a", "a b c").as_extended_dict()["rate"], 2.0)

    def test_impossible_or_invalid_counts_rejected(self):
        for score in (ErrorCounts(3, 0, 0, 2), ErrorCounts(0, -1, 0, 2),
                      ErrorCounts(True, 0, 0, 2), ErrorCounts(0, 0, 0, 1.5)):
            with self.subTest(score=score), self.assertRaises(ValueError):
                score.as_extended_dict()
