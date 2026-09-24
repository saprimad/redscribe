# RedScribe

RedScribe is a desktop application for transcribing research interviews and other recorded speech. Version 2.0 uses Faster-Whisper for transcription and can optionally use pyannote.audio to distinguish between speakers. It exports a structured Excel workbook for researcher-led verification and qualitative analysis.

## Current release

**Version 2.0.0**

The primary application is [`redscribe_gpu.py`](redscribe_gpu.py). The earlier Qwen/Ollama prototype, [`whisper_gui.py`](whisper_gui.py), is deprecated and retained only for historical reference. It is not supported or recommended for research use.

## Features

- Whisper `large-v3` transcription through Faster-Whisper
- NVIDIA CUDA first, with automatic CPU fallback
- Optional speaker diarisation using `pyannote/speaker-diarization-community-1`
- Optional expected-speaker count
- Live timestamped transcript display
- Sentence-level speaker and timestamp assignment
- Excel export with study metadata, a verification worksheet, speaker counts, speech/silence summary, timeline density and token frequency
- Editable Microsoft Word (`.docx`) report with the same early report sections as Excel, including summary tables, speaker counts, speech/silence and timeline charts, top keywords, and consecutive speech grouped by speaker
- Bottom controls that remain visible as the live transcript area resizes

RedScribe produces an automated draft. Researchers remain responsible for checking the transcript, speaker labels and analytical outputs against the original recording.

## Workflow

Audio or video → Faster-Whisper transcription → optional speaker diarisation → Excel and Word export → researcher verification

## Requirements

- Windows 10 or 11
- Python 3.10 or 3.11 recommended
- FFmpeg available in `PATH`
- NVIDIA GPU recommended; CPU mode is supported but slower
- A Hugging Face account and accepted model conditions when speaker diarisation is enabled

## Installation

1. Clone the repository and enter its folder:

   ```powershell
   git clone https://github.com/saprimad/redscribe.git
   cd redscribe
   ```

2. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   ```

3. If using an NVIDIA GPU, install the appropriate PyTorch build for the CUDA version shown by your driver. Use the command provided by the [PyTorch installation selector](https://pytorch.org/get-started/locally/).

4. Install RedScribe dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Install FFmpeg if it is not already available:

   ```powershell
   winget install Gyan.FFmpeg
   ```

   Close and reopen PowerShell after installation, then verify it with `ffmpeg -version`.

## Speaker diarisation setup

1. Open the model page for [`pyannote/speaker-diarization-community-1`](https://huggingface.co/pyannote/speaker-diarization-community-1) and accept any required conditions.
2. Create a Hugging Face token with read access.
3. Either paste the token into the masked RedScribe field for the current session or set it as an environment variable:

   ```powershell
   $env:HF_TOKEN="your_token_here"
   ```

RedScribe does not write the token to a configuration file. Never commit a token, participant recording or identifiable transcript to GitHub.

## Running RedScribe

```powershell
python redscribe_gpu.py
```

Select an audio or video file, complete the optional study metadata, choose whether to enable speaker diarisation, and start transcription. Matching `.xlsx` and `.docx` files are written to `output/YYYY-MM/`. The Word file begins with the Excel `Early_Report` information and charts, followed by a transcript that combines adjacent utterances from the same speaker into one editable paragraph, labelled with the first start and last end time. The Excel workbook retains each utterance separately, along with verification columns.

Supported input formats shown in the interface are MP3, WAV, M4A and MP4. FFmpeg may support additional formats, but they are not currently exposed by the file picker.

## Processing and privacy

Audio transcription and diarisation run on the user's computer. Internet access may still be required initially to download model files and authenticate with Hugging Face. After the required models are cached, processing can generally occur locally.

The repository's `.gitignore` excludes common audio, video, spreadsheet, transcript, data, credential and output files. This is a safeguard, not a substitute for checking every commit before pushing research material.

## GPU fallback

RedScribe attempts to load Whisper with CUDA and `float16`. If that fails, it falls back to CPU with `int8`. Speaker diarisation is sent to CUDA only when CUDA is available; a diarisation failure does not stop transcription.

## Troubleshooting

- **`ffmpeg` not found:** install FFmpeg, reopen the terminal and confirm `ffmpeg -version` works.
- **Hugging Face access error:** accept the model conditions and check that the token has read access.
- **CUDA or DLL error:** confirm that the NVIDIA driver, PyTorch build and CUDA runtime are compatible.
- **Diarisation fails but transcription continues:** review the warning shown in the application and inspect the generated Excel metadata.
- **Slow processing:** confirm that the status bar reports `CUDA`; CPU transcription with `large-v3` can be substantially slower.

## Repository files

- `redscribe_gpu.py` — current RedScribe v2 application
- `whisper_gui.py` — deprecated Qwen/Ollama prototype retained for historical reference
- `requirements.txt` — Python dependencies
- `CITATION.cff` — software citation metadata
- `CHANGELOG.md` — release history

## Citation

If RedScribe supports a study, cite the software using the metadata in `CITATION.cff`. A DOI can be added after a GitHub release is archived in Zenodo.

## Author

Mad Sapri Tumiran<br>
Faculty of Pharmacy, Universiti Teknologi MARA (UiTM), Malaysia<br>
Support: saprimad@moh.gov.my

## Licence

No open-source licence has yet been declared. The source is publicly viewable, but reuse and redistribution rights are not granted unless the author adds a licence.
