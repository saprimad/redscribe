# RedScribe Benchmarking Mode — Implementation status

> **Latest status (25 November 2026):** [Software validation record](validation/FINAL_SOFTWARE_VALIDATION_2026-11-25.md). Synthetic regression suite passed 84/84 on each of Windows and Ubuntu; CPU dependency validation passed on both. Scientific figure checks passed within the synthetic scope. Expert review and local GUI/GPU runtime validation remain pending. All dated sections below are historical, including earlier smoke-test instructions and implementation limitations; use the current validation record for the review gate.

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

## Batch + GPU / VAD / OSD experimental activation — 17 November 2026
- `benchmark_batch.py`: runs a **sequential batch of researcher-confirmed pairs**; validates approved reference manifest and unique mapping before starting; writes one child experiment folder per audio, `batch_results.csv` and atomic `batch_manifest.json` after every recording. Failed inputs are logged and later pairs continue. **Resume is not implemented**; checkpointing only protects output already written.
- `benchmark_batch_ui.py`: researcher explicitly maps each audio to a distinct **already approved** reference. No assumptions about name similarity. Any reapproval or source reselection resets mapping.
- `benchmark_ui.py`: batch and single trial launch controls; checkboxes for GPU/CPU/RAM monitoring, Silero VAD and pyannote Community-1 OSD; optional HF access token. **Maximum 180 seconds per audio still applies**. Choices are optional and off by default for VAD/OSD; GPU monitoring defaults on.
- `benchmark_resources.py`: system-wide nvidia-smi GPU-0 utilisation, used VRAM and temperature plus optional psutil system-wide CPU/RAM snapshots at ~0.5-second intervals. The peaks are **system-wide snapshots**, not process-specific CUDA allocations; this means background GPU workloads can influence results. `*_resources.csv` saved alongside each model output when available. Missing drivers/tools yield null values, not invented zero readings.
- `benchmark_speech.py`: Silero VAD estimated speech/silence and *derived* overlap from cross-speaker intersections of Community-1's **non-exclusive** speaker diarisation timeline. Do **not** substitute its exclusive diarisation output to measure overlap. This is **not** a dedicated OSD classifier and is not validated overlap ground truth.
- `requirements-benchmark.txt` contains optional `silero-vad` and `psutil` installations. Additional gated pyannote model access and optional CUDA runtime configuration may be required for OSD; per-feature failures are clearly marked `unavailable`, and ASR continues.
- `tests/test_benchmark_batch.py` defines synthetic pairing and cross-speaker overlap tests. All tests require execution on the researcher's Windows environment; no actual RTX 5070 run was performed remotely.

### First smoke test instructions
```powershell
git fetch origin
git switch redscribe-benchmark-timeline
git pull --ff-only
python -m pip install -r requirements-benchmark.txt
python -m unittest discover -s tests -p "test_benchmark*.py"
python redscribe_gpu.py
```
Select Batch; select several audio recordings (each <= 3 min) and human-verified DOCX references; approve references individually; click **Verify batch audio / DOCX pairing** and explicitly assign each reference; select one known-working model (Turbo recommended) and enable GPU monitoring initially. Toggle Silero VAD and OSD only after first successful basic test, because OSD may need Hugging Face model access and substantial GPU RAM.

**Scientific HOLD unchanged**: actual DOCX layout and extraction rules; BM/English/Kelantan normalisation; separate interviewer/participant scores; overlap handling in scoring; cross-backend CUDA/Windows/WSL compatibility. VAD/OSD are purely descriptive and do not affect WER. The experimental branch is not publication-ready and must not be merged without explicit approval.
