import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from redscribe.benchmark.benchmark_experiments import new_experiment, load_experiment, save_master, saved_master
from redscribe.benchmark.benchmark_reference import approve_reference
from redscribe.benchmark.benchmark_structured_output import PRIVATE, validate_output_root

class ExperimentTests(unittest.TestCase):
    def test_automatic_manifest_and_unique_folders(self):
        with tempfile.TemporaryDirectory() as d:
            master = Path(d)
            audio = master / "audio.wav"
            audio.write_bytes(b"audio")
            doc = master / "ref.docx"
            doc.write_bytes(b"reference")
            ref, _, _ = approve_reference(doc, "hmm kawe", master, reviewer_acknowledged=True)
            rows = [dict(participant_id="P1", audio=str(audio), reference_manifest=str(ref))]
            with self.assertRaises(ValueError):
                new_experiment(master, rows, ["turbo"], "ms", True)
            a, manifest = new_experiment(master, rows, ["turbo"], "ms", True, researcher_acknowledged=True)
            b, _ = new_experiment(master, rows, ["turbo"], "ms", True, researcher_acknowledged=True)
            self.assertNotEqual(a, b)
            self.assertEqual(manifest.parent, a / PRIVATE)
            self.assertEqual(validate_output_root(a), a)
            self.assertEqual(load_experiment(a), (manifest, ("turbo",), "ms", True))
            audio.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                load_experiment(a)

    def test_master_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch("redscribe.benchmark.benchmark_experiments.SETTINGS", root / "settings" / "config.json"):
                self.assertIsNone(saved_master())
                save_master(root)
                self.assertEqual(saved_master(), root)
