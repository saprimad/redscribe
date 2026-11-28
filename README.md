# RedScribe

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22941754.svg)](https://doi.org/10.5281/zenodo.22941754)

RedScribe is a local desktop application for researchers working with recorded interviews. **Transcription** produces an editable Word transcript and an Excel workbook for checking the speech and speaker labels against the recording. **Benchmarking** compares selected automatic speech recognition (ASR) systems against a researcher-approved verbatim reference and reports recognition errors and processing time.

| To… | Start here |
| --- | --- |
| Install the desktop application | [Installation](#installation) |
| Transcribe an interview or run a benchmark | [Illustrated user guide](docs/user-guide/README.md) |
| Choose models and install optional adapters | [Model setup](docs/MULTI_MODEL_ASR.md) |
| Understand how outputs are generated and scored | [Scientific documentation](docs/scientific/README.md) |
| Assess the release candidate or prepare a study | [Readiness assessment](docs/scientific/RELEASE_READINESS.md) |

## Installation

These instructions use the development branch for v2.1.0. The [main branch](https://github.com/saprimad/redscribe/tree/main) contains the stable transcription application. For formal workstation acceptance use the [pinned Windows GPU procedure](docs/validation/WINDOWS_GPU_ACCEPTANCE.md).

### Windows

Install Git, Python 3.11 with Tkinter, and FFmpeg. In PowerShell, create a dedicated environment.

```powershell
git clone --branch redscribe-benchmark-timeline https://github.com/saprimad/redscribe.git
cd redscribe
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If FFmpeg is missing, install it with `winget install Gyan.FFmpeg`, reopen PowerShell and reactivate the environment. For NVIDIA acceleration, install a compatible PyTorch build in this environment before installing the application dependencies. [PyTorch installation selector](https://pytorch.org/get-started/locally/)

### macOS

The transcription application can use Faster-Whisper on CPU. The five optional ASR adapters require NVIDIA CUDA with FP16. With Homebrew installed, run the following in Terminal.

```bash
brew install git python@3.11 python-tk@3.11 ffmpeg
git clone --branch redscribe-benchmark-timeline https://github.com/saprimad/redscribe.git
cd redscribe
"$(brew --prefix python@3.11)/bin/python3.11" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### Install and launch

With the environment active, install the desktop dependencies and check FFmpeg.

```bash
python -m pip install -r requirements.txt
ffmpeg -version
```

For benchmarking, also run `python -m pip install -r requirements-benchmark.txt`. If using optional models, follow the [adapter installation instructions](docs/MULTI_MODEL_ASR.md). Model weights may download on first use. Start either mode from the same application.

```bash
python redscribe_gpu.py
```

## Validation and interpretation

A historical RTX 5070 run processed one full-length recording with seven models. The paired outputs provide an example of error counts and efficiency measurements for that recording. The current readiness assessment identifies the workstation checks and study approvals still required for a larger comparison. [Historical runtime record](docs/validation/P1_SEVEN_MODEL_GPU_VALIDATION_2026-11-26.md) · [Current validation and release gates](docs/scientific/RELEASE_READINESS.md)

## Citation

When citing the archived transcription software, use the recorded version 2.0.0 and DOI. For a study using the development branch, also identify the exact Git commit and effective model configurations. [Citation metadata](CITATION.cff) · [Zenodo record](https://doi.org/10.5281/zenodo.22941754) · [Change history](CHANGELOG.md)

## Authors

Mad Sapri bin Tumiran; Mohd Shahezwan bin Abd Wahab; Janattul Ain binti Jamal; Nursyuhadah binti Othman<br>
Malaysia copyright notification: CRDV2026W02110<br>
Faculty of Pharmacy, Universiti Teknologi MARA (UiTM), Malaysia<br>
Support: saprimad@moh.gov.my

## Licence

RedScribe's original code and documentation are available under the [PolyForm Noncommercial License 1.0.0](LICENSE). The licence permits noncommercial use, modification and redistribution under its terms. It also expressly permits use by charitable organisations, educational institutions, public research, public safety or health, environmental protection and government organisations, regardless of their funding source or obligations arising from funding. A grant alone does not trigger a fee for those organisations.

For a purpose outside the licence's permissions, contact **saprimad@moh.gov.my** to discuss a separate written paid licence before use. Sending an enquiry does not itself grant permission. PolyForm Noncommercial is a source-available licence, not an OSI-approved open-source licence. Third-party dependencies and models retain their own licence terms.
