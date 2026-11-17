# RedScribe Benchmarking Mode — Implementation status

**17 November 2026 — Phase 1 foundation only.** This is not a working UI, runner or validated benchmark.

## Current additions
- `benchmark_config.py`: eleven stable desktop-model keys, seven selected by default, strict validation and canonical selection order. Single/batch **configuration only**.
- `benchmark_metrics.py`: standalone raw WER/CER edit counts (S/D/I), corpus totals and macro-average; deliberately no preprocessing assumptions.
- `tests/test_benchmark_foundation.py`: small deterministic unit-test cases for configuration, editing and aggregation.

## Audit observations
- `redscribe_gpu.py` is the current Tkinter application; not modified here.
- `model_options.py` already defines all eleven stable model keys.
- `asr_backends.py` has optional model adapters, but model availability/per-model VRAM remains unverified.
- `performance_log.py` logs runtime and RTF already; benchmark-specific monitoring should reuse measured concepts without confusing preparation with inference.
- `requirements.txt` currently has no dedicated WER package; this foundation uses pure Python.

## Not implemented
GUI tab/checkboxes, DOCX parsing and speaker filtering, validated ground-truth matching, model queue, checkpoints, GPU monitoring, VAD/OSD, Excel reporting, statistical testing, normalised scoring and word-level alignment exports. No actual audio was scored.

## Deferred/HOLD decisions
1. Structure of actual ground-truth Word documents.
2. BM/English/Kelantan normalisation rules.
3. Speaker-specific WER/CER.
4. Overlapping speech and interruption scoring.
5. Model backend/dependency/GPU compatibility.

**Safety:** Do not import participant transcripts into GitHub. Keep this branch separate from `main` until reviewed. The raw metrics implementation uses quadratic dynamic-programming memory and needs profiling/optimisation before full-length research transcripts are scored.
