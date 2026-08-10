"""Regression: a module truncated at the capacity boundary must not be starved.

Found by demo_attention.py, which showed both rungs scoring 0.00 at zero noise
while *adding* noise improved them. Adding noise should never help an oracle.

Cause: a module whose content was cut off at the capacity boundary still
appeared in the broadcast text, so the "already broadcast, bid lower" decay
fired for it. Every module decayed by the same amount every cycle, relative
ordering never changed, and the module that lost the first competition lost
every subsequent one. Its fact never reached the controller at any number of
cycles.

This mattered because the failure is silent and capacity-dependent: it looks
exactly like a capacity effect on the curve, which is the one thing the whole
experiment is trying to measure.
"""

from gwbench.architectures import WorkspaceAgent
from gwbench.models import OracleSumModel, RecordingModel
from gwbench.tasks import IntegrationTask


def task():
    return IntegrationTask.generate(seed=0, n_required=3, n_distractors=6)


class TestTruncatedModulesKeepCompeting:
    def test_a_truncated_module_eventually_broadcasts_in_full(self):
        t = task()
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(model, capacity_tokens=12, n_cycles=3)

        agent.run(t)

        prompt = model.calls[-1]
        for name in t.required_modules:
            assert t.module_contents[name] in prompt, f"{name} never delivered in full"

    def test_more_cycles_deliver_more_content(self):
        """The livelock made cycle 2 and cycle 3 byte-identical to cycle 1."""
        t = task()

        def delivered(n_cycles):
            model = RecordingModel(reply="0")
            WorkspaceAgent(model, capacity_tokens=12, n_cycles=n_cycles).run(t)
            return sum(
                1 for c in t.module_contents.values() if c in model.calls[-1]
            )

        assert delivered(3) > delivered(1)


class TestNoiseNeverHelpsAnOracle:
    """The symptom that exposed the bug, kept as a guard."""

    def test_zero_noise_scores_at_least_as_well_as_noisy_attention(self):
        def mean_score(noise):
            total = 0.0
            for seed in range(20):
                t = IntegrationTask.generate(
                    seed=seed, n_required=3, n_distractors=6
                )
                agent = WorkspaceAgent(
                    OracleSumModel(),
                    capacity_tokens=12,
                    n_cycles=3,
                    attention_noise=noise,
                    seed=seed,
                )
                total += agent.run(t).score
            return total / 20

        quiet = mean_score(0.0)
        noisy = mean_score(1.0)

        assert quiet >= noisy, f"noise improved an oracle: {quiet=} {noisy=}"

    def test_deterministic_attention_solves_the_task_given_enough_cycles(self):
        total = 0.0
        for seed in range(20):
            t = IntegrationTask.generate(seed=seed, n_required=3, n_distractors=6)
            agent = WorkspaceAgent(
                OracleSumModel(), capacity_tokens=12, n_cycles=4
            )
            total += agent.run(t).score

        assert total / 20 == 1.0
