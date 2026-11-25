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


    def test_optional_speaker_prefix_removal(self):
        from redscribe.benchmark.benchmark_ground_truth import remove_speaker_labels
        text = "Penemu duga: Haa, P1: disebut\nP01: emm ikae\nP25: aa aa\nInterviewer: betul\nPenemuduga: ya\nP26: kekal\nP1 tanpa kolon"
        expected = "Haa, P1: disebut\nemm ikae\naa aa\nbetul\nya\nP26: kekal\nP1 tanpa kolon"
        result, counts = remove_speaker_labels(text)
        self.assertEqual(result, expected)
        self.assertEqual(sum(counts.values()), 5)
        self.assertEqual(remove_speaker_labels(result), (result, {}))
