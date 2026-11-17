# RedScribe Benchmarking Mode — Implementation status

**17 November 2026 — Phase 1 foundation + Tkinter configuration preview.** This is not a working benchmark runner or validated benchmark.

## Current additions
- `benchmark_config.py`: eleven stable desktop-model keys, seven selected by default, strict validation and canonical selection order. Single/batch **configuration only**.
- `benchmark_metrics.py`: standalone raw WER/CER edit counts (S/D/I), corpus totals and macro-average; deliberately no preprocessing assumptions.
- `tests/test_benchmark_foundation.py`: small deterministic unit-test cases for configuration, editing and aggregation.
- `benchmark_ui.py`: standalone Tkinter Toplevel preview with Single/Batch controls, all 11 model checkboxes (7 default), file chooser, validation of non-empty selection and explanatory pre-run warning. It cannot start ASR.
- `redscribe_gpu.py`: a single header button and lazy callback open the independent preview. Existing transcription controls and processing are not deliberately altered.

## Audit observations
- `redscribe_gpu.py` is the current Tkinter application; not modified here.
- `model_options.py` already defines all eleven stable model keys.
- `asr_backends.py` has optional model adapters, but model availability/per-model VRAM remains unverified.
- `performance_log.py` logs runtime and RTF already; benchmark-specific monitoring should reuse measured concepts without confusing preparation with inference.
- `requirements.txt` currently has no dedicated WER package; this foundation uses pure Python.

## Not implemented
Functional benchmark execution, DOCX parsing and speaker filtering, validated ground-truth matching, model queue, checkpoints, GPU monitoring, VAD/OSD, Excel reporting, statistical testing, normalised scoring and word-level alignment exports. The UI is a **preview**, not a finished tab or production runner. No actual audio was scored.

## Deferred/HOLD decisions
1. Structure of actual ground-truth Word documents.
2. BM/English/Kelantan normalisation rules.
3. Speaker-specific WER/CER.
4. Overlapping speech and interruption scoring.
5. Model backend/dependency/GPU compatibility.

**Safety:** Do not import participant transcripts into GitHub. Keep this branch separate from `main` until reviewed. The raw metrics implementation uses quadratic dynamic-programming memory and needs profiling/optimisation before full-length research transcripts are scored.

## UI preview verification
- Source integration checked: header opens `benchmark_ui.open_benchmark_window` through lazy import.
- Existing mode configuration uses the canonical eleven model keys from `model_options.py`.
- Local Tkinter visual smoke test and full automated test run are **not yet performed**; users should verify on their Windows environment before considering the UI validated.

## Design decisions recorded — 17 November 2026
- Approved conceptual DOCX workflow: **Extract → Preview → Approve → Freeze → Score → Audit**, preserving the original human-corrected document.
- Agreed on **one Python WER/CER scoring engine**; `jiwer` is a candidate, not yet installed or chosen. Existing `benchmark_metrics.py` is only a raw foundation and has not been independently validated.
- NIST SCTK/SCLITE will serve as **independent validation** during development, not a mandatory runtime component.
- Open ASR Leaderboard and MLPerf Whisper provide **reproducibility and consistent scoring principles**, not separate installed engines.
- Record hashes and versions of approved references and model hypotheses for traceability.
- The five pre-existing deferred methodological items remain **HOLD**. No parser, approval/freeze workflow or NIST integration has been implemented yet.

## Ground truth import implementation — 17 November 2026
**Committed in benchmark branch only:**
- `benchmark_ground_truth.py` extracts paragraph and table-cell content from DOCX in document order without silently deleting speaker labels, dialect or fillers. It deliberately does **not** assume a final Word layout.
- `benchmark_reference.py` creates a locally stored approved scoring-text snapshot plus SHA-256 manifest; can detect a subsequent modification of the frozen text.
- `benchmark_reference_ui.py` supports document selection, editable scoring-text preview, explicit researcher acknowledgement and local Approve & Freeze.
- `benchmark_ui.py` now exposes **Review / Approve / Freeze DOCX** after selecting references and displays the count of approved local references.
- `tests/test_benchmark_reference.py` defines synthetic-DOCX tests of extraction ordering, explicit approval, no changes to the original DOCX and hash validation.

**Validation pending:** tests have been written, but could not be executed against the user's Windows environment from this session. Visual Tkinter testing, more complex DOCX cases (merged cells, tracked changes, text boxes, headers/footers), confidentiality checks and real-file parser audit remain outstanding.

**Critical controls:** clicking approval does not launch an ASR benchmark. A frozen reference is private local researcher data; avoid pushing outputs to GitHub. Audio/reference pair matching is **not** approved yet. Five existing methodological questions remain HOLD.

## Short-audio pilot execution — experimental (17 November 2026)
- `benchmark_pilot.py`: **real** sequential ASR execution for **Single mode only** (audio <= 180 seconds). For each selected model: preflight, load and transcribe through existing model adapters, calculate **raw** WER/CER/S/D/I against the approved local text, then persist transcript TXT, results CSV and atomic JSON manifest. Failures are recorded with null scores; subsequent models continue.
- `benchmark_ui.py`: **Start short-audio pilot**, confirmation warning, status text and cooperative **Stop pilot** request. Only locally approved/frozen references can be used. Runs in a worker thread. Checkpoint *writes* exist, but **resume is not implemented**.
- `benchmark_metrics.py` now uses a linear-memory edit-count DP to reduce CER memory pressure (still quadratic CPU time).
- `tests/test_benchmark_pilot.py`: mocked smoke cases for one successfully scored model and failed CUDA preflight.

**Important limitations:** UI Batch mode is still preview-only. Automatic speaker-label removal, reference/audio matching, approved normalisation, full word-level alignment, independent NIST scoring validation, VAD/OSD, resource sampling, Excel reporting, complete resumability and strict fair decoding-policy alignment have not been completed. Optional adapter inference time may include lazy model loading; the pilot flags it in `timing_note` rather than treating it as pure ASR time. Faster-Whisper may fall back to CPU; model-specific runtime constraints remain. Do **not** use pilot results as publication-ready comparisons yet.

**Test status:** GitHub commit made; local Windows GPU/GUI tests and test-suite execution are not yet verified. Run `python -m unittest discover -s tests -p "test_benchmark*.py"`, followed by a short non-sensitive audio with one model first. The user's five pending design decisions stay HOLD. No changes to `main`.
