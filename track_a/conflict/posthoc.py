"""Post hoc directional revision analysis (NOT preregistered; label it so).

The preregistered trial-level indicator asked only "did any stance change".
These functions ask the sharper questions the reviewers will: of the
revisions that happened, how many moved TO the correct option (corrective
share), and in novel trials, do corrective revisions concentrate after the
defeating module's content first clears the workspace?

Timing convention: a stance recorded at cycle c was formed after seeing
broadcasts through cycle c-1, so a delivery at occupancy index d can first
influence stances at cycle d+1. "After" therefore means revision.cycle >= d+1.
"""

from __future__ import annotations

from math import comb
from typing import Optional

ALWAYS_REQUIRED = {"perception", "goals"}


def corrective_share(rows: list[dict]) -> dict:
    total = corrective = 0
    for row in rows:
        for revision in row["revisions"]:
            total += 1
            if revision["new"] == row["correct_option"]:
                corrective += 1
    return {
        "total": total,
        "corrective": corrective,
        "share": corrective / total if total else None,
    }


def defeater_delivery_cycle(row: dict) -> Optional[int]:
    """First occupancy index where a defeating module lands real content."""
    defeating = set(row["required_modules"]) - ALWAYS_REQUIRED
    if not defeating:
        return None
    for index, cycle in enumerate(row["occupancy"]):
        for source, kind, _text in cycle:
            if kind != "stance" and source in defeating:
                return index
    return None


def revision_timing(rows: list[dict]) -> dict:
    """Do corrective revisions concentrate after defeater delivery?

    Pooled binomial test: each corrective revision in a trial with a known
    delivery cycle counts as one draw; under uniform timing it lands "after"
    with probability equal to that trial's fraction of eligible cycles after
    delivery. The pooled expectation is the mean of those fractions weighted
    by each trial's corrective count; the test is one-sided (concentration).
    """
    after = before = 0
    expected_fractions: list[float] = []
    for row in rows:
        delivery = defeater_delivery_cycle(row)
        if delivery is None:
            continue
        n_cycles = max(len(h) for h in row["stance_history"].values())
        # Revisions are possible at cycles 1..n_cycles-1; those at
        # delivery+1 or later could have seen the delivered content.
        eligible = n_cycles - 1
        after_slots = max(0, n_cycles - 1 - delivery)
        for revision in row["revisions"]:
            if revision["new"] != row["correct_option"]:
                continue
            expected_fractions.append(after_slots / eligible if eligible else 0.0)
            if revision["cycle"] >= delivery + 1:
                after += 1
            else:
                before += 1

    total = after + before
    if total == 0:
        return {
            "corrective_after": 0,
            "corrective_before": 0,
            "observed_after_fraction": None,
            "expected_after_fraction": None,
            "binomial_p": None,
        }

    expected = sum(expected_fractions) / total
    # One-sided binomial upper tail at the pooled expectation.
    p = sum(
        comb(total, k) * expected**k * (1 - expected) ** (total - k)
        for k in range(after, total + 1)
    )
    return {
        "corrective_after": after,
        "corrective_before": before,
        "observed_after_fraction": after / total,
        "expected_after_fraction": expected,
        "binomial_p": min(1.0, p),
    }
