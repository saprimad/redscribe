# Changelog

All notable changes to RedScribe are documented in this file. The dated 2.0.0 entry records the repository baseline on 22 September 2026; no tagged GitHub Release has been published yet. Features under **Unreleased** are already on the main branch but have not been assigned to a tagged release.

## [Unreleased]

### Added

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
