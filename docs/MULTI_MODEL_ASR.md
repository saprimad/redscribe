# Local ASR model options

The desktop **ASR model** dropdown adds five optional backends alongside existing Faster-Whisper models. Models download only when selected for a run; they are cached by Hugging Face. Inference is local. The app remembers the selection using its existing settings file; old settings remain compatible.

## Seven research candidates

| Desktop choice | Checkpoint | Desktop runtime |
| --- | --- | --- |
| `large-v3` | `openai/whisper-large-v3` (converted Faster-Whisper weights) | Existing Faster-Whisper |
| `turbo` | `openai/whisper-large-v3-turbo` (converted Faster-Whisper weights) | Existing Faster-Whisper |
| `Mesolitica Whisper v3` | `mesolitica/Malaysian-whisper-large-v3-turbo-v3` | Transformers Whisper, standard `transcribe` task |
| `Mesolitica XLS-R 300M` | `mesolitica/wav2vec2-xls-r-300m-mixed` | Transformers CTC, greedy decoding without external LM |
| `Meta MMS 1B (Malay)` | `facebook/mms-1b-all` | Transformers CTC, `zsm` Malay adapter |
| `Qwen3-ASR 1.7B` | `Qwen/Qwen3-ASR-1.7B` | Official `qwen-asr` Transformers backend |
| `BuzzASR Malay` | `BuzzASR/malay` | Transformers Whisper |

The original `medium`, `small` and `base` choices remain available. This table names the model families; the two existing Faster-Whisper choices use converted weights rather than the Transformers runtime specified in the study plan.

## Installation and trial

Use the existing RedScribe virtual environment with working CUDA PyTorch. First fetch the feature branch (do not overwrite uncommitted local work):

```powershell
git fetch origin
git switch feat/multi-model-local-asr
```

Install the existing app dependencies if this is a new environment:

```powershell
python -m pip install -r requirements.txt
```

For Mesolitica, MMS and BuzzASR:

```powershell
python -m pip install -r requirements-models.txt
```

To enable **all** options including Qwen, install this file instead; it includes the shared model dependencies:

```powershell
python -m pip install -r requirements-qwen.txt
python -m pip check
python redscribe_gpu.py
```

Qwen's package currently pins Transformers 4.57.6 and Accelerate 1.12.0. Dependency resolution and Windows-specific dependencies need checking on the trial machine; no vLLM or FlashAttention installation is requested. A missing optional runtime produces an install instruction when starting the selected model. Existing Faster-Whisper use does not import the optional runtimes.

## Diarisation model options

Settings now offers **pyannote Community-1** (default) and **NVIDIA Sortformer** independently of the ASR dropdown. Diarisation remains on by default. See [Sortformer setup](SORTFORMER.md) for its separate optional runtime, four-speaker limit, FP32 diarisation mode and Windows trial limitations. This does not add an eighth ASR model.

## Before starting and output organisation

The text below **ASR model** changes with the selected model: language behaviour, CUDA FP16/CPU fallback policy and timestamp method are visible before starting. Selecting a model does not download its weights.

On Start, a background requirements check verifies the optional runtime classes and CUDA availability before any model download, diarisation or report-folder creation. A failed check shows an actionable message and installation command in the app. This is an availability check, not a guarantee that inference fits VRAM or that model access has been granted. Existing Faster-Whisper CPU support remains available.

Outputs are grouped under `output/<YYYY-MM>/<model>/`, for example `output/2026-11/mesolitica_whisper_turbo_v3/`. Word and Excel remain together and both filenames include the stable model name, so copied files remain identifiable. Existing output folders are untouched; repeated runs keep the existing collision-safe numbering. **Open output folder** opens the current model's folder. A preflight failure does not replace the last successful output-folder location.

## Model-loading notifications

Live Transcript logs model preparation, explains the first-use download, and confirms when the model is ready. A highlighted activity banner and bottom status line animate with elapsed time throughout preparation; the UI remains responsive. Faster-Whisper distinguishes cached weights, actual downloads and loading into memory. Extra Transformers/Qwen backends report checking cached files / automatically downloading missing files because their internal loaders do not expose a reliable unified transfer percentage.

No fake percentage is shown for unknown download totals, and preparation time is separate from transcription progress. Ready is only announced after weights load successfully; an interrupted/failed preparation does not announce success. Existing diarisation activity notices remain in use. Notifications appear inside the app without a blocking pop-up.

## Precision, language and memory

- Extra models require CUDA and FP16, batch size one. They never silently retry in CPU, FP32, BF16 or quantised mode. Loading/inference errors fail the run rather than exporting incomplete reports.
- Existing Faster-Whisper options retain their CUDA FP16 → CPU INT8 fallback for desktop compatibility. **This desktop path is not the strict study benchmark runner.**
- Extra ASR weights load after pyannote has finished and released its pipeline, reducing simultaneous GPU allocations. There is no guarantee every model fits all audio workloads within 12 GB VRAM.
- MMS uses the Malay `zsm` adapter. XLS-R uses its fixed mixed-language decoder. BuzzASR is Malay-specific. For these options, `Auto detect` means the configured Malay/mixed decoder; it does not perform language detection. Explicit English selection is rejected.
- Qwen and Mesolitica Whisper allow Auto detect, Bahasa Melayu and English. No forced-aligner model is downloaded for Qwen. Mesolitica's optional `transcribeprecise` task is not used, and no global tokenizer task list is patched.
- Stop is checked before/after model loading and each audio chunk. A running download or GPU inference step must return before cancellation completes.

## Timing and outputs

Extra models process the entire audio in contiguous chunks of at most 30 seconds. With diarisation enabled (still the default), chunk boundaries also split at speaker-turn boundaries. Gaps are retained; overlapping turns do not cause repeated audio. Very short turns and overlapping speakers may reduce transcription quality.

These are **audio chunk boundaries, not model-predicted transcript timestamps or word alignment**. Sentence positions are distributed estimates. Word/Excel metadata and the Live Transcript display explicitly identify the timing method. Chunk spans are not measured speech activity: speech/silence durations show "Not measured (audio chunks)", and the speech/silence chart is omitted for these adapters.

Existing Word/Excel exports and shared speaker colours remain in use. Metadata records the selected checkpoint, available model revision, actual device/precision and timing method. Automatic or selected language can differ from chunk to chunk under automatic detection; no single detected language is claimed for those extra-model runs.

## Validation status and research use

Automated tests cover chunk coverage, turn boundaries, language guards, lazy loading, FP16 and MMS adapter arguments, Qwen invocation, cancellation/failure cleanup, and existing export/token/UI logic without downloading model weights. **Real model inference and Windows CUDA FP16 smoke tests have not yet run.** This branch is for local trial before merging.

Try a short non-sensitive Malay clip on each model, confirm both exports and the checkpoint metadata, then test Stop and a longer recording. Record failures instead of silently changing precision. No claim is made that these models have been ranked or validated on Kelantan dialect.

The study plan remains separate: 25 verified reference transcripts, fixed audio preprocessing and chunk boundaries, diarisation off, no timestamp scoring, and matched decoding/runtime settings for WER/CER comparison. Desktop diarisation-dependent chunks and existing Faster-Whisper fallback are not publication benchmark settings. No batch benchmark or WER/CER scorer is added by this change.

## Primary implementation references

- [Mesolitica Whisper model card](https://huggingface.co/mesolitica/Malaysian-whisper-large-v3-turbo-v3)
- [Mesolitica XLS-R model card](https://huggingface.co/mesolitica/wav2vec2-xls-r-300m-mixed)
- [MMS usage and language adapters](https://huggingface.co/facebook/mms-1b-all)
- [Qwen ASR model card and official API](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)
- [Qwen package dependency pins](https://github.com/QwenLM/Qwen3-ASR/blob/main/pyproject.toml)
- [BuzzASR Malay model card](https://huggingface.co/BuzzASR/malay)

Third-party checkpoints retain their own licences; MMS is CC-BY-NC-4.0. This feature does not relicense any checkpoint.
