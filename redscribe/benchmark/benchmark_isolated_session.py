"""Local subprocess boundary for native ASR sessions.

Only the parent writes scientific checkpoints. The child exchanges Python messages over
a dedicated pipe (not stdout), so library output cannot corrupt the protocol.
"""
import multiprocessing as mp
import os
import sys
import traceback
from pathlib import Path


def _controlled_shutdown(session, conn, log):
    """Windows Large-v3 workaround, exclusively inside the disposable worker."""
    session.prepare_controlled_shutdown()
    print("CONTROLLED PROCESS EXIT: wrapper destructor intentionally bypassed", file=log, flush=True)
    log.flush()
    os.fsync(log.fileno())
    conn.send(("ok", "controlled_process_exit"))
    conn.close()
    os._exit(0)


def _serve(conn, key, language, log_path):
    import faulthandler
    import sys
    with open(log_path, "a", encoding="utf-8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        faulthandler.enable(file=log, all_threads=True)
        print(f"MODEL: {key} | LANGUAGE: {language}", flush=True)
        session = None
        try:
            # Import the desktop entry point to initialise its existing module paths.
            import redscribe_gpu
            from asr_backends import EXTRA_MODELS
            from model_options import preflight_model
            preflight_model(key, language)
            if key in EXTRA_MODELS:
                from .benchmark_local_session import LocalBenchmarkSession
                session = LocalBenchmarkSession(key, language)
            else:
                from .benchmark_whisper_session import WhisperSession
                session = WhisperSession(key, language)
            conn.send(("ok", (session.device, session.precision, session.provenance)))
            while True:
                command, argument = conn.recv()
                if command == "close":
                    print("CLEANUP START", flush=True)
                    if key == "large-v3" and sys.platform == "win32":
                        _controlled_shutdown(session, conn, log)
                    session.close()
                    session = None
                    print("CLEANUP PASS", flush=True)
                    conn.send(("ok", "normal_destructor"))
                    return
                if command != "transcribe":
                    raise ValueError("Unknown worker command")
                print("INFERENCE START", flush=True)
                prediction = session.transcribe(argument)
                conn.send(("ok", prediction))
                print("INFERENCE PASS", flush=True)
        except Exception as exc:
            traceback.print_exc(file=log)
            try:
                conn.send(("error", type(exc).__name__ + ": " + str(exc)))
            except (OSError, EOFError):
                pass
        finally:
            conn.close()


class IsolatedSession:
    def __init__(self, key, language, log_path, *, target=_serve):
        self.log_path = Path(log_path)
        self.cleanup_error = None
        self.shutdown_strategy = None
        context = mp.get_context("spawn")
        self.conn, child = context.Pipe()
        self.process = context.Process(target=target,
            args=(child, key, language, str(self.log_path)))
        try:
            self.process.start()
        except BaseException:
            self.conn.close()
            child.close()
            raise
        child.close()
        try:
            self.device, self.precision, self.provenance = self._receive()
        except BaseException:
            self._finish()
            raise

    def _receive(self, timeout=None):
        import time
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if self.conn.poll(.2):
                try:
                    status, value = self.conn.recv()
                except (EOFError, OSError):
                    break
                if status != "ok":
                    raise RuntimeError(value)
                return value
            if not self.process.is_alive():
                break
            if deadline is not None and time.monotonic() >= deadline:
                raise RuntimeError("ASR worker response timed out")
        self.process.join(timeout=2)
        raise RuntimeError(f"ASR worker exited: {self.process.exitcode}; see local worker log")

    def transcribe(self, audio):
        self.conn.send(("transcribe", str(audio)))
        return self._receive()

    def _finish(self):
        self.conn.close()
        self.process.join(timeout=5)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)
        if self.process.is_alive():
            self.process.kill()
            self.process.join()

    def close(self):
        if self.conn.closed:
            return
        try:
            if self.process.is_alive():
                self.conn.send(("close", None))
                self.shutdown_strategy = self._receive(timeout=60)
                if self.shutdown_strategy not in (None, "normal_destructor", "controlled_process_exit"):
                    raise RuntimeError("Unexpected worker shutdown acknowledgement")
            else:
                raise RuntimeError("ASR worker exited before cleanup")
        except (RuntimeError, OSError, EOFError) as exc:
            self.cleanup_error = str(exc)
        finally:
            self._finish()
        if self.process.exitcode != 0:
            self.cleanup_error = f"ASR worker exit code {self.process.exitcode}; {self.cleanup_error or 'abnormal termination'}"
        if self.cleanup_error:
            try:
                with self.log_path.open("a", encoding="utf-8") as log:
                    log.write("\nCLEANUP FAILURE: " + self.cleanup_error + "\n")
            except OSError as exc:
                self.cleanup_error += f"; diagnostic log write failed: {exc}"
