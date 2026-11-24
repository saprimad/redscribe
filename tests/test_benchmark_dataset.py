import tempfile
import unittest
from pathlib import Path
from redscribe.benchmark.benchmark_reference import approve_reference
from redscribe.benchmark.benchmark_dataset import approve_dataset, verify_dataset

class DatasetTests(unittest.TestCase):
    def test_approval_duplicates_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            audio = p / "audio.wav"
            audio.write_bytes(b"synthetic audio")
            source = p / "source.docx"
            source.write_bytes(b"synthetic docx")
            ref, _, _ = approve_reference(source, "kawe", p, reviewer_acknowledged=True)
            pair = dict(participant_id="P01", audio=str(audio), reference_manifest=str(ref))
            output = p / "dataset.json"
            with self.assertRaises(ValueError):
                approve_dataset([pair], output)
            with self.assertRaises(ValueError):
                approve_dataset([pair, dict(pair, participant_id="P02")], output, researcher_acknowledged=True)
            with self.assertRaises(ValueError):
                approve_dataset([pair], output, researcher_acknowledged=True, expected_count=25)
            approve_dataset([pair], output, researcher_acknowledged=True, expected_count=1)
            self.assertEqual(verify_dataset(output)["count"], 1)
            audio.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_dataset(output)
