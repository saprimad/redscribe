"""Selectable local pyannote checkpoints; runtime calls are mocked."""
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from diarization_options import (DEFAULT_DIARIZATION_MODEL, DIARIZATION_MODELS, DEFAULT_DIARIZATION_CHOICE,
                                  load_pyannote_pipeline_class, DiarizationDependencyError)

SOURCE=ast.parse(Path(__file__).resolve().parents[1].joinpath('redscribe_gpu.py').read_text())


def load_functions(names,namespace):
    nodes=[n for n in SOURCE.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'redscribe_gpu.py','exec'),namespace)


class PipelineChoiceTests(unittest.TestCase):
    def setUp(self):
        self.pipeline=Mock()
        self.ns=dict(os=os,load_pyannote_pipeline_class=load_pyannote_pipeline_class,DIARIZATION_MODEL=DEFAULT_DIARIZATION_MODEL,DIARIZATION_MODELS=DIARIZATION_MODELS)
        load_functions({'create_diarization_pipeline'},self.ns)
        patcher=patch.dict(sys.modules,{'pyannote.audio':SimpleNamespace(Pipeline=self.pipeline)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_both_checkpoints_use_selected_token_and_never_switch_models(self):
        for checkpoint in DIARIZATION_MODELS.values():
            self.pipeline.reset_mock()
            result=self.ns['create_diarization_pipeline']('example-only','cpu',model_id=checkpoint)
            self.pipeline.from_pretrained.assert_called_once_with(checkpoint,token='example-only')
            self.assertIs(result,self.pipeline.from_pretrained.return_value)

    def test_default_checkpoint_is_community(self):
        self.ns['create_diarization_pipeline']('example-only')
        self.pipeline.from_pretrained.assert_called_once_with(DEFAULT_DIARIZATION_MODEL,token='example-only')

    def test_old_auth_keyword_fallback_preserves_selected_checkpoint(self):
        checkpoint='pyannote/speaker-diarization-3.1'
        self.pipeline.from_pretrained.side_effect=[TypeError('unexpected keyword token'),'pipeline']
        result=self.ns['create_diarization_pipeline']('example-only','cpu',model_id=checkpoint)
        self.assertEqual(result,'pipeline')
        self.pipeline.from_pretrained.assert_called_with(checkpoint,use_auth_token='example-only')
        self.assertEqual(self.pipeline.from_pretrained.call_count,2)

    def test_access_failure_does_not_substitute_community(self):
        self.pipeline.from_pretrained.side_effect=OSError('access denied')
        with self.assertRaises(OSError):
            self.ns['create_diarization_pipeline']('example-only','cpu',model_id='pyannote/speaker-diarization-3.1')
        self.pipeline.from_pretrained.assert_called_once()

    def test_unknown_checkpoint_rejected_before_loading(self):
        with self.assertRaises(ValueError):
            self.ns['create_diarization_pipeline']('example-only',model_id='unknown/checkpoint')
        self.pipeline.from_pretrained.assert_not_called()


class DependencyImportTests(unittest.TestCase):
    def test_missing_pyannote_is_distinguished_from_missing_subdependency(self):
        for missing in ('pyannote','pyannote.audio'):
            with patch('importlib.import_module',side_effect=ModuleNotFoundError('missing',name=missing)):
                with self.assertRaisesRegex(DiarizationDependencyError,'not installed'):
                    load_pyannote_pipeline_class()
        with patch('importlib.import_module',side_effect=ModuleNotFoundError('missing',name='other_dependency')):
            with self.assertRaises(DiarizationDependencyError) as caught:
                load_pyannote_pipeline_class()
        self.assertIn('dependency could not be imported',str(caught.exception))
        self.assertNotIn('pyannote.audio is not installed',str(caught.exception))

    def test_opentelemetry_error_has_repair_steps_and_interpreter(self):
        error=ImportError("cannot import name '_ExtendedAttributes' from 'opentelemetry.util.types'")
        with patch('importlib.import_module',side_effect=error):
            with self.assertRaises(DiarizationDependencyError) as caught:
                load_pyannote_pipeline_class()
        message=str(caught.exception)
        self.assertIn('OpenTelemetry dependencies are incompatible',message)
        self.assertIn('opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp',message)
        self.assertIn(sys.executable,message)
        self.assertNotIn('pyannote.audio is not installed',message)
        self.assertIs(caught.exception.__cause__,error)

    def test_success_does_not_load_any_model_weights(self):
        pipeline=Mock()
        with patch('importlib.import_module',return_value=SimpleNamespace(Pipeline=pipeline)):
            self.assertIs(load_pyannote_pipeline_class(),pipeline)
        pipeline.assert_not_called()
        pipeline.from_pretrained.assert_not_called()


class PreferenceTests(unittest.TestCase):
    def test_independent_preferences_and_default_migrate_old_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            ns=dict(os=os,json=json,model_settings_path=lambda:str(path),WHISPER_MODELS=('large-v3','turbo'),
                    DIARIZATION_MODELS=DIARIZATION_MODELS,DEFAULT_DIARIZATION_CHOICE=DEFAULT_DIARIZATION_CHOICE)
            load_functions({'save_model_preference','load_diarization_preference','save_preference'},ns)
            self.assertEqual(ns['load_diarization_preference'](),DEFAULT_DIARIZATION_CHOICE)
            ns['save_model_preference']('turbo')
            self.assertEqual(ns['load_diarization_preference'](),DEFAULT_DIARIZATION_CHOICE)
            ns['save_preference']('diarization_model','pyannote/speaker-diarization-3.1')
            ns['save_model_preference']('large-v3')
            self.assertEqual(ns['load_diarization_preference'](),'3.1 (Legacy / comparison)')
            self.assertEqual(json.loads(path.read_text()),{'whisper_model':'large-v3',
                'diarization_model':'pyannote/speaker-diarization-3.1'})
            ns['save_preference']('diarization_model','removed-model')
            self.assertEqual(ns['load_diarization_preference'](),DEFAULT_DIARIZATION_CHOICE)
