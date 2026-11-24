"""Experimental model-major scheduler; independent of GUI and ASR adapters."""
from time import perf_counter
from uuid import uuid4

def run_model_major(models, recordings, *, open_model, infer, close_model,
                    checkpoint, stopped=lambda: False, warmup=None,
                    is_verified=lambda model, recording: False, progress=lambda *args: None):
    """Run one session per model. Checkpoint callback must persist each outcome.
    
    A failed inference invalidates the session: remaining recordings are marked
    not_run rather than silently reusing a potentially corrupted GPU context.
    """
    models, recordings = tuple(models), tuple(recordings)
    for model in models:
        if stopped():
            return
        pending = [r for r in recordings if not is_verified(model, r)]
        if not pending:
            continue
        session_id = uuid4().hex
        session = None
        try:
            start = perf_counter()
            try:
                progress(model,None,'loading')
                session = open_model(model)
            except Exception as exc:
                for recording in pending:
                    checkpoint(model, recording, {"status": "failed", "stage": "loading", "error": str(exc)})
                continue
            loading = perf_counter() - start
            warmup_seconds = None
            if warmup is not None:
                start = perf_counter()
                try:
                    warmup(session)
                except Exception as exc:
                    for recording in pending:
                        checkpoint(model, recording, {"status": "failed", "stage": "warmup", "error": str(exc)})
                    continue
                warmup_seconds = perf_counter() - start
            failed = False
            for recording in pending:
                if stopped():
                    return
                if failed:
                    checkpoint(model, recording, {"status": "not_run", "stage": "session_invalidated"})
                    continue
                start = perf_counter()
                try:
                    progress(model,recording,'running')
                    result = infer(session, recording)
                except Exception as exc:
                    failed = True
                    checkpoint(model, recording, {"status": "failed", "stage": "inference", "error": str(exc)})
                    continue
                if stopped():
                    return
                checkpoint(model, recording, {"status": "completed", "result": result,
                    "session_id": session_id, "session_loading_seconds": loading,
                    "session_warmup_seconds": warmup_seconds, "inference_seconds": perf_counter()-start})
        finally:
            if session is not None:
                close_model(session)
