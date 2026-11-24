"""Offline matrix accuracy audit using JiWER's separate scoring interface."""
import json
import math
from pathlib import Path
from .benchmark_dataset import verify_dataset
from .benchmark_reference import verify_reference,sha256_file

def audit_matrix(directory,dataset_path):
    import jiwer
    directory=Path(directory).resolve()
    state=json.loads((directory/"matrix.json").read_text(encoding="utf-8"))
    dataset=verify_dataset(dataset_path)
    if state["identity"]["dataset"]!=dataset:
        raise ValueError("Dataset identity mismatch")
    pairs={p["participant_id"]:p for p in dataset["pairs"]}
    results=[]
    for model in state["identity"]["models"]:
        for pid in state["identity"]["recordings"]:
            row=state["results"].get(model,{}).get(pid,{})
            item={"model_key":model,"participant_id":pid,"status":"skipped"}
            if row.get("status")=="completed":
                try:
                    p=pairs[pid]
                    manifest=Path(p["reference_manifest"])
                    ref=verify_reference(manifest)
                    text=(manifest.parent/ref["scoring_text_file"]).read_bytes().decode("utf-8")
                    path=(directory/row["prediction_file"]).resolve()
                    if path.parent!=directory or sha256_file(path)!=row["prediction_sha256"]:
                        raise ValueError("Prediction integrity mismatch")
                    pred=path.read_bytes().decode("utf-8")
                    # JiWER uses RapidFuzz internally; this is a separate interface,
                    # not an independent edit-distance implementation.
                    w=jiwer.process_words(" ".join(text.split())," ".join(pred.split()),
                        reference_transform=jiwer.Compose([jiwer.ReduceToListOfListOfWords()]),
                        hypothesis_transform=jiwer.Compose([jiwer.ReduceToListOfListOfWords()]))
                    c=jiwer.process_characters(text,pred,
                        reference_transform=jiwer.Compose([jiwer.ReduceToListOfListOfChars()]),
                        hypothesis_transform=jiwer.Compose([jiwer.ReduceToListOfListOfChars()]))
                    for prefix,metric,n,score in (("word","wer",len(text.split()),w),("char","cer",len(text),c)):
                        total=score.substitutions+score.deletions+score.insertions
                        reported=sum(row[prefix+"_"+k] for k in ("substitutions","deletions","insertions"))
                        expected=total/n if n else None
                        denom="reference_words" if prefix=="word" else "reference_characters"
                        if total!=reported or row[denom]!=n or row[metric]!=expected:
                            raise ValueError(metric+" mismatch")
                    item["status"]="verified"
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    item.update(status="mismatch",reason=str(exc))
            results.append(item)
    return results
