"""Compatibility entry point for redscribe.benchmark.benchmark_excel."""
import importlib as _importlib
import sys as _sys

if __name__ == "__main__":
    import runpy as _runpy
    _runpy.run_module("redscribe.benchmark.benchmark_excel", run_name="__main__")
else:
    _sys.modules[__name__] = _importlib.import_module("redscribe.benchmark.benchmark_excel")
