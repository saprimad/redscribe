import unittest
from redscribe.benchmark.benchmark_provenance import runtime_provenance

class ProvenanceTests(unittest.TestCase):
    def test_schema(self):
        p = runtime_provenance()
        self.assertTrue(p['python'])
        self.assertIn('torch', p['packages'])
        self.assertIn('git_commit', p)
        self.assertIn(p['git_dirty'], (True, False, None))
