"""Local experiment management; no changes to ASR or scoring."""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from .benchmark_config import ordered_selection
from .benchmark_dataset import approve_dataset, verify_dataset
from .benchmark_reference import verify_reference
from .benchmark_structured_output import PRIVATE

SETTINGS = Path.home() / ".redscribe" / "benchmark-settings.json"

def saved_master():
    try:
        path = Path(json.loads(SETTINGS.read_text(encoding="utf-8"))["master"])
        return path if path.is_dir() else None
    except (OSError, ValueError, KeyError, TypeError):
        return None

def save_master(path):
    path = Path(path).resolve()
    if not path.is_dir():
        raise ValueError("Choose an existing master directory")
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS.with_name(uuid4().hex + ".tmp")
    try:
        tmp.write_text(json.dumps({"master": str(path)}), encoding="utf-8")
        tmp.replace(SETTINGS)
    finally:
        tmp.unlink(missing_ok=True)
    return path

def reference_cache(master):
    path = Path(master) / "_PRIVATE Frozen References"
    path.mkdir(exist_ok=True)
    return path

def new_experiment(master, rows, models, language, monitor, *, researcher_acknowledged=False, configuration_confirmation=None):
    if not researcher_acknowledged:
        raise ValueError("Explicit pairing approval required")
    models = ordered_selection(models)
    if not models or not rows:
        raise ValueError("Select recordings and models")
    # Only P-number pseudonyms may appear in the public-facing directory name.
    pid = rows[0]["participant_id"].strip()
    label = pid if len(rows) == 1 and re.fullmatch(r"P[0-9]{1,6}", pid) else f"Run_{len(rows)}recordings"
    root = Path(master).resolve() / (label + "_" + datetime.now().strftime("%Y-%m-%d_%H%M%S") + "_" + uuid4().hex[:8])
    root.mkdir(exist_ok=False)
    private = root / PRIVATE
    private.mkdir()
    (private / "CONFIDENTIAL - READ ME.txt").write_text(
        "Private research data. Folder segregation is not encryption. Do not distribute.", encoding="utf-8")
    frozen = private / "Frozen References"
    frozen.mkdir()
    copied = []
    for row in rows:
        source = Path(row["reference_manifest"]).resolve()
        info = verify_reference(source)
        dest = frozen / uuid4().hex
        dest.mkdir()
        shutil.copy2(source, dest / source.name)
        name = info["scoring_text_file"]
        # verify_reference has already checked this path stays within its directory.
        shutil.copy2(source.parent / name, dest / name)
        target = dest / source.name
        verify_reference(target)
        copied.append(dict(row, reference_manifest=str(target)))
    manifest = private / "approved_dataset.json"
    approve_dataset(copied, manifest, researcher_acknowledged=True, expected_count=len(rows))
    config = {"models": list(models), "language": language, "monitor": bool(monitor)}
    if configuration_confirmation is not None:
        config["configuration_confirmation"] = configuration_confirmation
    with (private / "experiment.json").open("x", encoding="utf-8") as stream:
        json.dump(config, stream, indent=2)
    return root, manifest

def load_experiment(root):
    root = Path(root).resolve()
    private = root / PRIVATE
    manifest = private / "approved_dataset.json"
    config = json.loads((private / "experiment.json").read_text(encoding="utf-8"))
    models = ordered_selection(config["models"])
    if not models or config["language"] not in ("ms", "en", None) or type(config["monitor"]) is not bool:
        raise ValueError("Invalid experiment configuration")
    verify_dataset(manifest)
    return manifest, models, config["language"], config["monitor"]
