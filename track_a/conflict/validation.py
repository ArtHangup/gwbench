"""Offline validation: oracle modules through all three architectures.

The point is deliverable 3 from the boot document: with oracles, architecture
A must show revision and orderly recruitment, B must show zero revision, and
C must show neither, so the pipeline and the DVs discriminate by construction
before a single model call is spent.
"""

from __future__ import annotations

from conflict.architectures import run_flat, run_gwt, run_hub
from conflict.metrics import (
    conflict_resolved,
    floor_waste,
    recruitment_latency,
    revision_rate,
    summarize,
)
from conflict.scenarios import DOMAINS, generate


def run_validation(n_per_cell: int = 30) -> dict:
    """Run the battery and evaluate every architecture signature.

    Returns a JSON-serializable report: the summary table, the pass/fail
    checks, and recruitment statistics for architecture A.
    """
    scenarios = [
        generate(seed=seed, domain=domain, kind=kind)
        for domain in DOMAINS
        for kind in ("routine", "novel")
        for seed in range(n_per_cell)
    ]

    trials = []
    gwt_latencies: list[int] = []
    gwt_wastes: list[int] = []
    checks: dict[str, bool] = {
        "gwt_novel_revises": True,
        "gwt_novel_resolves": True,
        "gwt_routine_no_revision": True,
        "gwt_recruits_all_required": True,
        "gwt_no_floor_waste": True,
        "hub_zero_revision": True,
        "hub_zero_formation": True,
        "flat_no_dynamics": True,
        "all_architectures_decide_correctly": True,
    }

    for scenario in scenarios:
        gwt = run_gwt(scenario)
        hub = run_hub(scenario)
        flat = run_flat(scenario)
        trials += [gwt, hub, flat]

        if scenario.kind == "novel":
            checks["gwt_novel_revises"] &= revision_rate(gwt) > 0.0
            checks["gwt_novel_resolves"] &= conflict_resolved(gwt)
        else:
            checks["gwt_routine_no_revision"] &= revision_rate(gwt) == 0.0

        latency = recruitment_latency(gwt, scenario.required_modules)
        checks["gwt_recruits_all_required"] &= latency is not None
        waste = floor_waste(gwt, scenario.required_modules)
        checks["gwt_no_floor_waste"] &= waste == 0
        if latency is not None:
            gwt_latencies.append(latency)
        gwt_wastes.append(waste)

        checks["hub_zero_revision"] &= hub.revisions == []
        checks["hub_zero_formation"] &= hub.formations == []
        checks["flat_no_dynamics"] &= (
            flat.occupancy == [] and flat.revisions == [] and flat.formations == []
        )
        checks["all_architectures_decide_correctly"] &= (
            gwt.correct and hub.correct and flat.correct
        )

    table = {
        f"{architecture}/{kind}": row
        for (architecture, kind), row in summarize(trials).items()
    }
    report = {
        "n_per_cell": n_per_cell,
        "n_scenarios": len(scenarios),
        "n_trials": len(trials),
        "checks": checks,
        "table": table,
        "gwt_recruitment": {
            "mean_latency_cycles": (
                sum(gwt_latencies) / len(gwt_latencies) if gwt_latencies else None
            ),
            "max_latency_cycles": max(gwt_latencies, default=None),
            "total_floor_waste": sum(gwt_wastes),
        },
    }
    return report


def render_markdown(report: dict) -> str:
    lines = [
        "# Offline validation: oracle modules, three architectures",
        "",
        f"Battery: {report['n_scenarios']} scenarios "
        f"({report['n_per_cell']} per domain x kind cell), "
        f"{report['n_trials']} trials, zero API calls.",
        "",
        "## Signature checks",
        "",
    ]
    for name, ok in report["checks"].items():
        lines.append(f"- {'PASS' if ok else 'FAIL'}: {name}")
    lines += [
        "",
        "## Summary table",
        "",
        "| architecture/kind | n | accuracy | revision rate | formations | resolved |",
        "|---|---|---|---|---|---|",
    ]
    for key in sorted(report["table"]):
        row = report["table"][key]
        lines.append(
            f"| {key} | {row['n']} | {row['accuracy']:.2f} | "
            f"{row['revision_rate']:.3f} | {row['formations']:.1f} | "
            f"{row['resolved']:.2f} |"
        )
    recruitment = report["gwt_recruitment"]
    lines += [
        "",
        "## Recruitment (architecture A)",
        "",
        f"- mean cycles to full required-module coverage: "
        f"{recruitment['mean_latency_cycles']:.2f}",
        f"- max: {recruitment['max_latency_cycles']}",
        f"- broadcast slots wasted on repeats before coverage: "
        f"{recruitment['total_floor_waste']}",
        "",
        "Oracle decision quality is at ceiling everywhere by design; the "
        "architectures separate on the non-accuracy DVs, which is the point.",
    ]
    return "\n".join(lines) + "\n"
