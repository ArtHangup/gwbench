"""Dependent variables, defined once.

Priority order per the design: (1) revision after broadcast, (2) recruitment
sequences, (3) decision quality. The first two are not accuracy, so a model
that finds the task easy cannot erase them.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from conflict.architectures import TrialResult


def revision_rate(trial: TrialResult) -> float:
    """Stance changes between formed stances, per module-cycle opportunity."""
    cycles = max((len(h) for h in trial.stance_history.values()), default=0)
    if cycles <= 1:
        return 0.0
    opportunities = len(trial.stance_history) * (cycles - 1)
    return len(trial.revisions) / opportunities


def conflict_resolved(trial: TrialResult) -> bool:
    """Did every module end the trial backing the correct option?"""
    return all(
        stances and stances[-1] == trial.correct_option
        for stances in trial.stance_history.values()
    )


def recruitment_latency(
    trial: TrialResult, required_modules: frozenset[str]
) -> Optional[int]:
    """First cycle by which every required module had delivered real content.

    None when coverage never completes, including architecture C, which has
    no workspace and therefore no recruitment at all.
    """
    delivered: set[str] = set()
    for index, cycle in enumerate(trial.occupancy):
        for source, kind, _text in cycle:
            if kind != "stance":
                delivered.add(source)
        if set(required_modules) <= delivered:
            return index
    return None


def floor_waste(trial: TrialResult, required_modules: frozenset[str]) -> int:
    """Broadcast slots spent re-delivering old content before coverage.

    Orderly recruitment wastes nothing; a thrashing workspace re-broadcasts
    what it already said while required specialists still wait.
    """
    horizon = recruitment_latency(trial, required_modules)
    if horizon is None:
        horizon = len(trial.occupancy) - 1
    seen: set[tuple[str, str]] = set()
    waste = 0
    for cycle in trial.occupancy[: horizon + 1]:
        for source, kind, text in cycle:
            if kind == "stance":
                continue
            if (source, text) in seen:
                waste += 1
            seen.add((source, text))
    return waste


def summarize(trials: list[TrialResult]) -> dict[tuple[str, str], dict]:
    """Per (architecture, kind): the battery-level readout."""
    grouped: dict[tuple[str, str], list[TrialResult]] = defaultdict(list)
    for trial in trials:
        grouped[(trial.architecture, trial.kind)].append(trial)

    table: dict[tuple[str, str], dict] = {}
    for key, bucket in grouped.items():
        n = len(bucket)
        table[key] = {
            "n": n,
            "accuracy": sum(t.correct for t in bucket) / n,
            "revision_rate": sum(revision_rate(t) for t in bucket) / n,
            "formations": sum(len(t.formations) for t in bucket) / n,
            "resolved": sum(conflict_resolved(t) for t in bucket) / n,
        }
    return table
