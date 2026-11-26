"""Cross-platform OS-backed single writer lock; released on process exit."""
from contextlib import contextmanager
from pathlib import Path
import os

@contextmanager
def output_lock(directory):
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/".benchmark.lock").open("a+b") as stream:
        stream.seek(0,2)
        if stream.tell()==0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Benchmark output directory already in use or lock unavailable") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name=="nt":
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
