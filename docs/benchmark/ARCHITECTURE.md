# Benchmark software architecture

The sections below record the package migration and its historical acceptance checks. For current execution routes and subsequent runtime evidence see [Part II](../scientific/part-II-benchmarking/README.md) and the [consolidated record](../validation/CONSOLIDATED_DEVELOPMENT_RECORD_2026-11-28.md).

## Package layout

```text
redscribe/
  benchmark/   Configuration, reference preparation, execution, metrics, resources and reporting
  ui/          Benchmark configuration, reference review and batch pairing
```

The desktop entry point remains `redscribe_gpu.py`. Shared ASR adapters remain at the root pending a separate migration. Root benchmark modules alias the packaged implementations to preserve existing imports and mock targets; the Excel command-line entry point is retained. The UI output directory remains at repository root. This staged refactor does not change scoring rules, model selection or study methodology.

## Verification gate

Run `python -m compileall -q redscribe tests` and `python -m unittest discover -s tests -p "test_benchmark*.py" -v`. Then verify desktop launch, reference approval, single/batch execution, output paths and Excel regeneration on Windows. No merge until results are reviewed. This migration is not evidence of scientific validation.

## Review status — 25 November 2026

The synthetic suite passed 84/84 on each of Windows and Ubuntu; CPU dependency checks passed on both. See the [software validation record](../validation/FINAL_SOFTWARE_VALIDATION_2026-11-25.md). Batch execution supports resume with integrity verification; publication reporting is implemented in `redscribe/benchmark/benchmark_publication.py` and matrix reporting in `redscribe/benchmark/benchmark_matrix_reporting.py`. Actual GUI and GPU inference remain unverified. Root compatibility modules are intentional; do not remove them during documentation housekeeping.
