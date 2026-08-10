"""An attention schema: a model of the system's own attention.

Two properties make this a schema rather than a log, and AST-1 asks for both:

  predictive - it commits to what it expects to be attended before the
               competition runs, and can turn out to be wrong.
  controlling - what it got wrong feeds back as a salience bias on the next
               cycle, so the model of attention actually steers attention.

The schema is deliberately simplified relative to the true attentional state.
That is the point of Graziano's account: a schema is a useful caricature, not
an accurate readout. Here the caricature is that it ranks by unperturbed
salience while the real competition is perturbed by noise.
"""

from __future__ import annotations

from typing import Optional


class AttentionSchema:
    def __init__(self, expected_winners: int = 1) -> None:
        self.expected_winners = expected_winners
        self.predicted: set[str] = set()
        self.attended: set[str] = set()
        self.missed: set[str] = set()
        self._hits: list[float] = []

    def expect(self, salience_by_source: dict[str, float]) -> None:
        ranked = sorted(salience_by_source.items(), key=lambda kv: (-kv[1], kv[0]))
        self.predicted = {name for name, _ in ranked[: self.expected_winners]}

    def observe(self, attended: set[str]) -> None:
        self.attended = set(attended)
        self.missed = self.predicted - self.attended

        if self.predicted:
            overlap = len(self.predicted & self.attended) / len(self.predicted)
        else:
            overlap = 1.0
        self._hits.append(overlap)

    @property
    def accuracy(self) -> Optional[float]:
        if not self._hits:
            return None
        return sum(self._hits) / len(self._hits)

    def bias(self, source: str) -> float:
        """Control: push harder for something expected but not received."""
        return 0.4 if source in self.missed else 0.0

    def summary(self) -> str:
        attending = ", ".join(sorted(self.attended)) or "nothing"
        text = f"Your attention is currently on: {attending}."
        if self.missed:
            missed = ", ".join(sorted(self.missed))
            text += f" You expected but did not receive: {missed}."
        return text
