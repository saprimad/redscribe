# Changelog

All notable changes to RedScribe are documented in this file.

## [Unreleased]

### Added

- Editable Word transcript export alongside the existing Excel workbook.
- Added the Excel early report's metadata, transcription summary, speaker counts, charts, timeline and top keywords to the Word output.

### Changed

- Preserve previous Excel/Word output pairs by numbering filenames on repeated runs; show the original error when export fails.
- Grouped adjacent utterances from the same speaker into one paragraph in the Word transcript.
- Kept the status and action buttons visible while the transcript panel resizes to fit the window.
- Sized the initial window to the available screen area.

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
