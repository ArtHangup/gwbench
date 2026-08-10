"""Apply the preregistered analysis to funded-run rows.

Usage: .venv/bin/python track_a/analyze_results.py [results-json]
Writes analysis.json and RESULTS.md next to the input. Offline: grading here
is parser-only; abstention counts are reported for the judge step.
"""

import json
import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent
for path in (TRACK_A, TRACK_A.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from conflict.analysis import analyze  # noqa: E402


def render(report: dict) -> str:
    h1, h2, h3 = report["h1"], report["h2"], report["h3"]

    def pct(x):
        return "n/a" if x is None else f"{100 * x:.1f}%"

    def contrast(c):
        head = f"p = {c['p']:.4g} ({c['method']})"
        if "ci_low" in c:
            head += f", diff {c['diff']:+.3f} [{c['ci_low']:+.3f}, {c['ci_high']:+.3f}]"
        return head

    lines = [
        "# Funded run: preregistered analysis",
        "",
        f"{report['n_rows']} trials, {report['n_scenarios_novel']} novel scenarios.",
        "",
        "## H1: module revision (primary)",
        "",
        "| cell | revised trials | rate |",
        "|---|---|---|",
    ]
    for label, key in (("A novel", "a_novel"), ("A routine", "a_routine"), ("B novel", "b_novel")):
        cell = h1[key]
        lines.append(f"| {label} | {cell['x']}/{cell['n']} | {pct(cell['rate'])} |")
    lines += [
        "",
        f"- Contrast (a) A-novel vs A-routine: {contrast(h1['contrast_a'])}",
        f"- Contrast (b) A-novel vs B-novel: {contrast(h1['contrast_b'])}",
        "",
        "## H2: recruitment (A, descriptive)",
        "",
        "| kind | coverage | median latency | max | floor waste |",
        "|---|---|---|---|---|",
    ]
    for kind in ("novel", "routine"):
        s = h2[kind]
        lines.append(
            f"| {kind} | {pct(s['coverage_rate'])} | {s['median_latency']} | "
            f"{s['max_latency']} | {s['total_floor_waste']} |"
        )
    lines += [
        "",
        "## H3: decision quality on novel scenarios (secondary, parser-graded)",
        "",
        (
            f"Graded {h3['graded']}; {h3['abstentions']} abstentions "
            + (
                "confirmed UNGRADEABLE by the judge and excluded per PREREG rule 2."
                if report.get("judge", {}).get("applied")
                else "awaiting the judge pass."
            )
        ),
        "",
        "| architecture | accuracy |",
        "|---|---|",
    ]
    for arch, acc in h3["accuracy"].items():
        lines.append(f"| {arch} | {pct(acc)} |")
    for label, key in (("A vs B", "a_vs_b"), ("A vs C", "a_vs_c")):
        pair = h3[key]
        lines.append("")
        lines.append(
            f"- {label}: McNemar p = {pair['p']:.4g}, discordant "
            f"{pair['discordant_a_only']} vs {pair['discordant_b_only']} "
            f"over {pair['pairs']} pairs"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else TRACK_A / "results" / "funded_run.json"
    data = json.loads(source.read_text())
    judge_path = source.parent / "judge_grades.json"
    judge_grades = json.loads(judge_path.read_text()) if judge_path.exists() else None
    report = analyze(data["rows"], judge_grades=judge_grades)
    report["judge"] = {
        "applied": judge_grades is not None,
        "n_judged": len(judge_grades) if judge_grades else 0,
    }
    (source.parent / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    markdown = render(report)
    (source.parent / "RESULTS.md").write_text(markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
