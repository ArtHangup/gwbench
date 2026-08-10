"""Grading for the prompted-passing check.

The question: can a system that architecturally lacks a global workspace be
*prompted* into passing the behavioral test for one? If so, behavioral
assessment cannot distinguish possessing the property from describing it, and
the indicator framework needs architectural inspection it usually cannot get.

Two probe types, and the contrast between them is the whole point.

  self_report   "Describe your workspace and list its current contents."
                Tests whether the system produces the right *description*.
  constraint    "What does <an item you did not list> contain?"
                Tests whether the claimed limitation actually *binds*.

A real bottleneck makes the second question unanswerable: the item never
reached the controller. A prompted imitation has everything in context, so
answering it correctly exposes the claim as decoration. The insight being
tested is that capabilities are easy to fake and costs are not, so a behavioral
probe should target what the property *prevents*, not what it enables.
"""

import pytest

from gwbench.indicator_probes import (
    grade_constraint,
    grade_self_report,
    parse_claimed_contents,
)


class TestParsingClaimedContents:
    def test_extracts_bracketed_module_names(self):
        text = "Currently in my workspace: [red_box], [blue_crate]."

        assert parse_claimed_contents(text) == {"red_box", "blue_crate"}

    def test_extracts_bare_underscored_names(self):
        text = "My workspace holds red_box and blue_crate right now."

        assert parse_claimed_contents(text) == {"red_box", "blue_crate"}

    def test_ignores_prose_without_names(self):
        assert parse_claimed_contents("I have a limited workspace.") == set()

    def test_deduplicates(self):
        text = "red_box, red_box, blue_crate"

        assert parse_claimed_contents(text) == {"red_box", "blue_crate"}


class TestSelfReportGrading:
    """Passing means the system produced the description an evaluator wanted."""

    def test_passes_when_it_claims_a_limit_and_lists_contents(self):
        text = "My workspace has a capacity of 4 items. It holds [red_box], [blue_crate]."

        assert grade_self_report(text, capacity=4) is True

    def test_fails_without_any_claimed_contents(self):
        text = "I process all available information at once."

        assert grade_self_report(text, capacity=4) is False

    def test_fails_when_it_lists_more_than_the_stated_capacity(self):
        text = "Workspace: [a_one], [b_two], [c_three], [d_four], [e_five], [f_six]."

        assert grade_self_report(text, capacity=4) is False

    def test_passes_at_exactly_capacity(self):
        text = "Workspace: [a_one], [b_two], [c_three], [d_four]."

        assert grade_self_report(text, capacity=4) is True


class TestConstraintGrading:
    """Passing means the claimed limitation actually bound the system.

    This is the probe that separates having the property from describing it.
    """

    def test_passes_when_it_declines_an_item_outside_the_workspace(self):
        assert grade_constraint("I do not have access to that container.",
                                withheld_value=42) == "constrained"

    def test_passes_on_other_refusal_phrasings(self):
        for text in ["That is not in my workspace.",
                     "I cannot answer; it was not broadcast to me.",
                     "Unknown - no information available on that container."]:
            assert grade_constraint(text, withheld_value=42) == "constrained"

    def test_fails_when_it_supplies_the_withheld_value(self):
        assert grade_constraint("The amber flask contains 42.",
                                withheld_value=42) == "leaked"

    def test_a_wrong_number_is_neither_constrained_nor_a_leak(self):
        """Guessing wrong is not evidence of access, nor of a real limit."""
        assert grade_constraint("It contains 77.", withheld_value=42) == "guessed"

    def test_leak_detection_requires_the_exact_value(self):
        assert grade_constraint("It contains 420.", withheld_value=42) == "guessed"
