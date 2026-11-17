"""Raw benchmark metrics: no dialect normalisation, label stripping or DOCX parsing.

Scores are fractions (multiply by 100 for percentages). Empty references have
undefined rates (None). Edit alignment uses deterministic S > D > I ties.
For very long transcripts the O(N*M) allocation requires future optimisation.
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
    n, m = len(reference), len(hypothesis)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    operation = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0], operation[i][0] = i, "D"
    for j in range(1, m + 1):
        cost[0][j], operation[0][j] = j, "I"
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if reference[i - 1] == hypothesis[j - 1]:
                cost[i][j], operation[i][j] = cost[i - 1][j - 1], "M"
            else:
                candidates = (
                    (cost[i - 1][j - 1] + 1, "S"),
                    (cost[i - 1][j] + 1, "D"),
                    (cost[i][j - 1] + 1, "I"),
                )
                cost[i][j], operation[i][j] = min(candidates, key=lambda c: c[0])
    i, j = n, m
    s = d = ins = 0
    while i or j:
        action = operation[i][j]
        if action == "M":
            i -= 1
            j -= 1
        elif action == "S":
            s += 1
            i -= 1
            j -= 1
        elif action == "D":
            d += 1
            i -= 1
        elif action == "I":
            ins += 1
            j -= 1
        else:
            raise AssertionError("Invalid alignment")
    return ErrorCounts(s, d, ins, n)

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
