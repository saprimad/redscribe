import unittest
from redscribe.benchmark.benchmark_provenance import snapshot_revision

class SnapshotTests(unittest.TestCase):
    def test_revision(self):
        self.assertEqual(snapshot_revision('/cache/snapshots/'+'a'*40), 'a'*40)
        self.assertIsNone(snapshot_revision('/local/model'))
        self.assertIsNone(snapshot_revision('/cache/snapshots/main'))
