"""Offline validation of the preregistered perturbation runner.

The runner may not spend in this session, so every test injects scripted
models: an honest one that derives its report from the context it is shown,
and a static one that answers from a fixed script. If the pipeline is right,
the covariance detector must separate them end to end with zero API calls.
"""

import pytest

from covariance import analyze
from perturbation import (
    AST_NOISES,
    GWT_CAPACITIES,
    N_PER_CELL,
    build_ast_context,
    build_gwt_context,
    make_plan,
    run_gwt_arm,
    run_ast_arm,
)


class HonestModel:
    """Reports exactly the container names present in its context block."""

    def complete(self, prompt: str) -> str:
        lines = [l for l in prompt.splitlines() if l.startswith("[")]
        names = [l.split("]")[0][1:] for l in lines]
        if "expect to attend to but did not receive" in prompt:
            missed = [l for l in prompt.splitlines()
                      if "expected but did not receive" in l]
            return missed[0] if missed else "I missed nothing."
        return "Currently holding: " + ", ".join(names)


class StaticModel:
    """The imposter's script: the same four claims, whatever the input."""

    def complete(self, prompt: str) -> str:
        if "expect to attend to but did not receive" in prompt:
            return "I received everything I expected."
        return "My workspace holds red_box, blue_crate, green_jar, black_pail."


class TestPlan:
    def test_plan_is_within_budget(self):
        plan = make_plan()
        assert plan.est_cost_usd < 20.0
        assert plan.total_calls == (
            len(GWT_CAPACITIES) * 3 * N_PER_CELL
            + len(AST_NOISES) * 2 * N_PER_CELL
        )

    def test_trial_order_is_randomized_not_blocked(self):
        # The unlucky-imposter lesson: an ascending schedule turns script
        # drift into a false positive, so the plan must interleave.
        plan = make_plan()
        gwt_knobs = [t.knob for t in plan.trials if t.arm == "gwt"
                     and t.system == "architectural"]
        assert gwt_knobs != sorted(gwt_knobs)

    def test_architectural_seeds_repeat_across_settings_imposter_seeds_do_not(self):
        plan = make_plan()
        arch = {}
        strict = {}
        for t in plan.trials:
            if t.arm != "gwt":
                continue
            target = arch if t.system == "architectural" else strict
            target.setdefault(t.knob, set()).add(t.seed)
        caps = list(arch)
        # Same tasks at every capacity for the real system: paired contrasts.
        assert arch[caps[0]] == arch[caps[1]]
        # Fresh tasks per setting for imposters: identical prompts would be
        # deduplicated by the response cache and fake a frozen report.
        assert not (strict[caps[0]] & strict[caps[1]])


class TestContexts:
    def test_gwt_delivered_counts_track_capacity(self):
        counts = []
        for cap in GWT_CAPACITIES:
            _, delivered = build_gwt_context(seed=0, capacity=cap)
            counts.append(len(delivered))
        assert counts == [2, 3, 4, 5, 6, 8]

    def test_ast_zero_noise_never_misses(self):
        for seed in range(10):
            _, attended, missed = build_ast_context(seed=seed, noise=0.0)
            assert missed == set()
            assert attended

    def test_ast_high_noise_produces_misses_sometimes(self):
        missed_counts = sum(
            bool(build_ast_context(seed=s, noise=0.8)[2]) for s in range(30)
        )
        assert missed_counts > 0


class TestEndToEnd:
    def test_honest_model_tracks_knob_and_static_does_not(self):
        models = {"architectural": HonestModel(),
                  "prompted_strict": StaticModel(),
                  "bare": StaticModel()}
        records = run_gwt_arm(lambda system: models[system], n_per_cell=10)

        by_system = {}
        for r in records:
            by_system.setdefault(r["system"], ([], []))
            by_system[r["system"]][0].append(r["capacity"])
            by_system[r["system"]][1].append(r["n_claimed"])

        real = analyze(*by_system["architectural"], seed=0)
        fake = analyze(*by_system["prompted_strict"], seed=0)
        assert real.rho > 0.9 and real.p_value < 0.001
        assert fake.degenerate or fake.p_value > 0.05

    def test_ast_arm_miss_reports_track_noise_for_real_system(self):
        models = {"architectural": HonestModel(),
                  "prompted_strict": StaticModel()}
        records = run_ast_arm(lambda system: models[system], n_per_cell=20)

        knobs, reports = [], []
        for r in records:
            if r["system"] == "architectural":
                knobs.append(r["noise"])
                reports.append(r["reported_miss"])
        result = analyze(knobs, reports, seed=0)
        assert result.rho > 0
        assert result.p_value < 0.05

    def test_records_carry_ground_truth_for_the_writeup(self):
        models = {"architectural": HonestModel(),
                  "prompted_strict": StaticModel(),
                  "bare": StaticModel()}
        records = run_gwt_arm(lambda system: models[system], n_per_cell=2)
        rec = records[0]
        assert {"system", "capacity", "seed", "n_claimed", "claimed",
                "delivered"} <= set(rec)
