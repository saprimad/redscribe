# Scientific reporting v1.0 — initial architecture gap analysis

Baseline: `2e1a523f5d70cd08444ec6bbe3bff67480f88fda` on `refactor/benchmark-architecture`, draft PR #27.
Scope: Benchmarking Mode only. Standard transcription remains out of scope.

## Evidence from the baseline

- `benchmark_metrics.py`: existing raw edit counts and deterministic DP policy.
- `benchmark_fast_metrics.py`: RapidFuzz editops policy for model-major scoring.
- `tests/test_benchmark_jiwer.py`: independent JiWER total-error/rate cross-checks, not proof that all S/D/I alignments are identical.
- `benchmark_reporting.py` and `benchmark_matrix_reporting.py`: validated per-recording and cohort reporting with S/D/I, denominators and fractional rates.
- `benchmark_publication.py`: existing XLSX, SVG and 600-DPI PNG exports.
- `benchmark_export_audit.py`: checks exact output schema; adding legacy columns without compatibility planning could invalidate historical export audits.
- `requirements-benchmark.txt`: pinned JiWER, RapidFuzz, Matplotlib and openpyxl.

## Initial implementation

Add an extended reporting view to the existing ErrorCounts object: hits, hypothesis units, total errors, and validation of count feasibility. This is an additive API only. It preserves original rate semantics, tokenisation, empty-reference policy and existing as_dict() schema. It does not modify inference or historical outputs.

Synthetic tests are supplied; new CI execution must be checked independently.

## Remaining scope and sequence

1. Integrate extended counts with the authoritative benchmark result records using a versioned export without invalidating older manifests or audit schemas.
2. Implement engine-consistent lexical alignment and frequencies. Do not re-align with another engine and present divergent S/D/I as the canonical result. Keep lexical details private; record alignment policy.
3. Inspect dataset/manifest, freeze integrity, resource and timing schemas in detail, then implement a per-recording reporting adapter. Report unavailable values explicitly.
4. Implement stable rainbow model colours and traffic-light error colours, bottom legends, vector figures, and all 13 requested PDF sections with dynamic A4 pagination.
5. Implement collision-safe filename-based folders, versioned JSON, report regeneration and a shareable redacted output. Do not modify frozen datasets or historical results.
6. Add representative synthetic PDFs, numerical and rendering tests, documentation and regression tests. Windows GPU runtime and actual report inspection remain separate release gates.

No external leaderboard or blind benchmark infrastructure in this release. No merge to main. This is an initial gap analysis, not a completed feature or release sign-off.
