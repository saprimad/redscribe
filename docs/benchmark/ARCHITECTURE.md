# Benchmark software architecture

## Package layout

```text
redscribe/
  benchmark/   Configuration, reference preparation, execution, metrics, resources and reporting
  ui/          Benchmark configuration, reference review and batch pairing
```

The desktop entry point remains `redscribe_gpu.py`. Shared ASR adapters remain at the root pending a separate migration. Root benchmark modules alias the packaged implementations to preserve existing imports and mock targets; the Excel command-line entry point is retained. The UI output directory remains at repository root. This staged refactor does not change scoring rules, model selection or study methodology.

## Verification gate

Run `python -m compileall -q redscribe tests` and `python -m unittest discover -s tests -p "test_benchmark*.py" -v`. Then verify desktop launch, reference approval, single/batch execution, output paths and Excel regeneration on Windows. No merge until results are reviewed. This migration is not evidence of scientific validation.
