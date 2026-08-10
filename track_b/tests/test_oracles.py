"""Oracle validation for the covariance detector.

Three scripted reporters with known ground truth, no API anywhere:

  honest    report derived from the real Workspace broadcast at the given
            capacity, using the harness read-only. Has the knob.
  static    a fixed script, the prompted imposter's shape. No knob.
  drifting  a script that changes over the run for reasons unrelated to the
            knob. The unlucky imposter: under an ascending knob schedule its
            drift masquerades as tracking, which sets the false-positive
            bound and is why the prereg must randomize trial order.

By construction, honest and static must separate at small n.
"""

import pytest

from covariance import analyze, trials_to_detect
from oracles import drifting_report, honest_report, knob_schedule, static_report


class TestHonestReport:
    def test_report_is_delivered_container_count(self):
        # Required containers are 5 whitespace tokens each and outbid every
        # distractor, so delivered count is capacity // 5 up to n_required.
        assert honest_report(capacity=10, seed=0) == 2
        assert honest_report(capacity=20, seed=0) == 4
        assert honest_report(capacity=30, seed=0) == 6
        assert honest_report(capacity=40, seed=0) == 8

    def test_matches_real_broadcast_not_a_formula(self):
        # Grounded in the harness: at capacity 22 a fifth container is
        # truncated mid-content and must not count as delivered.
        assert honest_report(capacity=22, seed=0) == 4


class TestSchedule:
    def test_ascending_blocks(self):
        assert knob_schedule([10, 20], 2, order="ascending") == [10, 10, 20, 20]

    def test_randomized_is_a_permutation_and_reproducible(self):
        a = knob_schedule([10, 20, 30], 4, order="randomized", seed=1)
        b = knob_schedule([10, 20, 30], 4, order="randomized", seed=1)
        assert a == b
        assert sorted(a) == [10] * 4 + [20] * 4 + [30] * 4
        assert a != sorted(a)


class TestSeparationAtSmallN:
    def test_honest_reporter_is_detected_at_n20(self):
        knobs = knob_schedule([10, 20, 30, 40], 5, order="randomized", seed=0)
        reports = [honest_report(k, seed=i) for i, k in enumerate(knobs)]
        result = analyze(knobs, reports, seed=0)
        assert result.rho > 0.95
        assert result.p_value < 0.01

    def test_static_imposter_is_degenerate_at_any_n(self):
        knobs = knob_schedule([10, 20, 30, 40], 5, order="randomized", seed=0)
        reports = [static_report(k, seed=i) for i, k in enumerate(knobs)]
        result = analyze(knobs, reports, seed=0)
        assert result.degenerate
        assert result.p_value == 1.0

    def test_required_n_is_tiny_for_this_effect(self):
        # The by-construction effect is near-perfect correlation against
        # none, so the power estimate should come in far under one block
        # of trials per setting.
        assert trials_to_detect(0.95, 0.0) < 20


class TestUnluckyImposter:
    def test_ascending_schedule_produces_false_positive(self):
        # The imposter's script drifts with trial index. Sweep the knob in
        # ascending blocks and index stands in for knob: the detector is
        # fooled. This is the false-positive mode, quantified.
        knobs = knob_schedule([10, 20, 30, 40], 10, order="ascending")
        reports = [drifting_report(i, len(knobs)) for i in range(len(knobs))]
        result = analyze(knobs, reports, seed=0)
        assert result.rho > 0.9
        assert result.p_value < 0.05

    def test_randomized_schedule_kills_the_false_positive(self):
        # Same script, same drift, knob order randomized: the accidental
        # correlation vanishes. This is the exclusion rule the prereg needs.
        knobs = knob_schedule([10, 20, 30, 40], 10, order="randomized", seed=3)
        reports = [drifting_report(i, len(knobs)) for i in range(len(knobs))]
        result = analyze(knobs, reports, seed=0)
        assert abs(result.rho) < 0.4
        assert result.p_value > 0.05

    def test_false_positive_rate_is_bounded_by_alpha(self):
        # The quantitative bound: with randomized trial order, the drifting
        # imposter fools the detector at no more than the nominal alpha,
        # up to binomial noise over 100 schedules.
        false_positives = 0
        for schedule_seed in range(100):
            knobs = knob_schedule(
                [10, 20, 30, 40], 10, order="randomized", seed=schedule_seed
            )
            reports = [drifting_report(i, len(knobs)) for i in range(len(knobs))]
            result = analyze(knobs, reports, seed=0, n_permutations=500)
            if result.p_value < 0.05:
                false_positives += 1
        assert false_positives <= 10
