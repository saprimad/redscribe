# RedScribe Benchmarking Workflow — Academic v8

![RedScribe Benchmark Workflow — Academic v8](RedScribe_Benchmark_Workflow_Academic_v8.svg)

The current **experimental** benchmark workflow shows how audio recordings and researcher-verified DOCX references are prepared, paired, processed across selected ASR models, and evaluated using raw WER/CER with optional speech and resource analysis.

## Latest diagram
- [Academic v8 — SVG figure](RedScribe_Benchmark_Workflow_Academic_v8.svg) — displays directly in GitHub and is suitable for scalable figures.
- [Academic v8 — interactive HTML](RedScribe_Benchmark_Workflow_Academic_v8.html) — open locally for export to SVG/PNG.

## Previous version
- [Reviewed v7 — SVG](RedScribe_Benchmark_Workflow_Reviewed_v7.svg)
- [Reviewed v7 — HTML](RedScribe_Benchmark_Workflow_Reviewed_v7.html)

**Research status:** Figure reflects code/design in the `redscribe-benchmark-timeline` experimental branch, not a completed or independently validated scientific benchmark. Normalisation, diarisation-ground-truth evaluation and other methodological HOLD items remain open. Do not commit recordings, approved transcript data, or personally identifiable material to this repository.

## Code audit and publication readiness

- [Critical static code audit — 18 November 2026](CRITICAL_CODE_AUDIT_2026-11-18.md): confirmed implementation fixes, unresolved scoring comparability risks, and priority Windows/GPU test plan.
- **Do not describe the experimental benchmarking mode as IEEE-validated yet.** Run and record full synthetic tests and real-device pilot checks first; maintain the five existing methodological HOLD decisions.
