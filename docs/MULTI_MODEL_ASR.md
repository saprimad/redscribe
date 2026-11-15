# Local ASR model options

See the [pre-merge trial record](PRE_MERGE_TEST_LOG.md) for user-reported Windows results, fixes and outstanding checks.

The desktop **ASR model** dropdown adds five optional backends alongside existing Faster-Whisper models. Models download only when selected for a run; they are cached by Hugging Face. Inference is local. The app remembers the selection using its existing settings file; old settings remain compatible.

## Seven research candidates

| Desktop choice | Checkpoint | Desktop runtime |
| --- | --- | --- |
| OpenAI Whisper Large-v3 | `openai/whisper-large-v3` (converted Faster-Whisper weights) | Existing Faster-Whisper |
| OpenAI Whisper Large-v3 Turbo | `openai/whisper-large-v3-turbo` (converted Faster-Whisper weights) | Existing Faster-Whisper |
| Mesolitica Malaysian Whisper Large-v3 Turbo v3 | `mesolitica/Malaysian-whisper-large-v3-turbo-v3` | Transformers Whisper, standard `transcribe` task |
| Mesolitica Wav2Vec2 XLS-R 300M Mixed | `mesolitica/wav2vec2-xls-r-300m-mixed` | Transformers CTC, greedy decoding without external LM |
| Meta MMS-1B-All — Malay | `facebook/mms-1b-all` | Transformers CTC, `zlm` Malay adapter |
| Qwen3-ASR 1.7B | `Qwen/Qwen3-ASR-1.7B` | Official `qwen-asr` Transformers backend |
| BuzzASR Malay — Whisper Large-v3 | `BuzzASR/malay` | Transformers Whisper |

The model menu uses full English names and places those seven study candidates first. Four supplementary choices follow:

- OpenAI Whisper Medium (Legacy)
- OpenAI Whisper Small (Legacy)
- OpenAI Whisper Base (Legacy)
- OpenAI Whisper Tiny (Legacy)

Here, Legacy means outside the seven-model study shortlist, not an upstream deprecation claim. Tiny uses the existing Faster-Whisper runtime, caching, CPU/CUDA policy and exports. The native selection menu sizes to full labels and the selected full name is repeated in the wrapped description below it. Status messages and report model names use the full label too. Stable internal keys, saved preferences and existing output folder names remain unchanged; Tiny adds `whisper_tiny` as its output folder.

 This table names the model families; the two existing Faster-Whisper choices use converted weights rather than the Transformers runtime specified in the study plan.

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

## Local diarisation options

**Settings → Diarisation model** offers:

| Choice | Checkpoint | Role |
| --- | --- | --- |
| Community-1 (Recommended) | `pyannote/speaker-diarization-community-1` | Default |
| 3.1 (Legacy / comparison) | `pyannote/speaker-diarization-3.1` | Optional older comparison pipeline |

Diarisation stays on by default. The selected checkpoint is captured at Start and recorded in Word/Excel. Selection persists independently from the ASR dropdown, and existing settings default to Community-1. Both use the installed local `pyannote.audio` runtime and existing CPU/CUDA handling; no WSL/NeMo engine is involved.

Both accept automatic/expected speaker counts and use the existing token selection. For 3.1, accept both its model conditions and those for `pyannote/segmentation-3.0` using the same Hugging Face account. Selecting a model only changes the preference; first-use downloads happen during the run. Loading/progress notices identify the requested checkpoint. No automatic substitution with the other model occurs if loading fails; the existing policy continues transcription without speaker labels and records the diarisation failure.

The adapter accepts both legacy Annotation output and Community-1 DiarizeOutput. **Actual 3.1 loading/inference and compatibility with the installed pyannote release remain unvalidated.** The legacy model card specifies pyannote.audio >=3.1; Community-1 uses a newer runtime, so do not downgrade a working environment simply to try the legacy option. Access approval alone does not guarantee compatible dependencies.

Primary reference: [3.1 model card and requirements](https://huggingface.co/pyannote/speaker-diarization-3.1).

## Before starting and output organisation

The text below **ASR model** changes with the selected model: language behaviour, CUDA FP16/CPU fallback policy and timestamp method are visible before starting. Selecting a model does not download its weights.

On Start, a background requirements check verifies the optional runtime classes and CUDA availability before any model download, diarisation or report-folder creation. A failed check shows an actionable message and installation command in the app. This is an availability check, not a guarantee that inference fits VRAM or that model access has been granted. Existing Faster-Whisper CPU support remains available.

Outputs are grouped under `output/<YYYY-MM>/<model>/`, for example `output/2026-11/mesolitica_whisper_turbo_v3/`. Word and Excel remain together and both filenames include the stable model name, so copied files remain identifiable. Existing output folders are untouched; repeated runs keep the existing collision-safe numbering. **Open output folder** opens the current model's folder. A preflight failure does not replace the last successful output-folder location.

## Diarisation dependency checks and automatic downloads

With diarisation enabled, the worker checks that pyannote's Pipeline class can be imported before downloading ASR weights or processing audio. Missing pyannote and broken subdependencies are diagnosed separately. The `_ExtendedAttributes` OpenTelemetry import failure produces an alignment/upgrade command, `pip check`, the active interpreter path and a restart instruction; dependency repair is separate from model downloads. No package installation is performed by the app.

Once the runtime imports successfully, `Pipeline.from_pretrained` automatically fetches missing selected-model weights/dependencies using the existing Hugging Face token and cache. Live Transcript logs **Checking cached diarisation files / automatically downloading missing model weights** before loading and **Diarisation model ready** only after successful loading. Complete cached files are reused by pyannote/Hugging Face. Model access still requires accepted conditions; no fake download percentage is displayed.

A broken runtime now stops the run before processing so an enabled diarisation request is not lost because of an import failure. Model access/inference failures after preparation retain the existing explicit continuation-without-speaker-labels policy and failure metadata. See [dependency repair commands](../README.md#diarisation-dependency-repair). The user subsequently supplied `pyannote import OK` and speaker-labelled output after environment repair; exact dependency versions and full runtime compatibility remain unverified. See the pre-merge trial record.

Fixed-language extra decoders report **Configured decoder language**, rather than claiming their configured Malay decoder was automatically detected.

## MMS Malay adapter correction

The MMS checkpoint's Malay adapter is **`zlm`**. An earlier integration incorrectly requested `zsm`, which caused `adapter.zsm.bin` not found after the main 3.86 GB checkpoint downloaded. This is a configuration error, not evidence of a failed main-model download or insufficient GPU memory.

MMS now uses `zlm` consistently for the processor vocabulary, model `target_lang` and adapter loading. It verifies that the downloaded tokenizer vocabulary supports `zlm` before loading the large weights, never substitutes another language and avoids forcing a duplicate adapter reload when Transformers already loaded it during `from_pretrained`. Existing checkpoint cache/output-folder names are unchanged, so previously downloaded valid weights can be reused. Source: [MMS supported language list](https://huggingface.co/facebook/mms-1b-all).

Mocked regression checks cover target-language forwarding and early rejection of an unsupported vocabulary. The user subsequently supplied a successful `zlm` adapter download, model-ready confirmation and generated text, but reported poor Malay transcription with diarisation both on and off. Inference output is therefore observed; accuracy and equivalence to upstream inference remain unvalidated.

## Model-loading notifications

Live Transcript logs model preparation, explains first-use downloads and confirms readiness. A highlighted activity banner and bottom status line animate with elapsed time throughout preparation. Faster-Whisper distinguishes cached weights, actual downloads and loading into memory.

For supported Hugging Face HTTP/Xet transfers, the app now mirrors **real file-download byte progress** in Live Transcript, for example:

```text
Downloading model-00001-of-00002.safetensors: 24.0% | 1.01 GB / 4.22 GB (file progress)
Downloading model-00002-of-00002.safetensors: 50.0% | 239.0 MB / 478.0 MB (file progress)
```

Each transfer has a separate line that is replaced in place rather than appended on every update. Parallel Qwen shards remain separate. Updates are throttled to two per second per file, with initial/final actual byte counts included. Cached files create no fake transfer events; resumed downloads retain the starting byte count. Bytes received for a file are not proof the model is loaded or validated. Model-ready confirmation still comes after successful loading.

These are **per-file percentages**, not the complete model download or transcription percentage. An unknown total shows bytes received and "total size unknown". Interrupted transfers retain their actual percentage; completion is never forced to 100%. The bottom transcription progress bar stays separate. The elapsed banner shows the most recently updated file while both file lines remain visible.

The observer uses the Hub file-download progress context for HTTP/Xet, including the Hub 0.36-style runtime used with these optional adapters. It delegates transfer/cache/resume work to the installed Hub and restores the temporary hook after preparation, including failures. It does not scrape terminal text or redirect stdout/stderr; terminal diagnostics remain available. If the installed Hub does not expose this context or a backend uses another transfer path, the existing elapsed/stage notices remain available without a numerical percentage. Download descriptions are reduced to safe filenames without signed URL queries.

Coverage includes ASR preparation and pyannote model preparation; no additional model files or Python packages are downloaded merely to observe progress. No blocking progress popup is used. UI updates run on Tk's main thread. Actual Windows network transfers and live Text rendering remain to be trialled; mocked HTTP/Xet/concurrent transfer checks pass.

An already running app cannot acquire the new observer dynamically: finish/stop the current run, update the trial branch and relaunch for the next run.

## Precision, language and memory

- Extra models require CUDA and FP16, batch size one. They never silently retry in CPU, FP32, BF16 or quantised mode. Loading/inference errors fail the run rather than exporting incomplete reports.
- Existing Faster-Whisper options retain their CUDA FP16 → CPU INT8 fallback for desktop compatibility. **This desktop path is not the strict study benchmark runner.**
- Extra ASR weights load after pyannote has finished and released its pipeline, reducing simultaneous GPU allocations. There is no guarantee every model fits all audio workloads within 12 GB VRAM.
- MMS uses the Malay `zlm` adapter. XLS-R uses its fixed mixed-language decoder. BuzzASR is Malay-specific. For these options, `Auto detect` means the configured Malay/mixed decoder; it does not perform language detection. Explicit English selection is rejected.
- Qwen and Mesolitica Whisper allow Auto detect, Bahasa Melayu and English. No forced-aligner model is downloaded for Qwen. Mesolitica's optional `transcribeprecise` task is not used, and no global tokenizer task list is patched.
- Stop is checked before/after model loading and each audio chunk. A running download or GPU inference step must return before cancellation completes.

## Timing and outputs

Extra models process the entire audio in contiguous chunks of at most 30 seconds. With diarisation enabled (still the default), chunk boundaries also split at speaker-turn boundaries. Gaps are retained; overlapping turns do not cause repeated audio. Very short turns and overlapping speakers may reduce transcription quality.

These are **audio chunk boundaries, not model-predicted transcript timestamps or word alignment**. Sentence positions are distributed estimates. Word/Excel metadata and the Live Transcript display explicitly identify the timing method. Chunk spans are not measured speech activity: speech/silence durations show "Not measured (audio chunks)", and the speech/silence chart is omitted for these adapters.

Existing Word/Excel exports and shared speaker colours remain in use. Metadata records the selected checkpoint, available model revision, actual device/precision and timing method. Automatic or selected language can differ from chunk to chunk under automatic detection; no single detected language is claimed for those extra-model runs.

## Completion and another run

When transcript generation ends, the app logs that report preparation has started, shows elapsed activity for Excel and Word saving, logs each successfully saved path and displays final memory cleanup. Start remains disabled until cleanup finishes and the run returns to idle. The completion/error dialog appears after that reset. A cleanup exception is shown as a warning and does not strand the controls. These messages identify the active stage; they do not guarantee that an underlying export or GPU call cannot block. The reported Legacy next-run stall still needs a Windows re-test after this ordering fix.

## Local performance records

Every run writes a uniquely named `.json` record and readable `.log` under `output/performance/`, and prints a performance summary plus log location in Live Transcript. This includes failed/cancelled runs and partial export success. If the log cannot be saved, a warning appears and normal completion/control reset still proceeds.

Records include UTC start time, outcome, selected model/checkpoint, available revision, actual device/precision once known, requested language/diarisation, audio duration once ASR completes, and wall-clock timings for requirements checks, ASR model preparation, diarisation, ASR processing, Excel, Word and final cleanup. They do not serialise GUI inputs, Hugging Face tokens, study/researcher names, audio filenames or transcript text.

Model preparation combines cache checks, downloads if necessary and loading; **download-only time is not measured separately**. Diarisation includes its own loading/download and cleanup. For lazy ASR backends, preparation happens inside the ASR pipeline interval: overlap is subtracted for the reported ASR processing time. Raw stage durations can overlap and must not be summed.

For completed ASR with a positive audio duration and processing time, `RTF = ASR processing seconds / audio seconds`, and speed is its reciprocal. Failed/cancelled ASR has no speed claim. A later export failure may still have completed ASR timings. ASR processing includes audio decoding, VAD where supported, segment iteration, UI dispatch and backend cleanup; it is not GPU kernel-only timing. Total time runs from worker start through final cleanup, excluding performance-file writing and completion-dialog time. No RAM/VRAM sampling or accuracy scoring is added. Existing Word/Excel processing-minutes fields retain their prior scope; use the explicit performance record for stage comparisons.

These are desktop diagnostics. First-run downloads, CPU fallback, caching, warm-up, different diarisation settings and background workload can affect comparisons. They are not a substitute for the controlled 25-recording benchmark protocol.

## Validation status and research use

Automated tests cover chunk coverage, turn boundaries, language guards, lazy loading, FP16 and MMS adapter arguments, Qwen invocation, cancellation/failure cleanup, and existing export/token/UI logic without downloading model weights. **No independent GPU inference was run in the development workspace. User-supplied Windows trials include completed Whisper output and MMS output after the adapter correction, with poor MMS quality reported; they do not establish full model parity or accuracy.** This branch is for local trial before merging.

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
