"""Preregistered analysis for the rater-salience arm (PREREG_SALIENCE.md).

Usage: .venv/bin/python track_a/analyze_salience.py
Compares against the funded run's architecture A cells, recomputed from the
raw rows rather than quoted.
"""

import json
import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent
for path in (TRACK_A, TRACK_A.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from conflict.analysis import _contrast, _h2_summary, _latency  # noqa: E402
from conflict.posthoc import corrective_share  # noqa: E402


def cells(rows):
    return (
        [r for r in rows if r["kind"] == "novel"],
        [r for r in rows if r["kind"] == "routine"],
    )


def covered(rows):
    return sum(1 for r in rows if _latency(r) is not None)


def main() -> int:
    arm = json.loads((TRACK_A / "results" / "salience_arm.json").read_text())["rows"]
    base = json.loads((TRACK_A / "results" / "funded_run.json").read_text())["rows"]
    base = [r for r in base if r["architecture"] == "gwt"]

    arm_novel, arm_routine = cells(arm)
    base_novel, base_routine = cells(base)

    contrast = _contrast(
        covered(arm_novel), len(arm_novel), covered(base_novel), len(base_novel)
    )

    lines = [
        "",
        "## Rater-salience arm (preregistered, PREREG_SALIENCE.md)",
        "",
        "Same 144 scenarios, architecture A only, salience from a separate",
        "relevance rater instead of module self-rating.",
        "",
        "| measure | rater novel | self novel | rater routine | self routine |",
        "|---|---|---|---|---|",
    ]
    for label, fn in (
        ("coverage", lambda rs: f"{covered(rs)}/{len(rs)}"),
        ("median latency", lambda rs: str(_h2_summary(rs)["median_latency"])),
        ("floor waste", lambda rs: str(_h2_summary(rs)["total_floor_waste"])),
        ("revised trials", lambda rs: f"{sum(1 for r in rs if r['revisions'])}/{len(rs)}"),
        (
            "corrective share",
            lambda rs: (
                f"{corrective_share(rs)['share']:.2f}"
                if corrective_share(rs)["share"] is not None
                else "n/a"
            ),
        ),
    ):
        lines.append(
            f"| {label} | {fn(arm_novel)} | {fn(base_novel)} | "
            f"{fn(arm_routine)} | {fn(base_routine)} |"
        )
    lines += [
        "",
        f"Primary contrast (novel coverage, rater vs self): "
        f"p = {contrast['p']:.4g} ({contrast['method']}), "
        f"rates {contrast['rate1']:.3f} vs {contrast['rate2']:.3f}.",
    ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
