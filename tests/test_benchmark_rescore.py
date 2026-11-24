import json
import tempfile
import unittest
from pathlib import Path
from hashlib import sha256
from redscribe.benchmark.benchmark_reference import approve_reference
from redscribe.benchmark.benchmark_rescore import rescore

class RescoreTests(unittest.TestCase):
    def test_verified_and_tampered(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            source = p / "source.docx"
            source.write_bytes(b"synthetic source")
            refpath, _, ref = approve_reference(source, "kawe", p, reviewer_acknowledged=True)
            pred = p / "prediction.txt"
            pred.write_bytes(b"kawe")
            row = dict(status="completed", prediction_file=pred.name, prediction_sha256=sha256(b"kawe").hexdigest(),
                       prediction_bytes=4, wer=0, cer=0, word_substitutions=0, word_deletions=0,
                       word_insertions=0, char_substitutions=0, char_deletions=0, char_insertions=0,
                       reference_words=1, reference_characters=4)
            run = p / "manifest.json"
            run.write_text(json.dumps(dict(reference_id=ref["reference_id"], reference_sha256=ref["approved_text_sha256"], model_results={"test":row})))
            self.assertEqual(rescore(run, refpath)["results"][0]["status"], "verified")
            row["cer"] = 1
            run.write_text(json.dumps(dict(reference_id=ref["reference_id"], reference_sha256=ref["approved_text_sha256"], model_results={"test":row})))
            self.assertEqual(rescore(run, refpath)["results"][0]["status"], "mismatch")
            pred.write_bytes(b"makan")
            self.assertEqual(rescore(run, refpath)["results"][0]["status"], "unverifiable")
