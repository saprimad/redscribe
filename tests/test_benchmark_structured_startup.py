import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from redscribe.benchmark.benchmark_structured_output import (
    PRIVATE, PDF, EXCEL, SUPPORT, run_structured_batch, validate_output_root,
    verify_publication,
)
from redscribe.benchmark.benchmark_reference import approve_reference
from redscribe.benchmark.benchmark_dataset import approve_dataset


class StructuredStartupTests(unittest.TestCase):
    def test_nonempty_output_is_rejected_without_modification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = root / "approved_dataset.json"
            manifest.write_text("untouched", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "separate empty output folder"):
                validate_output_root(root)
            self.assertEqual(manifest.read_text(encoding="utf-8"), "untouched")
            self.assertFalse((root / PRIVATE).exists())

    def test_structured_batch_executes_and_publishes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            audio = root / "synthetic.wav"
            audio.write_bytes(b"synthetic audio")
            doc = root / "synthetic.docx"
            doc.write_bytes(b"synthetic reference source")
            ref, _, _ = approve_reference(doc, "hmm kawe", root,
                                          reviewer_acknowledged=True)
            dataset = root / "approved_dataset.json"
            approve_dataset([dict(participant_id="P1", audio=str(audio),
                                  reference_manifest=str(ref))], dataset,
                            researcher_acknowledged=True)
            output = root / "output"
            events = []
            class Session:
                device = "cuda"
                precision = "float16"
                def transcribe(self, path):
                    return "hmm kawe"
                def close(self):
                    pass
            state = run_structured_batch(
                dataset, ["large-v3"], output,
                session_factory=lambda key: Session(),
                duration_check=lambda path: 1,
                progress=lambda *event: events.append(event),
            )
            self.assertEqual(state["results"]["large-v3"]["P1"]["wer"], 0)
            self.assertEqual(set(p.name for p in output.iterdir()),
                             {PRIVATE, PDF, EXCEL, SUPPORT})
            self.assertTrue(verify_publication(output))
            self.assertTrue((output / PDF).read_bytes().startswith(b"%PDF-"))
            self.assertTrue((output / PRIVATE / "matrix.json").is_file())
            self.assertIn(("Startup", None, "Initialising checkpoint"), events)
            self.assertIn(("large-v3", "P1", "running"), events)
            self.assertIn(("Reporting", None, "Publishing structured scientific reports"), events)
