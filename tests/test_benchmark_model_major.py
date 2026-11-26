import unittest
from redscribe.benchmark.benchmark_model_major import run_model_major

class ModelMajorTests(unittest.TestCase):
    def test_order_and_loading(self):
        events, rows = [], []
        def load(m):
            events.append(("load", m))
            return m
        def infer(m, r):
            events.append((m, r))
            return r
        run_model_major(["a","b"], range(25), open_model=load, infer=infer,
                        close_model=lambda m: events.append(("close",m)),
                        checkpoint=lambda *r: rows.append(r))
        self.assertEqual(len(rows), 50)
        self.assertEqual(events[:3], [("load","a"),("a",0),("a",1)])
        self.assertEqual(events[26:29], [("close","a"),("load","b"),("b",0)])
        self.assertEqual(events[-1], ("close","b"))

    def test_failure_isolation(self):
        rows, closed = [], []
        def infer(m,r):
            if m == "a":
                raise RuntimeError("synthetic failure")
            return r
        run_model_major(["a","b"], [1,2], open_model=lambda m:m, infer=infer,
                        close_model=closed.append, checkpoint=lambda *r:rows.append(r))
        self.assertEqual([r[2]["status"] for r in rows],
                         ["failed","not_run","completed","completed"])
        self.assertEqual(closed, ["a","b"])

    def test_cancel_closes_session(self):
        rows, closed = [], []
        run_model_major(["a","b"], [1,2], open_model=lambda m:m, infer=lambda m,r:r,
                        close_model=closed.append, checkpoint=lambda *r:rows.append(r),
                        stopped=lambda:bool(rows))
        self.assertEqual(len(rows),1)
        self.assertEqual(closed,["a"])
