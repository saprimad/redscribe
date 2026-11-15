"""Local per-run wall-clock measurements; never serialise GUI inputs or tokens."""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import time
from uuid import uuid4


class RunPerformance:
    def __init__(self, model, clock=None):
        self.clock = clock or time.perf_counter
        self.started = self.clock()
        self.started_utc = datetime.now(timezone.utc).isoformat()
        self.run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid4().hex[:12]
        self.details = {'model': model, 'python_version': platform.python_version(),
                        'platform': platform.system()}
        self.active = {}
        self.intervals = {}
        self.outcome = 'failed'
        self.asr_completed = False

    def begin(self, stage):
        if stage in self.active:
            raise RuntimeError(f'Performance stage already active: {stage}')
        self.active[stage] = self.clock()

    def end(self, stage):
        start = self.active.pop(stage, None)
        if start is not None:
            self.intervals.setdefault(stage, []).append((start, self.clock()))

    def finish(self):
        stopped = self.clock()
        interrupted = list(self.active)
        for name, start in self.active.items():
            self.intervals.setdefault(name, []).append((start, stopped))
        self.active.clear()
        stages = {name: sum(b-a for a, b in spans) for name, spans in self.intervals.items()}
        asr_spans = self.intervals.get('asr_pipeline', [])
        prep_spans = self.intervals.get('asr_model_preparation', [])
        overlap = sum(max(0, min(b, d)-max(a, c)) for a, b in asr_spans for c, d in prep_spans)
        asr_seconds = max(0, stages.get('asr_pipeline', 0)-overlap) if self.asr_completed else None
        duration = self.details.get('audio_duration_seconds')
        valid_ratio = duration is not None and duration > 0 and asr_seconds is not None and asr_seconds > 0
        return {
            'schema_version': 1, 'run_id': self.run_id, 'started_utc': self.started_utc,
            'outcome': self.outcome, **self.details,
            'total_wall_seconds': round(stopped-self.started, 6),
            'stage_seconds': {key: round(value, 6) for key, value in stages.items()},
            'unfinished_stages': interrupted, 'asr_completed': self.asr_completed,
            'asr_processing_seconds_excluding_model_preparation': round(asr_seconds, 6) if asr_seconds is not None else None,
            'asr_real_time_factor': round(asr_seconds/duration, 6) if valid_ratio else None,
            'asr_speed_x_realtime': round(duration/asr_seconds, 6) if valid_ratio else None,
            'timing_scope': 'Host wall time. ASR includes audio decoding, VAD where supported, segment iteration, UI dispatch and backend cleanup; excludes model preparation overlapping that interval. Not GPU kernel timing.',
            'stage_overlap_note': 'ASR model preparation can occur inside asr_pipeline for lazy backends; stage durations must not be summed. Diarisation includes its own loading/download and cleanup.',
        }


def performance_summary(record):
    stages = record['stage_seconds']
    asr = record['asr_processing_seconds_excluding_model_preparation']
    speed = record['asr_speed_x_realtime']
    asr_text = f'{asr:.2f}s' if asr is not None else 'incomplete / unavailable'
    ratio = f" | RTF {record['asr_real_time_factor']:.3f} | {speed:.2f}x realtime" if speed is not None else ''
    return (f"Performance [{record['outcome']}]: total {record['total_wall_seconds']:.2f}s | "
            f"ASR model preparation (cache/download/load) {stages.get('asr_model_preparation', 0):.2f}s | "
            f"diarisation (including preparation) {stages.get('diarisation', 0):.2f}s | "
            f"ASR processing {asr_text}{ratio} | Excel {stages.get('excel_export', 0):.2f}s | "
            f"Word {stages.get('word_export', 0):.2f}s | cleanup {stages.get('cleanup', 0):.2f}s")


def save_performance(record, output_directory):
    folder = Path(output_directory) / 'performance'
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / (record['run_id'] + '.json')
    log_path = folder / (record['run_id'] + '.log')
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    log_path.write_text(performance_summary(record) + '\n\n' +
                        f"Model: {record['model']}\nStarted (UTC): {record['started_utc']}\n" +
                        record['timing_scope'] + '\n' + record['stage_overlap_note'] + '\n', encoding='utf-8')
    return json_path, log_path
