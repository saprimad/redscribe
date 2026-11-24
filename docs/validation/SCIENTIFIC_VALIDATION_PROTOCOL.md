# Independent metric validation

Primary external oracle: [JiWER](https://github.com/jitsi/jiwer), pinned to 4.0.0 in CI. Compare minimum edit totals and rates on 225 synthetic reference/hypothesis pairs for each metric. WER uses Python whitespace tokenisation; CER preserves Unicode code points, whitespace, case and punctuation. No dialect normalisation or filler removal. Empty-reference rates remain undefined in RedScribe; compare edit totals only in this case. Individual S/D/I counts may differ on tied optimal alignments; do not claim equivalence of error attribution.

Acceptance: all synthetic comparisons and existing regression tests pass. This does not establish full-length performance, audio/reference alignment or scientific validity on real recordings. NIST SCTK cross-check, Windows GPU validation and real-data validation remain pending. No participant data in CI.

External references for subsequent review: [NIST SCTK](https://github.com/usnistgov/SCTK), [ESPnet](https://github.com/espnet/espnet), [Open ASR Leaderboard](https://github.com/huggingface/open_asr_leaderboard). These are technical references, not verified Scopus-indexed literature.
