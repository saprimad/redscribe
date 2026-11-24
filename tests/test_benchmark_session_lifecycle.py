import unittest
from redscribe.benchmark.benchmark_model_major import run_model_major

class SessionLifecycleTests(unittest.TestCase):
    def test_verified_skip_and_warmup(self):
        events, rows = [], []
        run_model_major(["a","b"], [1,2], open_model=lambda m:events.append(("load",m)) or m,
            infer=lambda s,r:events.append(("infer",s,r)) or r,
            close_model=lambda s:events.append(("close",s)),
            checkpoint=lambda *r:rows.append(r),
            warmup=lambda s:events.append(("warmup",s)),
            is_verified=lambda m,r:m=="a" or r==1)
        self.assertEqual(events,[("load","b"),("warmup","b"),("infer","b",2),("close","b")])
        self.assertEqual(len(rows),1)
        self.assertIsNotNone(rows[0][2]["session_warmup_seconds"])
        self.assertTrue(rows[0][2]["session_id"])

    def test_warmup_failure(self):
        rows, closed = [], []
        def warm(s):
            raise RuntimeError("warmup failed")
        run_model_major(["a"],[1,2],open_model=lambda m:m,infer=lambda *a:self.fail(),
            close_model=closed.append,checkpoint=lambda *r:rows.append(r),warmup=warm)
        self.assertEqual(closed,["a"])
        self.assertEqual([r[2]["stage"] for r in rows],["warmup","warmup"])
