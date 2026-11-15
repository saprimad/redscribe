# NVIDIA Sortformer diarisation option

**Settings → Diarisation model** offers two independent choices:

| Choice | Checkpoint | Speaker count | Runtime |
| --- | --- | --- | --- |
| pyannote Community-1 (default) | `pyannote/speaker-diarization-community-1` | Automatic or expected count | Existing pyannote |
| NVIDIA Sortformer | `nvidia/diar_streaming_sortformer_4spk-v2.1` | Automatic, up to four speakers | Optional NeMo, CUDA required by this adapter |

Diarisation remains on by default. Backend selection is saved independently of ASR selection. Seven ASR research candidates remain separate choices; Sortformer supplies speaker turns, not transcript text.

## Install and try

The optional adapter follows NVIDIA's NeMo API. Use a compatible **Linux/CUDA environment**, including a suitably configured WSL2 environment where available, and the RedScribe feature branch. Native Windows installation and inference are **not validated**. Installing NeMo may change PyTorch/Transformers and other dependencies, so use an environment that can accommodate both the chosen ASR backend and NeMo. A separate trial environment avoids disturbing a working Windows installation.

With CUDA PyTorch and the desktop dependencies already installed in that environment:

```bash
python -m pip install -r requirements-sortformer.txt
python -m pip check
python redscribe_gpu.py
```

A Linux desktop or WSLg session with Tk is needed to display the app. If NeMo dependencies fail, use NVIDIA's installation guidance below; no automatic installation or system changes are made by RedScribe. Selecting pyannote does not import or require NeMo.

Choose NVIDIA Sortformer in Settings. Try a short recording with two speakers first. The expected-speaker entry is disabled because this integration does not force a speaker count for Sortformer. Use pyannote for recordings with more than four speakers. Both diarisation engines produce automated labels requiring researcher verification.

## Downloads, credentials and progress

Before processing, RedScribe checks the selected Sortformer runtime and CUDA availability without downloading weights. Missing runtime produces an actionable installation message before ASR download or diarisation starts.

At first use, `hf_hub_download` obtains `diar_streaming_sortformer_4spk-v2.1.nemo` from the NVIDIA checkpoint. Cached files are reused. RedScribe passes the resolved session/keyring/environment/Hugging Face credential when available; it does not modify the process environment or write credentials to the settings JSON. Access conditions depend on the checkpoint; a token is not assumed to grant access automatically.

Live Transcript shows cached-file/download preparation, CUDA loading, audio preparation, speaker detection and timeline preparation. The animated elapsed banner remains active during long model calls. No download percentage or inference percentage is invented. Stop is checked between phases; a current download or NeMo inference call must finish before cancellation is observed.

## Audio and output behaviour

The adapter decodes the selected recording to mono 16 kHz audio and passes **one complete recording** to NeMo. Sortformer's internal streaming configuration uses chunk length 340, right context 40, FIFO 40, speaker-cache update period 300 and speaker-cache length 188, following the model-card configuration. It does not reset speaker IDs by running independent audio chunks.

NeMo text segments (`start end speaker_index`) become the existing `{start, end, speaker}` structure with `SPEAKER_00`–`SPEAKER_03` labels. Overlap is retained; assignment to ASR segments still uses the existing overlap-based method. Speaker colours and Word/Excel formats stay shared. The selected diarisation checkpoint is recorded in both exports. IDs identify automated within-recording labels, not named people or persistent identities across recordings.

This adapter explicitly uses **CUDA FP32 for diarisation**, separate from the selected ASR model's FP16 setting. No claim is made that Sortformer FP16 has been validated. A Sortformer failure is logged and the app follows its existing policy of continuing transcription without speaker labels; it never silently swaps to pyannote. Both output reports record diarisation failure status. GPU references are released on success, failure and phase-boundary cancellation.

## Validation status

Unit tests cover API arguments, complete-recording input, token forwarding without notification disclosure, expected-count behaviour, speaker parsing, malformed output rejection, CUDA/runtime checks, cleanup and independent model preferences. Tests use mocked NeMo/CUDA. Actual NeMo installation, model download, real audio inference, native Windows compatibility, VRAM fit and Kelantan speaker-diarisation accuracy remain unvalidated. This stays on the trial branch before merge.

The publication ASR comparison still uses diarisation off; comparing diarisation accuracy would require its own reference speaker annotations and evaluation design.

## Primary references

- [NVIDIA Sortformer v2.1 model card and quickstart](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2.1)
- [Checkpoint files](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2.1/tree/main)
- [NVIDIA NeMo speaker diarisation API](https://docs.nvidia.com/nemo/speech/nightly/asr/speaker_diarization/api.html)
- [NVIDIA NeMo diarisation examples](https://github.com/NVIDIA-NeMo/Speech/blob/main/examples/speaker_tasks/diarization/README.md)

The checkpoint retains its NVIDIA Open Model Licence; this integration does not relicense it.
