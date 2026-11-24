import unittest
from redscribe.benchmark.benchmark_matrix_reporting import build_matrix_reports

class MatrixReportingTests(unittest.TestCase):
    def test_common_and_weighted(self):
        def row(n,e):
            return dict(status="completed",wer=e/n,cer=e/n,word_substitutions=e,word_deletions=0,word_insertions=0,reference_words=n,char_substitutions=e,char_deletions=0,char_insertions=0,reference_characters=n,audio_seconds=10,inference_seconds=2)
        state={"identity":{"models":["a","b"],"recordings":["P1","P2"]},"results":{"a":{"P1":row(10,1),"P2":row(90,45)},"b":{"P1":row(10,2),"P2":{"status":"failed"}}}}
        summary,rows,eff=build_matrix_reports(state)
        self.assertAlmostEqual(summary[0]["corpus_wer"],.46)
        self.assertAlmostEqual(summary[0]["macro_wer"],.3)
        self.assertEqual(summary[2]["recordings_total"],1)
        self.assertEqual(summary[1]["recordings_failed"],1)
        self.assertIsNone(rows[3]["wer"])
        self.assertEqual(eff[0]["aggregate_rtf"],.2)
