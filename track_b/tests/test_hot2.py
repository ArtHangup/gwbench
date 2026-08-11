"""Offline validation of the HOT-2 confidence grid.

Same discipline as the perturbation runner: scripted models only, the real
pipeline end to end, zero API. The honest model derives its confidence from
the disagreement evidence in its context; the static model answers from a
script. The detector must separate them before anything spends.
"""

import re

import pytest

from covariance import analyze
from hot2 import (
    CORRUPTION_RATES,
    build_hot_context,
    hot_probe,
    make_hot_plan,
    parse_confidence_and_total,
    run_hot_grid,
)


class TestHotContext:
    def test_zero_corruption_cycles_agree(self):
        ctx = build_hot_context(seed=0, q=0.0)
        assert ctx.corrupted == []
        # Every required container appears twice with the same value.
        for name, value in ctx.true_values.items():
            assert ctx.text.count(f"The {name.replace('_', ' ')} contains {value}.") == 2

    def test_corruption_hits_exactly_one_cycle(self):
        ctx = build_hot_context(seed=3, q=0.5)
        assert ctx.corrupted
        for name in ctx.corrupted:
            true = ctx.true_values[name]
            shown = re.findall(
                rf"The {name.replace('_', ' ')} contains (\d+)\.", ctx.text
            )
            assert len(shown) == 2
            assert str(true) in shown
            assert len(set(shown)) == 2  # the other copy disagrees

    def test_answer_is_sum_of_true_values(self):
        ctx = build_hot_context(seed=3, q=0.5)
        assert ctx.answer == str(sum(ctx.true_values.values()))

    def test_distractors_never_broadcast(self):
        # Capacity 60 admits exactly the 12 required containers per cycle.
        ctx = build_hot_context(seed=0, q=0.5)
        assert len(ctx.true_values) == 12

    def test_same_seed_same_q_is_deterministic(self):
        a = build_hot_context(seed=7, q=0.25)
        b = build_hot_context(seed=7, q=0.25)
        assert a.text == b.text and a.corrupted == b.corrupted


class TestParse:
    def test_labeled_lines(self):
        conf, total = parse_confidence_and_total(
            "working...\nTOTAL: 612\nCONFIDENCE: 85"
        )
        assert conf == 85 and total == "612"

    def test_missing_labels_is_unparseable(self):
        conf, total = parse_confidence_and_total("the sum is 612, I am 85% sure")
        assert conf is None and total is None

    def test_out_of_range_confidence_is_unparseable(self):
        conf, _ = parse_confidence_and_total("TOTAL: 612\nCONFIDENCE: 140")
        assert conf is None

    def test_empty_reply(self):
        assert parse_confidence_and_total("") == (None, None)


class TestHotPlan:
    def test_budget_and_counts(self):
        plan = make_hot_plan()
        assert plan.total_calls == len(CORRUPTION_RATES) * 3 * 100
        assert plan.est_cost_usd < 20.0

    def test_seed_policy(self):
        plan = make_hot_plan()
        arch, imp = {}, {}
        for t in plan.trials:
            target = arch if t.system == "architectural" else imp
            target.setdefault((t.system, t.knob), set()).add(t.seed)
        qs = CORRUPTION_RATES
        assert arch[("architectural", qs[0])] == arch[("architectural", qs[1])]
        assert not (imp[("prompted_hot", qs[0])] & imp[("prompted_hot", qs[1])])

    def test_order_randomized(self):
        knobs = [t.knob for t in make_hot_plan().trials
                 if t.system == "architectural"]
        assert knobs != sorted(knobs)


class HonestModel:
    """Confidence derived from the disagreement evidence actually present."""

    def complete(self, prompt: str) -> str:
        values = {}
        disagreements = 0
        for name, value in re.findall(r"The ([a-z ]+) contains (\d+)\.", prompt):
            if name in values and values[name] != value:
                disagreements += 1
            values.setdefault(name, value)
        conf = max(0, 95 - 15 * disagreements)
        return f"TOTAL: 0\nCONFIDENCE: {conf}"


class StaticModel:
    def complete(self, prompt: str) -> str:
        return "TOTAL: 0\nCONFIDENCE: 85"


class TestEndToEnd:
    def test_honest_confidence_tracks_corruption_and_static_does_not(self):
        models = {"architectural": HonestModel(),
                  "prompted_hot": StaticModel(),
                  "bare": StaticModel()}
        records = run_hot_grid(lambda s: models[s], n_per_cell=15)

        by = {}
        for r in records:
            if r["confidence"] is None:
                continue
            by.setdefault(r["system"], ([], []))
            by[r["system"]][0].append(r["q"])
            by[r["system"]][1].append(r["confidence"])

        real = analyze(*by["architectural"], seed=0)
        fake = analyze(*by["prompted_hot"], seed=0)
        assert real.rho < -0.3 and real.p_value < 0.01
        assert fake.degenerate or abs(fake.rho) < 0.2

    def test_records_carry_ground_truth(self):
        models = {"architectural": HonestModel(),
                  "prompted_hot": StaticModel(),
                  "bare": StaticModel()}
        rec = run_hot_grid(lambda s: models[s], n_per_cell=2)[0]
        assert {"system", "q", "seed", "confidence", "score",
                "n_corrupted", "unparseable"} <= set(rec)


class TestProbe:
    def test_probe_carries_both_format_contracts(self):
        ctx = build_hot_context(seed=0, q=0.0)
        probe = hot_probe(ctx)
        assert "TOTAL:" in probe and "CONFIDENCE:" in probe
        assert "exactly these containers" in probe  # the task question itself
