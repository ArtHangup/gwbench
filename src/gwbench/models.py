"""Model interface.

Every architecture talks to a model only through `Model.complete`, so the same
architecture can be driven by a real API or by a fake in tests. Keeping this
narrow is what makes the ladder comparable: no rung gets privileged access.
"""

from __future__ import annotations

import re

from typing import Protocol


class Model(Protocol):
    def complete(self, prompt: str) -> str: ...


class ScriptedModel:
    """Returns pre-set replies in order. For testing exact conversations."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self._replies:
            return ""
        return self._replies.pop(0)


class RecordingModel:
    """Always returns the same reply, but records every prompt it was given.

    Used to assert what an architecture actually put in front of the model,
    which is the thing that distinguishes one rung of the ladder from another.
    """

    def __init__(self, reply: str = "") -> None:
        self.reply = reply
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.reply


class EchoModuleModel:
    """A fake specialist that simply reports whatever it was given.

    Lets the harness be exercised end to end without an API key, so the
    bandwidth sweep can be validated on plumbing before any money is spent.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return prompt.strip().splitlines()[-1] if prompt.strip() else ""


class OracleSumModel:
    """A model that perfectly uses whatever information reaches it.

    Reads the container values present in its prompt, works out which ones the
    prompt asked for, and sums exactly those. It cannot answer about a container
    whose value never made it through the workspace.

    This is a measuring instrument, not a baseline. Its score is a readout of how
    much task-relevant information the capacity limit allowed through, which is
    what validates the sweep before real models are used.
    """

    _FACT = re.compile(r"The ([a-z]+ [a-z]+) contains (\d+)\.")
    _ASKED = re.compile(r"exactly these containers: ([^.]+)\.")

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)

        available = {
            phrase.replace(" ", "_"): int(value)
            for phrase, value in self._FACT.findall(prompt)
        }

        asked_match = self._ASKED.search(prompt)
        if not asked_match:
            return "unknown"
        asked = [name.strip() for name in asked_match.group(1).split(",")]

        if any(name not in available for name in asked):
            return "insufficient information"

        return str(sum(available[name] for name in asked))


class OracleThroughputModel:
    """Oracle for the throughput control family.

    Reads every "The X employs N people." fact present in the prompt and reports
    all of them. It cannot report a fact whose module never won a broadcast, so
    its score is the fraction of modules the capacity limit let through.

    Exists so the control family can be validated. Without it, a broken control
    task and a genuine "capacity hurts here" result look identical, and the
    control is the thing that keeps the headline result honest.
    """

    _FACT = re.compile(r"The (\w+) employs (\d+) people\.")

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        facts = self._FACT.findall(prompt)
        if not facts:
            return "no information available"
        return " ".join(f"The {name} employs {value}." for name, value in facts)
