import tempfile
import unittest
from pathlib import Path
from redscribe.benchmark.benchmark_export_integrity import TABLES,write_export_manifest,verify_export_manifest

class ExportIntegrityTests(unittest.TestCase):
    def test_changed_figure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for n in TABLES:
                (p/n).write_bytes(b'{"identity":{}}')
            f=p/"corpus_accuracy.svg"
            f.write_bytes(b"<svg/>")
            write_export_manifest(p)
            self.assertTrue(all(verify_export_manifest(p).values()))
            f.write_bytes(b"<svg>changed</svg>")
            self.assertFalse(verify_export_manifest(p)[f.name])
