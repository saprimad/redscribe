"""Process-wide exclusion for desktop ASR workers."""
import threading
_lock = threading.Lock()

def start_exclusive(target, args=()):
    if not _lock.acquire(blocking=False):
        return None
    def run():
        try:
            target(*args)
        finally:
            _lock.release()
    thread = threading.Thread(target=run, daemon=True)
    try:
        thread.start()
    except BaseException:
        _lock.release()
        raise
    return thread
