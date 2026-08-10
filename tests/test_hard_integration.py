"""A harder integration task, built because the first real run saturated.

The pilot sweep found the model matching the oracle ceiling at every capacity:
perfect at capacity 5 and perfect at unlimited, so twelve distractors cost it
nothing. You cannot detect a filtering benefit in a system that was never
confused by the noise.

Two changes make filtering actually cost something:

  more to combine   - eight required values instead of three, so a single
                      retrieval slip is enough to fail the item.
  confusable names  - each distractor is a near-twin of a required container
                      ("pale_red_box" against "red_box"), so distinguishing
                      signal from noise takes real work rather than a glance.

The second is the load-bearing one. Global workspace theory says the bottleneck
earns its keep by filtering. If distractors are trivially distinguishable,
filtering is free and there is nothing for the bottleneck to buy.
"""

import pytest

from gwbench.tasks import HardIntegrationTask


class TestStructure:
    def test_generates_the_requested_counts(self):
        task = HardIntegrationTask.generate(seed=1, n_required=8, n_distractors=48)

        assert len(task.required_modules) == 8
        assert len(task.distractor_modules) == 48
        assert len(task.module_contents) == 56

    def test_answer_is_the_sum_of_the_required_values(self):
        task = HardIntegrationTask.generate(seed=1, n_required=8, n_distractors=48)

        assert task.answer == str(sum(task.required_values))

    def test_generation_is_deterministic_for_a_seed(self):
        a = HardIntegrationTask.generate(seed=5, n_required=8, n_distractors=48)
        b = HardIntegrationTask.generate(seed=5, n_required=8, n_distractors=48)

        assert a.module_contents == b.module_contents

    def test_prompt_does_not_leak_the_values(self):
        task = HardIntegrationTask.generate(seed=3, n_required=8, n_distractors=48)

        for value in task.required_values:
            assert str(value) not in task.prompt


class TestDistractorsAreConfusable:
    """The whole point of the redesign."""

    def test_every_distractor_is_a_near_twin_of_some_required_container(self):
        task = HardIntegrationTask.generate(seed=2, n_required=8, n_distractors=48)

        for distractor in task.distractor_modules:
            assert any(
                req.split("_", 1)[-1] in distractor for req in task.required_modules
            ), f"{distractor} resembles no required container"

    def test_no_distractor_is_itself_named_in_the_prompt(self):
        """A distractor named in the prompt would win the salience competition."""
        task = HardIntegrationTask.generate(seed=4, n_required=8, n_distractors=48)

        for distractor in task.distractor_modules:
            assert distractor not in task.prompt

    def test_no_required_name_is_a_substring_of_another(self):
        """Otherwise the salience check double-counts and selection is bogus."""
        task = HardIntegrationTask.generate(seed=6, n_required=8, n_distractors=48)

        for a in task.required_modules:
            for b in task.required_modules:
                if a != b:
                    assert a not in b


class TestScoring:
    def test_scores_the_correct_total(self):
        task = HardIntegrationTask.generate(seed=7, n_required=8, n_distractors=48)

        assert task.score(f"The total is {task.answer}") == 1.0

    def test_an_off_by_one_total_scores_zero(self):
        task = HardIntegrationTask.generate(seed=7, n_required=8, n_distractors=48)
        wrong = str(int(task.answer) + 1)

        assert task.score(f"The total is {wrong}") == 0.0

    def test_summing_a_confusable_twin_by_mistake_scores_zero(self):
        """The failure mode the task is designed to elicit."""
        task = HardIntegrationTask.generate(seed=8, n_required=8, n_distractors=48)
        twin = task.distractor_modules[0]
        swapped = (
            int(task.answer)
            - task.module_values[task.required_modules[0]]
            + task.module_values[twin]
        )

        if swapped != int(task.answer):
            assert task.score(str(swapped)) == 0.0


class TestOracleStillWorks:
    def test_the_oracle_can_solve_it_when_given_everything(self):
        from gwbench.models import OracleSumModel

        task = HardIntegrationTask.generate(seed=9, n_required=8, n_distractors=48)
        prompt = "\n".join(task.module_contents.values()) + "\n\n" + task.prompt

        assert task.score(OracleSumModel().complete(prompt)) == 1.0

    def test_the_oracle_fails_when_a_required_value_is_missing(self):
        from gwbench.models import OracleSumModel

        task = HardIntegrationTask.generate(seed=9, n_required=8, n_distractors=48)
        partial = [
            c
            for name, c in task.module_contents.items()
            if name != task.required_modules[0]
        ]
        prompt = "\n".join(partial) + "\n\n" + task.prompt

        assert task.score(OracleSumModel().complete(prompt)) == 0.0
