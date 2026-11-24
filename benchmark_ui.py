"""Compatibility entry point for redscribe.ui.benchmark_ui."""
import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("redscribe.ui.benchmark_ui")
