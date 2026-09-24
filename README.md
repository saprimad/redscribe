# RedScribe

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22941754.svg)](https://doi.org/10.5281/zenodo.22941754)

RedScribe is a Windows and macOS desktop application for transcribing research interviews and other recorded speech. Version 2.0 uses Faster-Whisper for transcription and can optionally use pyannote.audio to distinguish between speakers. It exports an Excel workbook and an editable Word report for researcher-led verification and qualitative analysis.

## Current source version

**Version 2.0.0**

No tagged GitHub Release has been published yet. The repository includes the changes listed under **Unreleased** in [CHANGELOG.md](CHANGELOG.md); the version number shown in the application has not been changed for those additions. A [RedScribe Zenodo record](https://doi.org/10.5281/zenodo.22941754) is available separately; this does not imply that a tagged GitHub Release has been archived.

The primary application is [`redscribe_gpu.py`](redscribe_gpu.py). The earlier Qwen/Ollama prototype, [`whisper_gui.py`](whisper_gui.py), is deprecated and retained only for historical reference. It is not supported or recommended for research use.

## Features

- Selectable Faster-Whisper models: `large-v3` (default), `turbo`, `medium`, `small` and `base`
- NVIDIA CUDA first, with automatic CPU fallback
- Spoken-language choice: Auto detect (default), Bahasa Melayu or English; transcription does not translate the recording
- Optional speaker diarisation using `pyannote/speaker-diarization-community-1`
- Optional expected-speaker count
- Local **Check Token** button to show whether a Hugging Face token is available, without displaying or validating it against the model
- Live timestamped transcript, detected-language notice, progress and estimated remaining time
- Speaker assignment and estimated sentence timestamps derived from Whisper segments
- Excel export with study metadata, an utterance-level verification worksheet, speaker counts, approximate speech/silence durations, five-minute utterance density and token frequency
- Editable Microsoft Word (`.docx`) report with the early report tables and charts, top tokens, and adjacent utterances grouped by speaker
- Numbered Excel/Word filenames on repeated runs to preserve previous reports
- Bottom controls that remain visible as the live transcript area resizes
- Red Stop button to cancel a run before report export begins

RedScribe produces an automated draft. Sentence timestamps are estimates; speech/silence figures use Whisper segment spans, and token counts are simple text frequencies rather than validated linguistic analysis. Researchers remain responsible for checking the transcript, speaker labels and analytical outputs against the original recording.

## Workflow

Audio or video → Faster-Whisper transcription → optional speaker diarisation → Excel and Word export → researcher verification

## Requirements

- Windows 10 or 11, or macOS
- Python 3.10 or 3.11 recommended
- FFmpeg available in `PATH`
- Windows: NVIDIA GPU recommended; CPU mode is supported but slower
- macOS: Apple Silicon is supported; the current version uses optimised CPU processing rather than NVIDIA CUDA
- A Hugging Face account and accepted model conditions when speaker diarisation is enabled

## Installation

### Windows 10 or 11

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

### macOS

RedScribe has been tested successfully on a Mac mini with an Apple M4 chip and 24 GB of unified memory. The current version runs transcription and speaker diarisation through CPU processing on Mac; NVIDIA CUDA instructions do not apply. Modern Apple Silicon can nevertheless provide strong local transcription performance.

1. Install [Homebrew](https://brew.sh/) if it is not already installed.

2. Install Git, Python 3.11 with Tkinter support, and FFmpeg:

   ```bash
   brew install git python@3.11 python-tk@3.11 ffmpeg
   ```

3. Clone the repository and enter its folder:

   ```bash
   git clone https://github.com/saprimad/redscribe.git
   cd redscribe
   ```

4. Create and activate a virtual environment:

   ```bash
   "$(brew --prefix python@3.11)/bin/python3.11" -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   ```

5. Install RedScribe dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Verify the installation and start RedScribe:

   ```bash
   ffmpeg -version
   python redscribe_gpu.py
   ```

The first launch may take longer while the selected Whisper model is downloaded. On a modern Apple Silicon Mac, use `large-v3` when prioritising transcription accuracy or `turbo` when prioritising faster processing. The `small` and `base` models remain useful for older Macs or systems with limited memory. If macOS asks for permission to access a folder containing the selected recording, allow access so RedScribe can read the file and save its reports.

## Speaker diarisation setup

1. Open the model page for [`pyannote/speaker-diarization-community-1`](https://huggingface.co/pyannote/speaker-diarization-community-1) and accept any required conditions.
2. Create a Hugging Face token with read access.
3. With RedScribe's virtual environment activated, log in once on this computer:

   ```powershell
   python -c "from huggingface_hub import interpreter_login; interpreter_login()"
   ```

   Enter the token when prompted (the input is hidden). When asked **Add token as git credential?**, answer `n`; Git access is not needed for diarisation.
4. Verify the login without displaying the token:

   ```powershell
   python -c "from huggingface_hub import get_token; print('Token saved' if get_token() else 'No token found')"
   ```

   If it prints `Token saved`, leave RedScribe's Hugging Face Token field blank. The app uses the locally cached login. Log in using the same Python environment that runs RedScribe.

In RedScribe, click **Check Token** beside the masked field to see whether a token is entered for this app session, available in the environment, or saved through Hugging Face login. This local check does not display the token, contact Hugging Face or test model access; if diarisation fails, confirm the token's read access and acceptance of the model conditions.

Alternatively, paste a token into the masked field for the current app session. A temporary `HF_TOKEN` environment variable also works for that terminal session, but must be set again in a new terminal.

RedScribe does not write the token to a configuration file. The Hugging Face login stores it locally on the computer. Never commit a token, participant recording or identifiable transcript to GitHub.

## Running RedScribe

```text
python redscribe_gpu.py
```

Select an audio or video file, complete the optional study metadata, choose whether to enable speaker diarisation, and start transcription. **Transcription Language** defaults to Auto detect; select Bahasa Melayu or English when detection is inaccurate. The app uses Whisper's transcription task, not translation. Mixed-language speech still needs checking against the recording. Matching `.xlsx` and `.docx` files are written to `output/YYYY-MM/`. Repeated runs create a numbered file pair rather than overwriting an earlier result. The Word file begins with the Excel `Early_Report` information and charts, followed by a transcript that combines adjacent utterances from the same speaker into one editable paragraph, labelled with the first start and last end time. The Excel workbook retains each utterance separately, along with verification columns. If a run stops with an unexpected Python error, details are written locally to `output/redscribe_error.log`; review the log before sharing it because paths may identify research files.

With Auto detect, the detected language appears in the live transcript area before the first segment. If it is wrong (for example, Welsh for a Malay recording), click **Stop**, choose Bahasa Melayu or English under Transcription Language, and start again. Stop waits for the current model-loading, diarisation or transcription step to finish; it cannot interrupt a library call instantly. A stopped run does not save a partial Word or Excel report. Once report saving begins, Stop is disabled until both exports finish. Previously completed reports are preserved.

**Whisper Model** defaults to `large-v3`. Use `small` or `base` for a CPU-only laptop, or try `turbo` for faster processing on a capable GPU; check each transcript against the audio. The selection is remembered on that computer in `%APPDATA%\RedScribe\settings.json` (or `~/.config/RedScribe/settings.json` if `APPDATA` is unavailable). This settings file contains only the model name, never a Hugging Face token or study details. The selected model and actual CPU/GPU mode are recorded in both outputs. The first use of another model downloads it from the Hugging Face Hub and needs an internet connection.

When transcription runs on CPU, RedScribe uses at most 70% of the detected logical processor count as Faster-Whisper worker threads, with a budget at least two below the total when available. This is a thread budget, **not a guaranteed 70% CPU-utilisation limit**; diarisation, other libraries and other applications have separate CPU activity. It does not prevent memory exhaustion. On a laptop, choose `small` or `base` if `large-v3` is slow or memory is limited.

Repeated runs with the same study details receive numbered filenames (for example, `_2.xlsx` and `_2.docx`) so an earlier report is preserved even while it is open.

Supported input formats shown in the interface are MP3, WAV, M4A and MP4. FFmpeg may support additional formats, but they are not currently exposed by the file picker.

## Processing and privacy

Audio transcription and diarisation run on the user's computer. Internet access may still be required initially to download model files and authenticate with Hugging Face. After the required models are cached, processing can generally occur locally.

The repository's `.gitignore` excludes common audio, video, spreadsheet, transcript, data, credential and output files. This is a safeguard, not a substitute for checking every commit before pushing research material.

## GPU acceleration and CPU fallback

On Windows, RedScribe attempts to load Whisper with CUDA and `float16`. If CUDA is unavailable or loading fails, it falls back to CPU with `int8`. On macOS, the current version uses CPU mode with `int8`. Speaker diarisation is sent to CUDA only when CUDA is available; otherwise it runs on CPU. A diarisation failure does not stop transcription.

## Troubleshooting

- **`ffmpeg` not found:** install FFmpeg, reopen the terminal and confirm `ffmpeg -version` works.
- **Tkinter is missing on macOS:** run `brew install python-tk@3.11`, recreate the virtual environment with the Homebrew Python 3.11 command above, and reinstall the dependencies.
- **Hugging Face access error:** accept the model conditions and check that the token has read access.
- **CUDA or DLL error:** confirm that the NVIDIA driver, PyTorch build and CUDA runtime are compatible.
- **Diarisation fails but transcription continues:** review the warning shown in the application and inspect the generated Excel metadata.
- **Slow processing:** on Windows with an NVIDIA GPU, confirm that the status bar reports `CUDA`. On Apple Silicon, try `turbo` for faster processing; reserve `small` or `base` for older Macs or systems with limited memory. CPU transcription with `large-v3` may be slower on older hardware.

## Repository files

- `redscribe_gpu.py` — current RedScribe v2 application
- `whisper_gui.py` — deprecated Qwen/Ollama prototype retained for historical reference
- `requirements.txt` — Python dependencies
- `CITATION.cff` — software citation metadata
- `CHANGELOG.md` — release history
- `LICENSE` — PolyForm Noncommercial 1.0.0 terms for the original RedScribe code and documentation

## Citation

If RedScribe supports a study, cite the software using its Zenodo DOI. The record is separate from any future tagged GitHub Release.

### APA

Tumiran, M. S., Abd Wahab, M. S., Jamal, J. A., & Othman, N. (2026). *RedScribe: Research Speech Transcription System* (Version 2.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.22941754

### IEEE

M. S. Tumiran, M. S. Abd Wahab, J. A. Jamal, and N. Othman, “RedScribe: Research Speech Transcription System,” ver. 2.0.0, Zenodo, 2026, doi: 10.5281/zenodo.22941754. [Online]. Available: https://doi.org/10.5281/zenodo.22941754

Machine-readable citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## Authors

Mad Sapri bin Tumiran; Mohd Shahezwan bin Abd Wahab; Janattul Ain binti Jamal; Nursyuhadah binti Othman<br>
Malaysia copyright notification: CRDV2026W02110<br>
Faculty of Pharmacy, Universiti Teknologi MARA (UiTM), Malaysia<br>
Support: saprimad@moh.gov.my

## Licence

RedScribe's original code and documentation are available under the [PolyForm Noncommercial License 1.0.0](LICENSE). The licence permits noncommercial use, modification and redistribution under its terms. It also expressly permits use by charitable organisations, educational institutions, public research, public safety or health, environmental protection and government organisations, regardless of their funding source or obligations arising from funding. A grant alone does not trigger a fee for those organisations.

For a purpose outside the licence's permissions, contact **saprimad@moh.gov.my** to discuss a separate written paid licence before use. Sending an enquiry does not itself grant permission. PolyForm Noncommercial is a source-available licence, not an OSI-approved open-source licence. Third-party dependencies and models retain their own licence terms.
