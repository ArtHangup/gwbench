"""Covariance detector: do self-reports track a knob the assessor turned?

Pure arithmetic on (knob, report) pairs. No model calls anywhere in this
module; it is the offline half of the perturbation-probe design.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist
from typing import Optional, Sequence


def pearson_r(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Pearson correlation, or None when either input has zero variance.

    None rather than 0.0 because a static imposter produces constant reports,
    and "reports do not vary at all" is a different finding from "reports vary
    but do not track the knob". Callers decide how to treat degeneracy.
    """
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have equal length")
    n = len(xs)
    if n < 2:
        raise ValueError("need at least two pairs")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    var_x = sum(d * d for d in dx)
    var_y = sum(d * d for d in dy)
    if var_x == 0 or var_y == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / math.sqrt(var_x * var_y)


def _average_ranks(values: Sequence[float]) -> list[float]:
    """Ranks starting at 1, ties sharing the mean of their positions."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Spearman rank correlation: Pearson on average ranks.

    The right statistic here because reports need only track the knob
    monotonically (capacity-to-delivered is a stepped floor divide), and
    because integer-count reports are full of ties.
    """
    return pearson_r(_average_ranks(xs), _average_ranks(ys))


@dataclass(frozen=True)
class CovarianceResult:
    """Verdict on one system's (knob, report) data."""

    rho: Optional[float]
    p_value: float
    n: int
    degenerate: bool


def analyze(
    knobs: Sequence[float],
    reports: Sequence[float],
    seed: int = 0,
    n_permutations: int = 10_000,
) -> CovarianceResult:
    """Does the report track the knob?

    Permutation test on Spearman rho: shuffle reports against knobs, count how
    often |rho| under the null meets or beats the observed. Degenerate inputs
    (either side constant) come back with rho None and p 1.0, which is the
    static imposter's signature: nothing to test because nothing varied.
    """
    observed = spearman_rho(knobs, reports)
    n = len(knobs)
    if observed is None:
        return CovarianceResult(rho=None, p_value=1.0, n=n, degenerate=True)

    rng = random.Random(seed)
    shuffled = list(reports)
    hits = 0
    for _ in range(n_permutations):
        rng.shuffle(shuffled)
        rho = spearman_rho(knobs, shuffled)
        if rho is not None and abs(rho) >= abs(observed):
            hits += 1
    # Add-one correction keeps the estimate away from an impossible p of 0.
    p = (hits + 1) / (n_permutations + 1)
    return CovarianceResult(rho=observed, p_value=p, n=n, degenerate=False)


def trials_to_detect(
    r_real: float,
    r_imposter: float = 0.0,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Per-condition trial count to separate two correlations.

    Two-sample comparison via Fisher z: each group's transformed correlation
    has variance 1/(n-3), so the difference has variance 2/(n-3) at equal n,
    giving n = 3 + 2 ((z_alpha + z_beta) / dz)^2, rounded up. The analogue of
    the paper's ~225-trials-per-condition figure for leak rates.
    """
    dz = abs(math.atanh(r_real) - math.atanh(r_imposter))
    if dz == 0:
        raise ValueError("identical correlations cannot be separated at any n")
    z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
    z_beta = NormalDist().inv_cdf(power)
    return math.ceil(3 + 2 * ((z_alpha + z_beta) / dz) ** 2)
