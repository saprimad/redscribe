"""Compatibility entry point for redscribe.benchmark.benchmark_speech."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("redscribe.benchmark.benchmark_speech")
