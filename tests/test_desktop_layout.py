"""Real Tk widget smoke checks; no model downloads, inference or OS credentials.

Run with a display, for example DISPLAY=:99 python -m unittest discover -s tests.
Headless runs skip this module's checks while the logic tests still run.
"""
import ast
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

try:
    import tkinter as tk
    from tkinter import ttk, font as tkfont, scrolledtext
except ImportError:
    tk = None

from token_store import TokenSelection, TokenStoreError


@unittest.skipUnless(tk is not None and os.environ.get("DISPLAY"), "A Tk display is required")
class DesktopLayoutTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.addCleanup(self.close_root)
        self.ns = dict(
            tk=tk, ttk=ttk, tkfont=tkfont, scrolledtext=scrolledtext, os=os,
            time=__import__("time"), __file__=str(Path(__file__).resolve().parents[1] / "redscribe_gpu.py"),
            threading=SimpleNamespace(Lock=threading.Lock, Event=threading.Event, Thread=Mock()),
            APP_TITLE="RedScribe - UI test", APP_VERSION="2.0.0",
            WHISPER_MODELS=("large-v3", "turbo", "medium", "small", "base"),
            TRANSCRIPTION_LANGUAGES={"Auto detect": None, "Bahasa Melayu": "ms", "English": "en"},
            load_model_preference=lambda: "large-v3", TokenStoreError=TokenStoreError,
            resolve_token=Mock(return_value=TokenSelection("example-test-only", "saved in system credential store")),
            save_token=Mock(), remove_saved_token=Mock(), messagebox=Mock(),
        )
        source = ast.parse(Path(self.ns["__file__"]).read_text())
        nodes = [n for n in source.body if isinstance(n, ast.ClassDef) and n.name == "RedScribeApp"
                 or isinstance(n, ast.FunctionDef) and n.name == "sec_to_hms"]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "redscribe_gpu.py", "exec"), self.ns)
        self.app = self.ns["RedScribeApp"](self.root)
        self.root.update()

    def close_root(self):
        # Cancel startup and activity callbacks before destroying this test root.
        for timer in self.root.tk.call("after", "info"):
            self.root.after_cancel(timer)
        self.root.destroy()

    def test_default_workspace_and_collapsible_details(self):
        self.assertTrue(self.app.diarization_enabled.get())
        self.assertFalse(hasattr(self.app, "token_entry"))
        self.assertGreater(self.app.live_box.winfo_width(), self.app.sidebar_canvas.winfo_width())
        self.assertTrue(self.app.study_fields.winfo_ismapped())
        self.assertLess(self.app.study_fields.winfo_rooty(), self.app.sidebar_canvas.winfo_rooty())
        self.app.toggle_study_details()
        self.root.update()
        self.assertFalse(self.app.study_fields.winfo_ismapped())
        self.app.toggle_study_details()
        self.root.update()
        self.assertTrue(self.app.study_fields.winfo_ismapped())
        self.app.project.set("Example study")
        self.app.toggle_study_details()
        self.app.toggle_study_details()
        self.root.update()
        self.assertEqual(self.app.project.get(), "Example study")

    def test_small_window_keeps_transcript_and_actions_visible(self):
        self.root.geometry("900x600")
        self.root.update()
        for widget in (self.app.live_box, self.app.start_btn, self.app.stop_btn, self.app.open_btn):
            self.assertTrue(widget.winfo_ismapped())
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(),
                                 self.root.winfo_rootx() + self.root.winfo_width())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(),
                                 self.root.winfo_rooty() + self.root.winfo_height())
        self.assertGreater(self.app.live_box.winfo_width(), 400)
        self.assertGreater(self.app.sidebar_content.winfo_height(), self.app.sidebar_canvas.winfo_height())
        self.app.sidebar_canvas.yview_moveto(1)
        self.root.update()
        self.assertGreater(self.app.sidebar_canvas.yview()[0], 0)

    def test_settings_summary_and_session_masking(self):
        self.app.open_token_settings()
        self.root.update()
        window = self.app.token_settings_window
        self.app.open_token_settings()
        self.assertIs(self.app.token_settings_window, window)
        self.app.diarization_enabled.set(False)
        self.assertIn("OFF", self.app.diarization_summary.get())
        self.app.speaker_count.set("2")
        self.app.diarization_enabled.set(True)
        self.assertIn("2 expected speakers", self.app.diarization_summary.get())
        self.app.hf_token.set("example-test-only")
        self.app.toggle_token_visibility()
        self.assertEqual(self.app.token_entry.cget("show"), "")
        self.app.close_token_settings()
        self.app.open_token_settings()
        self.root.update()
        self.assertEqual(self.app.token_entry.cget("show"), "*")
        self.assertEqual(self.app.hf_token.get(), "example-test-only")
        self.app.close_token_settings()

    def test_live_activity_and_speaker_text(self):
        self.app.begin_diarization_activity()
        self.app.update_diarization_activity("Detecting speech...", 4, 10)
        self.app.tick_diarization_activity()
        self.root.update()
        self.assertTrue(self.app.activity_label.winfo_ismapped())
        self.assertIn("40% of this stage", self.app.diarization_activity.get())
        self.app.end_diarization_activity()
        self.root.update()
        self.assertFalse(self.app.activity_label.winfo_ismapped())
        self.assertIsNone(self.app.diarization_timer)
        self.app.log_live_segment("00:00:08", "SPEAKER_01", "Example transcript.")
        self.app.log_live_segment("00:00:12", "SPEAKER_02", "Second speaker.")
        self.assertIn("Example transcript.", self.app.live_box.get("1.0", "end"))
        self.assertNotEqual(self.app.speaker_tags["SPEAKER_01"], self.app.speaker_tags["SPEAKER_02"])
        self.assertEqual(str(self.app.live_box.cget("state")), "disabled")

    def test_start_hands_saved_token_and_metadata_to_worker(self):
        with tempfile.NamedTemporaryFile(suffix=".wav") as audio:
            self.app.audio_path.set(audio.name)
            self.app.project.set("Example project")
            self.app.speaker_count.set("2")
            self.app.start()
        inputs = self.ns["threading"].Thread.call_args.kwargs["args"][0]
        self.assertEqual(inputs["hf_token"], "example-test-only")
        self.assertEqual(inputs["speaker_count"], "2")
        self.assertEqual(inputs["project"], "Example project")
        self.assertIn("disabled", self.app.start_btn.state())
        self.app.stop()
        self.assertTrue(self.app.stop_event.is_set())
        self.app.finish_run(cancelled=True)
        self.assertNotIn("disabled", self.app.start_btn.state())
        self.assertIn("disabled", self.app.stop_btn.state())
