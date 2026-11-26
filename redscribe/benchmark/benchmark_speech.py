"""Optional observational VAD and overlap speech summaries.

Silero: detected speech/non-speech seconds, not transcription ground truth.
OSD: intersecting *different speaker* turns from non-exclusive pyannote
speaker_diarization; never use exclusive_speaker_diarization for overlap.
Dependencies/models can be unavailable, in which case report 'unavailable'.
"""
import gc


def union_duration(intervals):
    merged = []
    for start, end in sorted((float(a), float(b)) for a, b in intervals if b > a):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return sum(b-a for a, b in merged)


def overlap_intervals(turns):
    """Sweeping interval endpoints: merged windows with >=2 distinct speaker IDs."""
    events = []
    for turn in turns:
        a, b = float(turn["start"]), float(turn["end"])
        if b > a:
            events.extend(((a, 1, turn["speaker"]), (b, -1, turn["speaker"])))
    events.sort(key=lambda x: (x[0], x[1]))  # ends processed before starts
    active = {}
    windows = []
    previous = None
    for timestamp, change, speaker in events:
        if previous is not None and timestamp > previous and len(active) >= 2:
            windows.append((previous, timestamp))
        active[speaker] = active.get(speaker, 0) + change
        if not active[speaker]:
            del active[speaker]
        previous = timestamp
    merged = []
    for a, b in windows:
        if merged and abs(merged[-1][1] - a) < 1e-8:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged


def analyse_vad(audio, sample_rate=16000):
    """Silero VAD via optional silero-vad package. CPU only."""
    from faster_whisper.audio import decode_audio
    from silero_vad import load_silero_vad, get_speech_timestamps
    import torch
    waveform = decode_audio(str(audio), sampling_rate=sample_rate)
    model = load_silero_vad()
    segments = get_speech_timestamps(torch.from_numpy(waveform), model,
                                     sampling_rate=sample_rate, return_seconds=True)
    speech = union_duration((s["start"], s["end"]) for s in segments)
    duration = len(waveform) / sample_rate
    del model
    gc.collect()
    return {"status": "completed", "engine": "silero-vad", "duration_s": round(duration, 3),
            "speech_s": round(speech, 3), "non_speech_s": round(max(0., duration-speech), 3),
            "speech_ratio": round(speech/duration, 5) if duration else None,
            "speech_segments": len(segments)}


def analyse_osd(audio, duration_s, *, token=None):
    """Non-exclusive Community-1 diarization overlap estimate.

    Reuses existing audio decode and pipeline setup, but deliberately does NOT
    reuse the ordinary run_diarization helper, which prefers exclusive tracks.
    """
    from redscribe_gpu import (create_diarization_pipeline,
                               load_audio_for_pyannote, release_gpu_cache)
    from diarization_options import DIARIZATION_MODELS, DEFAULT_DIARIZATION_MODEL
    import torch
    model_id = "pyannote/speaker-diarization-community-1"
    pipeline = create_diarization_pipeline(token, "cuda" if torch.cuda.is_available() else "cpu",
                                           model_id=model_id)
    try:
        audio_input = load_audio_for_pyannote(str(audio))
        output = pipeline(audio_input)
        annotation = getattr(output, "speaker_diarization", None)
        if annotation is None:
            # Explicitly reject exclusive timelines; they CANNOT indicate overlap.
            if hasattr(output, "exclusive_speaker_diarization"):
                raise RuntimeError("No non-exclusive speaker timeline from Community-1")
            annotation = output
        turns = [{"start": t.start, "end": t.end, "speaker": str(s)}
                 for t, _, s in annotation.itertracks(yield_label=True)]
        overlaps = overlap_intervals(turns)
        seconds = sum(b-a for a, b in overlaps)
        return {"status": "completed", "engine": model_id,
                "method": "cross-speaker intersection of non-exclusive diarization turns",
                "overlap_s": round(seconds, 3), "overlap_ratio": round(seconds/duration_s, 5),
                "overlap_events": len(overlaps), "overlap_windows_s": overlaps,
                "speaker_count_estimate": len({t["speaker"] for t in turns})}
    finally:
        del pipeline
        release_gpu_cache()


def analyse_audio(audio, duration_s, *, vad=False, osd=False, hf_token=None,
                  notify=None):
    result = {"vad": {"status": "disabled"}, "osd": {"status": "disabled"}}
    for key, enabled, action in (
        ("vad", vad, lambda: analyse_vad(audio)),
        ("osd", osd, lambda: analyse_osd(audio, duration_s, token=hf_token)),
    ):
        if enabled:
            try:
                result[key] = action()
            except Exception as exc:
                result[key] = {"status": "unavailable",
                               "reason": f"{type(exc).__name__}: {exc}"}
                if notify is not None:
                    notify("warning", f"{key.upper()} unavailable: {type(exc).__name__}: {exc}")
    return result
