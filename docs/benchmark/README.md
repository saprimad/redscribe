# Benchmark protocols

For the desktop workflow, start with the [illustrated user guide](../user-guide/README.md). For code paths, model scheduling and output interpretation, see [Part II](../scientific/part-II-benchmarking/README.md) and the [architecture figures](../scientific/figures/README.md).

| Protocol | Use |
| --- | --- |
| [Ground truth preparation and verification](GROUND_TRUTH_PROTOCOL.md) | Prepare, review and freeze the scoring copy before inference. |
| [Accuracy and computational efficiency](../scientific/BENCHMARK_METHODOLOGY.md) | Interpret raw WER/CER, denominators, timing boundaries and resource observations. |
| [Statistical analysis and numerical revalidation](../scientific/STATISTICS.md) | Distinguish the planned paired comparison from the single-recording demonstration. |
| [Research integrity and provenance](../scientific/INTEGRITY.md) | Review evidence permissions, recording eligibility and reproducibility gates. |

## Earlier designs and audits

The historical [reporting protocol](REPORTING_ENGINE_PROTOCOL.md), [package migration](ARCHITECTURE.md), [scoring review](CODE_REVIEW_METRICS_2026-11-18.md), [single and batch runner audit](SINGLE_BATCH_RUNNER_AUDIT_2026-11-18.md) and [static code audit](CRITICAL_CODE_AUDIT_2026-11-18.md) describe their named revisions. The earlier diagrams remain available in [SVG v8](RedScribe_Benchmark_Workflow_Academic_v8.svg), [editable HTML v8](RedScribe_Benchmark_Workflow_Academic_v8.html), [SVG v7](RedScribe_Benchmark_Workflow_Reviewed_v7.svg) and [editable HTML v7](RedScribe_Benchmark_Workflow_Reviewed_v7.html).
