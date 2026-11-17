"""Run: python -m unittest discover -s tests -p 'test_benchmark_reference.py'"""
import tempfile
import unittest
from pathlib import Path
from docx import Document
from benchmark_ground_truth import extract_docx
from benchmark_reference import approve_reference, verify_reference, sha256_file


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.word = self.root / "synthetic.docx"
        doc = Document()
        doc.add_paragraph("Interviewer: Apa pandangan demo?")
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Participant"
        table.cell(0, 1).text = "Hmm kawe dok setuju"
        table.cell(1, 0).text = "Interviewer"
        table.cell(1, 1).text = "Kenapa?"
        doc.add_paragraph("Penutup")
        doc.save(self.word)

    def test_extract_preserves_order_and_dialect(self):
        original_hash = sha256_file(self.word)
        draft = extract_docx(str(self.word))
        self.assertEqual(draft.blocks, (
            "Interviewer: Apa pandangan demo?", "Participant",
            "Hmm kawe dok setuju", "Interviewer", "Kenapa?", "Penutup",
        ))
        self.assertIn("Hmm kawe dok setuju", draft.text)
        self.assertEqual(sha256_file(self.word), original_hash)

    def test_freeze_requires_approval_and_detects_mutations(self):
        draft = extract_docx(str(self.word))
        with self.assertRaises(ValueError):
            approve_reference(str(self.word), draft.text, self.root / "private")
        output = self.root / "private"
        manifest_path, text_path, info = approve_reference(
            str(self.word), "Apa pandangan demo?\nHmm kawe dok setuju",
            output, reviewer_acknowledged=True)
        self.assertEqual(verify_reference(manifest_path)["source_sha256"], sha256_file(self.word))
        self.assertEqual(text_path.read_text(encoding="utf-8"),
                         "Apa pandangan demo?\nHmm kawe dok setuju")
        text_path.write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_reference(manifest_path)

    def test_changed_original_docx_is_rejected_after_approval(self):
        manifest, _, _ = approve_reference(
            str(self.word), "Apa pandangan demo? Hmm kawe dok setuju",
            self.root / "private", reviewer_acknowledged=True)
        self.assertTrue(verify_reference(manifest)["source_sha256"])
        changed = Document(str(self.word))
        changed.add_paragraph("This is a later edit.")
        changed.save(self.word)
        with self.assertRaisesRegex(ValueError, "changed since approval"):
            verify_reference(manifest)

    def test_legacy_manifest_cannot_claim_source_verified(self):
        import json
        manifest, _, _ = approve_reference(
            str(self.word), "sample text", self.root / "private",
            reviewer_acknowledged=True)
        info = json.loads(manifest.read_text(encoding="utf-8"))
        del info["source_path"]
        manifest.write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "re-approve DOCX"):
            verify_reference(manifest)

    def test_empty_document_rejected(self):
        blank = self.root / "empty.docx"
        Document().save(blank)
        with self.assertRaises(ValueError):
            extract_docx(str(blank))


if __name__ == "__main__":
    unittest.main()
