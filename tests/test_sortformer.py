"""NeMo adapter tests without CUDA, NeMo, model weights or network."""
import ast
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from diarization_backends import (DEFAULT_DIARIZER, SORTFORMER, SORTFORMER_CHECKPOINT,
                                   DIARIZATION_MODELS, parse_sortformer_output,
                                   preflight_diarizer, run_sortformer)
from model_options import ModelPreflightError


class SortformerTests(unittest.TestCase):
    def setUp(self):
        self.torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True,empty_cache=Mock()),
                                   device=lambda value:value,float32='fp32',inference_mode=nullcontext)
        self.model=Mock()
        self.model.diarize.return_value=[['0.0 0.5 speaker_0','0.5 1.0 speaker_1']]
        self.nemo=SimpleNamespace(SortformerEncLabelModel=Mock())
        self.nemo.SortformerEncLabelModel.restore_from.return_value=self.model
        self.hub=SimpleNamespace(hf_hub_download=Mock(return_value='/cached/sortformer.nemo'))
        self.decoder=Mock(return_value=[0.0]*16000)
        patcher=patch.dict(sys.modules,{'torch':self.torch,'nemo.collections.asr.models':self.nemo,
                                       'huggingface_hub':self.hub,
                                       'faster_whisper.audio':SimpleNamespace(decode_audio=self.decoder)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_output_normalises_speakers_orders_turns_clamps_frame_rounding(self):
        turns=parse_sortformer_output([['1.0 2.05 speaker_1','0.0 1.0 0','0.5 1.2 speaker_2']],2)
        self.assertEqual(turns[0],dict(start=0,end=1,speaker='SPEAKER_00'))
        self.assertEqual(turns[1]['speaker'],'SPEAKER_02')
        self.assertEqual(turns[-1]['end'],2)
        self.assertEqual(parse_sortformer_output([[]],2),[])

    def test_malformed_output_is_rejected_instead_of_silently_dropping_labels(self):
        bad=[[],['0 1 speaker_0'],[['nan 1 speaker_0']],[['1 0 speaker_0']],
             [['0 1 speaker_4']],[['0 1 other']],[[[0,1,0]]]]
        for output in bad:
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    parse_sortformer_output(output,2)

    def test_one_full_recording_and_expected_count_is_not_forced(self):
        progress=Mock()
        turns=run_sortformer('input.mp3','example-token',speaker_count_text='2',progress_callback=progress)
        self.hub.hf_hub_download.assert_called_once_with(repo_id=SORTFORMER_CHECKPOINT,
            filename='diar_streaming_sortformer_4spk-v2.1.nemo',token='example-token')
        self.model.to.assert_called_once_with(device='cuda',dtype='fp32')
        args=self.model.diarize.call_args.kwargs
        self.assertEqual(len(args['audio']),1)
        self.assertEqual(len(args['audio'][0]),16000)
        self.assertEqual(args['sample_rate'],16000)
        self.assertEqual(args['num_workers'],0)
        self.assertNotIn('num_speakers',args)
        self.assertFalse(args['include_tensor_outputs'])
        self.assertEqual(turns[-1]['speaker'],'SPEAKER_01')
        self.assertTrue(any('expected speaker count is not applied' in c.args[0] for c in progress.call_args_list))
        self.assertFalse(any('example-token' in c.args[0] for c in progress.call_args_list))
        self.torch.cuda.empty_cache.assert_called_once()

    def test_inference_failure_cleans_gpu_and_propagates(self):
        self.model.diarize.side_effect=RuntimeError('failure')
        with self.assertRaises(RuntimeError):
            run_sortformer('input.wav')
        self.torch.cuda.empty_cache.assert_called_once()

    def test_stop_after_download_prevents_model_restore_and_cleans_up(self):
        stop=Mock(side_effect=[None,InterruptedError('stop')])
        with self.assertRaises(InterruptedError):
            run_sortformer('input.wav',check_stop=stop)
        self.nemo.SortformerEncLabelModel.restore_from.assert_not_called()
        self.torch.cuda.empty_cache.assert_called_once()

    def test_preflight_fails_without_cuda_before_download(self):
        self.torch.cuda.is_available=lambda:False
        with self.assertRaisesRegex(ModelPreflightError,'requires CUDA'):
            preflight_diarizer(SORTFORMER)
        self.hub.hf_hub_download.assert_not_called()

    def test_missing_nemo_has_install_instruction_and_no_download(self):
        with patch.dict(sys.modules,{'nemo.collections.asr.models':None}):
            with self.assertRaisesRegex(ModelPreflightError,'requirements-sortformer.txt'):
                preflight_diarizer(SORTFORMER)
        self.hub.hf_hub_download.assert_not_called()


class DiarizerPreferenceTests(unittest.TestCase):
    def test_model_choices_preserve_each_other_and_old_settings_default_to_pyannote(self):
        source=ast.parse(Path(__file__).resolve().parents[1].joinpath('redscribe_gpu.py').read_text())
        names={'save_model_preference','load_diarizer_preference','save_preference'}
        nodes=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in names]
        import os
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            ns=dict(json=json,os=os,model_settings_path=lambda:str(path),
                    WHISPER_MODELS=('large-v3','turbo'),DIARIZATION_MODELS=DIARIZATION_MODELS,
                    DEFAULT_DIARIZER=DEFAULT_DIARIZER)
            exec(compile(ast.Module(body=nodes,type_ignores=[]),'redscribe_gpu.py','exec'),ns)
            self.assertEqual(ns['load_diarizer_preference'](),DEFAULT_DIARIZER)
            ns['save_model_preference']('turbo')
            self.assertEqual(ns['load_diarizer_preference'](),DEFAULT_DIARIZER)
            ns['save_preference']('diarization_backend',SORTFORMER)
            ns['save_model_preference']('large-v3')
            data=json.loads(path.read_text())
            self.assertEqual(data,{'whisper_model':'large-v3','diarization_backend':SORTFORMER})
            self.assertEqual(ns['load_diarizer_preference'](),SORTFORMER)
