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
