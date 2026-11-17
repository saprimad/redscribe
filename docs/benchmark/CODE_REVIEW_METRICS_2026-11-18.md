# RedScribe Benchmarking Code Re-review — WER/CER and pipeline integration

**Date:** 18 November 2026  
**Branch:** `redscribe-benchmark-timeline` only  
**Scope:** static source inspection of 16 benchmark-related files, including metric scoring, DOCX extraction, reference approval, single and batch execution, ASR backends, monitoring and synthetic tests.

## Verification actually performed

- Compared the **production `benchmark_metrics.edit_counts` algorithm as reproduced from reviewed source** with an independent full-matrix Levenshtein distance implementation, on all **14,641** combinations of token sequences of length 0–4 from a three-token alphabet. Result: **14,641 / 14,641 distance totals agree**. This verifies short-sequence raw edit distance, not speaker scoring, model output, NIST compatibility, long-audio performance or end-to-end runtime.
- Checked manually expected illustrative raw scores: `makae` vs `makan` has one character substitution; `e + combining accent` versus `é` differ as Unicode code points; newline versus space changes raw CER.
- Added source-controlled regression file `tests/test_benchmark_metric_validation.py` with the independent full-matrix oracle, exhaustive tests, dialect/case/Unicode and micro/macro aggregate checks.
- **Not performed:** Running GitHub's entire test suite on Windows, using `jiwer`, NIST SCLITE, RTX 5070 inference, real interview audio, live Tkinter UI and model-by-model compatibility testing. These must not be reported as passed.

## Findings by severity

| ID | Priority | Evidence from source | Required decision/action |
|---|---|---|---|
| M01 | HIGH | `raw_wer` tokenises by `split()`; `raw_cer` operates on Unicode code points including punctuation, case, whitespace and newlines. DOCX reference lines and ASR's segment-joined hypothesis can therefore have systematic CER formatting differences | Prespecify reference/hypothesis formatting and verify that both use the same policy. **BM/Kelantan normalisation stays HOLD** |
| M02 | HIGH | The internal scorer returns `rate=None` for an empty reference even if hypothesis text exists. Single pilot rejects blank references, but external callers can request undefined metric values | Clearly distinguish undefined denominator from zero error. Keep not-scored status or explicit error handling when applicable |
| M03 | HIGH | S/D/I in `benchmark_metrics` use deterministic tie-breaking. Other valid aligners may produce different S/D/I partitions despite identical total WER/CER | Use a full documented alignment policy; independently validate edit-distance total and segmentation with `jiwer` and SCLITE before publication |
| M04 | HIGH | `benchmark_pilot` writes **only word-level S/D/I** into `results.csv`, while CER S/D/I counts are not exported. Corpus and macro aggregations exist in `benchmark_metrics` but are not integrated into reports | Separate word and character error component columns and add validated micro/macro result reporting |
| M05 | HIGH | Optional model weights are loaded during generator iteration, included in `transcription_seconds`; Faster-Whisper loading time is separate. RTF is therefore not comparable across all 11 models | Refactor per-backend timestamps and record model load, preprocess, decode and wall-clock timings consistently before any performance comparison |
| M06 | HIGH | Backend settings differ: chunked optional ASR, language-specific model support and CPU INT8 fallback for Faster-Whisper vs CUDA FP16 for optional models | Publish a controlled inference configuration per backend and define fairness criteria before comparing 11 models; **GPU compatibility HOLD** |
| M07 | HIGH | The experimental pilot accepts a 180-second audio but the current ground-truth approval relies on human verification for exact audio-span coverage | Test exact clip-to-reference matching on representative data, particularly when original interview DOCX is much longer; **audio-span/overlap policy HOLD** |
| M08 | MEDIUM | The batch saves per-audio/model rows and checkpoints, but its flat CSV does not include corpus WER/CER and cannot automatically resume | Add atomic, independently checked corpus aggregation and resume later, after validation |
| M09 | MEDIUM | Optional GPU monitoring is system-wide GPU 0 / RAM and can miss short spikes; VAD/OSD are descriptive estimates, not proof of speaker ground truth | Report sampler limitations and validate optional modules on the RTX 5070 |
| M10 | MEDIUM | The DOCX parser can flag revisions and special content but cannot certify that Word text boxes, tracked modifications or merged table representations match the scoring text | Continue human inspection of actual de-identified DOCX examples before freezing; maintain verification checklist |
| M11 | MEDIUM | `benchmark_pilot._cleanup` is called in `finally`, and cleanup errors other than selected torch exceptions may mask a successful model run | Treat cleanup failures separately from inference and scoring results in a future patch with an explicit regression test |
| M12 | LOW | GitHub synthetic tests are currently primarily mocks and example checks, not real 11-model inference | Run all tests and record output on the workstation before naming the platform verified |

## What can be concluded today?

**Mathematical core:** Short-sequence Levenshtein totals agree with a separate implementation on 14,641 combinations. This is encouraging evidence, but not independent package/SCLITE validation. `raw_wer` and `raw_cer` intentionally preserve original casing, punctuation, spacing and dialect; those rules must not silently change.

**Research readiness:** **NO-GO for IEEE-quality empirical claims** until the reference-format policy, independent scoring cross-check, matched audio-span validation and 11-backend timing/decoding policy have been completed. Code may continue to be used for de-identified exploratory smoke tests.

## Recommended immediate sequence

1. Execute the source-controlled synthetic regression suite on Windows and capture genuine pass/fail output.
2. Validate raw WER/CER totals against `jiwer` on predefined Malay, English and Kelantan fixtures; independently cross-check using NIST SCTK/SCLITE on compatible fixtures.
3. Record both **word and character** S/D/I and micro/macro batch aggregates, without silently modifying the scoring normalisation policy.
4. Harmonise reference/hypothesis formatting only after reviewer-approved, preregistered scoring rules; never introduce implicit linguistic standardisation.
5. Standardise experimental measurement instrumentation (runtime timing, GPU use, model revisions) prior to comparative benchmark runs.

**Privacy:** No participant DOCX, audio or ground-truth contents were uploaded. No main-branch edits.
