"""Post hoc directional revision analysis, anchored on oracle rows.

Oracles fix the right answers by construction: every oracle revision moves to
the correct option, and only after the defeating module's content clears the
workspace. If these functions do not recover that, they are wrong.
"""

from conflict.funded import serialize_trial
from conflict.posthoc import corrective_share, defeater_delivery_cycle, revision_timing
from conflict.scenarios import generate


def _gwt_rows(kind, n=10):
    from conflict.architectures import run_gwt

    rows = []
    for seed in range(n):
        scenario = generate(seed=seed, kind=kind)
        rows.append(serialize_trial(run_gwt(scenario), scenario))
    return rows


def test_oracle_single_defeater_revisions_are_all_corrective():
    # Cascade scenarios legitimately pass through an intermediate stance, so
    # the all-corrective anchor holds on single-defeater scenarios only.
    rows = [r for r in _gwt_rows("novel") if len(r["required_modules"]) == 3]
    share = corrective_share(rows)
    assert share["corrective"] == share["total"] > 0
    assert share["share"] == 1.0


def test_oracle_routine_has_no_revisions_to_share():
    share = corrective_share(_gwt_rows("routine"))
    assert share["total"] == 0
    assert share["share"] is None


def test_defeater_delivery_cycle_found_on_novel_rows():
    for row in _gwt_rows("novel", n=5):
        cycle = defeater_delivery_cycle(row)
        assert cycle is not None
        assert 0 <= cycle < len(row["occupancy"])


def test_oracle_corrective_revisions_all_land_after_delivery():
    timing = revision_timing(_gwt_rows("novel"))
    assert timing["corrective_after"] > 0
    assert timing["corrective_before"] == 0
    # Uniform-timing expectation is well below 1.0, so the concentration
    # statistic must exceed it for oracles.
    assert timing["observed_after_fraction"] == 1.0
    assert timing["expected_after_fraction"] < 1.0
    assert timing["binomial_p"] < 0.05
