"""Model requirements fail before processing; output names remain distinct."""
import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from performance_log import RunPerformance, performance_summary, save_performance
import threading
from unittest.mock import Mock, patch

from asr_backends import EXTRA_MODELS
from diarization_options import DiarizationDependencyError
from model_options import (LEGACY_MODELS, MODEL_FOLDERS, ModelPreflightError,
                           describe_model, model_output_folder, preflight_model, ASR_MODEL_LABELS, model_label)


class ModelOptionsTests(unittest.TestCase):
    def test_menu_labels_cover_all_runtimes_with_study_candidates_first(self):
        keys=list(ASR_MODEL_LABELS)
        self.assertEqual(len(keys),11)
        self.assertEqual(set(keys),set(LEGACY_MODELS)|set(EXTRA_MODELS))
        self.assertEqual(keys[-4:],['medium','small','base','tiny'])
        self.assertEqual(sum(label.endswith('(Legacy)') for label in ASR_MODEL_LABELS.values()),4)
        self.assertEqual(model_label('turbo'),'OpenAI Whisper Large-v3 Turbo')
        self.assertEqual(model_label('tiny'),'OpenAI Whisper Tiny (Legacy)')

    def test_tiny_uses_existing_runtime_and_has_its_own_output_folder(self):
        with patch('model_options.importlib.import_module') as importer:
            self.assertIn('CPU INT8',preflight_model('tiny'))
            importer.assert_not_called()
        self.assertEqual(Path(model_output_folder('output','2026-11','tiny')).name,'whisper_tiny')

    def test_distinct_stable_folders_for_every_choice(self):
        choices=(*LEGACY_MODELS,*EXTRA_MODELS)
        paths=[Path(model_output_folder('output','2026-11',name)) for name in choices]
        self.assertEqual(len(paths),len(set(paths)))
        self.assertTrue(all(p.parent==Path('output/2026-11') for p in paths))
        self.assertEqual(paths[0].name,'whisper_large_v3')
        self.assertEqual(MODEL_FOLDERS['Meta MMS 1B (Malay)'],'meta_mms_1b_malay')
        for name in MODEL_FOLDERS.values():
            self.assertRegex(name,r'^[a-z0-9_]+$')

    def test_help_text_explains_language_precision_and_timing(self):
        self.assertIn('CPU INT8 fallback',describe_model('large-v3'))
        for name in EXTRA_MODELS:
            text=describe_model(name)
            self.assertIn('CUDA FP16 required',text)
            self.assertIn('Approximate chunk timestamps',text)
        self.assertIn('zlm',describe_model('Meta MMS 1B (Malay)'))
        self.assertIn('Auto detect',describe_model('Qwen3-ASR 1.7B'))

    def test_legacy_checks_do_not_require_torch_or_optional_dependencies(self):
        with patch('model_options.importlib.import_module') as importer:
            self.assertIn('CPU INT8',preflight_model('turbo'))
            importer.assert_not_called()

    def test_unavailable_cuda_stops_before_optional_runtime_import(self):
        torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False))
        with patch('model_options.importlib.import_module',return_value=torch) as importer:
            with self.assertRaisesRegex(ModelPreflightError,'CUDA is unavailable'):
                preflight_model('BuzzASR Malay')
            importer.assert_called_once_with('torch')

    def test_missing_runtime_has_actionable_command_without_dependency_details(self):
        torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True))
        with patch('model_options.importlib.import_module',side_effect=[torch,ImportError('private detail')]):
            with self.assertRaises(ModelPreflightError) as caught:
                preflight_model('Qwen3-ASR 1.7B')
        self.assertIn('pip install -r requirements-qwen.txt',str(caught.exception))
        self.assertNotIn('private detail',str(caught.exception))

    def test_success_only_imports_runtime_without_loading_weights(self):
        torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True))
        runtime=SimpleNamespace(AutoProcessor=Mock(),WhisperForConditionalGeneration=Mock())
        with patch('model_options.importlib.import_module',side_effect=[torch,runtime]):
            self.assertIn('checks passed',preflight_model('BuzzASR Malay','ms'))
        runtime.AutoProcessor.assert_not_called()
        runtime.WhisperForConditionalGeneration.assert_not_called()

    def test_malay_language_guard_precedes_runtime_import(self):
        with patch('model_options.importlib.import_module') as importer:
            with self.assertRaises(ModelPreflightError):
                preflight_model('Meta MMS 1B (Malay)','en')
            importer.assert_not_called()

    def test_repeated_pair_names_do_not_overwrite_either_export(self):
        source=ast.parse(Path(__file__).resolve().parents[1].joinpath('redscribe_gpu.py').read_text())
        nodes=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='available_output_paths']
        import os
        namespace={'os':os}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'redscribe_gpu.py','exec'),namespace)
        with tempfile.TemporaryDirectory() as base:
            folder=Path(model_output_folder(base,'2026-11','BuzzASR Malay'))
            folder.mkdir(parents=True)
            stem='study_buzzasr_malay'
            old=folder/(stem+'.docx')
            old.write_text('keep previous result')
            xlsx,docx=namespace['available_output_paths'](str(folder),stem)
            self.assertEqual(Path(xlsx).stem,Path(docx).stem)
            self.assertEqual(Path(docx).stem,stem+'_2')
            self.assertEqual(old.read_text(),'keep previous result')


class WorkerPreflightTests(unittest.TestCase):
    def setUp(self):
        class Cancelled(Exception):
            pass
        self.cancelled=Cancelled
        self.check=Mock(return_value='Checks passed')
        self.ns=dict(RunPerformance=RunPerformance, performance_summary=performance_summary, save_performance=save_performance, model_label=lambda model:model, preflight_model=self.check,ModelPreflightError=ModelPreflightError,
                     DiarizationDependencyError=DiarizationDependencyError,load_pyannote_pipeline_class=Mock(),
                     TranscriptionCancelled=Cancelled,release_gpu_cache=Mock())
        source=ast.parse(Path(__file__).resolve().parents[1].joinpath('redscribe_gpu.py').read_text())
        node=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='RedScribeApp')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'redscribe_gpu.py','exec'),self.ns)
        self.app=self.ns['RedScribeApp'].__new__(self.ns['RedScribeApp'])
        self.app.root=Mock()
        self.app.run_lock=threading.Lock()
        self.app.show_run_error=Mock()
        self.app.status=Mock()
        self.app.check_stop=Mock()
        self.app._run_whisper=Mock()
        self.app.last_output_folder='previous-successful-folder'
        self.inputs={'whisper_model':'BuzzASR Malay','language':'ms'}

    def test_failure_never_enters_download_diarisation_or_output_pipeline(self):
        self.check.side_effect=ModelPreflightError('Install optional runtime')
        self.app.run_whisper(self.inputs)
        self.app._run_whisper.assert_not_called()
        self.assertEqual(self.app.last_output_folder,'previous-successful-folder')
        final=self.app.root.after.call_args.args
        self.assertEqual(final[1],self.app.complete_run)
        self.assertFalse(final[2])
        final[3]()
        self.app.show_run_error.assert_called_once_with('Model requirements','Install optional runtime','Requirements check failed; nothing processed')

    def test_success_enters_pipeline_after_requirements_and_stop_check(self):
        calls=[]
        self.check.side_effect=lambda *a:calls.append('requirements') or 'Checks passed'
        self.app.check_stop.side_effect=lambda:calls.append('stop check')
        self.app._run_whisper.side_effect=lambda *a:calls.append('pipeline')
        self.app.run_whisper(self.inputs)
        self.assertEqual(calls,['requirements','stop check','pipeline'])

    def test_broken_diarisation_dependency_stops_before_any_model_processing(self):
        self.inputs['diarization_enabled']=True
        self.ns['load_pyannote_pipeline_class'].side_effect=DiarizationDependencyError('Repair OpenTelemetry')
        self.app.run_whisper(self.inputs)
        self.app._run_whisper.assert_not_called()
        final=self.app.root.after.call_args.args
        self.assertEqual(final[1],self.app.complete_run)
        self.assertFalse(final[2])
        final[3]()
        self.app.show_run_error.assert_called_once_with('Model requirements','Repair OpenTelemetry','Requirements check failed; nothing processed')

    def test_stop_during_preflight_does_not_enter_pipeline(self):
        self.app.check_stop.side_effect=self.cancelled()
        self.app.run_whisper(self.inputs)
        self.app._run_whisper.assert_not_called()
        self.app.root.after.assert_any_call(0,self.app.complete_run,True,None)


if __name__=='__main__':
    unittest.main()
