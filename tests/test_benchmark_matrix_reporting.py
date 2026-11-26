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

    def test_session_timing_deduplication(self):
        from redscribe.benchmark.benchmark_matrix_reporting import session_timings
        rows=[dict(session_id="s1",session_loading_seconds=10,session_warmup_seconds=None,inference_seconds=2),
              dict(session_id="s1",session_loading_seconds=10,session_warmup_seconds=None,inference_seconds=3),
              dict(session_id="s2",session_loading_seconds=7,session_warmup_seconds=None,inference_seconds=4)]
        result=session_timings(rows)
        self.assertEqual(result["sessions_timed"],2)
        self.assertEqual(result["loading_seconds_total"],17)
        self.assertEqual(result["inference_seconds_total"],9)
        self.assertEqual(result["loading_inference_seconds_total"],26)
        self.assertIsNone(result["warmup_seconds_total"])
        rows[1]["session_loading_seconds"]=11
        self.assertIsNone(session_timings(rows)["loading_seconds_total"])
        self.assertIsNone(session_timings(rows)["loading_inference_seconds_total"])
        rows[0]["session_id"]=None
        self.assertIsNone(session_timings(rows)["loading_seconds_total"])
