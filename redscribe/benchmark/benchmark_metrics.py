"""Raw benchmark metrics: no dialect normalisation, label stripping or DOCX parsing.

Scores are fractions (multiply by 100 for percentages). Empty references have
undefined rates (None). Edit alignment uses deterministic S > D > I ties.
The dynamic-programming scorer uses linear working memory, but O(N*M) time.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ErrorCounts:
    substitutions: int
    deletions: int
    insertions: int
    reference_units: int

    @property
    def rate(self):
        if not self.reference_units:
            return None
        return (self.substitutions + self.deletions + self.insertions) / self.reference_units

    def as_dict(self):
        return {
            "substitutions": self.substitutions, "deletions": self.deletions,
            "insertions": self.insertions, "reference_units": self.reference_units,
            "rate": self.rate,
        }

def edit_counts(reference, hypothesis):
    """Count minimum-edit S/D/I with O(len(hypothesis)) working memory.

    Ties prefer substitution, then deletion, then insertion. This produces
    deterministic error totals but deliberately does not export alignment.
    """
    m = len(hypothesis)
    # (edit_distance, substitutions, deletions, insertions)
    previous = [(j, 0, 0, j) for j in range(m + 1)]
    for i, reference_unit in enumerate(reference, start=1):
        current = [(i, 0, i, 0)]
        for j, hypothesis_unit in enumerate(hypothesis, start=1):
            if reference_unit == hypothesis_unit:
                current.append(previous[j - 1])
                continue
            diag = previous[j - 1]
            delete = previous[j]
            insert = current[j - 1]
            candidates = (
                (diag[0] + 1, diag[1] + 1, diag[2], diag[3]),
                (delete[0] + 1, delete[1], delete[2] + 1, delete[3]),
                (insert[0] + 1, insert[1], insert[2], insert[3] + 1),
            )
            current.append(min(candidates, key=lambda x: x[0]))
        previous = current
    _, substitutions, deletions, insertions = previous[-1]
    return ErrorCounts(substitutions, deletions, insertions, len(reference))

def raw_wer(reference: str, hypothesis: str) -> ErrorCounts:
    """Whitespace tokenisation, case/punctuation preserved."""
    return edit_counts(reference.split(), hypothesis.split())

def raw_cer(reference: str, hypothesis: str) -> ErrorCounts:
    """Unicode code-point scoring, including spaces and punctuation."""
    return edit_counts(list(reference), list(hypothesis))

def corpus_counts(scores):
    return ErrorCounts(
        sum(s.substitutions for s in scores),
        sum(s.deletions for s in scores),
        sum(s.insertions for s in scores),
        sum(s.reference_units for s in scores),
    )

def macro_rate(scores):
    values = [s.rate for s in scores if s.rate is not None]
    return sum(values) / len(values) if values else None
