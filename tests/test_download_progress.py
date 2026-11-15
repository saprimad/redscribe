"""Real byte notifications using a simulated Hub HTTP/Xet context, no network."""
from contextlib import contextmanager
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from download_progress import ObservedProgress, hub_download_progress, progress_text, safe_filename


class Bar:
    def __init__(self,total=100,initial=0,desc='model.safetensors',disabled=False):
        self.total,self.n,self.desc,self.disabled=total,initial,desc,disabled
    def update(self,n=1):
        if not self.disabled:
            self.n+=n
        return 'original-result'


class ByteProgressTests(unittest.TestCase):
    def test_resume_and_disabled_terminal_bar_still_report_actual_bytes(self):
        for disabled in (False,True):
            notify=Mock()
            bar=Bar(total=1000,initial=250,disabled=disabled)
            now=[0.0]
            observed=ObservedProgress(bar,notify,clock=lambda:now[0])
            self.assertEqual(notify.call_args.args[1]['downloaded'],250)
            now[0]=1.0
            self.assertEqual(observed.update(250),'original-result')
            self.assertEqual(notify.call_args.args[1]['downloaded'],500)
            self.assertIn('50.0%',progress_text(notify.call_args.args[1]))

    def test_updates_are_throttled_and_completion_is_never_lost(self):
        notify=Mock()
        now=[0.0]
        observed=ObservedProgress(Bar(total=100),notify,clock=lambda:now[0])
        for _ in range(99):
            observed.update(1)
        self.assertEqual(notify.call_count,1)
        observed.update(1)
        self.assertEqual(notify.call_count,2)
        self.assertEqual(notify.call_args.args[1]['downloaded'],100)
        observed.emit(force=True)
        self.assertEqual(notify.call_count,2)

    def test_unknown_total_and_incomplete_rounding_do_not_invent_completion(self):
        notify=Mock()
        observed=ObservedProgress(Bar(total=None),notify)
        observed.update(50)
        observed.emit(force=True)
        self.assertNotIn('%',progress_text(notify.call_args.args[1]))
        self.assertIn('total size unknown',progress_text(notify.call_args.args[1]))
        self.assertIn('99.9%',progress_text(dict(filename='weights',total=10000,downloaded=9999)))

    def test_filename_does_not_expose_signed_urls_or_paths(self):
        name=safe_filename('https://example.test/private/model.safetensors?token=SECRET#hidden')
        self.assertEqual(name,'model.safetensors')
        self.assertNotIn('SECRET',name)
        self.assertEqual(safe_filename(r'C:\Users\Researcher\model.bin'),'model.bin')

    def test_gui_failure_does_not_change_transfer_return_or_raise(self):
        observed=ObservedProgress(Bar(),Mock(side_effect=RuntimeError('window closed')))
        self.assertEqual(observed.update(10),'original-result')


class HubContextTests(unittest.TestCase):
    def setUp(self):
        @contextmanager
        def original(*,desc='model',total=100,initial=0,name='huggingface_hub.http_get',_tqdm_bar=None):
            yield _tqdm_bar if _tqdm_bar is not None else Bar(total=total,initial=initial,desc=desc)
        self.original=original
        self.module=SimpleNamespace(_get_progress_bar_context=original)
        patcher=patch.dict(sys.modules,{'huggingface_hub.file_download':self.module})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_http_and_xet_files_have_independent_rows_and_context_restores(self):
        events=[]
        with hub_download_progress(lambda state,value:events.append((state,value))):
            def transfer(name,kind,total):
                with self.module._get_progress_bar_context(desc=name,total=total,name=kind) as bar:
                    bar.update(total)
            threads=[threading.Thread(target=transfer,args=(f'model-{index}.safetensors',kind,total))
                     for index,kind,total in [(1,'huggingface_hub.http_get',4220000000),
                                              (2,'huggingface_hub.xet_get',478000000)]]
            for thread in threads:thread.start()
            for thread in threads:thread.join()
        self.assertIs(self.module._get_progress_bar_context,self.original)
        finished=[value for _,value in events if value['downloaded']==value['total']]
        self.assertEqual(len(finished),2)
        self.assertNotEqual(finished[0]['id'],finished[1]['id'])
        self.assertEqual({value['total'] for value in finished},{4220000000,478000000})

    def test_failure_retains_partial_bytes_and_restores_original_context(self):
        notify=Mock()
        with self.assertRaises(OSError):
            with hub_download_progress(notify):
                with self.module._get_progress_bar_context(total=100) as bar:
                    bar.update(30)
                    raise OSError('network failed')
        self.assertIs(self.module._get_progress_bar_context,self.original)
        self.assertEqual(notify.call_args.args[1]['downloaded'],30)
        self.assertNotIn('100.0%',progress_text(notify.call_args.args[1]))

    def test_nested_http_retry_does_not_double_count_existing_bar(self):
        events=[]
        with hub_download_progress(lambda state,value:events.append(value)):
            with self.module._get_progress_bar_context(total=100) as first:
                first.update(20)
                with self.module._get_progress_bar_context(total=100,_tqdm_bar=first) as retry:
                    self.assertIs(first,retry)
                    retry.update(80)
        self.assertEqual(len({value['id'] for value in events}),1)
        self.assertEqual(events[-1]['downloaded'],100)

    def test_cached_files_and_unavailable_hooks_do_not_fake_a_percentage(self):
        notify=Mock()
        with hub_download_progress(notify):
            pass  # A cache hit creates no transfer bar.
        notify.assert_not_called()
        del self.module._get_progress_bar_context
        with hub_download_progress(notify):
            pass
        notify.assert_not_called()
