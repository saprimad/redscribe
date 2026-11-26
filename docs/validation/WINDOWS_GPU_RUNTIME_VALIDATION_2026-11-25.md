# Windows GPU runtime validation — 25 November 2026

**Scope:** experimental full-length benchmark, PR #27. Technical validation only; not formal study results.

## Configuration

- Tested code: [6721ae4](https://github.com/saprimad/redscribe/commit/6721ae47309b7a5d919ccb856a91f9b29d7c1bdb); runtime manifest reports a clean Git working tree.
- Windows build 26200; Python 3.11.9; NVIDIA GeForce RTX 5070; driver 610.88; CUDA FP16.
- PyTorch 2.10.0+cu130; Faster-Whisper 1.2.1; CTranslate2 4.7.1; RapidFuzz 3.14.3.
- One approved full-length recording; Malay transcription; beam size 5, VAD disabled, conditioning on previous text enabled. Raw scoring policy unchanged.

## Defect history and corrective actions

| Stage | Observed outcome |
| --- | --- |
| Original in-process benchmark | Native abort during Whisper wrapper destruction, Windows status 0xC0000409; entire application terminated. |
| Subprocess isolation ([1d9c370](https://github.com/saprimad/redscribe/commit/1d9c3703c30aab2d4feb7f36745031b3c865b358)) | Native cleanup abort contained; both model results and reporting completed. |
| Explicit native unload ([b272dfe](https://github.com/saprimad/redscribe/commit/b272dfe3c1431e20c5ed657c054c8224c32e992a)) | Large-v3 native unload succeeded but wrapper release still aborted; Turbo completed normally. |
| Controlled shutdown ([6721ae4](https://github.com/saprimad/redscribe/commit/6721ae47309b7a5d919ccb856a91f9b29d7c1bdb)) | Windows Large-v3 explicitly unloads weights, acknowledges shutdown and exits its disposable worker without invoking the problematic wrapper destructor. Turbo retains normal cleanup. Both exit codes were zero. |

The underlying upstream destructor defect is not claimed to be fixed. The controlled exit is a scoped operational workaround, not evidence of normal destructor completion.

## Actual GPU runtime evidence

| Acceptance criterion | Large-v3 | Turbo |
| --- | --- | --- |
| Full-length inference | PASS | PASS |
| Explicit native unload | PASS | PASS |
| Shutdown strategy | controlled_process_exit | normal_destructor |
| Cleanup status in matrix | completed | completed |
| Cleanup error | null | null |
| Worker exit code | 0 | 0 |

Sanitised diagnostic excerpts:

```text
MODEL: large-v3 | LANGUAGE: ms
INFERENCE START
INFERENCE PASS
CLEANUP START
NATIVE UNLOAD START
NATIVE UNLOAD PASS
CONTROLLED PROCESS EXIT: wrapper destructor intentionally bypassed
```

```text
MODEL: turbo | LANGUAGE: ms
INFERENCE START
INFERENCE PASS
CLEANUP START
NATIVE UNLOAD START
NATIVE UNLOAD PASS
WRAPPER RELEASE START
WRAPPER RELEASE PASS
CLEANUP PASS
```

The operator reported that the benchmark completed with the GUI remaining operational. The supplied matrix records both cells as completed and associates each with its worker log. A scientific workbook and export manifest were produced; the manifest lists 15 reporting artefacts. This public record does not independently certify every artefact or recompute transcript-level scores.

## Continuous integration

Both workflows for the tested commit completed successfully:

- [Benchmark runner synthetic tests — 45642290643](https://github.com/saprimad/redscribe/actions/runs/45642290643)
- [Benchmark dependency validation — 45642290408](https://github.com/saprimad/redscribe/actions/runs/45642290408)

These are distinct from the operator's actual GPU test.

## Release gate and limitations

- Operational native shutdown defect: passed for this tested Windows/GPU configuration and two models only.
- Remaining: seven-model full-length pilot, same-version repeatability assessment, experimental version/configuration freeze and expert review. Large-v3 predictions varied across development revisions; this is not a controlled same-version reproducibility test.
- Ordinary transcription and diarisation on the main branch are not covered by this validation.
- No formal participant-level experiment or general claim of zero crashes is authorised by this record.
- Raw recordings, references, predictions, participant identifiers, local paths and raw study manifests are deliberately excluded. Retain original evidence privately under the approved research governance arrangements.
