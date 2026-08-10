"""Model-backed modules and controller for the funded run.

Same emit/decide contract as the oracles, driven by any gwbench Model (a
scripted fake in tests, a live model later). The prompt and response format
here are pinned by tests and quoted in PREREG.md; changing them after
preregistration is a protocol deviation.

Response format the module must produce:

    SAY: <one short statement to share> | URGENCY: <0.0 to 1.0>
    SAY: <optional second statement> | URGENCY: <0.0 to 1.0>
    RECOMMEND: <A, B, C, or NONE>

SAY lines become workspace proposals whose salience is the module's own
urgency rating (clamped to [0, 1]; malformed ratings fall back to 0.5; at
most two lines are kept). RECOMMEND becomes the stance statement the revision
DV is computed from. Malformed output degrades to an unformed stance, which
biases against the revision hypothesis, never toward it.
"""

from __future__ import annotations

import re

from conflict.modules import Decision, STANCE_SALIENCE
from conflict.parser import parse_decision
from conflict.scenarios import Scenario, Statement

MAX_SAY_LINES = 2
DEFAULT_URGENCY = 0.5

_SAY = re.compile(r"^\s*SAY:\s*(?P<text>.+?)\s*\|\s*URGENCY:\s*(?P<urgency>\S+)\s*$")
_RECOMMEND = re.compile(r"^\s*RECOMMEND:\s*(?P<option>\S+)\s*$", re.IGNORECASE)


def _clamp_urgency(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_URGENCY
    return max(0.0, min(1.0, value))


class ModelModule:
    def __init__(self, name: str, scenario: Scenario, model) -> None:
        self.name = name
        self.scenario = scenario
        self.model = model
        self._labels = tuple(option.label for option in scenario.options)

    def _prompt(self, visible: list[Statement]) -> str:
        private = "\n".join(f"- {s.text}" for s in self.scenario.evidence[self.name])
        parts = [
            f"You are the {self.name} specialist on a team deciding the following.",
            self.scenario.prompt,
            "Your private knowledge (only you know this):",
            private,
        ]
        if visible:
            broadcast = "\n".join(f"[{s.module}] {s.text}" for s in visible)
            parts += ["Broadcast so far (shared with the whole team):", broadcast]
        parts += [
            "Reply in exactly this format, nothing else:",
            "SAY: <one short statement to share> | URGENCY: <0.0 to 1.0>",
            "SAY: <optional second statement> | URGENCY: <0.0 to 1.0>",
            "RECOMMEND: <A, B, C, or NONE if you cannot pick yet>",
        ]
        return "\n\n".join(parts)

    def emit(self, visible: list[Statement]) -> list[Statement]:
        reply = self.model.complete(self._prompt(visible))

        statements: list[Statement] = []
        stance: str | None = None
        for line in reply.splitlines():
            say = _SAY.match(line)
            if say and len(statements) < MAX_SAY_LINES:
                statements.append(
                    Statement(
                        module=self.name,
                        text=say.group("text"),
                        payload={"kind": "model"},
                        salience=_clamp_urgency(say.group("urgency")),
                    )
                )
                continue
            recommend = _RECOMMEND.match(line)
            if recommend:
                option = recommend.group("option").upper().strip(".")
                if option in self._labels:
                    stance = option

        if stance is None:
            text = f"{self.name} has no basis to recommend an option yet."
        else:
            text = f"{self.name} recommends option {stance}."
        statements.append(
            Statement(
                module=self.name,
                text=text,
                payload={"kind": "stance", "option": stance},
                salience=STANCE_SALIENCE,
            )
        )
        return statements


class ModelController:
    def __init__(self, scenario: Scenario, model) -> None:
        self.scenario = scenario
        self.model = model
        self._labels = tuple(option.label for option in scenario.options)

    def decide(self, visible: list[Statement]) -> Decision:
        broadcast = "\n".join(f"[{s.module}] {s.text}" for s in visible)
        prompt = "\n\n".join(
            [
                "You are the deciding controller.",
                self.scenario.prompt,
                "Information that reached you:",
                broadcast if broadcast else "(nothing reached you)",
                'Reply with one line: "Decision: option <letter>." plus one sentence of reasoning.',
            ]
        )
        reply = self.model.complete(prompt)
        option = parse_decision(reply, self.scenario.options)
        if option is None:
            option = self._labels[0]
        return Decision(option=option, text=reply)
