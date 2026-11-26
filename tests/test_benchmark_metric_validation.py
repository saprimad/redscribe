"""Independent, dependency-free metric validation using a full-matrix edit-distance oracle.

These tests validate the raw Levenshtein distance and error-rate denominator.
They intentionally do NOT choose Malay/Kelantan normalisation rules.
Run: python -m unittest discover -s tests -p 'test_benchmark*.py'
"""
import itertools
import unittest

from benchmark_metrics import raw_wer, raw_cer, edit_counts, corpus_counts, macro_rate


def independent_distance(reference, hypothesis):
    """Reference implementation using a full O(N*M) matrix, unlike production."""
    m, n = len(reference), len(hypothesis)
    matrix = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        matrix[i][0] = i
    for j in range(n + 1):
        matrix[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1]),
            )
    return matrix[m][n]


class IndependentMetricValidation(unittest.TestCase):
    def test_all_short_symbol_sequences_against_independent_distance(self):
        sequences = [
            tuple(items)
            for size in range(5)
            for items in itertools.product(("a", "b", "c"), repeat=size)
        ]
        # 121 x 121 = 14,641 exact reference/hypothesis comparisons.
        for ref in sequences:
            for hyp in sequences:
                result = edit_counts(ref, hyp)
                self.assertEqual(
                    result.substitutions + result.deletions + result.insertions,
                    independent_distance(ref, hyp),
                    (ref, hyp),
                )
                self.assertEqual(result.reference_units, len(ref))

    def test_unicode_whitespace_case_and_dialect_are_raw(self):
        self.assertAlmostEqual(raw_wer("kawe dok setuju", "kawe setuju").rate, 1 / 3)
        self.assertAlmostEqual(raw_wer("makae", "makan").rate, 1)
        self.assertEqual(raw_wer("Ganja", "ganja").rate, 1)
        self.assertEqual(raw_cer("ikan\npatin", "ikan patin").rate, 1 / 10)
        self.assertEqual(raw_cer("e\u0301", "\u00e9").reference_units, 2)
        self.assertEqual(raw_cer("e\u0301", "\u00e9").rate, 1)
        self.assertIsNone(raw_wer("", "tambahan").rate)
        self.assertIsNone(raw_cer("", "tambahan").rate)

    def test_micro_and_macro_differ_with_unequal_recordings(self):
        scores = [raw_wer("a", "b"), raw_wer("a b c d e f g h i", "a b c d e f g h i")]
        self.assertAlmostEqual(macro_rate(scores), 0.5)
        self.assertAlmostEqual(corpus_counts(scores).rate, 0.1)
        self.assertNotEqual(macro_rate(scores), corpus_counts(scores).rate)


if __name__ == "__main__":
    unittest.main()
