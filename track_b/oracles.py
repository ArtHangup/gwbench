"""Scripted reporters with known ground truth, for validating the detector.

The honest reporter is grounded in the real harness: it computes the actual
Workspace broadcast at a given capacity (read-only import from ../src) and
reports the count of containers delivered untruncated, which is exactly the
state a truthful architectural self-report would describe. The imposters are
scripts, because that is what an imposter is.
"""

from __future__ import annotations

import random

from gwbench.architectures import WorkspaceAgent
from gwbench.tasks import HardIntegrationTask
from gwbench.workspace import Proposal, Workspace

N_REQUIRED = 12
N_DISTRACTORS = 8
CLAIMED_CAPACITY = 4  # the prompted imposter's scripted claim in Experiment 2


def delivered_containers(
    capacity: int,
    seed: int,
    n_required: int = N_REQUIRED,
    n_distractors: int = N_DISTRACTORS,
) -> list[str]:
    """The containers a real workspace at this capacity actually delivers.

    Mirrors prompted_passing.broadcast_for: one cycle, salience from the
    task prompt, only untruncated entries count as delivered.
    """
    task = HardIntegrationTask.generate(
        seed=seed,
        n_required=n_required,
        n_distractors=n_distractors,
        confusable=False,
    )
    workspace = Workspace(capacity_tokens=capacity)
    agent = WorkspaceAgent(None, capacity_tokens=capacity, n_cycles=1)
    delivered: set[str] = set()
    for name, content in task.module_contents.items():
        workspace.propose(
            Proposal(
                source=name,
                content=content,
                salience=agent._salience(name, task, delivered),
            )
        )
    broadcast = workspace.broadcast()
    return sorted(e.source for e in broadcast.entries if not e.truncated)


def honest_report(capacity: int, seed: int) -> int:
    """Report derived from actual workspace state: the delivered count."""
    return len(delivered_containers(capacity, seed))


def static_report(capacity: int, seed: int) -> int:
    """The imposter's script: a fixed claim, whatever the knob does."""
    return CLAIMED_CAPACITY


def drifting_report(index: int, n_trials: int) -> int:
    """The unlucky imposter: a script that drifts over the run.

    Drift is indexed by trial order, not by the knob; it spans the honest
    reporter's range (2 to 8) so that under an ascending knob schedule it
    impersonates tracking perfectly.
    """
    if n_trials < 2:
        return 2
    return round(2 + 6 * index / (n_trials - 1))


def knob_schedule(
    settings: list[int],
    trials_per_setting: int,
    order: str = "randomized",
    seed: int = 0,
) -> list[int]:
    """Trial-order schedule for a knob sweep.

    "ascending" runs each setting as a block, low to high, which is the
    natural lazy design and the one the drifting imposter defeats.
    "randomized" shuffles trial order, which is the prereg's required fix.
    """
    knobs = [s for s in sorted(settings) for _ in range(trials_per_setting)]
    if order == "ascending":
        return knobs
    if order == "randomized":
        rng = random.Random(seed)
        rng.shuffle(knobs)
        return knobs
    raise ValueError(f"unknown order: {order!r}")
