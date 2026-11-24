import tempfile
import unittest
from pathlib import Path
from docx import Document
from benchmark_ground_truth import extract_docx

class GroundTruthIntegrityTests(unittest.TestCase):
    def test_whitespace_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.docx"
            d = Document()
            d.add_paragraph(" Hmm\tkawe\nsetuju ")
            t = d.add_table(rows=1, cols=2)
            t.cell(0,0).text = "ikae"
            t.cell(0,1).text = "ikae"
            d.add_paragraph("makae")
            d.save(p)
            before = p.read_bytes()
            result = extract_docx(str(p))
            self.assertEqual(result.blocks, (" Hmm\tkawe\nsetuju ", "ikae", "ikae", "makae"))
            self.assertEqual(p.read_bytes(), before)
