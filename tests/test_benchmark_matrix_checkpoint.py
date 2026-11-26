import tempfile
import unittest
from pathlib import Path
from redscribe.benchmark.benchmark_matrix_checkpoint import MatrixCheckpoint
from redscribe.benchmark.benchmark_model_major import run_model_major

class MatrixCheckpointTests(unittest.TestCase):
    def test_restart_and_verified_skip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"matrix.json"
            identity={"models":["a","b"],"recordings":["p1","p2"],"dataset_hash":"synthetic"}
            c=MatrixCheckpoint(p,identity)
            c.record("a","p1",{"status":"completed","result":"verified"})
            c=MatrixCheckpoint(p,identity)
            calls=[]
            run_model_major(identity["models"],identity["recordings"],open_model=lambda m:m,
                infer=lambda m,r:calls.append((m,r)) or "new",close_model=lambda m:None,
                checkpoint=c.record,is_verified=lambda m,r:c.verified(m,r,lambda m,r,row:row["result"]=="verified"))
            self.assertEqual(calls,[("a","p2"),("b","p1"),("b","p2")])
            self.assertEqual(MatrixCheckpoint(p,identity).state,c.state)
            with self.assertRaises(ValueError):
                MatrixCheckpoint(p,{**identity,"dataset_hash":"changed"})
            self.assertFalse(c.verified("a","p1",lambda *a:False))
