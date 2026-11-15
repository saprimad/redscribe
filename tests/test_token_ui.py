"""Exercise real UI handlers without a display or model downloads."""
import ast
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock, patch

from token_store import TokenSelection, TokenStoreError

# Load the actual class methods without importing the app's heavy AI dependencies.
source = ast.parse(Path(__file__).resolve().parents[1].joinpath("redscribe_gpu.py").read_text())
app_class = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "RedScribeApp")
namespace = {"TokenStoreError": TokenStoreError, "messagebox": Mock(), "resolve_token": Mock(),
             "save_token": Mock(), "remove_saved_token": Mock(), "os": Mock(),
             "TRANSCRIPTION_LANGUAGES": {"Auto detect": None}, "threading": Mock()}
exec(compile(ast.Module(body=[app_class], type_ignores=[]), "redscribe_gpu.py", "exec"), namespace)


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class TokenUITests(unittest.TestCase):
    def setUp(self):
        for value in namespace.values():
            if isinstance(value, Mock):
                value.reset_mock(return_value=True, side_effect=True)
        self.app = namespace["RedScribeApp"].__new__(namespace["RedScribeApp"])
        self.app.hf_token = Value("hf_example_only")
        self.app.token_status = Value()
        self.app.token_entry = Mock()
        self.app.show_token_btn = Mock()
        namespace["resolve_token"].return_value = TokenSelection("hf_example_only", "saved in system credential store")

    def test_successful_save_clears_and_masks_entry(self):
        self.app.save_hf_token()
        namespace["save_token"].assert_called_once_with("hf_example_only")
        self.assertEqual(self.app.hf_token.get(), "")
        self.app.token_entry.configure.assert_called_with(show="*")
        self.assertNotIn("hf_example_only", self.app.token_status.get())

    def test_failed_save_preserves_session_token(self):
        namespace["save_token"].side_effect = TokenStoreError("Store locked")
        self.app.save_hf_token()
        self.assertEqual(self.app.hf_token.get(), "hf_example_only")
        namespace["messagebox"].showwarning.assert_called_once()

    def test_remove_preserves_typed_session_token(self):
        self.app.remove_hf_token()
        namespace["remove_saved_token"].assert_called_once()
        self.assertEqual(self.app.hf_token.get(), "hf_example_only")
        namespace["messagebox"].showinfo.assert_called_once()

    def test_failed_remove_does_not_report_success(self):
        namespace["remove_saved_token"].side_effect = TokenStoreError("Store locked")
        self.app.remove_hf_token()
        namespace["messagebox"].showinfo.assert_not_called()
        namespace["messagebox"].showwarning.assert_called_once()

    def test_show_and_hide(self):
        for before, after in (("*", ""), ("", "*")):
            self.app.token_entry.cget.return_value = before
            self.app.toggle_token_visibility()
            self.app.token_entry.configure.assert_called_with(show=after)

    def test_worker_receives_resolved_saved_token_only_with_diarisation(self):
        for enabled in (True, False):
            with self.subTest(diarisation=enabled):
                namespace["resolve_token"].reset_mock()
                self.app.hf_token.set("")
                for name, value in (("audio_path", "example.wav"), ("project", ""), ("researcher", ""),
                                    ("label", ""), ("period", "2026-11"), ("diarization_enabled", enabled),
                                    ("speaker_count", ""), ("transcription_language", "Auto detect"),
                                    ("whisper_model", "large-v3")):
                    setattr(self.app, name, Value(value))
                for name in ("live_box", "progress_var", "status", "start_btn", "stop_btn", "stop_event"):
                    setattr(self.app, name, Mock())
                self.app.run_lock = threading.Lock()
                self.app.run_phase = "idle"
                namespace["os"].path.isfile.return_value = True
                self.app.start()
                inputs = namespace["threading"].Thread.call_args.kwargs["args"][0]
                self.assertEqual(inputs["hf_token"], "hf_example_only" if enabled else "")
                self.assertEqual(namespace["resolve_token"].call_count, int(enabled))


if __name__ == "__main__":
    unittest.main()
