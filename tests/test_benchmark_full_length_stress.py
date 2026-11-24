import unittest
import random
import time
from rapidfuzz.distance import Levenshtein
from redscribe.benchmark.benchmark_fast_metrics import raw_cer_fast, raw_wer_fast
from redscribe.benchmark.benchmark_metrics import raw_cer

class FullLengthStressTests(unittest.TestCase):
    def test_long_mixed_errors(self):
        for n in (10000,25000,50000,100000):
            for error_probability in (.1,.3,.5):
                rng=random.Random(42)
                ref="".join(rng.choices("kawe nok makae nasi hmm é\n",k=n))
                parts=[]
                for c in ref:
                    if rng.random()<error_probability:
                        parts.append(rng.choice(["","X","XY"]))
                    else:
                        parts.append(c)
                hyp="".join(parts)
                start=time.perf_counter()
                result=raw_cer_fast(ref,hyp)
                elapsed=time.perf_counter()-start
                self.assertEqual(result.substitutions+result.deletions+result.insertions,
                                 Levenshtein.distance(ref,hyp))
                self.assertEqual(n-result.deletions+result.insertions,len(hyp))
                self.assertEqual(result.reference_units,n)
                print(f"CER stress n={n} mutation_probability={error_probability} CER={result.rate:.6f} seconds={elapsed:.6f}",flush=True)

    def test_independent_mixed_errors(self):
        rng=random.Random(99)
        for _ in range(10):
            a="".join(rng.choices("abc é\n",k=200))
            b="".join(rng.choices("abc é\n",k=230))
            self.assertEqual(raw_cer(a,b).rate,raw_cer_fast(a,b).rate)

    def test_long_word_errors(self):
        rng=random.Random(7)
        words=rng.choices(["kawe","nok","makae","hmm","nasi"],k=10000)
        hyp=[w if rng.random()>.3 else "X" for w in words]
        result=raw_wer_fast(" ".join(words)," ".join(hyp))
        self.assertEqual(result.substitutions+result.deletions+result.insertions,
                         Levenshtein.distance(words,hyp))
