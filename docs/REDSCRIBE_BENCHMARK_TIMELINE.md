# RedScribe Benchmarking Mode — Specification & Development Timeline

**Status:** Design approved in principle; implementation not started  
**Updated:** 17 November 2026  
**Branch:** `redscribe-benchmark-timeline`  
**Scope:** Research-oriented ASR benchmarking. **Do not change production transcription behaviour or merge into `main` without review.**

## Objective
Introduce a reproducible, research-ready benchmarking mode that compares ASR transcription accuracy, audio/dataset characteristics and computational efficiency on user-supplied recordings with manually corrected ground-truth transcripts.

## Model selection
All 11 models must be independently selectable. The first seven are selected **by default**; all may be unchecked:
1. Whisper Large-v3
2. Whisper Large-v3 Turbo
3. Mesolitica Malaysian Whisper Large-v3 Turbo V3
4. Mesolitica XLS-R 300M Mixed
5. Meta MMS-1B All
6. Qwen3-ASR 1.7B
7. BuzzASR Malay

Optional, unchecked by default: Whisper Medium, Whisper Small, Whisper Base, Whisper Tiny.

Controls: **Default 7**, **Select All**, **Clear All**. Verify exact model repositories, compatibility and runtime availability during implementation; the names above describe the research plan, not an assertion that all are ready to run.

## Modes and operation
- **Single:** one recording with one matched ground-truth DOCX.
- **Batch:** multiple recordings paired unambiguously with corresponding DOCX files by Audio ID, with human confirmation of mapping.
- Sequential model execution; record start/end, model load and inference time separately, save intermediate results, attempt release of model resources before next model.
- Pre-run warning that long jobs consume CPU/GPU, memory, disk and energy. Show progress, per-model status, error logs and resumable checkpoints.
- On failure record Failed/Skipped and proceed safely; **never** count failed runs as WER = 100%.
- Use the same source recording for every model and record any preprocessing/model-specific requirements. VAD statistics must **not** silently trim scoring audio.

## Reference management
- Ground truth: manually corrected **Word (.docx)** transcripts with speaker labels and **no speaker timestamps**.
- Preserve original DOCX and verbatim dialect; extract spoken text into a preview for approval. Remove only labels and verified non-speech metadata from the **scoring copy**.
- Store file hashes, extraction rules and matching Audio IDs.
- Do **not** calculate DER/JER from speaker labels alone: diarization reference timestamps are not available.

## Accuracy metrics
- WER and CER per model / audio; substitution, deletion and insertion counts, word-level aligned errors and context.
- **Raw** and reproducibly **normalised** scoring with a clearly versioned shared text-normalisation policy. Never silently standardise Kelantan dialect.
- Batch: per-recording rows, macro-average and **corpus-level** (micro) WER/CER. Explicit denominators, missing data and confidence/uncertainty where appropriate.
- Keep speaker-specific accuracy an open design decision; dialogue labels in DOCX alone do not guarantee that ASR output can be mapped to speakers.

## Audio metadata report (automatic)
- Audio ID, original filename, duration, format, size, sample rate, channels, bit depth and bitrate when available.
- Peak amplitude (dBFS) and clipping estimates with defined algorithms and thresholds.
- No inferred participant demographics from audio.

## Speech characteristics
- **Silero VAD (planned):** estimated speech duration, non-speech duration, speech fraction, segment count and average segment length. Record VAD parameters, version and caveats.
- **pyannote OSD (optional, planned):** estimated simultaneous-speech duration / percentage. OSD is *not* a diarization reference or ground truth.
- Estimated SNR only if a defensible consistent estimation method and its limitations are documented; never present proxy SNR as laboratory-measured ground-truth SNR.
- Audio-quality flags and a language/dialect profile may be added; prefer researcher-supplied labels for language/dialect rather than unsupported automatic claims.

## Ground-truth transcript descriptives
Word and character counts, dialogue-turn count, unique speaker labels, interviewer and participant word counts, percentage of reference **words** spoken by participants, average words per turn and overall recording-level words/minute. Do not mislabel word fraction as speaker speaking-time fraction. Speaker identity across recordings follows approved participant IDs, not automatic voice identification.

## Dataset descriptive statistics
Number of recordings, total recorded hours, total reference words and per-variable mean, SD, median, IQR, min and max. Indicate missing/unavailable audio fields. Report per-audio descriptive rows and aggregate dataset summaries.

## Performance/resource monitoring
Measure transcription time separately from model loading time; RTF = inference time / source duration.
Record peak observed GPU VRAM, average/max sampled GPU utilisation, peak observed system RAM, average sampled CPU utilisation and GPU temperature where supported. Specify sampling cadence, measuring process versus whole system, tool versions and missing measurements. Avoid comparing differently measured timings as equivalent.

## Export and reproducibility
Excel workbook and machine-readable CSV, individual model transcripts, word-level errors, run logs and JSON experiment manifest. Proposed Excel sheets:
1. Audio & Dataset Descriptives
2. Transcript Descriptives
3. ASR Accuracy Results
4. Word-Level Error Analysis
5. Computational Performance
6. Model Comparison Summary
7. Experiment Manifest & Logs

Manifest: experiment ID, UTC/local timestamp, audio and reference hashes, selected models and exact versions/revisions, run status, runtime environment (including hardware), decoding/preprocessing settings, text-normalisation and metric-library versions, VAD/OSD versions/configuration and any exclusions.

## Implementation timeline — phases, not fixed calendar promises
| Phase | Deliverable | Exit/acceptance criteria |
|---|---|---|
| **0. Design review** | Confirm above scope and decide deferred issues | Written decisions; no code changes to `main` |
| **1. Repository audit** | Inspect current UI, model runners, DOCX parser, GPU backends and output paths | Compatibility map + regression-risk checklist |
| **2. Input and reference layer** | Single/batch file matching, DOCX extraction and preview | Speaker labels removed only from scoring copy; validated pairings; unchanged originals |
| **3. Benchmark orchestration** | Model selection, sequential queue, warning, checkpoint/resume, failure isolation | 7 default/11 selectable; repeatable runs; crash recovery |
| **4. Accuracy and error analysis** | WER/CER, S/D/I, alignment, raw/normalised scoring | Unit tests on known examples and corpus-vs-macro aggregation |
| **5. Descriptive analysis** | Audio metadata, VAD; optional OSD and quality proxies; DOCX statistics | Transparent methods, missing values and versioned settings |
| **6. Resource monitoring** | CPU/RAM/GPU/VRAM, load time, inference time and RTF | Sampling logs; failure-safe cross-platform reporting |
| **7. Reporting** | Workbook, CSV, manifest and publication tables | Rebuildable results, data provenance and clear metric definitions |
| **8. Pilot & validation** | Short pilot audio, sample DOCX, multi-model smoke tests and longer resumable batch | Benchmark results verified against independent reference calculations; no regressions in normal transcription mode |
| **9. Review & release decision** | Documentation, limitations, optional PR | Only merge after user review/approval |

### Deferred decisions — HOLD (do not silently decide)
1. Actual DOCX structure (tables vs paragraphs; formatting and annotations).
2. Malay / English / Kelantan text-normalisation specification.
3. Whether and how to report interviewer-only vs participant-only WER/CER.
4. Handling simultaneous speech, interruptions and associated scoring/exclusions.
5. Different model dependencies and GPU/back-end compatibility, including Windows vs WSL.

## Scientific caveats
- No DER/JER without timestamped diarization reference.
- VAD/OSD/SNR outputs are estimates; signal conditions and overlap can affect interpretation, not necessarily prove a causal effect on WER.
- Paired comparisons must use consistent source recordings and explicitly documented scoring transformations.
- Existing ground-truth DOCX may contain confidential participant speech; store and export only in researcher-authorised paths and avoid uploading raw participant data to the repository.
- The scope here is **documentation and timeline**, not evidence of working code or validated benchmark results.

## Scope control
This branch currently exists to preserve the **design and implementation roadmap**. Development should occur incrementally in this branch or subsequent feature branches; `main` stays unchanged until an explicitly reviewed merge.
