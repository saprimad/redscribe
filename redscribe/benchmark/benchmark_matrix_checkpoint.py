"""Persistent model-by-recording checkpoint for a single writer."""
import json
from pathlib import Path
from uuid import uuid4

class MatrixCheckpoint:
    def __init__(self, path, identity):
        self.path = Path(path)
        self.identity = json.loads(json.dumps(identity, allow_nan=False))
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
            if self.state.get("schema") != 1 or self.state.get("identity") != self.identity:
                raise ValueError("Checkpoint identity mismatch")
        else:
            self.state = {"schema":1, "identity":self.identity, "results":{}}
            self._save()

    def _save(self):
        tmp = self.path.with_name(self.path.name+"."+uuid4().hex+".tmp")
        try:
            with tmp.open("x", encoding="utf-8") as stream:
                json.dump(self.state, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                import os
                os.fsync(stream.fileno())
            tmp.replace(self.path)
        finally:
            tmp.unlink(missing_ok=True)

    def record(self, model, recording, outcome):
        if model not in self.identity["models"] or recording not in self.identity["recordings"]:
            raise ValueError("Unknown matrix cell")
        self.state["results"].setdefault(model,{})[recording] = outcome
        self._save()

    def verified(self, model, recording, verify_artifact):
        row = self.state["results"].get(model,{}).get(recording)
        return bool(row and row.get("status")=="completed" and verify_artifact(model,recording,row))
