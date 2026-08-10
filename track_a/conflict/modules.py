"""Scripted oracle modules and the oracle controller.

Zero API calls: these are deterministic stand-ins that implement the module
contract perfectly, so the offline validation can show the three architectures
separate on the dependent variables by construction.

An oracle module emits its private evidence plus one stance statement: the
recommendation the reference rule yields from (own evidence + broadcast
statements it has seen). A module that sees nothing new can never move its
stance; a module shown a decisive broadcast must. Set revises=False to get a
stubborn variant whose stance freezes after first forming, for negative
controls on the revision metric.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from conflict.scenarios import Scenario, Statement, reference_decide

STANCE_SALIENCE = 0.5


class OracleModule:
    def __init__(self, name: str, scenario: Scenario, revises: bool = True) -> None:
        self.name = name
        self.scenario = scenario
        self.revises = revises
        self._private = list(scenario.evidence[name])
        self._labels = tuple(option.label for option in scenario.options)
        self._last_stance: Optional[str] = None

    def emit(self, visible: list[Statement]) -> list[Statement]:
        """One cycle's output: private statements plus the current stance."""
        stance = reference_decide(self._labels, self._private + list(visible))
        if not self.revises and self._last_stance is not None:
            stance = self._last_stance
        self._last_stance = stance

        if stance is None:
            text = f"{self.name} has no basis to recommend an option yet."
        else:
            text = f"{self.name} recommends option {stance}."

        stance_statement = Statement(
            module=self.name,
            text=text,
            payload={"kind": "stance", "option": stance},
            salience=STANCE_SALIENCE,
        )
        return self._private + [stance_statement]


@dataclass(frozen=True)
class Decision:
    option: str
    text: str


class OracleController:
    """Decides from whatever statements reached it, and only those.

    Preference order: the reference rule on the evidence payloads; failing
    that, majority among visible stances (earliest option label breaks ties);
    failing that, option A. The fallbacks are what give graded decision
    quality when capacity or cycle count starves the controller.
    """

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self._labels = tuple(option.label for option in scenario.options)

    def decide(self, visible: list[Statement]) -> Decision:
        option = reference_decide(self._labels, list(visible))
        basis = "the directive after removing blocked options"

        if option is None:
            latest: dict[str, Optional[str]] = {}
            for s in visible:
                if s.payload["kind"] == "stance":
                    latest[s.module] = s.payload["option"]
            votes = Counter(v for v in latest.values() if v is not None)
            if votes:
                top = max(votes.values())
                option = min(label for label, n in votes.items() if n == top)
                basis = "the balance of module recommendations"

        if option is None:
            option = self._labels[0]
            basis = "default order, the evidence available settled nothing"

        return Decision(
            option=option,
            text=f"Decision: option {option}, on {basis}.",
        )
