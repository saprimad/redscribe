# Verbatim WER/CER Reporting Engine — experimental protocol

**Updated:** 18 November 2026 · **Branch:** `redscribe-benchmark-timeline` only.

## Prespecified scope

- **Primary measures:** corpus-level raw *verbatim* WER and CER, from speech by **all speakers** in the approved audio segment (interviewer, participants and other audible speakers).
- **Included:** spoken fillers (`hmm`, `aa`, `err` etc.), repetitions, English code-switching and Kelantan dialect, with their approved reference spellings. No filler exclusion, automatic dialect standardisation, code-switching separation or speaker-only filtering.
- **Raw WER:** case/punctuation retained, whitespace-separated word tokens. **Raw CER:** Unicode code points including punctuation, spaces and newlines. **Important HOLD:** before results are publishable, define a *consistent* reference/hypothesis layout and orthographic scoring policy, especially DOCX newlines vs ASR spaces and Unicode composition. No such normalisation is silently applied.
- No fabricated model outputs, no real participant recordings, and no upload of private reference text to GitHub.

## New export artefacts

For each **single** pilot and for the **batch** root folder:

1. `model_summary.csv`: two rows per selected model — `all_attempted` and `common_completed`. Stores success/failure/unavailable counts, word/character scored sample counts, totals of word S/D/I and character S/D/I, denominators, **corpus WER/CER** and **macro WER/CER**.
2. `error_breakdown.csv`: one row for each **selected model × recording**, including failed, pending and cancelled records; only valid completed entries have numerical scoring.
3. Existing `results.csv` and `batch_results.csv` retained. Single-model rows add explicit `word_substitutions`, `word_deletions`, `word_insertions`, `char_substitutions`, `char_deletions` and `char_insertions`. Old `substitutions`/`deletions`/`insertions` remain word counts for backwards compatibility.
4. Existing JSON run/batch manifests retain source and reference hashes, verification details and model status. No extra user-uploaded document required.

**Rates are raw fractions**: multiply by 100 to present percent figures in IEEE tables. `0.15` means 15%, not 0.15%. Scores exceeding 1.0 (100%) are permitted when insertion errors exceed the reference denominator.

## Formula and cohort rules

For each model, over a valid set of recordings:

\[
\mathrm{Corpus\ WER}=\frac{\sum_i(S_i+D_i+I_i)}{\sum_i N_i},\qquad
\mathrm{Macro\ WER}=\frac{1}{K}\sum_{i=1}^{K}\frac{S_i+D_i+I_i}{N_i}.
\]

CER applies the analogous equation to character units. A missing, noninteger, negative or arithmetically inconsistent error count is **not included** in aggregates; completed model records with incomplete metrics still count as completed, but `word_scored`/`character_scored` reveal missing scored observations. This prevents bogus zero errors from contaminating the mean.

- **all_attempted:** all submitted audio records as denominator for status reporting; numerical metrics include only valid completed model results.
- **common_completed:** only audio records with verified, complete word **and** character error totals from **every selected model**. It is a strict, same-recording cohort for fairer pairwise descriptive comparison. If none, cohort totals are zero and metrics remain blank, **not zero**.
- **Important:** differences in decoding, chunking, precision, loading time and language support still prevent a publication-ready claim of fair model comparison. A common cohort alone does not resolve them.

## IEEE publication layout (not an IEEE-imposed standard)

- **Table I:** model | N submitted | N scored | failures | corpus WER (%) | corpus CER (%) | optional RTF after timing is standardised.
- **Table II:** model | word substitutions | deletions | insertions | reference words.
- **Supplementary:** per-recording word/character S/D/I, macro scores and model status.
- **Do not** label results by a separate English WER category unless a properly verified English-only subset and separate research question are established. The current primary dataset includes code-switching within its overall verbatim scores.

## Validation and current limitations

- Added `tests/test_benchmark_reporting.py`: mathematically known corpus vs macro values, common-only matched cohort, per-character component availability, missing/failed outcomes, export formatting, and inconsistent records.
- Synthetic tests have been authored but **CI, Windows Tkinter and RTX 5070 runs have not yet been verified here**. Compare scoring independently with `jiwer` and NIST SCTK/SCLITE before claiming independent validation.
- `benchmark_summary.xlsx` now has an experimental standard-library XLSX exporter, called automatically at the end of a single or batch pilot. Four sheets: **Model Summary**, **Recording Results**, **Error Breakdown** and **Run Status**. Numeric rates use the Excel percent format (0.15 displays as 15%); source CSV and JSON remain the primary auditable results.
- To regenerate locally from a stored experimental run, execute `python benchmark_excel.py PATH_TO_MANIFEST_JSON` (single `manifest.json`, or batch `batch_manifest.json`). The workbook is saved beside the manifest.
- A language/dialect sheet is deliberately **not** generated: subgroup labels have not yet been researcher-verified; do not infer dialect from filenames or ASR language settings.
- Added `tests/test_benchmark_excel.py` to check XLSX ZIP/XML structure, numeric percent cells, missing results and formula-injection safety. **Actual spreadsheet application compatibility and CI success are still unverified**.
- Bootstrap 95% confidence intervals and significance testing remain **unimplemented**.
- Current results remain exploratory: per-pilot audio length <=180 seconds; exact clip/reference coverage requires research verification; overlap policy is not yet validated against timestamped speaker-annotated truth.
