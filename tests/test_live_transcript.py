"""Check actual live-display handlers without inference or a graphical display."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock

from speaker_styles import speaker_colour

source = ast.parse(Path(__file__).resolve().parents[1].joinpath('redscribe_gpu.py').read_text())
app_class = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'RedScribeApp')
namespace = {'speaker_colour': speaker_colour}
exec(compile(ast.Module(body=[app_class], type_ignores=[]), 'redscribe_gpu.py', 'exec'), namespace)


class LiveTranscriptTests(unittest.TestCase):
    def setUp(self):
        self.app = namespace['RedScribeApp'].__new__(namespace['RedScribeApp'])
        self.app.live_box = Mock()
        self.app.speaker_tags = {}
        self.app.last_live_speaker = None
        self.app.ui_font = 'Arial'

    def text(self):
        return ''.join(call.args[1] for call in self.app.live_box.insert.call_args_list)

    def test_same_speaker_appends_and_returning_speaker_gets_new_label(self):
        for ts, speaker, text in [('00:00:01', 'SPEAKER_01', 'First phrase.'),
                                  ('00:00:02', 'SPEAKER_01', 'Second phrase.'),
                                  ('00:00:03', 'SPEAKER_02', 'Response.'),
                                  ('00:00:04', 'SPEAKER_01', 'Returning.')]:
            self.app.log_live_segment(ts, speaker, text)
        self.assertEqual(self.text(), '00:00:01   SPEAKER_01: First phrase. Second phrase.\n'
                         '00:00:03   SPEAKER_02: Response.\n00:00:04   SPEAKER_01: Returning.')
        self.app.live_box.configure.assert_called_with(state='disabled')
        self.assertEqual(self.app.live_box.tag_configure.call_count, 2)

    def test_info_and_warning_do_not_join_speech(self):
        self.app.log_live_segment('00:00:01', 'SPEAKER_01', 'Before.')
        self.app.log_info('Notice.')
        self.app.log_live_segment('00:00:02', 'SPEAKER_01', 'After notice.')
        self.app.log_warning('Warning.')
        self.app.log_live_segment('00:00:03', 'SPEAKER_01', 'After warning.')
        self.assertEqual(self.text(), '00:00:01   SPEAKER_01: Before.\nNotice.\n'
                         '00:00:02   SPEAKER_01: After notice.\nWarning.\n'
                         '00:00:03   SPEAKER_01: After warning.')

    def test_blank_segments_do_not_break_speaker_continuity(self):
        self.app.log_live_segment('00:00:01', 'UNKNOWN', 'Original wording')
        self.app.log_live_segment('00:00:02', 'SPEAKER_02', '  ')
        self.app.log_live_segment('00:00:03', 'UNKNOWN', '  stays unchanged.  ')
        self.assertEqual(self.text(), '00:00:01   UNKNOWN: Original wording stays unchanged.')
        self.assertEqual(list(self.app.speaker_tags), ['UNKNOWN'])


if __name__ == '__main__':
    unittest.main()
