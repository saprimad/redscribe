# Changelog

All notable changes to RedScribe are documented in this file. The dated 2.0.0 entry records the repository baseline on 22 September 2026; no tagged GitHub Release has been published yet. Features under **Unreleased** are already on the main branch but have not been assigned to a tagged release.

## Development documentation for the v2.1.0 target

The [scientific index](docs/scientific/README.md) covers transcription and structured benchmarking. The [consolidated record](docs/validation/CONSOLIDATED_DEVELOPMENT_RECORD_2026-11-28.md) documents the subsequent P1 seven-model execution.

## Historical experimental benchmarking branch — 25 November 2026

Not released or merged into main. Staged package architecture with compatibility entry points; reference approval and integrity checks; single/batch execution and resume; reporting recovery and publication figures. Synthetic regression and CPU dependency validation passed on Windows and Ubuntu. See [validation evidence](docs/validation/FINAL_SOFTWARE_VALIDATION_2026-11-25.md). Actual GPU/GUI and expert review remain pending.

## [Unreleased]

### Added

- Optional local Mesolitica Whisper/XLS-R, Meta MMS-1B-All Malay (`zlm`), Qwen3-ASR and BuzzASR backends, model-specific output folders and checkpoint/precision/timing metadata. These CUDA FP16 adapters do not silently fall back to another precision or CPU.
- Full English model names, supplementary Whisper Tiny/Medium/Small/Base Legacy choices, and pyannote Community-1/3.1 settings.
- Requirements checks, model-preparation activity and real per-file download progress where the installed Hugging Face runtime exposes it.
- Local per-run JSON/readable performance logs with stage timings and completed-ASR RTF/speed, mirrored in Live Transcript and the terminal.
- A pre-merge Windows trial record covering observed results, dependency failures, fixes and outstanding model-quality checks.

- Live English diarisation stages, animated activity and elapsed time, real per-stage progress from pyannote hooks, and a bounded speaker timeline preview before transcription.

- Redesigned Hugging Face token controls with masked Show/Hide entry, Save Token and Remove Saved; persist tokens through native OS keyring backends, reject plaintext fallbacks, and retain session/environment/Hugging Face login support.

- Applied a conservative CPU thread budget to Faster-Whisper (at most 70% of detected logical processors, leaving two unused when available); this is not a system-wide CPU percentage or memory limit.

- Added a Stop button for safe cancellation before report export and a live display of the auto-detected language.
- Added a spoken-language selector (Auto detect, Bahasa Melayu, English) while keeping Whisper in transcription mode.
- Added a local Hugging Face token availability check beside the masked token field; it does not verify access to the diarisation model.
- Added a per-computer Whisper model choice (`large-v3`, `turbo`, `medium`, `small`, `base`) with `large-v3` as the default and the selected model recorded in both reports.
- Editable Word transcript export alongside the existing Excel workbook.
- Added the Excel early report's metadata, transcription summary, speaker counts, charts, timeline and top keywords to the Word output.
- Added the PolyForm Noncommercial 1.0.0 licence and the Malaysia copyright notification (CRDV2026W02110) in the documentation and application footer.

### Changed

- Redesigned the workflow figure in the RedScrap diagram style, separating run settings from the single recording input and showing Word and Excel as two branches from the shared export step.

- Aligned the public website with the redesigned workspace, grouped live paragraphs, diarisation activity and shared report colours.
- Replaced deprecated openpyxl font-copy calls with standard-library copying while preserving bold report headings.

- Group consecutive live transcript segments from the same speaker into one paragraph with an inline timestamp and coloured label, preserving segment data and export behaviour.

- Increased UI/control fonts and the live transcript to 13 pt, with closer segment spacing.
- Shared deterministic speaker-label colours across the live UI, Word transcript/summary and Excel Speaker cells/summary; UNKNOWN uses grey and transcript wording remains unchanged.

- Redesigned the desktop workspace with white/maroon styling, a scrollable left configuration column, a larger live transcript, compact Study details below Audio file in the left column (open by default) and persistent bottom actions.
- Moved all diarisation controls (enabled by default, expected speakers and token management) into Settings, with concise summaries on the main window.
- Added consistent speaker colours in the live transcript and a system-font fallback for Windows, macOS and Linux.

- Preserve previous Excel/Word output pairs by numbering filenames on repeated runs; show the original error when export fails.
- Grouped adjacent utterances from the same speaker into one paragraph in the Word transcript.
- Kept the status and action buttons visible while the transcript panel resizes to fit the window.
- Sized the initial window to the available screen area.
- Listed all four RedScribe authors in the application support dialog and citation metadata.

### Fixed

- Use the supported MMS Malay adapter `zlm` rather than `zsm`, validate vocabulary support and retain CUDA FP16 after loading adapter weights.
- Distinguish broken OpenTelemetry/pyannote imports from a missing package before model processing.
- Reset run state and enable Start only after cleanup, before completion dialogs; show Excel/Word/finalisation activity and recover controls after cleanup/log-write warnings.
- Explicitly request and forward the processor attention mask for optional Transformers Whisper backends, retaining its integer dtype.

## [2.0.0] - 2026-09-22

### Added

- Optional speaker diarisation using `pyannote/speaker-diarization-community-1`.
- Expected-speaker count control.
- Speaker labels and speaker summaries in the Excel output.
- FFmpeg and SoundFile audio-loading workaround for Windows environments affected by TorchCodec `AudioDecoder` errors.
- CUDA diarisation where available, with graceful continuation when diarisation fails.
- Installation, privacy, citation and troubleshooting documentation.

### Changed

- Updated the Whisper model from `medium` to `large-v3`.
- Replaced the Qwen/Ollama coding workflow in the primary application with transcription and speaker diarisation.
- Clarified that all generated content requires researcher verification.
- Standardised the v2 interface, status messages, errors, comments and documentation in professional British English.

### Security

- Added repository exclusions for credentials, recordings, transcripts, data and generated outputs.

## Earlier prototype

The initial repository contained Whisper transcription and experimental Qwen/Ollama-assisted coding. That unstable prototype remains in `whisper_gui.py` for historical reference but is deprecated and unsupported.
