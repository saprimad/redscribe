import tempfile
import unittest
from pathlib import Path
from hashlib import sha256
from benchmark_pilot import _persist_prediction
from benchmark_metrics import raw_cer

class PredictionIntegrityTests(unittest.TestCase):
    def test_exact_bytes_and_scoring(self):
        for text in ("", "Hmm  kawe\r\n setuju ", "e\u0301", "ikae\n"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                restored, meta = _persist_prediction(folder, "prediction", text)
                payload = (folder / meta["prediction_file"]).read_bytes()
                self.assertEqual(payload, text.encode("utf-8"))
                self.assertEqual(meta["prediction_sha256"], sha256(payload).hexdigest())
                self.assertEqual(meta["prediction_bytes"], len(payload))
                self.assertEqual(restored, text)
                self.assertEqual(raw_cer("kawe", restored), raw_cer("kawe", text))
                with self.assertRaises(FileExistsError):
                    _persist_prediction(folder, "prediction", "replacement")
                self.assertEqual((folder / meta["prediction_file"]).read_bytes(), payload)
