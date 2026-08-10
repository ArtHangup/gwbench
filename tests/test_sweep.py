"""The bandwidth sweep, and proof that it can measure anything.

The headline experiment reads a result off a capacity-versus-performance curve.
Before spending money on API calls, the harness must be shown capable of
producing a curve at all. An oracle model does that: it uses perfectly whatever
information reaches it, so its score is a direct readout of how much task-
relevant information the capacity limit let through.

If the sweep is flat under an oracle, the harness is broken and any flat curve
from a real model would be uninterpretable.
"""

import pytest

from gwbench.architectures import WorkspaceAgent
from gwbench.models import OracleSumModel
from gwbench.sweep import sweep
from gwbench.tasks import IntegrationTask


def make_task(seed: int) -> IntegrationTask:
    return IntegrationTask.generate(seed=seed, n_required=3, n_distractors=6)


class TestSweepMechanics:
    def test_returns_one_point_per_capacity(self):
        points = sweep(
            capacities=[0, 4, 8, None],
            agent_factory=lambda cap: WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap, n_cycles=2
            ),
            task_factory=make_task,
            n_trials=2,
        )

        assert [p.capacity for p in points] == [0, 4, 8, None]

    def test_each_point_averages_the_requested_trials(self):
        points = sweep(
            capacities=[8],
            agent_factory=lambda cap: WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap, n_cycles=2
            ),
            task_factory=make_task,
            n_trials=5,
        )

        assert points[0].n_trials == 5

    def test_uses_a_different_task_per_trial(self):
        seen = []

        def recording_factory(seed):
            seen.append(seed)
            return make_task(seed)

        sweep(
            capacities=[8],
            agent_factory=lambda cap: WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap
            ),
            task_factory=recording_factory,
            n_trials=4,
        )

        assert len(set(seen)) == 4

    def test_same_task_seeds_are_used_at_every_capacity(self):
        """Capacities must be compared on identical tasks, not different ones."""
        seen = {}

        def factory_for(cap):
            def make(seed):
                seen.setdefault(cap, []).append(seed)
                return make_task(seed)

            return make

        for cap in (4, 12):
            sweep(
                capacities=[cap],
                agent_factory=lambda c: WorkspaceAgent(
                    OracleSumModel(), capacity_tokens=c
                ),
                task_factory=factory_for(cap),
                n_trials=3,
            )

        assert seen[4] == seen[12]


class TestHarnessCanDetectACapacityEffect:
    """The smoke test that licenses spending money on the real experiment."""

    def test_zero_capacity_scores_zero_under_an_oracle(self):
        points = sweep(
            capacities=[0],
            agent_factory=lambda cap: WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap, n_cycles=2
            ),
            task_factory=make_task,
            n_trials=8,
        )

        assert points[0].mean_score == 0.0

    def test_unlimited_capacity_scores_perfectly_under_an_oracle(self):
        points = sweep(
            capacities=[None],
            agent_factory=lambda cap: WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap, n_cycles=2
            ),
            task_factory=make_task,
            n_trials=8,
        )

        assert points[0].mean_score == 1.0

    def test_performance_rises_with_capacity(self):
        points = sweep(
            capacities=[0, 6, 12, 24, None],
            agent_factory=lambda cap: WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap, n_cycles=2
            ),
            task_factory=make_task,
            n_trials=8,
        )
        scores = [p.mean_score for p in points]

        assert scores[0] < scores[-1], f"harness detected no effect at all: {scores}"
        assert scores == sorted(scores), f"not monotonic under an oracle: {scores}"

    def test_records_mean_broadcast_tokens_per_point(self):
        points = sweep(
            capacities=[6],
            agent_factory=lambda cap: WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap, n_cycles=2
            ),
            task_factory=make_task,
            n_trials=4,
        )

        assert points[0].mean_broadcast_tokens == pytest.approx(6, abs=6)
