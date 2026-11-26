"""Local, best-effort runtime provenance; never queries network."""
import platform
import sys
import subprocess
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

def runtime_provenance():
    packages = {}
    for name in ("torch", "faster-whisper", "ctranslate2", "transformers", "python-docx", "jiwer", "numpy", "pyannote.audio"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    root = Path(__file__).resolve().parents[2]
    def git(*args):
        try:
            return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL, timeout=5, text=True).strip()
        except (OSError, subprocess.SubprocessError):
            return None
    commit = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain") if commit else None
    return {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "packages": packages, "git_commit": commit,
            "git_dirty": bool(dirty) if dirty is not None else None}


def hardware_provenance():
    import os
    result = {"logical_cpu_count": os.cpu_count(), "ram_bytes": None, "cuda_build_version": None,
              "gpu_inventory": None, "nvidia_driver_inventory": None}
    try:
        import psutil
        result["ram_bytes"] = psutil.virtual_memory().total
    except Exception:
        pass
    try:
        import torch
        result["cuda_build_version"] = torch.version.cuda
        result["gpu_inventory"] = [{"index": i, "name": torch.cuda.get_device_properties(i).name,
                                    "vram_bytes": torch.cuda.get_device_properties(i).total_memory}
                                   for i in range(torch.cuda.device_count())]
    except Exception:
        pass
    try:
        result["nvidia_driver_inventory"] = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,name,driver_version,memory.total", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL, timeout=5, text=True).strip().splitlines()
    except (OSError, subprocess.SubprocessError):
        pass
    return result

def snapshot_revision(path):
    parts = Path(path).parts
    for i, part in enumerate(parts[:-1]):
        if part == "snapshots":
            candidate = parts[i+1]
            if len(candidate) == 40 and all(c in "0123456789abcdef" for c in candidate):
                return candidate
    return None
