import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from redscribe.benchmark import benchmark_pilot as pilot
from redscribe.benchmark.benchmark_reference import approve_reference
from redscribe.benchmark.benchmark_rescore import rescore
from redscribe.benchmark.benchmark_dataset import approve_dataset, verify_dataset

class EndToEndTests(unittest.TestCase):
    def test_real_artifacts_and_failure_continuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "sample.wav"
            audio.write_bytes(b"synthetic")
            source = root / "source.docx"
            source.write_bytes(b"synthetic")
            ref, _, _ = approve_reference(source, "kawe hmm", root, reviewer_acknowledged=True)
            dataset = root / "dataset.json"
            approve_dataset([dict(participant_id="P01", audio=str(audio), reference_manifest=str(ref))],
                            dataset, researcher_acknowledged=True, expected_count=1)
            verify_dataset(dataset)
            keys = list(pilot.ASR_MODEL_LABELS)[:2]
            def fake(key, audio, language, stopped, provenance):
                if key == keys[0]:
                    raise RuntimeError("synthetic GPU failure")
                provenance.update(engine="synthetic")
                return "kawe hmm", 0.1, 0.2, "cuda", "float16", ""
            with patch.object(pilot, "_decode_duration", return_value=1.0), patch.object(pilot, "_transcribe", side_effect=fake), patch.object(pilot, "hardware_provenance", return_value={}):
                folder, run = pilot.run_single_pilot(audio, ref, keys, root / "runs")
            self.assertEqual(run["status"], "completed_with_errors")
            self.assertEqual(run["model_results"][keys[0]]["status"], "failed")
            self.assertEqual(run["model_results"][keys[1]]["wer"], 0)
            self.assertTrue((folder / "results.csv").is_file())
            report = rescore(folder / "manifest.json", ref)
            self.assertEqual([r["status"] for r in report["results"]], ["skipped", "verified"])
            prediction = folder / run["model_results"][keys[1]]["prediction_file"]
            prediction.write_bytes(b"tampered")
            self.assertEqual(rescore(folder / "manifest.json", ref)["results"][1]["status"], "unverifiable")
