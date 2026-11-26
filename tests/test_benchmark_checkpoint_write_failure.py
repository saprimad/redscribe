import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from redscribe.benchmark.benchmark_matrix_checkpoint import MatrixCheckpoint

class CheckpointWriteFailureTests(unittest.TestCase):
    def test_failed_replace_preserves_disk_and_memory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"matrix.json"
            c=MatrixCheckpoint(p,{"models":["m"],"recordings":["p"]})
            c.record("m","p",{"status":"completed"})
            before=p.read_bytes()
            with patch.object(Path,"replace",side_effect=OSError(28,"No space")):
                with self.assertRaises(OSError):
                    c.record("m","p",{"status":"failed"})
            self.assertEqual(p.read_bytes(),before)
            self.assertEqual(c.state["results"]["m"]["p"]["status"],"completed")
            self.assertEqual(list(Path(d).glob("*.tmp")),[])
