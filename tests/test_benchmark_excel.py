"""Synthetic XLSX output integrity checks; no Office, GPU or model weights required."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from benchmark_excel import export_excel, export_from_manifest
from benchmark_reporting import build_summary

M = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

class ExcelReportingTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.directory = Path(self.root.name)
        self.state = {
            "models": ["large-v3", "tiny"],
            "items": [
                {"audio": "safe.wav", "audio_sha256": "hash-a", "status": "completed",
                 "model_results": {
                    "large-v3": {
                        "status": "completed", "word_substitutions": 1,
                        "word_deletions": 0, "word_insertions": 0,
                        "reference_words": 5, "wer": 0.2,
                        "char_substitutions": 2, "char_deletions": 0,
                        "char_insertions": 0, "reference_characters": 20,
                        "cer": 0.1,
                    },
                    "tiny": {"status": "failed", "error": "=HYPERLINK(\"bad\")",
                             "wer": None, "cer": None},
                 }},
                {"audio": "=1+1.wav", "audio_sha256": "hash-b", "status": "failed",
                 "error": "synthetic unreadable source", "model_results": {}},
            ],
        }

    def test_xlsx_has_four_expected_sheets_and_typed_metrics(self):
        output = export_excel(self.directory, self.state)
        self.assertTrue(output.is_file())
        with zipfile.ZipFile(output) as archive:
            self.assertIsNone(archive.testzip())
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            names = [
                s.attrib["name"]
                for s in workbook.findall(f".//{{{M}}}sheet")
            ]
            self.assertEqual(
                names, ["Model Summary", "Recording Results",
                        "Error Breakdown", "Run Status"])
            sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            cell = sheet.find(f".//{{{M}}}c[@r='K2']")
            self.assertIsNotNone(cell)
            self.assertEqual(cell.attrib.get("s"), "2")
            self.assertEqual(cell.find(f"{{{M}}}v").text, "0.2")
            self.assertEqual(
                len(sheet.findall(f".//{{{M}}}sheetData/{{{M}}}row")),
                1 + len(build_summary(self.state)))
            # All XLSX text is escaped into inline strings, never formulas.
            for n in range(1, 5):
                xml = ET.fromstring(archive.read(f"xl/worksheets/sheet{n}.xml"))
                self.assertFalse(xml.findall(f".//{{{M}}}f"))
            detail = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
            texts = [n.text or "" for n in detail.findall(f".//{{{M}}}t")]
            self.assertIn("=HYPERLINK(\"bad\")", texts)
            self.assertIn("=1+1.wav", texts)

    def test_missing_metrics_are_blank_not_zero(self):
        export_excel(self.directory, self.state)
        with zipfile.ZipFile(self.directory / "benchmark_summary.xlsx") as archive:
            xml = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            # Tiny model has no scored WER or CER.
            self.assertIsNone(xml.find(f".//{{{M}}}c[@r='K3']"))
            self.assertIsNone(xml.find(f".//{{{M}}}c[@r='L3']"))

    def test_invalid_manifest_rejected_without_spreadsheet(self):
        import json
        manifest = self.directory / "manifest.json"
        manifest.write_text(json.dumps({"unrecognised": True}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Expected RedScribe"):
            export_from_manifest(manifest)

if __name__ == "__main__":
    unittest.main()
