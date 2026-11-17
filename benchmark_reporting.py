"""Transparent reporting for short-audio verbatim ASR benchmarks.

Only completed runs with valid, nonnegative integer error counts contribute
to a score. Failed/not-run/cancelled attempts never become zero-error samples.
No filler, dialect, punctuation, case or whitespace normalisation is performed.
"""
from collections import Counter
import csv
import math
import os

from benchmark_metrics import ErrorCounts, corpus_counts, macro_rate

SUMMARY_FIELDS = (
    "cohort", "model_key", "recordings_total", "recordings_completed",
    "recordings_failed", "recordings_cancelled", "recordings_not_run",
    "recordings_unavailable", "word_scored", "character_scored",
    "word_substitutions", "word_deletions", "word_insertions", "reference_words",
    "char_substitutions", "char_deletions", "char_insertions", "reference_characters",
    "corpus_wer", "macro_wer", "corpus_cer", "macro_cer",
)
BREAKDOWN_FIELDS = (
    "audio", "audio_sha256", "model_key", "status", "word_substitutions",
    "word_deletions", "word_insertions", "reference_words", "wer",
    "char_substitutions", "char_deletions", "char_insertions",
    "reference_characters", "cer", "error",
)


def _counts(record, *, word):
    """Return counts only for a fully validated scored result.

    Existing legacy word S/D/I fields are accepted without re-scoring text.
    Character counts were introduced later and must be present explicitly.
    """
    if record.get("status") != "completed":
        return None
    if word:
        keys = (("word_substitutions", "substitutions"),
                ("word_deletions", "deletions"), ("word_insertions", "insertions"),
                ("reference_words",))
    else:
        keys = (("char_substitutions",), ("char_deletions",),
                ("char_insertions",), ("reference_characters",))
    values = []
    for alternatives in keys:
        value = next((record[k] for k in alternatives if record.get(k) is not None), None)
        if type(value) is not int or value < 0:
            return None
        values.append(value)
    if values[-1] == 0:
        return None
    count = ErrorCounts(*values)
    reported = record.get("wer" if word else "cer")
    if (reported is None or isinstance(reported, bool)
            or not isinstance(reported, (int, float))
            or not math.isfinite(reported)
            or not math.isclose(float(reported), count.rate, rel_tol=1e-8,
                                abs_tol=1e-8)):
        return None
    return count


def _model_record(item, model):
    return item.get("model_results", {}).get(model, {})


def _summarise(state, model, indices, cohort):
    counts = Counter()
    word_scores = []
    char_scores = []
    for index in indices:
        item = state["items"][index]
        record = _model_record(item, model)
        status = record.get("status")
        if not status:
            # A failed recording may never reach the model.
            status = "unavailable" if item.get("status") == "failed" else "not_run"
        if status not in ("completed", "failed", "cancelled", "not_run"):
            status = "unavailable"
        counts[status] += 1
        word = _counts(record, word=True)
        char = _counts(record, word=False)
        if word is not None:
            word_scores.append(word)
        if char is not None:
            char_scores.append(char)
    wc = corpus_counts(word_scores) if word_scores else None
    cc = corpus_counts(char_scores) if char_scores else None
    return {
        "cohort": cohort, "model_key": model,
        "recordings_total": len(indices),
        "recordings_completed": counts["completed"],
        "recordings_failed": counts["failed"],
        "recordings_cancelled": counts["cancelled"],
        "recordings_not_run": counts["not_run"],
        "recordings_unavailable": counts["unavailable"],
        "word_scored": len(word_scores), "character_scored": len(char_scores),
        "word_substitutions": wc.substitutions if wc else None,
        "word_deletions": wc.deletions if wc else None,
        "word_insertions": wc.insertions if wc else None,
        "reference_words": wc.reference_units if wc else None,
        "char_substitutions": cc.substitutions if cc else None,
        "char_deletions": cc.deletions if cc else None,
        "char_insertions": cc.insertions if cc else None,
        "reference_characters": cc.reference_units if cc else None,
        "corpus_wer": wc.rate if wc else None,
        "macro_wer": macro_rate(word_scores),
        "corpus_cer": cc.rate if cc else None,
        "macro_cer": macro_rate(char_scores),
    }


def build_summary(state):
    """Summarise all submitted audio, plus strictly common completed recordings.

    Returns fractional rates (e.g. 0.15 = 15%). 'common_completed' requires
    every selected model to have completed both word and character metrics.
    This does not imply every model had equivalent inference settings.
    """
    models = tuple(state["models"])
    items = state["items"]
    indices = list(range(len(items)))
    common = [
        i for i in indices
        if all(_counts(_model_record(items[i], model), word=True) is not None
               and _counts(_model_record(items[i], model), word=False) is not None
               for model in models)
    ]
    return [
        _summarise(state, model, subset, cohort)
        for cohort, subset in (("all_attempted", indices),
                               ("common_completed", common))
        for model in models
    ]


def build_error_breakdown(state):
    """Flat per-recording/per-model audit rows, including missing/failed cases."""
    rows = []
    for item in state["items"]:
        for model in state["models"]:
            record = _model_record(item, model)
            status = record.get("status") or (
                "unavailable" if item.get("status") == "failed" else "not_run")
            wc = _counts(record, word=True)
            cc = _counts(record, word=False)
            rows.append({
                "audio": item["audio"], "audio_sha256": item["audio_sha256"],
                "model_key": model, "status": status,
                "word_substitutions": wc.substitutions if wc else None,
                "word_deletions": wc.deletions if wc else None,
                "word_insertions": wc.insertions if wc else None,
                "reference_words": wc.reference_units if wc else None,
                "wer": wc.rate if wc else None,
                "char_substitutions": cc.substitutions if cc else None,
                "char_deletions": cc.deletions if cc else None,
                "char_insertions": cc.insertions if cc else None,
                "reference_characters": cc.reference_units if cc else None,
                "cer": cc.rate if cc else None,
                "error": record.get("error") or item.get("error", ""),
            })
    return rows


def _atomic_csv(path, fields, rows):
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def export_reporting(directory, state):
    """Export metadata-derived aggregates; does not need private source audio."""
    _atomic_csv(directory / "model_summary.csv", SUMMARY_FIELDS, build_summary(state))
    _atomic_csv(directory / "error_breakdown.csv", BREAKDOWN_FIELDS,
                build_error_breakdown(state))
