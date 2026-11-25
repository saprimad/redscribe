"""Synthetic native-process failures must not terminate the benchmark parent."""
import os
import tempfile
import unittest
from pathlib import Path

from redscribe.benchmark.benchmark_isolated_session import IsolatedSession


def fake_worker(conn, key, language, log_path):
    conn.send(("ok", ("cuda", "float16", {"model_key": key})))
    while True:
        cmd, value = conn.recv()
        if cmd == "transcribe":
            if key == "inference-crash":
                os._exit(17)
            conn.send(("ok", "synthetic prediction"))
        elif cmd == "close":
            if key == "cleanup-crash":
                os._exit(23)
            conn.send(("ok", None))
            conn.close()
            return


class IsolatedSessionTests(unittest.TestCase):
    def test_cleanup_crash_contained_and_next_model_can_run(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "worker.log"
            session = IsolatedSession("cleanup-crash", "ms", log, target=fake_worker)
            self.assertEqual(session.transcribe("fake.wav"), "synthetic prediction")
            session.close()
            self.assertIn("23", session.cleanup_error)
            self.assertFalse(session.process.is_alive())
            self.assertIn("CLEANUP FAILURE", log.read_text())
            next_session = IsolatedSession("normal", "ms", log, target=fake_worker)
            try:
                self.assertEqual(next_session.transcribe("fake.wav"), "synthetic prediction")
            finally:
                next_session.close()
            self.assertIsNone(next_session.cleanup_error)

    def test_inference_crash_is_not_a_successful_prediction(self):
        with tempfile.TemporaryDirectory() as folder:
            session = IsolatedSession("inference-crash", "ms",
                Path(folder) / "worker.log", target=fake_worker)
            try:
                with self.assertRaisesRegex(RuntimeError, "17"):
                    session.transcribe("fake.wav")
            finally:
                session.close()
            self.assertFalse(session.process.is_alive())


if __name__ == "__main__":
    unittest.main()
