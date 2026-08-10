"""Funded-run plan: battery, cost estimate, trial serialization, execution.

Everything here except run_battery's live model is offline and tested. The
numbers (calls per scenario, token estimates, Haiku prices) feed both the dry
run printout and PREREG.md; keep them in one place so they cannot drift apart.
"""

from __future__ import annotations

from typing import Optional

from conflict.architectures import (
    DEFAULT_CAPACITY,
    DEFAULT_CYCLES,
    TrialResult,
    run_flat,
    run_gwt,
    run_hub,
)
from conflict.scenarios import DOMAINS, Scenario, generate

# Seeds for the funded battery live far above the validation battery's range
# so no scenario is shared between pipeline validation and the experiment.
SEED_BASE = 10_000

# Per scenario: A and B each run DEFAULT_CYCLES x 5 module calls + 1
# controller; C runs 5 module calls + 1 controller.
CALLS_PER_ARCH_LOOP = DEFAULT_CYCLES * 5 + 1
CALLS_PER_SCENARIO = 2 * CALLS_PER_ARCH_LOOP + 6

# Working token estimates for Haiku-sized prompts in this design.
EST_INPUT_TOKENS_PER_CALL = 700
EST_OUTPUT_TOKENS_PER_CALL = 120

# claude-haiku-4-5 prices, USD per million tokens (claude-api skill, cached
# 2026-06-24; re-check before authorizing spend).
HAIKU_INPUT_PER_MTOK = 1.00
HAIKU_OUTPUT_PER_MTOK = 5.00
FUNDED_MODEL = "claude-haiku-4-5-20251001"

CALL_CAP_HEADROOM = 1.1  # retries for malformed output, nothing more


def battery(n_per_cell: int) -> list[Scenario]:
    """The funded scenario set: n per (kind) cell, stratified over domains.

    n_per_cell must be divisible by len(DOMAINS) for exact stratification;
    remainders spill deterministically across domains in order.
    """
    scenarios: list[Scenario] = []
    seed = SEED_BASE
    for kind in ("routine", "novel"):
        for index in range(n_per_cell):
            domain = DOMAINS[index % len(DOMAINS)]
            scenarios.append(generate(seed=seed, domain=domain, kind=kind))
            seed += 1
    return scenarios


def estimate(n_per_cell: int) -> dict:
    n_scenarios = 2 * n_per_cell
    total_calls = n_scenarios * CALLS_PER_SCENARIO
    input_tokens = total_calls * EST_INPUT_TOKENS_PER_CALL
    output_tokens = total_calls * EST_OUTPUT_TOKENS_PER_CALL
    cost = (
        input_tokens / 1_000_000 * HAIKU_INPUT_PER_MTOK
        + output_tokens / 1_000_000 * HAIKU_OUTPUT_PER_MTOK
    )
    return {
        "model": FUNDED_MODEL,
        "n_per_cell": n_per_cell,
        "n_scenarios": n_scenarios,
        "calls_per_scenario": CALLS_PER_SCENARIO,
        "total_calls": total_calls,
        "est_input_tokens": input_tokens,
        "est_output_tokens": output_tokens,
        "cost_usd": round(cost, 2),
        "call_cap": int(total_calls * CALL_CAP_HEADROOM),
        "capacity_tokens": DEFAULT_CAPACITY,
        "n_cycles": DEFAULT_CYCLES,
    }


def serialize_trial(trial: TrialResult, scenario: Scenario) -> dict:
    return {
        "architecture": trial.architecture,
        "seed": scenario.seed,
        "domain": scenario.domain,
        "kind": trial.kind,
        "correct_option": scenario.correct_option,
        "required_modules": sorted(scenario.required_modules),
        # The runner's operational option (with its abstain-to-A fallback) is
        # recorded, but the accuracy DV is graded from decision_text by the
        # GRADING.md pipeline, never from this field.
        "runner_option": trial.decision.option,
        "decision_text": trial.decision.text,
        "occupancy": [
            [[source, kind_, text] for source, kind_, text in cycle]
            for cycle in trial.occupancy
        ],
        "stance_history": trial.stance_history,
        "revisions": trial.revisions,
        "formations": trial.formations,
        "module_emits": trial.module_emits,
    }


def run_battery(
    scenarios: list[Scenario],
    model,
    checkpoint=None,
    controller_model=None,
) -> list[dict]:
    """Run every scenario through A, B, C with model-backed modules.

    `model` is anything satisfying gwbench's Model protocol; the live run
    passes an AnthropicModel with a disk cache and a hard call cap, so an
    interrupted run resumes for free. `checkpoint`, if given, is called with
    the accumulated rows after every scenario.
    """
    from conflict.model_modules import ModelController, ModelModule

    controller_model = controller_model or model

    def module_factory(name: str, scenario: Scenario):
        return ModelModule(name, scenario, model)

    def controller_factory(scenario: Scenario):
        return ModelController(scenario, controller_model)

    rows: list[dict] = []
    for scenario in scenarios:
        for runner in (run_gwt, run_hub, run_flat):
            trial = runner(
                scenario,
                module_factory=module_factory,
                controller_factory=controller_factory,
            )
            rows.append(serialize_trial(trial, scenario))
        if checkpoint is not None:
            checkpoint(rows)
    return rows
