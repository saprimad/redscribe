import tempfile
import unittest
from redscribe.benchmark.benchmark_output_lock import output_lock

class OutputLockTests(unittest.TestCase):
    def test_conflicting_writer_and_release(self):
        with tempfile.TemporaryDirectory() as d:
            with output_lock(d):
                with self.assertRaises(RuntimeError):
                    with output_lock(d):
                        self.fail("Second writer entered")
            with output_lock(d):
                pass
    def test_release_on_exception(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                with output_lock(d):
                    raise ValueError("synthetic failure")
            with output_lock(d):
                pass
