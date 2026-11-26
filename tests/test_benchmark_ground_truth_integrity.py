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


    def test_preprocessing_protocol(self):
        from redscribe.benchmark.benchmark_ground_truth import remove_speaker_labels
        from redscribe.benchmark.benchmark_reference import approve_reference, verify_reference
        text = " P1; Haa **\nP01:ikae\nPenemu duga; emm\nInterviewer: (noise) aa\nPenemuduga: P1; disebut\nP25; ulang ulang\nP26; kekal\nP1 tanpa kolon"
        expected = "Haa **\nikae\nemm\n(noise) aa\nP1; disebut\nulang ulang\nP26; kekal\nP1 tanpa kolon"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "synthetic.docx"
            doc = Document()
            for line in text.splitlines():
                doc.add_paragraph(line)
            doc.save(p)
            original = p.read_bytes()
            draft = extract_docx(str(p))
            cleaned, counts = remove_speaker_labels(draft.text)
            self.assertEqual(cleaned, expected)
            self.assertEqual(sum(counts.values()), 6)
            self.assertEqual(counts["P1;"], 1)
            self.assertEqual(counts["P01:"], 1)
            self.assertEqual(counts["Penemu duga;"], 1)
            checks = dict.fromkeys(("audio_verified", "coverage_verified", "speaker_labels_reviewed", "non_speech_reviewed"), True)
            manifest, scoring, info = approve_reference(p, cleaned, Path(tmp) / "private", reviewer_acknowledged=True, expected_source_sha256=draft.source_sha256, verification=checks, label_removal_history=[counts])
            self.assertEqual(scoring.read_text(encoding="utf-8"), expected)
            self.assertEqual(info["speaker_label_removal_history"], [counts])
            self.assertEqual(verify_reference(manifest), info)
            self.assertEqual(p.read_bytes(), original)
