"""Preregistered analysis, tested offline against oracle-generated rows and
known statistical values before any funded data is looked at."""

from math import comb

from conflict.analysis import (
    analyze,
    fisher_exact,
    mcnemar_exact,
    two_proportion,
)
from conflict.funded import serialize_trial
from conflict.scenarios import generate


def test_mcnemar_exact_known_value():
    # b=8, c=2: p = 2 * sum_{k>=8} C(10,k) / 2^10 = 112/1024
    assert abs(mcnemar_exact(8, 2) - 112 / 1024) < 1e-12
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0


def test_fisher_exact_known_value():
    # The maximally separated 2x2 table: only the two extreme tables count.
    expected = 2 * comb(10, 10) * comb(10, 0) / comb(20, 10)
    assert abs(fisher_exact(10, 0, 0, 10) - expected) < 1e-12
    assert fisher_exact(5, 5, 5, 5) == 1.0


def test_two_proportion_behaves():
    same = two_proportion(36, 72, 36, 72)
    assert same["p"] > 0.99
    strong = two_proportion(60, 72, 5, 72)
    assert strong["p"] < 1e-6
    assert strong["ci_low"] > 0
    assert 0 <= strong["ci_low"] <= strong["ci_high"] <= 1


def _oracle_rows(n_seeds=10):
    from conflict.architectures import run_flat, run_gwt, run_hub

    rows = []
    for seed in range(n_seeds):
        for kind in ("routine", "novel"):
            scenario = generate(seed=seed, kind=kind)
            for runner in (run_gwt, run_hub, run_flat):
                rows.append(serialize_trial(runner(scenario), scenario))
    return rows


def test_analyze_on_oracle_rows_recovers_the_validation_signatures():
    report = analyze(_oracle_rows())
    h1 = report["h1"]
    # Oracles: every A-novel trial revises, no A-routine or B-novel trial does.
    assert h1["a_novel"]["rate"] == 1.0
    assert h1["a_routine"]["rate"] == 0.0
    assert h1["b_novel"]["rate"] == 0.0
    assert h1["contrast_a"]["p"] < 0.01
    assert h1["contrast_b"]["p"] < 0.01

    h2 = report["h2"]
    assert h2["novel"]["coverage_rate"] == 1.0
    assert h2["novel"]["total_floor_waste"] == 0
    assert h2["novel"]["median_latency"] is not None

    h3 = report["h3"]
    # Oracle decisions parse cleanly and are always correct: no discordance.
    assert h3["graded"] == report["n_scenarios_novel"] * 3
    assert h3["abstentions"] == 0
    assert h3["a_vs_c"]["accuracy_a"] == 1.0
    assert h3["a_vs_c"]["p"] == 1.0


def test_analyze_report_is_json_serializable():
    import json

    json.dumps(analyze(_oracle_rows(n_seeds=4)))
