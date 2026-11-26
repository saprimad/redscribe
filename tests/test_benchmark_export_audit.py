import tempfile
import unittest
from pathlib import Path
from openpyxl import load_workbook
from redscribe.benchmark.benchmark_matrix_reporting import export_matrix_reporting
from redscribe.benchmark.benchmark_publication import export_publication
from redscribe.benchmark.benchmark_export_audit import audit_exports

class ExportAuditTests(unittest.TestCase):
    def test_tamper(self):
        row=dict(status="completed",wer=.1,cer=.1,word_substitutions=1,word_deletions=0,word_insertions=0,reference_words=10,char_substitutions=1,char_deletions=0,char_insertions=0,reference_characters=10)
        state={"identity":{"models":["a"],"recordings":["P1"]},"results":{"a":{"P1":row}}}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            export_matrix_reporting(p,state)
            export_publication(p,state)
            self.assertTrue(all(audit_exports(p,state).values()))
            f=p/"recording_results.csv"
            f.write_text(f.read_text(encoding="utf-8-sig").replace("0.1","0.9"),encoding="utf-8-sig")
            self.assertFalse(audit_exports(p,state)["recording_results.csv"])
            wb=load_workbook(p/"scientific_results.xlsx")
            wb["Model summary"]["A2"]="tampered"
            wb.save(p/"scientific_results.xlsx")
            wb.close()
            self.assertFalse(audit_exports(p,state)["Model summary"])
