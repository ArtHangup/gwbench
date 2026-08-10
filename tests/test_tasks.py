"""Task generators.

Two task families, and the contrast between them is the experiment:

  integration  - the answer requires combining facts held by several modules,
                 buried among distractors. GWT predicts a capacity limit helps.
  throughput   - many independent questions, no combining required.
                 A capacity limit should only hurt. This is the control that
                 catches "the bottleneck just reduces confusing context".
"""

import pytest

from gwbench.tasks import IntegrationTask, ThroughputTask


class TestIntegrationTask:
    def test_generates_requested_number_of_modules(self):
        task = IntegrationTask.generate(seed=1, n_required=3, n_distractors=5)

        assert len(task.module_contents) == 8

    def test_answer_is_the_sum_of_the_required_facts(self):
        task = IntegrationTask.generate(seed=1, n_required=3, n_distractors=5)

        assert task.answer == str(sum(task.required_values))

    def test_required_facts_live_in_distinct_modules(self):
        task = IntegrationTask.generate(seed=2, n_required=4, n_distractors=10)

        assert len(set(task.required_modules)) == 4

    def test_distractor_modules_are_not_required(self):
        task = IntegrationTask.generate(seed=3, n_required=2, n_distractors=6)

        overlap = set(task.required_modules) & set(task.distractor_modules)
        assert overlap == set()

    def test_generation_is_deterministic_for_a_seed(self):
        a = IntegrationTask.generate(seed=7, n_required=3, n_distractors=5)
        b = IntegrationTask.generate(seed=7, n_required=3, n_distractors=5)

        assert a.module_contents == b.module_contents
        assert a.answer == b.answer

    def test_different_seeds_give_different_tasks(self):
        a = IntegrationTask.generate(seed=1, n_required=3, n_distractors=5)
        b = IntegrationTask.generate(seed=2, n_required=3, n_distractors=5)

        assert a.module_contents != b.module_contents

    def test_prompt_names_every_required_module(self):
        task = IntegrationTask.generate(seed=4, n_required=3, n_distractors=5)

        for name in task.required_modules:
            assert name in task.prompt

    def test_prompt_does_not_leak_the_values(self):
        """If the prompt contains the numbers, no module lookup is needed."""
        task = IntegrationTask.generate(seed=5, n_required=3, n_distractors=5)

        for value in task.required_values:
            assert str(value) not in task.prompt

    def test_scores_correct_answer(self):
        task = IntegrationTask.generate(seed=6, n_required=2, n_distractors=3)

        assert task.score(f"The total is {task.answer}.") == 1.0

    def test_scores_wrong_answer(self):
        task = IntegrationTask.generate(seed=6, n_required=2, n_distractors=3)
        wrong = str(int(task.answer) + 1)

        assert task.score(f"The total is {wrong}.") == 0.0

    def test_a_distractor_value_alone_does_not_score(self):
        """Guards against a response that just echoes something it saw."""
        task = IntegrationTask.generate(seed=8, n_required=3, n_distractors=6)
        distractor_value = task.module_values[task.distractor_modules[0]]

        assert task.score(str(distractor_value)) == 0.0


class TestThroughputTask:
    def test_generates_one_question_per_module(self):
        task = ThroughputTask.generate(seed=1, n_modules=6)

        assert len(task.module_contents) == 6
        assert len(task.questions) == 6

    def test_each_question_is_answerable_from_one_module(self):
        task = ThroughputTask.generate(seed=2, n_modules=5)

        for q in task.questions:
            assert q.module in task.module_contents

    def test_scores_fraction_of_correct_answers(self):
        task = ThroughputTask.generate(seed=3, n_modules=4)
        answers = [q.answer for q in task.questions]
        response = " ".join(answers[:2])

        assert task.score(response) == pytest.approx(0.5)

    def test_perfect_response_scores_one(self):
        task = ThroughputTask.generate(seed=4, n_modules=4)
        response = " ".join(q.answer for q in task.questions)

        assert task.score(response) == pytest.approx(1.0)

    def test_generation_is_deterministic_for_a_seed(self):
        a = ThroughputTask.generate(seed=9, n_modules=5)
        b = ThroughputTask.generate(seed=9, n_modules=5)

        assert a.module_contents == b.module_contents
