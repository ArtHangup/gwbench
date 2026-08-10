"""The funded run, one command. Preregistered in PREREG.md.

Dry run (default, zero API calls) prints the plan and cost estimate and runs
a one-scenario-per-cell oracle smoke through the full pipeline:

    .venv/bin/python track_a/run_funded.py

The live run needs BOTH gates plus an API key, per the budget rules in
track_a/CLAUDE.md (fresh authorization from Josh is required before using
them; project spend already exceeds the authorized budget):

    .venv/bin/python track_a/run_funded.py --live --i-authorize-spend

Every model call goes through gwbench's AnthropicModel with a disk cache and
a hard call cap, so an interrupted run resumes at zero marginal cost and the
worst case spend is bounded up front.
"""

import argparse
import json
import os
import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent
for path in (TRACK_A, TRACK_A.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from conflict.funded import (  # noqa: E402
    FUNDED_MODEL,
    battery,
    estimate,
    run_battery,
)


def dry_run(n_per_cell: int) -> int:
    plan = estimate(n_per_cell)
    print("DRY RUN (no API calls). Plan for the funded run:")
    for key, value in plan.items():
        print(f"  {key}: {value}")

    print("\nOracle smoke through the full pipeline (2 scenarios):")
    from conflict.architectures import run_flat, run_gwt, run_hub
    from conflict.funded import SEED_BASE, serialize_trial
    from conflict.scenarios import generate

    for kind in ("routine", "novel"):
        scenario = generate(seed=SEED_BASE, kind=kind)
        for runner in (run_gwt, run_hub, run_flat):
            row = serialize_trial(runner(scenario), scenario)
            print(
                f"  {kind}/{row['architecture']}: decision {row['runner_option']} "
                f"(correct {row['correct_option']}), "
                f"{len(row['revisions'])} revisions"
            )
    print("\nPipeline sound. To spend money: --live --i-authorize-spend")
    return 0


def live_run(n_per_cell: int, out: Path) -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set; refusing to construct a client.")
        return 1

    from gwbench.anthropic_model import AnthropicModel

    plan = estimate(n_per_cell)
    print(f"LIVE run: {plan['total_calls']} calls, est ${plan['cost_usd']}, "
          f"hard cap {plan['call_cap']} calls, model {FUNDED_MODEL}")

    model = AnthropicModel(
        model=FUNDED_MODEL,
        max_tokens=400,
        effort=None,  # Haiku 4.5 predates the effort parameter
        cache_dir=TRACK_A.parent / ".api_cache",
        max_calls=plan["call_cap"],
    )

    out.parent.mkdir(parents=True, exist_ok=True)

    def checkpoint(rows: list[dict]) -> None:
        out.write_text(json.dumps({"plan": plan, "rows": rows}, indent=2))

    rows = run_battery(battery(n_per_cell), model, checkpoint=checkpoint)
    checkpoint(rows)
    print(
        f"Done: {len(rows)} trials -> {out}. "
        f"Usage: {model.usage.calls} calls, "
        f"{model.usage.input_tokens} in / {model.usage.output_tokens} out tokens."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-per-cell", type=int, default=72)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--i-authorize-spend",
        action="store_true",
        help="Explicit confirmation that fresh budget authorization exists.",
    )
    parser.add_argument(
        "--out", type=Path, default=TRACK_A / "results" / "funded_run.json"
    )
    args = parser.parse_args()

    if not args.live:
        return dry_run(args.n_per_cell)
    if not args.i_authorize_spend:
        print("Refusing: --live requires --i-authorize-spend (budget rules in CLAUDE.md).")
        return 1
    return live_run(args.n_per_cell, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
