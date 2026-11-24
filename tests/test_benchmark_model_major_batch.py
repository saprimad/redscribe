import tempfile
import unittest
from pathlib import Path
from redscribe.benchmark.benchmark_reference import approve_reference
from redscribe.benchmark.benchmark_dataset import approve_dataset
from redscribe.benchmark.benchmark_model_major_batch import run_model_major_batch

class ModelMajorBatchTests(unittest.TestCase):
    def test_real_artifacts_resume(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            pairs=[]
            for i in range(2):
                audio=root/f"{i}.wav"; audio.write_bytes(bytes([i]))
                doc=root/f"{i}.docx"; doc.write_bytes(bytes([i,1]))
                ref,_,_=approve_reference(doc,"hmm kawe",root,reviewer_acknowledged=True)
                pairs.append({"participant_id":str(i),"audio":str(audio),"reference_manifest":str(ref)})
            dataset=root/"dataset.json"
            approve_dataset(pairs,dataset,researcher_acknowledged=True)
            loads=[]
            class Session:
                device="cuda"
                precision="float16"
                def transcribe(self,p): return "hmm kawe"
                def close(self): pass
            def factory(k):
                loads.append(k)
                return Session()
            def run():
                return run_model_major_batch(dataset,["a","b"],root/"out",session_factory=factory,duration_check=lambda p:1)
            state=run()
            self.assertEqual(loads,["a","b"])
            self.assertEqual(state["results"]["a"]["0"]["wer"],0)
            run()
            self.assertEqual(loads,["a","b"])
            (root/"out"/state["results"]["a"]["0"]["prediction_file"]).write_text("tampered")
            run()
            self.assertEqual(loads,["a","b","a"])
