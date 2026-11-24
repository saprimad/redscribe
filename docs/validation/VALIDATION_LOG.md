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
