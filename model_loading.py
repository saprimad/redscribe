"""Phase notifications for model preparation; no invented download percentages."""
from contextlib import contextmanager
from download_progress import hub_download_progress


@contextmanager
def model_preparation(label, notify=None):
    notify = notify or (lambda state, message: None)
    notify("start", f"Preparing model: {label}")
    notify("info", "Checking saved model files. Missing files download automatically on first use; this may take several minutes. Keep the app open.")
    try:
        with hub_download_progress(notify):
            yield
    except BaseException:
        notify("failed", f"Model preparation interrupted: {label}. No model-ready confirmation was received.")
        raise
    else:
        notify("ready", f"Model ready: {label}. Ready for transcription.")
