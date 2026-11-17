"""Run: python -m unittest discover -s tests -p 'test_benchmark_foundation.py'"""
import unittest
from benchmark_config import ALL_MODELS, CORE_MODELS, BenchmarkConfig, ordered_selection
from benchmark_metrics import raw_wer, raw_cer, corpus_counts, macro_rate

class BenchmarkFoundationTests(unittest.TestCase):
    def test_default_models(self):
        self.assertEqual(len(BenchmarkConfig().models), 7)
        self.assertEqual(BenchmarkConfig().models, CORE_MODELS)
        self.assertEqual(len(ALL_MODELS), 11)
        self.assertEqual(BenchmarkConfig("batch", ALL_MODELS).mode, "batch")

    def test_selection(self):
        self.assertEqual(ordered_selection(["tiny", "large-v3"]), ("large-v3", "tiny"))
        for invalid in [(), ("unknown",), ("tiny", "tiny")]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                BenchmarkConfig(models=invalid)

    def test_errors(self):
        self.assertEqual(raw_wer("dia makan ikan", "dia makan ikan").rate, 0)
        sub = raw_wer("dia makan ikan", "dia makan ikang")
        self.assertEqual((sub.substitutions, sub.deletions, sub.insertions), (1, 0, 0))
        self.assertAlmostEqual(sub.rate, 1 / 3)
        self.assertEqual(raw_wer("a b", "a").deletions, 1)
        self.assertEqual(raw_wer("a", "a b").insertions, 1)
        self.assertAlmostEqual(raw_cer("ikan", "ikang").rate, 1 / 4)

    def test_aggregates(self):
        scores = [raw_wer("a b", "a"), raw_wer("a b c d", "a b c d")]
        self.assertAlmostEqual(macro_rate(scores), .25)
        self.assertAlmostEqual(corpus_counts(scores).rate, 1 / 6)
        self.assertIsNone(raw_wer("", "").rate)
        self.assertIsNone(macro_rate([raw_wer("", "")]))

if __name__ == "__main__":
    unittest.main()
