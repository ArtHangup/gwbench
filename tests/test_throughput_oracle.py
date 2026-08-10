"""An oracle for the throughput control family.

Without one there is no way to distinguish a broken control task from a genuine
"capacity hurts here" result, and the control exists precisely to catch that
kind of confound. Discovered when the fake end-to-end run scored 0.00 on
throughput at every capacity including unlimited.
"""

from gwbench.architectures import WorkspaceAgent
from gwbench.models import OracleThroughputModel
from gwbench.tasks import ThroughputTask


class TestOracleAnswersFromWhatItSees:
    def test_answers_every_question_when_all_facts_are_present(self):
        task = ThroughputTask.generate(seed=1, n_modules=5)
        prompt = "\n".join(task.module_contents.values()) + "\n\n" + task.prompt

        assert task.score(OracleThroughputModel().complete(prompt)) == 1.0

    def test_answers_none_when_no_facts_are_present(self):
        task = ThroughputTask.generate(seed=1, n_modules=5)

        assert task.score(OracleThroughputModel().complete(task.prompt)) == 0.0

    def test_partial_facts_give_a_partial_score(self):
        task = ThroughputTask.generate(seed=2, n_modules=4)
        some = list(task.module_contents.values())[:2]
        prompt = "\n".join(some) + "\n\n" + task.prompt

        assert task.score(OracleThroughputModel().complete(prompt)) == 0.5


class TestThroughputIsSolvableThroughTheWorkspace:
    """The control must work at unlimited capacity, or it measures nothing."""

    def test_unlimited_capacity_scores_perfectly(self):
        total = 0.0
        for seed in range(8):
            task = ThroughputTask.generate(seed=seed, n_modules=6)
            agent = WorkspaceAgent(
                OracleThroughputModel(), capacity_tokens=None, n_cycles=3
            )
            total += agent.run(task).score

        assert total / 8 == 1.0

    def test_a_capacity_limit_hurts_rather_than_helps(self):
        """GWT predicts no benefit here: there is nothing to integrate."""

        def mean(capacity):
            total = 0.0
            for seed in range(8):
                task = ThroughputTask.generate(seed=seed, n_modules=6)
                agent = WorkspaceAgent(
                    OracleThroughputModel(), capacity_tokens=capacity, n_cycles=3
                )
                total += agent.run(task).score
            return total / 8

        assert mean(6) < mean(None)
