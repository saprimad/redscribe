# WER/CER scoring preparation before the experiment

Status: planned implementation and pre-experiment gate. No scoring tool, participant-data extraction or study evaluation is implemented by this document. Follow the parent [FP16 protocol](PROTOCOL.md), including its existing normalisation rules. Complete and freeze this preparation before the 25-recording scored experiment.

## Tool and input contract

Use JiWER locally in a separate evaluation tool, with an exact tested package version pinned before scoring. It provides word- and character-level edit alignment and metrics. Do not rely on an unpinned latest installation or a public website for private interview text. Record the scoring script commit, Python/JiWER versions and configuration hash with results.

The planned tool accepts two explicitly assigned texts for each anonymous recording/model pair:

| Input | Meaning |
| --- | --- |
| Reference | Existing human-verified verbatim transcript, checked against the corresponding recording and declared interval. |
| Hypothesis | Unedited ASR output for the same recording/interval and frozen model configuration. |

Reference and hypothesis roles must not be reversed. Preserve original reference files, extracted UTF-8 text and raw model hypotheses with hashes. Extraction must take only dialogue, excluding report tables, headings, charts, study metadata, timestamps and speaker labels. Check extraction against the verified source; automatic regex cleanup alone is not verification. Prefer raw text captured by the planned benchmark runner rather than re-extracting model output from a formatted report. Do not overwrite source files or let ASR output alter the reference.

## One frozen normalisation policy

Apply the identical versioned policy to both sides, as already specified in the parent protocol:

1. Unicode NFC.
2. Lowercase.
3. Replace Unicode punctuation with spaces (do not join words).
4. Collapse whitespace and trim.
5. Preserve dialect spellings, fillers, code-switching, digits and diacritics. No synonym replacement, number expansion, standard-Malay conversion or LLM correction.

WER tokens are whitespace-separated words after these steps. CER uses the resulting text with whitespace removed. Validate references remain non-empty after transformation. Keep both raw and normalised text privately for audit. Punctuation replacement can split apostrophes/hyphens; document that behaviour and apply it consistently rather than changing rules after viewing model scores. Any later alternative normalisation is a separately labelled sensitivity analysis, not a replacement primary result.

## Planned scoring and exports

For each recording/model result retain word and character substitutions (S), deletions (D), insertions (I), hits, reference denominators, alignments, WER and CER. Report percentages, with raw counts retained so results can be reproduced. Lower is better; neither metric is a semantic-similarity score or a percentage of sentences understood.

- Corpus WER: `100 * sum(word_S + word_D + word_I) / sum(reference_words)`.
- Corpus CER: `100 * sum(char_S + char_D + char_I) / sum(reference_characters)` under the whitespace-free CER convention.
- Do not use an unweighted mean of the 25 recording percentages as the primary corpus score. Do not cap error rates at 100 percent.
- A successful run returning empty text is scored as deletions. A crashed/absent hypothesis is a failed or missing job, not an empty successful transcript and not zero error.
- Preserve failed-job status and coverage. Primary model ranking requires all 25 recordings; incomplete candidates need separately labelled matched-subset analysis, as specified in the protocol.
- Controlled SSIG-based read speech is scored and summarised separately from spontaneous interviews.

The planned local exports under `output/benchmark_kelantan_fp16/` are:

| File / workbook sheet | Planned content |
| --- | --- |
| `scoring_config.json` | Frozen normalisation policy, library/script versions and configuration hash. |
| `scores.jsonl` | Recording/model IDs, source/configuration hashes, status, counts, denominators, WER/CER and private alignment paths. |
| `evaluation_summary.xlsx` / `Per_recording` | One row per recording/model attempt, with score/status and available benchmark timing/resource measurements. |
| `evaluation_summary.xlsx` / `Model_summary` | Coverage out of 25, corpus WER/CER, timings/RTF and peak VRAM from the benchmark runner. |
| `evaluation_summary.xlsx` / `Error_alignment` | Word/character alignments and error types for review. |
| `evaluation_summary.xlsx` / `Scoring_config` | Versions, conventions, dataset/configuration hashes and freeze date. |

Evaluation does not infer processing speed or GPU memory from text. Link the benchmark runner's measured metrics by matching recording/model/configuration hashes; retain missing measurements as unavailable. Existing desktop performance logs have a different timing scope and are not automatically valid benchmark measurements. Keep private transcripts, alignments, completed manifests and result workbooks out of GitHub.

## Required checks before scoring study outputs

Build and test the scorer on synthetic examples and a separate non-study smoke-test recording. Do not tune normalisation, prompts or model settings using scores on the 25 study references.

| Check | Expected behaviour |
| --- | --- |
| Identical text | WER and CER are zero. |
| One deleted word: reference `saya makan nasi`, hypothesis `saya makan` | Word D=1, N=3, WER=33.333…%. |
| One substituted character: `abc` versus `adc` | Character S=1, N=3, CER=33.333…%. |
| Empty successful hypothesis versus a non-empty reference | WER and CER are 100%; inference status remains successful. |
| Reference `saya`, hypothesis `saya makan nasi` | Word I=2, N=1, WER=200%; do not cap it. |
| Case, punctuation and whitespace differences only | Identical normalised text under the declared rules. |
| Dialect versus standard-Malay wording | Retain differences and score them; do not silently map them to synonyms. |
| Blank reference after normalisation | Block scoring with a data-preparation error; do not silently omit the recording. |
| Missing/crashed job | Preserve failure status and exclude it from a claimed complete-model corpus result. |
| Corpus with unequal recording lengths | Sum edit counts and denominators, rather than averaging recording percentages. |
| Repeat the same frozen input/configuration | Identical counts, scores and alignments within the pinned environment. |

## Pre-experiment gate

- [ ] Confirm all 25 audio/reference mappings, scoring intervals, extraction checks and hashes.
- [ ] Implement the local evaluation tool and pin its tested Python/JiWER environment.
- [ ] Implement and freeze the normaliser, including whitespace-free CER.
- [ ] Pass the synthetic count/edge-case checks and a non-study end-to-end extraction/scoring/export check.
- [ ] Confirm no speaker labels, report metadata or timestamps enter scored text.
- [ ] Verify per-recording and corpus aggregation, failure handling and Excel/JSON export round-trip.
- [ ] Freeze scorer/configuration versions and record the freeze date before the experiment.
- [ ] Only then start the planned 25-recording model evaluations; preserve all attempted jobs and raw hypotheses.

This is additional preparation, not a change to the seven candidates, FP16 policy, no-diarisation rule or the separate controlled read-speech design. It does not add WER/CER controls to the main desktop app.

## Primary references

- [JiWER documentation](https://jitsi.github.io/jiwer/)
- [JiWER usage and alignment examples](https://github.com/jitsi/jiwer/blob/master/docs/usage.md)
- [Hugging Face WER definition](https://github.com/huggingface/evaluate/blob/main/metrics/wer/README.md)
- [Hugging Face CER definition](https://github.com/huggingface/evaluate/blob/main/metrics/cer/README.md)

Pin the versions actually used; the links describe capabilities and do not mean the scorer has been implemented or validated.
