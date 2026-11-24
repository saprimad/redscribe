# Validation log

Append-only record of software validation; retain failed runs. Dates UTC. Synthetic data only.

| Date | Commit | CI run | Expected | Observed | Disposition |
|---|---|---|---|---|---|
| 2026-11-24 | `bb7b492` | [45386582988](https://github.com/saprimad/redscribe/actions/runs/45386582988) | All tests pass | 39/41 passed; 2 failed | CER fixture used literal escapes; DOCX XML proxy ID reuse dropped a paragraph |
| 2026-11-24 | `094ee8e` | [45386756260](https://github.com/saprimad/redscribe/actions/runs/45386756260) | Compilation and regression suite pass | CI success | Correct fixture escapes; remove unsafe ID deduplication; add repeated table text regression |
| 2026-11-24 | `8ec56f3` | [45387103767](https://github.com/saprimad/redscribe/actions/runs/45387103767) | All tests and JiWER comparisons pass | 43/43 passed; JiWER subtests passed | 225 pairs per metric, 450 comparisons; pinned JiWER 4.0.0 |

Duplicate CI triggers: [45386595446](https://github.com/saprimad/redscribe/actions/runs/45386595446) failed; [45386768117](https://github.com/saprimad/redscribe/actions/runs/45386768117) and [45387113285](https://github.com/saprimad/redscribe/actions/runs/45387113285) succeeded. These are not additional independent experiments.

## Next validation gates
- P0: audit raw prediction persistence, scoring inputs, hashes, resume and failure handling.
- P0: audit DOCX extraction coverage, complex tables and explicit human review.
- P1: Windows/Linux CI and dependency provenance; external SCTK comparison subject to equivalent preprocessing.
- P2: real Windows GPU pilot and full-length validation before the 25-recording study.

No participant data uploaded. CI success does not establish ASR accuracy, real-data coverage, GPU compatibility or publication readiness. Do not merge solely on these results.

For future entries record UTC date, commit SHA, run ID, environment, expected/observed results, failure cause, corrective action and remaining limitations.

## Scope decision — 2026-11-24
Native segment export (b1d5037) withdrawn with researcher approval: whole-transcript accuracy is the objective. Retain exact scoring prediction and SHA-256 (908303f). Reversion CI pending. Benchmark branch only.

## Additional CI evidence — 2026-11-24
- [45387874220](https://github.com/saprimad/redscribe/actions/runs/45387874220): 44/44 pass, prediction integrity.
- [45388746718](https://github.com/saprimad/redscribe/actions/runs/45388746718): 45/45 pass, offline rescoring.
- [45388903639](https://github.com/saprimad/redscribe/actions/runs/45388903639): 45/46 pass; stale extraction version assertion (v2 vs v3). Update expected version; rerun pending.

## Feature freeze — 2026-11-24
[45391153563](https://github.com/saprimad/redscribe/actions/runs/45391153563): 50/50 tests passed at ca117aa. Strict configuration and provenance predecessor runs also succeeded. Full experiment not yet authorised; see FINAL_SOFTWARE_AUDIT.md.

## RapidFuzz long-text validation — 2026-11-24
[45406919114](https://github.com/saprimad/redscribe/actions/runs/45406919114), commit 2bce950: Windows and Ubuntu each passed 68/68 tests. At 100,000 characters, mutation probabilities 0.1/0.3/0.5 produced CER 0.12994/0.37833/0.60311. Windows scoring seconds 0.849511/1.092370/1.273784; Ubuntu 0.347787/0.409965/0.462277. Synthetic CI timings, not target hardware or ASR timings. Model-major duration ceiling raised to 7200 seconds; old pilot unchanged. Actual long-audio GPU validation pending.
