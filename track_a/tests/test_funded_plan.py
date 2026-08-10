"""The funded-run plan: battery construction, cost arithmetic, serialization.

All offline. The live path is exercised only by flag-gating logic; no test
here constructs an API client.
"""

import json

from conflict.funded import (
    CALLS_PER_SCENARIO,
    SEED_BASE,
    battery,
    estimate,
    serialize_trial,
)
from conflict.scenarios import DOMAINS, generate


def test_battery_is_stratified_and_deterministic():
    scenarios = battery(n_per_cell=8)
    assert len(scenarios) == 8 * 2  # n per kind cell, both kinds
    assert scenarios == battery(n_per_cell=8)
    for domain in DOMAINS:
        for kind in ("routine", "novel"):
            matching = [s for s in scenarios if s.domain == domain and s.kind == kind]
            assert len(matching) == 2, (domain, kind)


def test_battery_seeds_do_not_collide_with_validation_seeds():
    # Validation used seeds 0..n_per_cell per cell; the funded battery lives
    # in its own seed range so no scenario is reused across phases.
    assert all(s.seed >= SEED_BASE for s in battery(n_per_cell=4))


def test_estimate_arithmetic():
    plan = estimate(n_per_cell=72)
    assert plan["n_scenarios"] == 144
    assert plan["total_calls"] == 144 * CALLS_PER_SCENARIO
    assert plan["cost_usd"] < 25.0
    assert plan["cost_usd"] > 5.0
    assert plan["call_cap"] > plan["total_calls"]


def test_serialized_trial_is_json_round_trippable():
    from conflict.architectures import run_gwt

    scenario = generate(seed=SEED_BASE, domain="routing", kind="novel")
    trial = run_gwt(scenario)
    row = serialize_trial(trial, scenario)
    parsed = json.loads(json.dumps(row))
    assert parsed["architecture"] == "gwt"
    assert parsed["seed"] == scenario.seed
    assert parsed["kind"] == "novel"
    assert parsed["correct_option"] == scenario.correct_option
    assert parsed["decision_text"]
    assert "stance_history" in parsed
    assert "occupancy" in parsed
    assert parsed["required_modules"] == sorted(scenario.required_modules)
