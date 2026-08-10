"""The confusability control.

More distractors also means more text, so a decline could be plain context
length rather than interference. This control holds distractor count and text
volume constant while making the distractors trivially rejectable: twins of
containers that are *not* on the required list.

If scores fall equally in both arms, the effect is text volume and the filtering
story is unsupported. If they fall further with confusable distractors, the
extra drop is interference, which is what a bottleneck would be filtering.
"""

from gwbench.tasks import HardIntegrationTask


class TestNonConfusableArm:
    def test_distractors_do_not_resemble_any_required_container(self):
        task = HardIntegrationTask.generate(
            seed=1, n_required=8, n_distractors=48, confusable=False
        )

        for d in task.distractor_modules:
            for req in task.required_modules:
                assert not d.endswith(req), f"{d} is a twin of {req}"

    def test_counts_and_answer_match_the_confusable_arm(self):
        easy = HardIntegrationTask.generate(
            seed=2, n_required=8, n_distractors=48, confusable=False
        )
        hard = HardIntegrationTask.generate(
            seed=2, n_required=8, n_distractors=48, confusable=True
        )

        assert easy.required_modules == hard.required_modules
        assert easy.answer == hard.answer
        assert len(easy.module_contents) == len(hard.module_contents)

    def test_text_volume_is_comparable_between_arms(self):
        """Otherwise the control does not control for length."""
        easy = HardIntegrationTask.generate(
            seed=3, n_required=8, n_distractors=48, confusable=False
        )
        hard = HardIntegrationTask.generate(
            seed=3, n_required=8, n_distractors=48, confusable=True
        )
        n = lambda t: sum(len(c.split()) for c in t.module_contents.values())

        assert abs(n(easy) - n(hard)) / n(hard) < 0.05

    def test_confusable_defaults_to_true(self):
        task = HardIntegrationTask.generate(seed=4, n_required=8, n_distractors=48)

        assert any(
            d.endswith(task.required_modules[0]) for d in task.distractor_modules
        )
