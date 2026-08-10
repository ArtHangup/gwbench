"""The bandwidth sweep.

Runs the same set of tasks at every capacity so the resulting curve reflects
capacity and nothing else. Task seeds are fixed per trial index rather than
drawn fresh, because comparing capacities on different tasks would confound the
one variable the experiment cares about.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol

from gwbench.architectures import RunResult


class Agent(Protocol):
    def run(self, task) -> RunResult: ...


@dataclass
class SweepPoint:
    capacity: Optional[int]
    mean_score: float
    n_trials: int
    scores: list[float] = field(default_factory=list)
    mean_broadcast_tokens: float = 0.0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.scores) if len(self.scores) > 1 else 0.0


def sweep(
    capacities: list[Optional[int]],
    agent_factory: Callable[[Optional[int]], Agent],
    task_factory: Callable[[int], object],
    n_trials: int,
    base_seed: int = 0,
) -> list[SweepPoint]:
    seeds = [base_seed + i for i in range(n_trials)]
    points: list[SweepPoint] = []

    for capacity in capacities:
        scores: list[float] = []
        tokens: list[int] = []

        for seed in seeds:
            task = task_factory(seed)
            result = agent_factory(capacity).run(task)
            scores.append(result.score)
            tokens.extend(result.broadcast_tokens)

        points.append(
            SweepPoint(
                capacity=capacity,
                mean_score=statistics.fmean(scores) if scores else 0.0,
                n_trials=n_trials,
                scores=scores,
                mean_broadcast_tokens=statistics.fmean(tokens) if tokens else 0.0,
            )
        )

    return points
