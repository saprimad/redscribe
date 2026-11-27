"""Exercise actual worker/export completion ordering without GPU or a display."""
import ast
from pathlib import Path
from types import SimpleNamespace
import os
import tempfile
import threading
import time
import traceback
import unittest
from performance_log import RunPerformance, performance_summary, save_performance
from unittest.mock import Mock

SOURCE = ast.parse(Path(__file__).resolve().parents[1].joinpath('redscribe_gpu.py').read_text())
NODES = [n for n in SOURCE.body if isinstance(n, ast.ClassDef) and n.name in ('RedScribeApp', 'TranscriptionCancelled')]


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.queue = []
        self.events = []
        self.model = Mock()
        self.model.revision = "test-revision"
        self.model.transcribe.return_value = (iter([SimpleNamespace(start=0, end=2, text='Hello.')]),
                                              SimpleNamespace(duration=3, language='en'))
        self.ns = dict(RunPerformance=RunPerformance, performance_summary=performance_summary, save_performance=save_performance, print_performance=Mock(), time=time, os=os, re=__import__('re'), traceback=traceback,
                       ModelPreflightError=type('PreflightError', (Exception,), {}),
                       DiarizationDependencyError=type('DependencyError', (Exception,), {}),
                       preflight_model=Mock(return_value='Runtime ready'),
                       load_pyannote_pipeline_class=Mock(), release_gpu_cache=Mock(),
                       EXTRA_MODELS={}, LocalASR=type('LocalASR', (), {}),
                       model_label=lambda value: value, MODEL_FOLDERS={'tiny': 'whisper_tiny'},
                       model_output_folder=lambda *args: self.temp.name,
                       ensure_dir=lambda path: None, build_output_name=lambda **kwargs: 'trial',
                       available_output_paths=lambda *args: ('trial.xlsx', 'trial.docx'),
                       create_whisper_model=Mock(return_value=(self.model, 'cuda', 'float16')),
                       assign_speaker=lambda *args: 'UNKNOWN', sec_to_hms=str, sec_to_mmss=str,
                       split_sentences_universal=lambda text: [text],
                       distribute_times=lambda a, b, rows: [(a, b, rows[0])],
                       save_xlsx_with_early_report=Mock(), save_docx_transcript=Mock(),
                       DIARIZATION_MODEL='community-1', messagebox=Mock(), open_folder=Mock())
        exec(compile(ast.Module(body=NODES, type_ignores=[]), 'redscribe_gpu.py', 'exec'), self.ns)
        self.app = self.ns['RedScribeApp'].__new__(self.ns['RedScribeApp'])
        self.app.root = Mock()
        self.app.root.after.side_effect = lambda delay, callback, *args: self.queue.append((callback, args))
        self.app.run_lock = threading.Lock()
        self.app.run_phase = 'processing'
        self.app.stop_event = threading.Event()
        self.app.base_output_dir = self.temp.name
        for attr in ('start_btn', 'stop_btn', 'status', 'progress_var', 'begin_model_activity',
                     'update_diarization_activity', 'end_diarization_activity', 'log_info',
                     'mode_button',
                     'log_warning', 'log_live_segment'):
            setattr(self.app, attr, Mock())
        self.inputs = dict(audio_path='clip.wav', project='test', researcher='test', label='clip',
                           period='2026-11', whisper_model='tiny', language='en',
                           diarization_enabled=False)

    def flush(self):
        while self.queue:
            callback, args = self.queue.pop(0)
            callback(*args)

    def test_success_waits_for_cleanup_and_resets_state_before_modal(self):
        def cleanup():
            self.assertEqual(self.app.run_phase, 'finalising')
            self.app.start_btn.config.assert_not_called()
            self.ns['messagebox'].showinfo.assert_not_called()
            self.events.append('cleanup')
        self.ns['release_gpu_cache'].side_effect = cleanup
        def popup(*args):
            self.assertEqual(self.app.run_phase, 'idle')
            self.app.start_btn.config.assert_called_once_with(state='normal')
            self.app.mode_button.configure.assert_called_once_with(state='normal')
            self.events.append('popup')
        self.ns['messagebox'].showinfo.side_effect = popup
        self.app.run_whisper(self.inputs)
        self.assertEqual(self.app.run_phase, 'finalising')
        self.app.start_btn.config.assert_not_called()
        self.app.mode_button.configure.assert_not_called()
        self.flush()
        self.assertEqual(self.events, ['cleanup', 'popup'])
        self.ns['save_xlsx_with_early_report'].assert_called_once()
        self.ns['save_docx_transcript'].assert_called_once()
        messages = [c.args[0] for c in self.app.log_info.call_args_list]
        self.assertTrue(any('Transcription finished' in m for m in messages))
        self.assertIn('Excel report saved: trial.xlsx', messages)
        self.assertIn('Word report saved: trial.docx', messages)
        self.app.begin_model_activity.assert_any_call('Saving Excel report...')
        self.app.update_diarization_activity.assert_any_call('Saving Word report...')
        self.app.status.set.assert_called_with('Completed - 100% | CUDA (float16)')

    def test_actual_worker_saves_performance_without_serialising_private_inputs(self):
        self.inputs.update(hf_token='SECRET_TOKEN', project='PRIVATE_STUDY', researcher='PRIVATE_NAME')
        self.app.run_whisper(self.inputs)
        self.flush()
        files = list(Path(self.temp.name, 'performance').glob('*.json'))
        self.assertEqual(len(files), 1)
        raw = files[0].read_text()
        record = __import__('json').loads(raw)
        self.assertEqual(record['outcome'], 'completed')
        self.assertEqual(record['actual_compute_type'], 'float16')
        self.assertEqual(record['audio_duration_seconds'], 3)
        self.assertTrue(record['asr_completed'])
        for private in ('SECRET_TOKEN', 'PRIVATE_STUDY', 'PRIVATE_NAME', 'Hello.', 'clip.wav'):
            self.assertNotIn(private, raw)
        self.assertIn('excel_export', record['stage_seconds'])
        self.assertIn('word_export', record['stage_seconds'])
        console = [c.args[0] for c in self.ns['print_performance'].call_args_list]
        self.assertTrue(console[0].startswith('Performance [completed]:'))
        self.assertTrue(console[1].startswith('Performance log saved:'))

    def test_performance_write_failure_does_not_block_completion(self):
        self.ns['save_performance'] = Mock(side_effect=PermissionError('read only'))
        self.app.run_whisper(self.inputs)
        self.flush()
        self.assertEqual(self.app.run_phase, 'idle')
        self.ns['messagebox'].showinfo.assert_called_once()
        self.app.log_warning.assert_called_with('Performance log could not be saved: read only')

    def test_two_consecutive_runs_each_finish_idle(self):
        for index in range(2):
            self.app.run_phase = 'processing'
            self.model.transcribe.return_value = (iter([]), SimpleNamespace(duration=1, language='en'))
            self.app.run_whisper(self.inputs)
            self.flush()
            self.assertEqual(self.app.run_phase, 'idle')
        self.assertEqual(self.ns['release_gpu_cache'].call_count, 2)
        self.assertEqual(self.ns['messagebox'].showinfo.call_count, 2)

    def test_cleanup_error_does_not_strand_controls_or_discard_saved_reports(self):
        self.ns['release_gpu_cache'].side_effect = RuntimeError('cleanup error')
        self.app.run_whisper(self.inputs)
        self.flush()
        self.assertEqual(self.app.run_phase, 'idle')
        self.app.log_warning.assert_called_with('Model memory cleanup warning: cleanup error')
        self.ns['messagebox'].showinfo.assert_called_once()

    def test_excel_failure_waits_for_cleanup_and_never_claims_success(self):
        self.ns['save_xlsx_with_early_report'].side_effect = PermissionError('file open')
        self.app.run_whisper(self.inputs)
        self.ns['messagebox'].showerror.assert_not_called()
        self.ns['release_gpu_cache'].assert_called_once()
        self.flush()
        self.ns['save_docx_transcript'].assert_not_called()
        self.ns['messagebox'].showinfo.assert_not_called()
        self.ns['messagebox'].showerror.assert_called_once()
        self.app.status.set.assert_called_with('Excel save failed')
        self.assertEqual(self.app.run_phase, 'idle')

    def test_word_failure_retains_excel_and_reports_partial_success(self):
        self.ns['save_docx_transcript'].side_effect = PermissionError('file open')
        self.app.run_whisper(self.inputs)
        self.flush()
        self.ns['messagebox'].showwarning.assert_called_once()
        self.ns['messagebox'].showinfo.assert_not_called()
        self.app.status.set.assert_called_with('Completed; Word export failed')
        self.assertEqual(self.app.run_phase, 'idle')

    def test_preflight_failure_returns_idle_without_processing(self):
        self.ns['preflight_model'].side_effect = self.ns['ModelPreflightError']('missing runtime')
        self.app.run_whisper(self.inputs)
        self.ns['create_whisper_model'].assert_not_called()
        self.flush()
        self.app.status.set.assert_called_with('Requirements check failed; nothing processed')
        self.assertEqual(self.app.run_phase, 'idle')

    def test_cancelled_run_cleans_up_and_is_ready_for_next_run(self):
        self.app.stop_event.set()
        self.app.run_whisper(self.inputs)
        self.flush()
        self.ns['release_gpu_cache'].assert_called_once()
        self.ns['save_xlsx_with_early_report'].assert_not_called()
        self.ns['messagebox'].showinfo.assert_not_called()
        self.assertEqual(self.app.run_phase, 'idle')
        self.app.status.set.assert_called_with('Stopped; no reports were saved for this run')

    def test_inference_failure_closes_generator_and_logs_error(self):
        class Segments:
            closed = False
            def __iter__(self):
                raise RuntimeError('inference failed')
            def close(self):
                self.closed = True
        segments = Segments()
        self.model.transcribe.return_value = (segments, SimpleNamespace(duration=3, language='en'))
        self.app.run_whisper(self.inputs)
        self.assertTrue(segments.closed)
        self.flush()
        self.ns['save_xlsx_with_early_report'].assert_not_called()
        self.app.status.set.assert_called_with('Transcription failed')
        self.assertIn('inference failed', Path(self.temp.name, 'redscribe_error.log').read_text())
        self.assertEqual(self.app.run_phase, 'idle')


if __name__ == '__main__':
    unittest.main()
