"""Experimental model-major scheduler; independent of GUI and ASR adapters."""
from time import perf_counter

def run_model_major(models, recordings, *, open_model, infer, close_model,
                    checkpoint, stopped=lambda: False):
    """Run one session per model. Checkpoint callback must persist each outcome.
    
    A failed inference invalidates the session: remaining recordings are marked
    not_run rather than silently reusing a potentially corrupted GPU context.
    """
    models, recordings = tuple(models), tuple(recordings)
    for model in models:
        if stopped():
            return
        session = None
        try:
            start = perf_counter()
            try:
                session = open_model(model)
            except Exception as exc:
                for recording in recordings:
                    checkpoint(model, recording, {"status": "failed", "stage": "loading", "error": str(exc)})
                continue
            loading = perf_counter() - start
            failed = False
            for recording in recordings:
                if stopped():
                    return
                if failed:
                    checkpoint(model, recording, {"status": "not_run", "stage": "session_invalidated"})
                    continue
                start = perf_counter()
                try:
                    result = infer(session, recording)
                except Exception as exc:
                    failed = True
                    checkpoint(model, recording, {"status": "failed", "stage": "inference", "error": str(exc)})
                    continue
                if stopped():
                    return
                checkpoint(model, recording, {"status": "completed", "result": result,
                    "session_loading_seconds": loading, "inference_seconds": perf_counter()-start})
        finally:
            if session is not None:
                close_model(session)
