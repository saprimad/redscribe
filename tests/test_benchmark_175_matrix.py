import unittest
from redscribe.benchmark.benchmark_model_major import run_model_major

class FullMatrixStress(unittest.TestCase):
    def test_175_cells_and_resume(self):
        models=list(range(7)); recordings=list(range(25))
        loads=[]; closed=[]; outcomes={}
        def load(m):
            loads.append(m)
            return m
        def save(m,p,row):
            outcomes[m,p]=row
        run_model_major(models,recordings,open_model=load,infer=lambda m,p: "hmm kawe",
            close_model=closed.append,checkpoint=save)
        self.assertEqual(len(outcomes),175)
        self.assertEqual(loads,models)
        self.assertEqual(closed,models)
        self.assertTrue(all(r["status"]=="completed" for r in outcomes.values()))
        run_model_major(models,recordings,open_model=load,infer=lambda m,p: self.fail("unexpected inference"),
            close_model=closed.append,checkpoint=save,is_verified=lambda m,p:(m,p) in outcomes)
        self.assertEqual(loads,models)
