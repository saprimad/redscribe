import unittest
from redscribe.benchmark.benchmark_matrix_reporting import build_matrix_reports

class InvalidScoreAuditTests(unittest.TestCase):
    def test_invalid_rate_excluded_from_flat_and_common(self):
        good=dict(status="completed",wer=.1,cer=.1,word_substitutions=1,word_deletions=0,word_insertions=0,reference_words=10,char_substitutions=1,char_deletions=0,char_insertions=0,reference_characters=10)
        state={"identity":{"models":["a","b"],"recordings":["P1"]},"results":{"a":{"P1":good},"b":{"P1":dict(good,wer=.9)}}}
        summary,rows,_=build_matrix_reports(state)
        self.assertIsNone(rows[1]["wer"])
        self.assertTrue(all(r["recordings_total"]==0 for r in summary if r["cohort"]=="common_completed"))
