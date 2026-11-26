import unittest
from redscribe.benchmark.benchmark_configuration import verify_configuration, verify_parameters

class ConfigurationTests(unittest.TestCase):
    def test_strict(self):
        self.assertEqual(verify_configuration("cuda:0", "torch.float16"), ("cuda", "float16"))
        for d,p in [("cpu","float16"),("cuda","float32"),("cuda",None),(None,"float16")]:
            with self.assertRaises(RuntimeError):
                verify_configuration(d,p)
        with self.assertRaises(RuntimeError):
            verify_parameters([])
