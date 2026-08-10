"""The capacity invariant, checked across the full sweep range.

The experiment varies capacity from 0 upward and reads performance off the curve.
A leak at any single capacity value would show up as a spurious result at exactly
one point on that curve, which is the hardest kind of bug to notice in a plot.
"""

import random

import pytest

from gwbench.workspace import Proposal, Workspace

CAPACITIES = list(range(0, 65))


def random_proposals(rng: random.Random, n: int) -> list[Proposal]:
    return [
        Proposal(
            source=f"mod{i}",
            content=" ".join(f"tok{j}" for j in range(rng.randint(0, 40))),
            salience=rng.random(),
        )
        for i in range(n)
    ]


@pytest.mark.parametrize("capacity", CAPACITIES)
def test_broadcast_respects_capacity_for_every_capacity(capacity):
    rng = random.Random(capacity)
    ws = Workspace(capacity_tokens=capacity)
    for p in random_proposals(rng, n=8):
        ws.propose(p)

    broadcast = ws.broadcast()

    assert broadcast.token_count <= capacity


@pytest.mark.parametrize("capacity", CAPACITIES)
def test_reported_token_count_matches_actual_broadcast_content(capacity):
    """token_count is what the analysis trusts, so it must not drift from reality."""
    rng = random.Random(1000 + capacity)
    ws = Workspace(capacity_tokens=capacity)
    for p in random_proposals(rng, n=8):
        ws.propose(p)

    broadcast = ws.broadcast()
    actual = sum(len(e.content.split()) for e in broadcast.entries)

    assert broadcast.token_count == actual


@pytest.mark.parametrize("capacity", CAPACITIES)
def test_every_proposal_is_either_broadcast_or_rejected(capacity):
    """Nothing may vanish silently: accounting must be complete."""
    rng = random.Random(2000 + capacity)
    proposals = random_proposals(rng, n=8)
    ws = Workspace(capacity_tokens=capacity)
    for p in proposals:
        ws.propose(p)

    broadcast = ws.broadcast()
    accounted = {e.source for e in broadcast.entries} | {
        p.source for p in broadcast.rejected
    }

    assert accounted == {p.source for p in proposals}


def test_capacity_zero_and_unlimited_bracket_the_sweep():
    rng = random.Random(99)
    proposals = random_proposals(rng, n=8)
    total = sum(len(p.content.split()) for p in proposals)

    def run(capacity):
        ws = Workspace(capacity_tokens=capacity)
        for p in proposals:
            ws.propose(p)
        return ws.broadcast().token_count

    assert run(0) == 0
    assert run(None) == total
