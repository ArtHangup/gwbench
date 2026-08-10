"""The preregistered analysis, operating on serialized funded-run rows.

Statistics are stdlib-only: exact McNemar and Fisher tests via math.comb, the
two-proportion z test via the normal CDF. Method selection follows PREREG.md:
Fisher replaces the z test when any cell count is below 10.
"""

from __future__ import annotations

from collections import defaultdict
from math import comb, erf, sqrt
from statistics import median
from typing import Optional

from conflict.parser import parse_decision
from conflict.scenarios import generate

MIN_CELL_FOR_Z = 10


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar on the discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    k = max(b, c)
    tail = sum(comb(n, i) for i in range(k, n + 1)) / 2**n
    return min(1.0, 2.0 * tail)


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact for the 2x2 table [[a, b], [c, d]]."""
    row1, row2, col1 = a + b, c + d, a + c
    n = row1 + row2

    def point(k: int) -> float:
        return comb(row1, k) * comb(row2, col1 - k) / comb(n, col1)

    observed = point(a)
    low = max(0, col1 - row2)
    high = min(col1, row1)
    total = sum(
        p for k in range(low, high + 1) if (p := point(k)) <= observed * (1 + 1e-12)
    )
    return min(1.0, total)


def two_proportion(x1: int, n1: int, x2: int, n2: int) -> dict:
    """Pooled two-sided z test plus an unpooled 95 percent CI on the diff."""
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se_pooled = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se_pooled == 0:
        z, p = 0.0, 1.0
    else:
        z = (p1 - p2) / se_pooled
        p = 2.0 * (1.0 - _norm_cdf(abs(z)))
    se_diff = sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return {
        "rate1": p1,
        "rate2": p2,
        "diff": p1 - p2,
        "z": z,
        "p": p,
        "ci_low": (p1 - p2) - 1.959963985 * se_diff,
        "ci_high": (p1 - p2) + 1.959963985 * se_diff,
    }


def _contrast(x1: int, n1: int, x2: int, n2: int) -> dict:
    cells = (x1, n1 - x1, x2, n2 - x2)
    if min(cells) < MIN_CELL_FOR_Z:
        return {
            "method": "fisher",
            "p": fisher_exact(*cells),
            "rate1": x1 / n1,
            "rate2": x2 / n2,
            "diff": x1 / n1 - x2 / n2,
        }
    result = two_proportion(x1, n1, x2, n2)
    result["method"] = "z"
    return result


def _revised(row: dict) -> bool:
    return len(row["revisions"]) > 0


def _cell(rows: list[dict], architecture: str, kind: str) -> list[dict]:
    return [r for r in rows if r["architecture"] == architecture and r["kind"] == kind]


def _rate(rows: list[dict]) -> dict:
    x = sum(_revised(r) for r in rows)
    return {"x": x, "n": len(rows), "rate": x / len(rows) if rows else None}


def _latency(row: dict) -> Optional[int]:
    required = set(row["required_modules"])
    delivered: set[str] = set()
    for index, cycle in enumerate(row["occupancy"]):
        for source, kind, _text in cycle:
            if kind != "stance":
                delivered.add(source)
        if required <= delivered:
            return index
    return None


def _floor_waste(row: dict) -> int:
    horizon = _latency(row)
    if horizon is None:
        horizon = len(row["occupancy"]) - 1
    seen: set[tuple[str, str]] = set()
    waste = 0
    for cycle in row["occupancy"][: horizon + 1]:
        for source, kind, text in cycle:
            if kind == "stance":
                continue
            if (source, text) in seen:
                waste += 1
            seen.add((source, text))
    return waste


def _h2_summary(rows: list[dict]) -> dict:
    latencies = [_latency(r) for r in rows]
    covered = [lat for lat in latencies if lat is not None]
    return {
        "n": len(rows),
        "coverage_rate": len(covered) / len(rows) if rows else None,
        "median_latency": median(covered) if covered else None,
        "max_latency": max(covered) if covered else None,
        "total_floor_waste": sum(_floor_waste(r) for r in rows),
    }


def _grade(row: dict, judge_grades: Optional[dict] = None) -> Optional[bool]:
    """Parser-graded correctness; the judge fills abstentions per GRADING.md.

    judge_grades maps "seed:architecture" to an option letter or None
    (UNGRADEABLE). Remaining None is an abstention.
    """
    scenario = generate(seed=row["seed"], domain=row["domain"], kind=row["kind"])
    picked = parse_decision(row["decision_text"], scenario.options)
    if picked is None and judge_grades is not None:
        picked = judge_grades.get(f"{row['seed']}:{row['architecture']}")
    if picked is None:
        return None
    return picked == row["correct_option"]


def _mcnemar_pair(by_seed: dict, arch_a: str, arch_b: str) -> dict:
    both_correct = a_only = b_only = neither = 0
    graded_a = []
    for seed, grades in by_seed.items():
        ga, gb = grades.get(arch_a), grades.get(arch_b)
        if ga is None or gb is None:
            continue
        graded_a.append(ga)
        if ga and gb:
            both_correct += 1
        elif ga and not gb:
            a_only += 1
        elif gb and not ga:
            b_only += 1
        else:
            neither += 1
    return {
        "pairs": both_correct + a_only + b_only + neither,
        "accuracy_a": (
            sum(graded_a) / len(graded_a) if graded_a else None
        ),
        "discordant_a_only": a_only,
        "discordant_b_only": b_only,
        "p": mcnemar_exact(a_only, b_only),
    }


def analyze(rows: list[dict], judge_grades: Optional[dict] = None) -> dict:
    a_novel = _rate(_cell(rows, "gwt", "novel"))
    a_routine = _rate(_cell(rows, "gwt", "routine"))
    b_novel = _rate(_cell(rows, "hub", "novel"))

    h1 = {
        "a_novel": a_novel,
        "a_routine": a_routine,
        "b_novel": b_novel,
        "contrast_a": _contrast(
            a_novel["x"], a_novel["n"], a_routine["x"], a_routine["n"]
        ),
        "contrast_b": _contrast(a_novel["x"], a_novel["n"], b_novel["x"], b_novel["n"]),
    }

    h2 = {
        "novel": _h2_summary(_cell(rows, "gwt", "novel")),
        "routine": _h2_summary(_cell(rows, "gwt", "routine")),
    }

    novel_rows = [r for r in rows if r["kind"] == "novel"]
    by_seed: dict[int, dict[str, Optional[bool]]] = defaultdict(dict)
    graded = abstentions = 0
    accuracy: dict[str, list[bool]] = defaultdict(list)
    for row in novel_rows:
        grade = _grade(row, judge_grades)
        if grade is None:
            abstentions += 1
        else:
            graded += 1
            accuracy[row["architecture"]].append(grade)
        by_seed[row["seed"]][row["architecture"]] = grade

    h3 = {
        "graded": graded,
        "abstentions": abstentions,
        "accuracy": {
            arch: sum(vals) / len(vals) for arch, vals in sorted(accuracy.items())
        },
        "a_vs_b": _mcnemar_pair(by_seed, "gwt", "hub"),
        "a_vs_c": _mcnemar_pair(by_seed, "gwt", "flat"),
    }

    return {
        "n_rows": len(rows),
        "n_scenarios_novel": len({r["seed"] for r in novel_rows}),
        "h1": h1,
        "h2": h2,
        "h3": h3,
    }
