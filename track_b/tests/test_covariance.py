"""Tests for the covariance detector.

The detector answers one question: given (knob setting, self-report) pairs, do
the reports track the knob? A real architecture's reports covary with its
actual state; a scripted imposter's reports are frozen or track the wrong
thing. Everything here is offline arithmetic; no model, no API.
"""

import pytest

from covariance import analyze, pearson_r, spearman_rho, trials_to_detect


class TestPearson:
    def test_known_value(self):
        # Hand-computed: xs deviations (-2,-1,0,1,2), ys deviations
        # (-3,-1,0,1,3). cov=12/5, sx=sqrt(2), sy=sqrt(4), r=12/(5*2*sqrt(2))
        xs = [1, 2, 3, 4, 5]
        ys = [2, 4, 5, 6, 8]
        assert pearson_r(xs, ys) == pytest.approx(0.9899, abs=1e-4)

    def test_perfect_negative(self):
        assert pearson_r([1, 2, 3], [6, 4, 2]) == pytest.approx(-1.0)

    def test_constant_input_is_degenerate(self):
        # A static imposter's reports never vary. That is not "correlation
        # zero", it is "correlation undefined", and the caller must be able
        # to tell the difference. None is the sentinel.
        assert pearson_r([1, 2, 3], [7, 7, 7]) is None


class TestSpearman:
    def test_monotone_nonlinear_is_perfect(self):
        # Reports need not be linear in the knob, only track it. Capacity in
        # tokens maps to delivered containers via a floor divide, which is
        # monotone but stepped; Spearman is the right statistic for that.
        xs = [1, 2, 3, 4, 5]
        ys = [1, 8, 27, 64, 125]
        assert pearson_r(xs, ys) < 1.0
        assert spearman_rho(xs, ys) == pytest.approx(1.0)

    def test_ties_use_average_ranks(self):
        # Self-reports are small integer counts, so ties are the norm.
        # scipy.stats.spearmanr([1,2,3,4], [10,20,20,30]) = 0.9486832...
        assert spearman_rho([1, 2, 3, 4], [10, 20, 20, 30]) == pytest.approx(
            0.9486832, abs=1e-6
        )

    def test_constant_input_is_degenerate(self):
        assert spearman_rho([1, 2, 3], [7, 7, 7]) is None


class TestAnalyze:
    def test_tracking_reports_get_small_p(self):
        # A knob swept over four settings, ten trials each, reports that step
        # with the knob plus one flipped trial of noise. This is the honest
        # reporter's shape and it should be flatly significant.
        knobs = [10] * 10 + [20] * 10 + [30] * 10 + [40] * 10
        reports = [2] * 10 + [4] * 10 + [6] * 9 + [4] + [8] * 10
        result = analyze(knobs, reports, seed=0)
        assert result.rho > 0.9
        assert result.p_value < 0.001
        assert result.n == 40
        assert not result.degenerate

    def test_static_reports_are_degenerate_not_significant(self):
        knobs = [10, 20, 30, 40] * 10
        reports = [4] * 40
        result = analyze(knobs, reports, seed=0)
        assert result.degenerate
        assert result.rho is None
        assert result.p_value == 1.0

    def test_unrelated_reports_get_large_p(self):
        # Reports vary but are assigned independently of the knob.
        rng_reports = [3, 7, 5, 2, 8, 4, 6, 1, 5, 7, 2, 6, 4, 8, 3, 5]
        knobs = [10, 20, 30, 40] * 4
        result = analyze(knobs, rng_reports, seed=0)
        assert result.p_value > 0.05

    def test_seed_makes_p_reproducible(self):
        knobs = [10, 20, 30, 40] * 4
        reports = [3, 7, 5, 2, 8, 4, 6, 1, 5, 7, 2, 6, 4, 8, 3, 5]
        a = analyze(knobs, reports, seed=7)
        b = analyze(knobs, reports, seed=7)
        assert a.p_value == b.p_value


class TestTrialsToDetect:
    """Per-condition n to separate a real system's correlation from an
    imposter's, at 80% power and two-sided alpha 0.05, via Fisher z. This is
    the analogue of the paper's ~225-trials-per-condition figure for leak
    rates, so the prereg can state the same kind of number for covariance."""

    def test_hand_computed_value(self):
        # dz = atanh(0.5) = 0.549306; n = 3 + 2*((1.95996+0.84162)/dz)^2 = 55.02
        assert trials_to_detect(0.5, 0.0) == 56

    def test_big_gaps_need_few_trials(self):
        assert trials_to_detect(0.95, 0.0) <= 10

    def test_smaller_gap_needs_more_trials(self):
        assert trials_to_detect(0.3, 0.0) > trials_to_detect(0.6, 0.0)

    def test_imposter_defaults_to_uncorrelated(self):
        assert trials_to_detect(0.5) == trials_to_detect(0.5, 0.0)

    def test_equal_correlations_are_undetectable(self):
        with pytest.raises(ValueError):
            trials_to_detect(0.5, 0.5)
