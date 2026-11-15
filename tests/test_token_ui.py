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
from asr_backends import EXTRA_MODELS, validate_language
from diarization_options import DIARIZATION_MODELS, DEFAULT_DIARIZATION_CHOICE, describe_diarization

namespace = {"DIARIZATION_MODELS": DIARIZATION_MODELS, "describe_diarization": describe_diarization, "EXTRA_MODELS": EXTRA_MODELS, "validate_language": validate_language, "TokenStoreError": TokenStoreError, "messagebox": Mock(), "resolve_token": Mock(),
             "save_token": Mock(), "remove_saved_token": Mock(), "os": Mock(),
             "TRANSCRIPTION_LANGUAGES": {"Auto detect": None}, "threading": Mock(),
             "tk": Mock(), "ttk": Mock()}
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
        self.app.ui_font = "Segoe UI"
        self.app.diarization_choice = Value(DEFAULT_DIARIZATION_CHOICE)
        self.app.hf_token = Value("hf_example_only")
        self.app.token_status = Value()
        self.app.token_summary = Value()
        self.app.token_settings_window = None
        self.app.root = Mock()
        self.app.speaker_tags = {}
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

    def test_summary_distinguishes_saved_available_and_missing_tokens(self):
        for token, source, expected in (
            ("example", "saved in system credential store", "Token saved"),
            ("example", "found in environment", "Token available"),
            ("example", "entered in app (session only)", "Session token"),
            (None, "no token found", "Token not configured"),
        ):
            with self.subTest(source=source):
                namespace["resolve_token"].return_value = TokenSelection(token, source)
                self.app.check_hf_token()
                self.assertIn(expected, self.app.token_summary.get())
                self.assertNotIn("example", self.app.token_summary.get())

    def test_open_settings_constructs_masked_entry_and_close_handlers(self):
        self.app.root.winfo_rootx.return_value = 0
        self.app.root.winfo_rooty.return_value = 0
        self.app.root.winfo_width.return_value = 1100
        self.app.root.winfo_height.return_value = 760
        self.app.root.winfo_screenwidth.return_value = 1440
        self.app.root.winfo_screenheight.return_value = 900
        self.app.diarization_enabled = Value(True)
        self.app.speaker_count = Value("")
        namespace["ttk"].Frame.return_value.winfo_reqheight.return_value = 620
        win = namespace["tk"].Toplevel.return_value
        self.app.open_token_settings()
        self.assertIs(self.app.token_settings_window, win)
        self.assertEqual(namespace["ttk"].Entry.call_count, 2)
        self.assertEqual(namespace["ttk"].Entry.call_args.kwargs["show"], "*")
        win.protocol.assert_called_with("WM_DELETE_WINDOW", self.app.close_token_settings)
        win.grab_set.assert_called_once()
        win.geometry.assert_called_with("560x624+270+68")

    def test_reopening_settings_focuses_existing_window(self):
        window = Mock()
        window.winfo_exists.return_value = True
        self.app.token_settings_window = window
        self.app.open_token_settings()
        window.lift.assert_called_once()
        window.focus_set.assert_called_once()
        namespace["tk"].Toplevel.assert_not_called()

    def test_closing_settings_masks_entry_and_preserves_session(self):
        window = Mock()
        self.app.token_settings_window = window
        self.app.close_token_settings()
        self.app.token_entry.configure.assert_called_with(show="*")
        window.grab_release.assert_called_once()
        window.destroy.assert_called_once()
        self.assertIsNone(self.app.token_settings_window)
        self.assertEqual(self.app.hf_token.get(), "hf_example_only")
        self.app.close_token_settings()  # Closing again is safe.

    def test_worker_receives_resolved_saved_token_only_with_diarisation(self):
        for enabled, choice in ((enabled, choice) for enabled in (True, False) for choice in DIARIZATION_MODELS):
            with self.subTest(diarisation=enabled, model=choice):
                self.app.diarization_choice.set(choice)
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
                self.assertEqual(inputs["diarization_model"], DIARIZATION_MODELS[choice])
                self.assertEqual(namespace["resolve_token"].call_count, int(enabled))


if __name__ == "__main__":
    unittest.main()
