"""Deterministic timing and real local log serialization, without models."""
import json
from pathlib import Path
import tempfile
import unittest
from performance_log import RunPerformance, performance_summary, save_performance


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.perf = RunPerformance('test model', clock=lambda: self.now)

    def tick(self, seconds):
        self.now += seconds

    def test_lazy_preparation_excluded_from_asr_and_total_counted_once(self):
        self.perf.begin('preflight'); self.tick(1); self.perf.end('preflight')
        self.perf.begin('asr_pipeline'); self.tick(2)
        self.perf.begin('asr_model_preparation'); self.tick(10); self.perf.end('asr_model_preparation')
        self.tick(3); self.perf.end('asr_pipeline')
        self.perf.begin('excel_export'); self.tick(2); self.perf.end('excel_export')
        self.perf.asr_completed = True
        self.perf.outcome = 'completed'
        self.perf.details['audio_duration_seconds'] = 20
        result = self.perf.finish()
        self.assertEqual(result['total_wall_seconds'], 18)
        self.assertEqual(result['stage_seconds']['asr_pipeline'], 15)
        self.assertEqual(result['asr_processing_seconds_excluding_model_preparation'], 5)
        self.assertEqual(result['asr_real_time_factor'], .25)
        self.assertEqual(result['asr_speed_x_realtime'], 4)
        self.assertIn('4.00x realtime', performance_summary(result))

    def test_eager_preparation_is_not_subtracted_twice(self):
        self.perf.begin('asr_model_preparation'); self.tick(10); self.perf.end('asr_model_preparation')
        self.perf.begin('asr_pipeline'); self.tick(5); self.perf.end('asr_pipeline')
        self.perf.asr_completed = True
        self.perf.details['audio_duration_seconds'] = 20
        self.assertEqual(self.perf.finish()['asr_processing_seconds_excluding_model_preparation'], 5)

    def test_cancelled_or_failed_inference_has_no_speed_claim(self):
        self.perf.begin('asr_pipeline'); self.tick(5)
        self.perf.outcome = 'cancelled'
        self.perf.details['audio_duration_seconds'] = 20
        result = self.perf.finish()
        self.assertEqual(result['unfinished_stages'], ['asr_pipeline'])
        self.assertEqual(result['stage_seconds']['asr_pipeline'], 5)
        self.assertIsNone(result['asr_real_time_factor'])
        self.assertIsNone(result['asr_speed_x_realtime'])
        self.assertIn('incomplete', performance_summary(result))

    def test_missing_or_zero_audio_duration_does_not_invent_rtf(self):
        self.perf.asr_completed = True
        self.perf.details['audio_duration_seconds'] = 0
        self.perf.begin('asr_pipeline'); self.tick(2); self.perf.end('asr_pipeline')
        self.assertIsNone(self.perf.finish()['asr_real_time_factor'])

    def test_real_files_are_unique_parseable_and_contain_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            record = self.perf.finish()
            json_path, log_path = save_performance(record, folder)
            self.assertEqual(json.loads(json_path.read_text())['run_id'], record['run_id'])
            self.assertIn('Performance [failed]', log_path.read_text())
            another = RunPerformance('other').finish()
            another_json, _ = save_performance(another, folder)
            self.assertNotEqual(json_path, another_json)
            self.assertEqual(json_path.parent.name, 'performance')
            self.assertEqual(len(list(Path(folder).rglob('*.json'))), 2)

    def test_repeated_stage_accumulates_and_duplicate_open_stage_rejected(self):
        for _ in range(2):
            self.perf.begin('cleanup'); self.tick(1); self.perf.end('cleanup')
        self.assertEqual(self.perf.finish()['stage_seconds']['cleanup'], 2)
        self.perf.begin('cleanup')
        with self.assertRaises(RuntimeError):
            self.perf.begin('cleanup')


if __name__ == '__main__':
    unittest.main()
