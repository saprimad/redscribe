"""Observe real HF HTTP/Xet byte progress while preserving its cache/transfer code.

The Hub's internal progress-context hook is optional and restored after each
preparation. If unavailable, existing elapsed/stage notices remain in use.
No terminal scraping, extra downloads, credentials, or global stdout redirects.
"""
from contextlib import contextmanager
import importlib
import itertools
import math
import re
import threading
import time
from urllib.parse import urlsplit, unquote

_PATCH_LOCK = threading.RLock()
_IDS = itertools.count()


def safe_filename(description):
    # Some download descriptions can be URLs: never show query credentials.
    text = str(description or "model file").replace("\\", "/")
    text = unquote(urlsplit(text).path).rsplit("/", 1)[-1]
    return re.sub(r"[^\w.()\- …]", "_", text)[:120] or "model file"


def format_bytes(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} GB"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} MB"
    if value >= 1_000:
        return f"{value / 1_000:.1f} KB"
    return f"{value:.0f} B"


def progress_text(progress):
    downloaded = format_bytes(progress["downloaded"])
    total = progress["total"]
    if total is not None and total > 0:
        percent = min(100, 100 * progress["downloaded"] / total)
        # Do not round an incomplete transfer up to 100%.
        percent = min(percent, 99.9) if progress["downloaded"] < total else percent
        return f"Downloading {progress['filename']}: {percent:.1f}% | {downloaded} / {format_bytes(total)} (file progress)"
    return f"Downloading {progress['filename']}: {downloaded} received | total size unknown"


class ObservedProgress:
    """Delegate the original bar; only mirror its update calls to the GUI."""
    def __init__(self, bar, notify, description=None, clock=time.monotonic):
        self._bar = bar
        self._notify = notify
        self._clock = clock
        self._lock = threading.RLock()
        self._id = f"download_{next(_IDS)}"
        self._filename = safe_filename(description or getattr(bar, "desc", None))
        self._downloaded = float(getattr(bar, "n", 0) or 0)
        self._last_emit = float("-inf")
        self._last_value = None
        self.emit(force=True)

    def __getattr__(self, name):
        return getattr(self._bar, name)

    @property
    def total(self):
        return self._bar.total

    @total.setter
    def total(self, value):
        self._bar.total = value

    def update(self, amount=1):
        with self._lock:
            result = self._bar.update(amount)
            self._downloaded += float(amount or 0)
            self.emit()
            return result

    def emit(self, force=False):
        with self._lock:
            total = getattr(self._bar, "total", None)
            total = float(total) if total is not None else None
            if total is not None and (not math.isfinite(total) or total <= 0):
                total = None
            downloaded = max(0, self._downloaded)
            if not math.isfinite(downloaded):
                return
            if total is not None:
                downloaded = min(total, downloaded)
            now = self._clock()
            value = (downloaded, total)
            finished = total is not None and downloaded >= total
            if value == self._last_value or (not force and not finished and now - self._last_emit < 0.5):
                return
            self._last_emit, self._last_value = now, value
            try:
                self._notify("download", {"id": self._id, "filename": self._filename,
                                          "downloaded": downloaded, "total": total})
            except Exception:
                # UI closure must not change the Hub transfer/cache behaviour.
                pass


@contextmanager
def hub_download_progress(notify=None):
    if notify is None:
        yield
        return
    try:
        module = importlib.import_module("huggingface_hub.file_download")
    except ImportError:
        yield
        return
    # Resolve the original only after taking the lock, so overlapping tracked
    # preparations cannot accidentally capture each other's temporary wrapper.
    with _PATCH_LOCK:
        original = getattr(module, "_get_progress_bar_context", None)
        if not callable(original):
            yield
            return

        @contextmanager
        def observed_context(*args, **kwargs):
            with original(*args, **kwargs) as bar:
                # HTTP retry/resume can reuse an already observed progress bar.
                if isinstance(bar, ObservedProgress):
                    yield bar
                    return
                # Count only byte-transfer bars, not snapshot file-count bars.
                name = str(kwargs.get("name", ""))
                if name and not any(kind in name for kind in ("http_get", "xet_get")):
                    yield bar
                    return
                observed = ObservedProgress(bar, notify, kwargs.get("desc"))
                try:
                    yield observed
                finally:
                    # Interrupted transfers retain actual progress; never force 100%.
                    observed.emit(force=True)

        module._get_progress_bar_context = observed_context
        try:
            yield
        finally:
            module._get_progress_bar_context = original
