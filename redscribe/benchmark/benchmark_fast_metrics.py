"""Explicit RapidFuzz scoring policy for model-major experiments."""
from .benchmark_metrics import ErrorCounts

ENGINE = "rapidfuzz-levenshtein-editops-v1"

def edit_counts_fast(reference, hypothesis):
    from rapidfuzz.distance import Levenshtein
    counts = {"replace":0,"delete":0,"insert":0}
    for op in Levenshtein.editops(reference,hypothesis):
        counts[op.tag] += 1
    return ErrorCounts(counts["replace"],counts["delete"],counts["insert"],len(reference))

def raw_wer_fast(reference,hypothesis):
    return edit_counts_fast(reference.split(),hypothesis.split())

def raw_cer_fast(reference,hypothesis):
    return edit_counts_fast(reference,hypothesis)
