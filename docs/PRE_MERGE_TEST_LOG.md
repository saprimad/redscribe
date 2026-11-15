# Pre-merge trial record

Recorded: 15 November 2026 (UTC). Branch: `feat/multi-model-local-asr`. Pull request: [#24](https://github.com/saprimad/redscribe/pull/24). Application baseline: `63244cf`.

This is a retrospective record of the user's Windows trials and supplied screenshots/terminal messages, not a controlled benchmark. Individual run dates, audio hashes, package inventories and model revisions were not captured. Statuses below describe only the evidence supplied. No private recordings or transcripts are added by this record. The branch remains for trial; this record does not approve or perform a merge.

## Trial environment

- Windows, VS Code terminal, Python 3.11.
- Reported interpreter: `C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe` (global installation, not a confirmed project virtual environment).
- Reported workstation: NVIDIA RTX 5070 12 GB, 64 GB RAM; CUDA FP16 shown by the application.
- Desktop diarisation is enabled by default. Trials also included manually disabling it.

## User trials, one by one

| Item | Supplied evidence / observed result | Status and follow-up |
| --- | --- | --- |
| OpenAI Whisper Large-v3 | Earlier screenshots show transcription running and a completed podcast run at 100%, CUDA float16, with speaker-coloured text. | Desktop completion observed. No WER/CER or measured runtime comparison recorded. |
| Layout and study details | User tried the redesigned UI, requested larger text and tighter spacing, and placed the compact Study details panel below Audio file. Later screenshot shows that arrangement. | Layout trial observed; all screen sizes have not been assessed. |
| Word and Excel outputs | Sample Word/Excel files were supplied during the trial sequence; shared speaker-colour export support exists in the branch. | Samples exist; no separate per-model export acceptance result was supplied for every new backend. |
| Optional model downloads | Terminal logs show model/config/tokenizer downloads and cache checks across the new options. | Downloads observed; a completed download alone is not a completed inference test. |
| Mesolitica Wav2Vec2 XLS-R 300M Mixed | Terminal excerpt includes tokenizer/config/preprocessor files and a 1.26 GB weight download. | Download evidence only; no distinct successful transcription result or accuracy score supplied. |
| Mesolitica Malaysian Whisper Large-v3 Turbo v3 | Shared terminal excerpt includes Whisper-family tokenizer and weight downloads, without an unambiguous checkpoint-to-result mapping. | Do not infer an individual inference pass from that excerpt. Dedicated run still to record. |
| Qwen3-ASR 1.7B | Terminal identifies `Qwen/Qwen3-ASR-1.7B`; two shards show partial download progress (4.22 GB and 478 MB totals). | Download started. Completion, inference and exports not confirmed. |
| BuzzASR Malay — Whisper Large-v3 | User reported a slow download; terminal shows about 8.22 MB of 3.09 GB at approximately 518 kB/s. | Slow transfer observed, not proof of a stalled transfer. Completion/inference not confirmed. |
| MMS initial preparation | Main weight download reached 3.86 GB, then model preparation ended without ready confirmation. Subsequent error identified missing `adapter.zsm.bin`. | Integration configuration defect identified and corrected; see MMS section. |
| MMS after correction | Live Transcript shows loading `zlm`, download of `adapter.zlm.safetensors` (9.0 MB, 100%), then Model ready and generated text. | Adapter preparation and inference observed. This does not establish accuracy or equivalence to upstream inference. |
| MMS on English audio | User reported very poor text while the log explicitly showed a configured Malay decoder. | Unsuitable language configuration for an English accuracy test. No English-performance conclusion recorded. |
| MMS on Malay audio | User reported poor transcription, including after disabling diarisation. | Quality concern remains open. No verified reference comparison, WER/CER or direct upstream parity test performed. |
| Pyannote / OpenTelemetry | Import failed with `_ExtendedAttributes` from `opentelemetry.util.types`; earlier UI incorrectly presented this as missing pyannote. | Branch now distinguishes broken subdependencies from a missing package and gives repair instructions. |
| Pyannote after environment repair | User's terminal ended with `pyannote import OK`, with TorchCodec DLL warnings. Later screenshots contain diarisation turns and speaker labels. | Import success and speaker-labelled application output observed. Exact dependency versions and diarisation accuracy not established. |
| TorchCodec / FFmpeg DLL warnings | Import output lists failed `libtorchcodec_core*.dll` loads but still reaches `pyannote import OK`. | Warning retained as environment evidence. Do not treat import success as a full codec test. Application has a waveform-input path. |
| Pyannote Community-1 | Requested checkpoint appears in loading logs; later speaker-labelled output was supplied. | Speaker output observed; no DER or independently verified speaker reference available. |
| Pyannote 3.1 | Added as a legacy/comparison setting. | No user-supplied loading/inference result on this installation. |
| Download percentages in Live Transcript | Terminal percentages prompted the request; branch now observes real per-file Hub download bytes with elapsed-time fallback. | Automated observer checks exist. No clear post-update Windows screenshot supplied to confirm every transfer path renders live percentages. |
| Medium / Small / Base / Tiny (Legacy) | Menu choices retained/added outside the seven-model study shortlist. | No individual current-branch run supplied for these choices. |

## Meta MMS correction and remaining limitation

Correct display name: **Meta MMS-1B-All — Malay**. Checkpoint: `facebook/mms-1b-all`. Malay adapter: **`zlm`**, not the previously configured `zsm`.

Commit `63244cf` already corrected this before this record was created. The production loader checks that the configured adapter exists in the checkpoint vocabulary, selects the same tokenizer language, passes `target_lang="zlm"` to the CTC model, loads that adapter and casts the model/adapter to CUDA FP16. It does not silently select another language. Existing regression tests check these loading arguments and rejection of an unsupported adapter.

The user's later log confirms that the 9 MB `zlm` adapter downloaded and MMS produced text. The reported poor Malay output remains unresolved. Short diarisation-driven chunks may affect output, but the user also reported poor output with diarisation disabled, so diarisation alone is not an established explanation. FP16 has not been established as the cause either.

At the user's request, the proposed extra FP32/FP16/upstream diagnostic script was cancelled and was not added. Current integration remains in place. MMS stays an experimental comparison candidate, not a validated accuracy baseline. A future same-audio reference comparison is needed before attributing poor performance solely to the model or solely to integration.

## Fixes included in the trial branch

| Change | Commit | Scope |
| --- | --- | --- |
| Optional local ASR backends | `84c1a71` | Mesolitica, MMS, Qwen and BuzzASR alongside existing Faster-Whisper. |
| Preparation notifications | `107a903` | Stage/elapsed messages; ready message follows successful loading. |
| Runtime checks and separate output folders | `2588c2c` | Explain selected model and fail early for unavailable requirements. |
| Remove Sortformer | `630a7db` | User chose to retain the pyannote workflow without WSL/NeMo. |
| Pyannote model choices | `cdbb0c7` | Community-1 default and 3.1 legacy/comparison. |
| Full English names and Tiny | `85383c5` | Seven study candidates, then four Legacy choices. |
| Dependency diagnostics | `63429fe` | Separate OpenTelemetry import failure from missing pyannote; clarify model downloads versus package repair. |
| Real per-file download percentages | `90a2ead` | Scoped download observer; no invented total percentage. |
| Correct MMS Malay adapter | `63244cf` | `zsm` to `zlm`, vocabulary guard and regression coverage. |

## Validation boundary and next records

Automated checks use mocked model runtimes; they do not validate real GPU inference or transcription accuracy. Checks rerun on 15 November 2026: `python -m unittest discover -s tests -p 'test_*.py'` ran 102 tests: 94 passed and 8 Tk/display-dependent tests were skipped. `git diff --check` passed. No new executable diagnostic or runtime change is included in this documentation update. No independent CUDA execution was performed in the development workspace.

Before treating the software as a validated comparison tool, record each selected model's completed run, both exports, actual language/precision/checkpoint, and any error. Keep failed runs in the record. For the separate 25-recording Kelantan study, use the verified references and agreed controlled FP16 protocol; desktop diarisation-dependent chunks and Faster-Whisper CPU fallback are not equivalent benchmark conditions.

Merge remains a separate user decision. Open items above are retained explicitly rather than marked passed.

## Follow-up: Legacy run completion / next-run controls

The user subsequently clarified that a Legacy model finished producing transcript text, then appeared stuck during the transition to completion or the next run. The supplied description does not identify a specific Legacy checkpoint, export stage or exception. This is a new issue report, not a confirmed successful Legacy trial.

Code inspection found a completion-order defect: `_run_whisper` queued a modal completion popup and enabled Start before the outer worker had finished memory cleanup and reset `run_phase` to idle. Clicking Start during that interval could leave an apparently available button with the previous run still active. Cleanup failure could also prevent the old final reset from being scheduled. This is a reproducible control-order risk, not proof of the entire cause of the user's Windows hang.

The branch now returns the completion callback to the outer worker, releases model/cache resources first, and resets the controls/run state on the Tk thread before displaying the modal completion/error message. Only that final reset re-enables Start. Cleanup exceptions generate a warning and still restore controls. Saving Excel, saving Word, saved-file paths and final memory cleanup now have visible activity/log messages. No timeout or forced interruption of an active GPU/export call is introduced.

Regression checks exercise the real worker/export orchestration with mocked inference and queued Tk callbacks: successful completion, two consecutive runs, cleanup failure, Excel failure, Word partial success, preflight failure, cancellation and inference-generator cleanup. They do not simulate an actual Windows CUDA hang. A new short Legacy run followed by a second run on the user's PC remains necessary; if it still stalls, the last visible saving/finalising stage is the next diagnostic evidence.

Follow-up validation: the full suite ran 110 tests: 102 passed and 8 display-dependent tests were skipped. Python compilation and `git diff --check` passed. Actual Windows Legacy completion/re-run remains pending.

## Follow-up: local performance logging

The user requested timing/performance records similar to the RedScrap workflow. The branch now saves a readable `.log` and machine-readable `.json` for each run under `output/performance/`, with a Live Transcript summary. Records distinguish ASR preparation (cache/download/load), diarisation, ASR processing, exports and final cleanup; full details and overlap rules are documented in [the model guide](MULTI_MODEL_ASR.md#local-performance-records). Completed-ASR real-time factor and speed are calculated from full audio duration and ASR processing time excluding overlapping model preparation. Failed/cancelled ASR does not receive a speed estimate. No transcript, token, study name or audio filename is serialised into these records. This does not change study precision or add a benchmark runner.

Deterministic timing tests cover eager/lazy preparation, overlap subtraction, interrupted stages, zero/missing duration and real JSON/log writes. Worker tests check private GUI fields are excluded and a log-write failure does not strand completion. Actual Windows timing accuracy/overhead remains to be trialled; no GPU performance result is claimed from mocked tests.

Performance-log validation: 118 tests ran; 110 passed and 8 display-dependent tests were skipped. Python compilation and `git diff --check` passed.

## Follow-up: Windows performance output and terminal mirroring

The user supplied a completed Whisper Large-v3 run with total 99.79 s, model preparation 12.56 s, diarisation 20.52 s, ASR processing 63.16 s, RTF 0.058, speed 17.18x realtime, Excel 0.06 s, Word 0.13 s and final cleanup 0.12 s. Both exports and a performance-log path appeared in Live Transcript. These are rounded values from one user run, not a controlled benchmark; no accuracy conclusion follows.

The user noted the summary did not appear in the VS Code terminal. The branch now mirrors the performance summary and saved-log location (or log-save warning) to an attached terminal with immediate flushing. A closed/detached console does not block report completion. This requires updating and restarting the application; previous runs are not replayed automatically.
