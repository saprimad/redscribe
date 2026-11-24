import unittest
from redscribe.benchmark.benchmark_model_major_batch import validate_duration

class FullDurationTests(unittest.TestCase):
    def test_accept(self):
        for n in (1,180,2700,3600,7200):
            self.assertEqual(validate_duration(n),n)
    def test_reject(self):
        for n in (0,-1,7200.01,float("nan"),float("inf")):
            with self.assertRaises(ValueError):
                validate_duration(n)
