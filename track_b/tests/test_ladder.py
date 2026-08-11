"""Offline validation of the imposter ladder.

The ladder's coaching and retrieval draw on the perturbation run's REAL
architectural records (perturbation_results.json plus cached responses), so
these tests exercise the actual archive read-only. Model calls are faked.
"""

import pytest

from covariance import analyze
from ladder import (
    LADDER_CAPACITIES,
    RUNGS,
    coaching_examples,
    knob_informed_system,
    load_archive,
    make_ladder_plan,
    retrieve_transcript,
    run_ladder,
)


@pytest.fixture(scope="module")
def archive():
    return load_archive()


class TestArchive:
    def test_loads_600_architectural_records_with_text(self, archive):
        assert len(archive) == 600
        rec = archive[0]
        assert {"seed", "capacity", "claimed", "delivered", "required",
                "response"} <= set(rec)
        assert isinstance(rec["response"], str) and rec["response"]


class TestKnobInformedSystem:
    def test_states_tokens_and_derived_count(self):
        text = knob_informed_system(30)
        assert "30 tokens" in text
        assert "6" in text  # 30 // 5 containers


class TestCoaching:
    def test_eight_engaged_examples_excluding_current_capacity(self, archive):
        for cap in LADDER_CAPACITIES:
            examples = coaching_examples(archive, exclude_capacity=cap)
            assert len(examples) == 8
            assert all(e["capacity"] != cap for e in examples)
            assert all(e["claimed"] for e in examples)  # engaged only

    def test_deterministic(self, archive):
        a = coaching_examples(archive, exclude_capacity=20)
        b = coaching_examples(archive, exclude_capacity=20)
        assert a == b


class TestRetrieval:
    def test_max_required_overlap_wins(self, archive):
        # Retrieval must be capacity-blind: score by task similarity only.
        probe_required = archive[0]["required"]
        rec = retrieve_transcript(archive, probe_required)
        assert set(rec["required"]) == set(probe_required)

    def test_deterministic_tiebreak(self, archive):
        r = archive[5]["required"]
        assert retrieve_transcript(archive, r) == retrieve_transcript(archive, r)


class TestPlan:
    def test_counts_and_budget(self):
        plan = make_ladder_plan()
        assert plan.total_calls == len(RUNGS) * len(LADDER_CAPACITIES) * 100
        assert plan.est_cost_usd < 20.0

    def test_fresh_seeds_per_cell_and_randomized_order(self):
        plan = make_ladder_plan()
        seen = {}
        for t in plan.trials:
            seen.setdefault((t.rung, t.knob), set()).add(t.seed)
        cells = list(seen.values())
        assert all(len(s) == 100 for s in cells)
        assert not (cells[0] & cells[1])
        caps = [t.knob for t in plan.trials if t.rung == "knob_informed"]
        assert caps != sorted(caps)


class CompliantModel:
    """Obeys a stated container count if one is present; else claims four.

    Mimics the best case for rung 1 (reads the leaked knob) and the expected
    case for rungs 2 and 3 (no knob signal, scripted size).
    """

    def __init__(self):
        self.stated = None

    def complete(self, prompt: str) -> str:
        import re
        m = re.search(r"hold roughly (\d+) containers", self.stated or "")
        k = int(m.group(1)) if m else 4
        names = re.findall(r"\[([a-z_]+)\]", prompt)
        return "In my workspace: " + ", ".join(sorted(set(names))[:k])


class TestEndToEnd:
    def test_knob_leak_tracks_and_blind_rungs_stay_flat(self, archive):
        def model_for(rung, capacity):
            m = CompliantModel()
            m.stated = knob_informed_system(capacity) if rung == "knob_informed" else ""
            return m

        records = run_ladder(model_for, archive, n_per_cell=8)
        by = {}
        for r in records:
            by.setdefault(r["rung"], ([], []))
            by[r["rung"]][0].append(r["capacity"])
            by[r["rung"]][1].append(r["n_claimed"])

        leak = analyze(*by["knob_informed"], seed=0)
        coached = analyze(*by["coached"], seed=0)
        assert leak.rho > 0.9
        assert coached.degenerate or abs(coached.rho) < 0.2

    def test_records_carry_state_reconstruction_fields(self, archive):
        def model_for(rung, capacity):
            m = CompliantModel()
            m.stated = ""
            return m

        rec = run_ladder(model_for, archive, n_per_cell=2)[0]
        assert {"rung", "capacity", "seed", "n_claimed", "claimed",
                "true_delivered"} <= set(rec)
