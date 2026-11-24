"""Cross-check raw error totals against independent JiWER 4.0.0."""
import itertools
import unittest
import jiwer
from benchmark_metrics import raw_wer, raw_cer

class JiwerValidation(unittest.TestCase):
    def test_raw_scores(self):
        samples = ["", "kawe", "Hmm kawe", "makae", "makan", "ikae", "ikan",
                   "Ganja", "ganja", "a  b", "a\nb", "e\u0301", "\u00e9", "a!", "a\tb"]
        word_transform = jiwer.Compose([jiwer.ReduceToListOfListOfWords()])
        char_transform = jiwer.Compose([jiwer.ReduceToListOfListOfChars()])
        for ref, hyp in itertools.product(samples, repeat=2):
            with self.subTest(ref=ref, hyp=hyp):
                # Canonicalise whitespace only for WER, matching str.split().
                a, b = " ".join(ref.split()), " ".join(hyp.split())
                for score, external in [
                    (raw_wer(ref, hyp), jiwer.process_words(a,b,reference_transform=word_transform,hypothesis_transform=word_transform)),
                    (raw_cer(ref, hyp), jiwer.process_characters(ref,hyp,reference_transform=char_transform,hypothesis_transform=char_transform)),
                ]:
                    self.assertEqual(score.substitutions+score.deletions+score.insertions,
                                     external.substitutions+external.deletions+external.insertions)
                    if score.reference_units:
                        self.assertAlmostEqual(score.rate, (external.substitutions+external.deletions+external.insertions)/score.reference_units)
                    else:
                        self.assertIsNone(score.rate)
