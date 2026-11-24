import tempfile
import unittest
from pathlib import Path
from openpyxl import load_workbook
from redscribe.benchmark.benchmark_publication import export_publication

class PublicationTests(unittest.TestCase):
    def test_exports(self):
        row=dict(status="completed",wer=.1,cer=.1,word_substitutions=1,word_deletions=0,word_insertions=0,reference_words=10,char_substitutions=1,char_deletions=0,char_insertions=0,reference_characters=10)
        state={"identity":{"models":["a"],"recordings":["P1"]},"results":{"a":{"P1":row}}}
        with tempfile.TemporaryDirectory() as d:
            export_publication(d,state)
            p=Path(d)
            wb=load_workbook(p/"scientific_results.xlsx")
            self.assertEqual(wb.sheetnames,["Model summary","Recording results","Efficiency"])
            wb.close()
            for name in ("corpus_accuracy","wer_distribution"):
                for ext in ("svg","png"):
                    self.assertGreater((p/(name+"."+ext)).stat().st_size,0)
            state["results"]={}
            export_publication(d,state)
            self.assertFalse((p/"corpus_accuracy.png").exists())
