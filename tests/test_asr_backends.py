"""Adapter contracts without network, model weights or a GPU."""
from contextlib import nullcontext
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from asr_backends import EXTRA_MODELS, LocalASR, chunk_ranges, validate_language


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.torch = SimpleNamespace(cuda=Mock(), float16="fp16", inference_mode=nullcontext)
        self.torch.cuda.is_available.return_value = True
        self.transformers = SimpleNamespace(AutoProcessor=Mock(), AutoModelForCTC=Mock(),
                                            WhisperForConditionalGeneration=Mock())
        self.transformers.AutoProcessor.from_pretrained.return_value.tokenizer.vocab={"eng":{},"zlm":{}}
        self.qwen = SimpleNamespace(Qwen3ASRModel=Mock())
        self.runtime = patch.dict(sys.modules, torch=self.torch, transformers=self.transformers, qwen_asr=self.qwen)
        self.runtime.start()
        self.addCleanup(self.runtime.stop)

    def test_ranges_cover_audio_once_with_overlap_and_gaps(self):
        ranges = list(chunk_ranges(95, [{"start": 4, "end": 40}, {"start": 30, "end": 70}]))
        self.assertEqual(ranges[0][0], 0)
        self.assertEqual(ranges[-1][1], 95)
        self.assertAlmostEqual(sum(b-a for a,b in ranges), 95)
        for (a,b),(c,d) in zip(ranges,ranges[1:]):
            self.assertEqual(b,c)
        self.assertTrue(all(0 < b-a <= 30 for a,b in ranges))
        for point in (4,30,40,70):
            self.assertIn(point, [b for _,b in ranges])

    def test_invalid_duration_and_chunk_size_rejected(self):
        for duration in (0,-1,float("nan"),float("inf")):
            with self.assertRaises(ValueError):
                list(chunk_ranges(duration))
        with self.assertRaises(ValueError):
            list(chunk_ranges(10, max_seconds=0))

    def test_no_cpu_or_precision_fallback(self):
        self.torch.cuda.is_available.return_value = False
        with self.assertRaisesRegex(RuntimeError, "No CPU/precision fallback"):
            LocalASR("BuzzASR Malay")
        self.transformers.AutoProcessor.from_pretrained.assert_not_called()

    def test_fixed_malay_decoders_reject_english(self):
        for name in ("BuzzASR Malay", "Meta MMS 1B (Malay)", "Mesolitica XLS-R 300M"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    validate_language(EXTRA_MODELS[name], "en")
                validate_language(EXTRA_MODELS[name], None)

    def test_missing_runtime_reports_install_command(self):
        with patch.dict(sys.modules, transformers=None):
            with self.assertRaisesRegex(RuntimeError, 'requirements-models.txt'):
                LocalASR("BuzzASR Malay")
        with patch.dict(sys.modules, qwen_asr=None):
            with self.assertRaisesRegex(RuntimeError, 'requirements-qwen.txt'):
                LocalASR("Qwen3-ASR 1.7B")

    def test_loading_is_lazy_and_mms_adapter_is_cast_after_loading(self):
        adapter=LocalASR("Meta MMS 1B (Malay)")
        self.transformers.AutoModelForCTC.from_pretrained.assert_not_called()
        model=self.transformers.AutoModelForCTC.from_pretrained.return_value
        model.config._commit_hash="revision-test"
        adapter._load()
        kwargs=self.transformers.AutoModelForCTC.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs["target_lang"], "zlm")
        self.assertEqual(kwargs["torch_dtype"], "fp16")
        model.load_adapter.assert_called_once_with("zlm", force_load=False)
        model.to.assert_called_once_with(device="cuda",dtype="fp16")
        self.transformers.AutoProcessor.from_pretrained.return_value.tokenizer.set_target_lang.assert_called_once_with("zlm")
        self.assertEqual(adapter.revision, "revision-test")

    def test_mms_rejects_unsupported_adapter_before_loading_large_weights(self):
        adapter=LocalASR("Meta MMS 1B (Malay)")
        self.transformers.AutoProcessor.from_pretrained.return_value.tokenizer.vocab={"eng":{}}
        with self.assertRaisesRegex(RuntimeError,"configured Malay adapter 'zlm'"):
            adapter._load()
        self.transformers.AutoModelForCTC.from_pretrained.assert_not_called()

    def test_mms_load_requests_real_checkpoint_malay_adapter_without_substitution(self):
        calls=[]
        def checkpoint_load(checkpoint, **kwargs):
            self.assertEqual(checkpoint,"facebook/mms-1b-all")
            if kwargs.get("target_lang") != "zlm":
                raise OSError("checkpoint adapter not found")
            calls.append(kwargs["target_lang"])
            return Mock()
        self.transformers.AutoModelForCTC.from_pretrained.side_effect=checkpoint_load
        adapter=LocalASR("Meta MMS 1B (Malay)")
        adapter._load()
        self.assertEqual(calls,["zlm"])
        self.assertEqual(adapter.spec.language_adapter,"zlm")

    def test_qwen_batch_one_fp16_and_malay_language(self):
        adapter=LocalASR("Qwen3-ASR 1.7B", "ms")
        adapter._load()
        kwargs=self.qwen.Qwen3ASRModel.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs["dtype"], "fp16")
        self.assertEqual(kwargs["max_inference_batch_size"], 1)
        adapter.model.transcribe.return_value=[SimpleNamespace(text=" uji ")]
        audio=[0.1]
        self.assertEqual(adapter._decode(audio), "uji")
        adapter.model.transcribe.assert_called_once_with(audio=(audio,16000),language="Malay")

    def test_chunk_offsets_and_cleanup_on_success(self):
        adapter=LocalASR("BuzzASR Malay")
        adapter._load=Mock()
        adapter._decode=Mock(return_value="ujian")
        adapter.close=Mock()
        audio=[0.0]*16000*31
        with patch.dict(sys.modules, {"faster_whisper.audio":SimpleNamespace(decode_audio=Mock(return_value=audio))}):
            segments,info=adapter.transcribe("local.mp3")
            self.assertEqual(info.duration,31)
            self.assertEqual(info.language_source,"configured")
            adapter._load.assert_not_called()
            rows=list(segments)
        self.assertEqual([(r.start,r.end) for r in rows],[(0,15.5),(15.5,31)])
        self.assertEqual(sum(len(c.args[0]) for c in adapter._decode.call_args_list),len(audio))
        adapter.close.assert_called_once()

    def test_cancelled_or_failed_inference_releases_model(self):
        for failure in (RuntimeError("out of memory"), InterruptedError("stop")):
            with self.subTest(error=failure):
                adapter=LocalASR("BuzzASR Malay")
                adapter._load=Mock(side_effect=failure)
                adapter.close=Mock()
                with patch.dict(sys.modules, {"faster_whisper.audio":SimpleNamespace(decode_audio=Mock(return_value=[0.0]*16000))}):
                    segments,_=adapter.transcribe("local.mp3")
                    with self.assertRaises(type(failure)):
                        list(segments)
                adapter.close.assert_called_once()

    def test_ctc_non_finite_fp16_output_is_rejected(self):
        adapter=LocalASR("Mesolitica XLS-R 300M")
        adapter._load()
        tensor=Mock()
        tensor.is_floating_point.return_value=True
        adapter.processor.return_value={"input_values":tensor}
        self.torch.isfinite=Mock()
        self.torch.isfinite.return_value.all.return_value=False
        with self.assertRaisesRegex(RuntimeError,"Non-finite FP16"):
            adapter._decode([0.1])
        adapter.processor.batch_decode.assert_not_called()

    def test_whisper_decode_uses_transcribe_without_global_tokenizer_patch(self):
        adapter=LocalASR("Mesolitica Whisper v3", "ms")
        adapter._load()
        tensor=Mock()
        tensor.is_floating_point.return_value=True
        adapter.processor.return_value={"input_features":tensor}
        adapter.processor.batch_decode.return_value=[" hasil "]
        self.assertEqual(adapter._decode([0.2]),"hasil")
        kwargs=adapter.model.generate.call_args.kwargs
        self.assertEqual(kwargs["task"],"transcribe")
        self.assertFalse(kwargs["return_timestamps"])
        self.assertEqual(kwargs["language"],"ms")
        tensor.to.assert_called_once_with(device="cuda",dtype="fp16")


if __name__=="__main__":
    unittest.main()
