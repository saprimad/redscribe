"""Verify hook progress and UI timer cleanup without models or a display."""
import ast
from download_progress import hub_download_progress
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

source = ast.parse(Path(__file__).resolve().parents[1].joinpath('redscribe_gpu.py').read_text())
selected = [node for node in source.body if
            isinstance(node, ast.FunctionDef) and node.name in ('run_diarization', 'sec_to_hms')
            or isinstance(node, ast.ClassDef) and node.name == 'RedScribeApp']


class DiarizationStatusTests(unittest.TestCase):
    def setUp(self):
        self.clock = Mock()
        self.clock.monotonic.return_value = 10.0
        self.pipeline = Mock()
        self.annotation = Mock()
        self.annotation.itertracks.return_value = [(SimpleNamespace(start=8, end=20), None, 'SPEAKER_01')]
        self.pipeline.return_value = SimpleNamespace(exclusive_speaker_diarization=self.annotation)
        self.ns = dict(hub_download_progress=hub_download_progress, time=self.clock, create_diarization_pipeline=Mock(return_value=self.pipeline),
                       load_audio_for_pyannote=Mock(return_value='audio'), release_gpu_cache=Mock())
        exec(compile(ast.Module(body=selected, type_ignores=[]), 'redscribe_gpu.py', 'exec'), self.ns)

    def test_hooks_forward_stage_counts_and_preserve_output(self):
        progress = Mock()
        def infer(audio, *, hook, **kwargs):
            self.assertEqual(kwargs['num_speakers'], 2)
            hook('segmentation', None, completed=0, total=10)
            hook('segmentation', None, completed=10, total=10)
            hook('embeddings', None, completed=1, total=4)
            hook('embeddings', object())
            return SimpleNamespace(exclusive_speaker_diarization=self.annotation)
        self.pipeline.side_effect = infer
        turns = self.ns['run_diarization']('file.wav', None, 'cpu', '2', progress)
        self.assertEqual(turns, [dict(start=8.0, end=20.0, speaker='SPEAKER_01')])
        progress.assert_any_call('Detecting speech...', 10, 10)
        progress.assert_any_call('Analysing speaker characteristics...', 1, 4)
        progress.assert_any_call('Grouping speakers...', None, None)
        self.ns['release_gpu_cache'].assert_called_once()

    def test_legacy_choice_is_forwarded_and_annotation_output_is_supported(self):
        self.pipeline.return_value = SimpleNamespace(itertracks=self.annotation.itertracks)
        turns = self.ns['run_diarization']('file.wav', 'example-token', 'cpu', '2',
                                          model_id='pyannote/speaker-diarization-3.1')
        self.ns['create_diarization_pipeline'].assert_called_once_with(
            'example-token', 'cpu', model_id='pyannote/speaker-diarization-3.1')
        self.assertEqual(turns, [dict(start=8.0, end=20.0, speaker='SPEAKER_01')])
        self.ns['release_gpu_cache'].assert_called_once()

    def test_download_preparation_notice_precedes_pipeline_load_and_ready_follows(self):
        events=[]
        progress=lambda stage,*args:events.append(stage)
        self.ns['create_diarization_pipeline'].side_effect=lambda *a,**kw:events.append('LOADED') or self.pipeline
        self.ns['run_diarization']('file.wav',None,'cpu',progress_callback=progress)
        loading=next(i for i,event in enumerate(events) if 'automatically downloading missing' in event)
        ready=next(i for i,event in enumerate(events) if 'Diarisation model ready' in event)
        self.assertLess(loading,events.index('LOADED'))
        self.assertGreater(ready,events.index('LOADED'))
        self.assertNotIn('%',events[loading])

    def test_pipeline_failure_releases_resources(self):
        self.pipeline.side_effect = RuntimeError('model failure')
        with self.assertRaises(RuntimeError):
            self.ns['run_diarization']('file.wav', None, 'cpu')
        self.ns['release_gpu_cache'].assert_called_once()

    def test_hook_cancellation_propagates_and_releases_resources(self):
        class Cancelled(Exception):
            pass
        def infer(audio, *, hook, **kwargs):
            hook('segmentation', None, completed=1, total=10)
        def report(stage, completed=None, total=None):
            if completed is not None:
                raise Cancelled()
        self.pipeline.side_effect = infer
        with self.assertRaises(Cancelled):
            self.ns['run_diarization']('file.wav', None, 'cpu', progress_callback=report)
        self.ns['release_gpu_cache'].assert_called_once()

    def make_app(self):
        app = self.ns['RedScribeApp'].__new__(self.ns['RedScribeApp'])
        app.root = Mock()
        app.root.after.return_value = 'timer-id'
        app.diarization_timer = None
        app.diarization_started = None
        app.diarization_activity = Mock()
        app.activity_label = Mock()
        app.status = Mock()
        app.stop_event = Mock()
        app.stop_event.is_set.return_value = False
        app.log_info = Mock()
        return app

    def test_stage_percentage_elapsed_and_timer_cleanup(self):
        app = self.make_app()
        app.begin_diarization_activity()
        app.update_diarization_activity('Detecting speech...', 4, 10)
        self.clock.monotonic.return_value = 75.0
        app.tick_diarization_activity()
        display = app.status.set.call_args.args[0]
        self.assertIn('40% of this stage', display)
        self.assertIn('Elapsed: 00:01:05', display)
        app.end_diarization_activity()
        app.root.after_cancel.assert_called_once_with('timer-id')
        app.diarization_activity.set.assert_called_with('')
        app.update_diarization_activity('Late callback', 1, 2)
        self.assertIsNone(app.diarization_started)

    def test_model_banner_uses_elapsed_timer_and_cleans_up_after_ready(self):
        app = self.make_app()
        app.log_warning = Mock()
        app.show_model_notification('start', 'Preparing model: test')
        app.show_model_notification('stage', 'Downloading model: test')
        self.clock.monotonic.return_value = 40.0
        app.tick_diarization_activity()
        self.assertIn('Downloading model: test', app.status.set.call_args.args[0])
        self.assertIn('Elapsed: 00:00:30', app.status.set.call_args.args[0])
        self.assertNotIn('%', app.status.set.call_args.args[0])
        app.show_model_notification('ready', 'Model ready: test')
        self.assertIsNone(app.diarization_started)
        app.activity_label.grid_remove.assert_called()
        app.log_info.assert_called_with('Model ready: test')
        app.log_warning.assert_not_called()

    def test_failed_preparation_hides_banner_and_logs_warning(self):
        app = self.make_app()
        app.log_warning = Mock()
        app.show_model_notification('start', 'Preparing model')
        app.show_model_notification('failed', 'Preparation interrupted')
        app.log_warning.assert_called_once_with('Preparation interrupted')
        self.assertIsNone(app.diarization_timer)
        self.assertIsNone(app.diarization_started)

    def test_stopping_and_unknown_percentage(self):
        app = self.make_app()
        app.begin_diarization_activity()
        app.update_diarization_activity('Grouping speakers...')
        app.tick_diarization_activity()
        self.assertNotIn('%', app.status.set.call_args.args[0])
        app.stop_event.is_set.return_value = True
        app.tick_diarization_activity()
        self.assertIn('Stopping', app.status.set.call_args.args[0])

    def test_summary_preview_is_bounded(self):
        app = self.make_app()
        app.log_diarization_summary([dict(start=i, end=i + 1, speaker='SPEAKER_00') for i in range(30)])
        self.assertEqual(app.log_info.call_count, 23)
        self.assertIn('first 20 of 30', app.log_info.call_args_list[-2].args[0])
        self.assertEqual(app.log_info.call_args.args[0], 'Starting transcription...')


if __name__ == '__main__':
    unittest.main()
