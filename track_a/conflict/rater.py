"""Rater-assigned salience: the alternative answer to "who computes salience".

Wraps any module. SAY statements keep their text and payload; their salience
is replaced by a separate relevance rater's score. The rater sees only the
decision question and the statement text: no private evidence, no ground
truth, no speaker identity. Pinned by PREREG_SALIENCE.md.
"""

from __future__ import annotations

import re
from dataclasses import replace

from conflict.scenarios import Statement

DEFAULT_RATING = 0.5
_NUMBER = re.compile(r"\d*\.?\d+")

RATER_PROMPT = """A team must decide the following.

{prompt}

One specialist wants to share this statement with the whole team:

{text}

How urgent is it that the whole team hears this statement now? Reply with
only a number from 0.0 to 1.0."""


def _parse_rating(reply: str) -> float:
    """First number anywhere in the reply; models often preface the value."""
    match = _NUMBER.search(reply)
    if match is None:
        return DEFAULT_RATING
    return max(0.0, min(1.0, float(match.group(0))))


class RaterModule:
    def __init__(self, inner, rater_model) -> None:
        self.inner = inner
        self.rater = rater_model
        self.name = inner.name
        self.scenario = inner.scenario

    def emit(self, visible: list[Statement]) -> list[Statement]:
        statements = self.inner.emit(visible)
        rated: list[Statement] = []
        for statement in statements:
            if statement.payload["kind"] != "model":
                rated.append(statement)
                continue
            reply = self.rater.complete(
                RATER_PROMPT.format(
                    prompt=self.scenario.prompt, text=statement.text
                )
            )
            rated.append(replace(statement, salience=_parse_rating(reply)))
        return rated
