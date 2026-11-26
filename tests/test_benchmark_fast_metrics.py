import unittest
from itertools import product
from redscribe.benchmark.benchmark_metrics import edit_counts
from redscribe.benchmark.benchmark_fast_metrics import edit_counts_fast, raw_cer_fast, raw_wer_fast

class FastMetricsTests(unittest.TestCase):
    def test_exhaustive_totals(self):
        seq=["".join(x) for n in range(5) for x in product("ab ",repeat=n)]
        for a in seq:
            for b in seq:
                old,new=edit_counts(a,b),edit_counts_fast(a,b)
                self.assertEqual(old.rate,new.rate)
                self.assertEqual(old.substitutions+old.deletions+old.insertions,
                                 new.substitutions+new.deletions+new.insertions)
    def test_unicode_and_fillers(self):
        self.assertEqual(raw_wer_fast("hmm kawe","kawe").rate,.5)
        self.assertEqual(raw_cer_fast("é\r\n","e\r\n").substitutions,1)
        self.assertIsNone(raw_cer_fast("","abc").rate)
    def test_long(self):
        for n in (1000,5000,10000,25000,50000,100000):
            a=("kawe nok makae nasi " * n)[:n]
            b=a[:n//2]+"X"+a[n//2+1:]
            self.assertEqual(raw_cer_fast(a,b).rate,1/n)
