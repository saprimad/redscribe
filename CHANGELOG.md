# Changelog

All notable changes to RedScribe are documented in this file.

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

### Security

- Added repository exclusions for credentials, recordings, transcripts, data and generated outputs.

## Earlier prototype

The initial repository contained Whisper transcription and experimental Qwen/Ollama-assisted coding. That prototype remains available in `whisper_gui.py` for reference.
