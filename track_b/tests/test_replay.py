"""Tests for cache replay: rebuilding prompted_passing prompts bit-for-bit
and reading the corresponding cached responses. Integration tests run against
the real repo cache read-only; a miss raises nothing and spends nothing.
"""

import pytest

from replay import RUNS, cached_response, jaccard, replay_trial, self_report_prompt


class TestJaccard:
    def test_disjoint(self):
        assert jaccard({"a"}, {"b"}) == 0.0

    def test_identical(self):
        assert jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_partial(self):
        assert jaccard({"a", "b", "c"}, {"b", "c", "d"}) == pytest.approx(0.5)

    def test_both_empty(self):
        assert jaccard(set(), set()) == 1.0


class TestPromptReconstruction:
    def test_architectural_prompt_hits_cache(self):
        # Seed 0, GWT-2, haiku: verified by hand during the boot spike.
        prompt = self_report_prompt(seed=0, system="architectural", indicator="GWT-2")
        text = cached_response(prompt, model="claude-haiku-4-5", effort=None,
                               system_prompt=None)
        assert isinstance(text, str) and len(text) > 0

    def test_miss_returns_none_and_never_spends(self):
        assert cached_response("no such prompt was ever sent",
                               model="claude-haiku-4-5", effort=None,
                               system_prompt=None) is None


class TestReplayTrial:
    def test_architectural_seed0_gwt2(self):
        run = next(r for r in RUNS if r.indicator == "GWT-2"
                   and r.model == "claude-haiku-4-5")
        rec = replay_trial(run, "architectural", seed=0)
        assert rec is not None
        assert rec["delivered"] == ["amber_flask", "black_pail",
                                    "blue_crate", "brass_drum"]
        # Whatever the model claimed, the parse must stay inside this task's
        # container vocabulary, exactly as run_case restricted it.
        assert set(rec["claimed"]) <= set(rec["all_containers"])

    def test_imposter_context_holds_everything(self):
        run = next(r for r in RUNS if r.indicator == "GWT-2"
                   and r.model == "claude-haiku-4-5")
        rec = replay_trial(run, "prompted_strict", seed=0)
        assert rec is not None
        assert rec["delivered"] == sorted(rec["all_containers"])
