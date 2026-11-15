"""Loading notifications and cache/download phases without network or weights."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

from model_loading import model_preparation
from model_options import model_label

SOURCE=ast.parse(Path(__file__).resolve().parents[1].joinpath("redscribe_gpu.py").read_text())


class PreparationTests(unittest.TestCase):
    def test_ready_follows_success_only(self):
        notify=Mock()
        with model_preparation("test-model",notify):
            self.assertNotIn("ready",[c.args[0] for c in notify.call_args_list])
        self.assertEqual([c.args[0] for c in notify.call_args_list],["start","info","ready"])
        self.assertIn("first use",notify.call_args_list[1].args[1])

    def test_failed_or_cancelled_load_never_announces_ready(self):
        for error in (RuntimeError("download failed"),InterruptedError("stop")):
            notify=Mock()
            with self.assertRaises(type(error)):
                with model_preparation("test-model",notify):
                    raise error
            self.assertEqual([c.args[0] for c in notify.call_args_list],["start","info","failed"])


class WhisperPreparationTests(unittest.TestCase):
    def setUp(self):
        class MissingCache(Exception):
            pass
        self.missing=MissingCache
        self.download=Mock(return_value="cached/model")
        self.engine=Mock(return_value="loaded-model")
        self.os=Mock()
        self.os.path.isfile.return_value=True
        self.ns=dict(os=self.os,WhisperModel=self.engine,model_preparation=model_preparation,model_label=model_label,
                     WHISPER_DEVICE_PRIORITY=["cuda","cpu"],WHISPER_COMPUTE_TYPE={"cuda":"float16","cpu":"int8"},
                     cpu_thread_budget=lambda:4)
        node=next(n for n in SOURCE.body if isinstance(n,ast.FunctionDef) and n.name=="create_whisper_model")
        exec(compile(ast.Module(body=[node],type_ignores=[]),"redscribe_gpu.py","exec"),self.ns)
        patcher=patch.dict(sys.modules,{
            "faster_whisper.utils":SimpleNamespace(download_model=self.download),
            "huggingface_hub.errors":SimpleNamespace(LocalEntryNotFoundError=MissingCache)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_cache_hit_does_not_download(self):
        notify=Mock()
        self.assertEqual(self.ns['create_whisper_model']('turbo',notify),('loaded-model','cuda','float16'))
        self.download.assert_called_once_with('turbo',local_files_only=True)
        self.assertIn('Using saved model files',notify.call_args_list[2].args[1])
        self.assertEqual(notify.call_args.args[0],'ready')

    def test_cache_miss_and_partial_cache_download_before_loading(self):
        for partial in (False,True):
            with self.subTest(partial=partial):
                self.download.reset_mock()
                self.download.side_effect=None if partial else [self.missing(),"downloaded/model"]
                self.os.path.isfile.return_value=not partial
                notify=Mock()
                self.ns['create_whisper_model']('large-v3',notify)
                self.assertEqual(self.download.call_count,2)
                messages=[c.args[1] for c in notify.call_args_list]
                self.assertTrue(any('Downloading model:' in x for x in messages))
                self.assertTrue(any('Download complete.' in x for x in messages))
                self.assertEqual(notify.call_args.args[0],'ready')

    def test_network_failure_does_not_try_inference_or_announce_ready(self):
        self.download.side_effect=[self.missing(),OSError('network down')]
        notify=Mock()
        with self.assertRaises(OSError):
            self.ns['create_whisper_model']('turbo',notify)
        self.engine.assert_not_called()
        self.assertEqual(notify.call_args.args[0],'failed')

    def test_cpu_fallback_is_announced_without_second_download(self):
        self.engine.side_effect=[RuntimeError('CUDA unavailable'),'cpu-model']
        notify=Mock()
        self.assertEqual(self.ns['create_whisper_model']('turbo',notify),('cpu-model','cpu','int8'))
        self.download.assert_called_once()
        self.assertTrue(any('CPU INT8 fallback' in c.args[1] for c in notify.call_args_list))


if __name__=='__main__':
    unittest.main()
