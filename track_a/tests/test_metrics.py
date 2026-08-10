"""Dependent-variable definitions.

These are the quantities the funded run reports, so their definitions live in
one place and are pinned here against the oracle architectures, whose values
are known by construction.
"""

from conflict.architectures import run_flat, run_gwt, run_hub
from conflict.metrics import (
    conflict_resolved,
    floor_waste,
    recruitment_latency,
    revision_rate,
    summarize,
)
from conflict.scenarios import generate

NOVEL = [generate(seed=n, kind="novel") for n in range(8)]
ROUTINE = [generate(seed=n, kind="routine") for n in range(8)]


def test_revision_rate_positive_for_gwt_on_novel_zero_for_hub_and_flat():
    for s in NOVEL:
        assert revision_rate(run_gwt(s)) > 0.0, s.seed
        assert revision_rate(run_hub(s)) == 0.0, s.seed
        assert revision_rate(run_flat(s)) == 0.0, s.seed


def test_revision_rate_zero_for_gwt_on_routine():
    for s in ROUTINE:
        assert revision_rate(run_gwt(s)) == 0.0, s.seed


def test_conflict_resolved_only_where_broadcast_returns():
    for s in NOVEL:
        assert conflict_resolved(run_gwt(s)), s.seed
        assert not conflict_resolved(run_hub(s)), s.seed


def test_recruitment_latency_is_finite_for_gwt_and_orderly():
    for s in NOVEL:
        trial = run_gwt(s)
        latency = recruitment_latency(trial, s.required_modules)
        assert latency is not None, s.seed
        assert latency < len(trial.occupancy), s.seed
        # Orderly recruitment: no floor wasted on repeats before coverage.
        assert floor_waste(trial, s.required_modules) == 0, s.seed


def test_recruitment_latency_is_none_for_flat():
    trial = run_flat(NOVEL[0])
    assert recruitment_latency(trial, NOVEL[0].required_modules) is None


def test_summarize_groups_by_architecture_and_kind():
    trials = (
        [run_gwt(s) for s in NOVEL]
        + [run_gwt(s) for s in ROUTINE]
        + [run_hub(s) for s in NOVEL]
    )
    table = summarize(trials)
    gwt_novel = table[("gwt", "novel")]
    assert gwt_novel["n"] == len(NOVEL)
    assert gwt_novel["accuracy"] == 1.0
    assert gwt_novel["revision_rate"] > 0.0
    assert gwt_novel["resolved"] == 1.0
    assert table[("gwt", "routine")]["revision_rate"] == 0.0
    assert table[("hub", "novel")]["revision_rate"] == 0.0
    assert table[("hub", "novel")]["resolved"] == 0.0
