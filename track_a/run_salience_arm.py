"""The rater-salience arm, preregistered in PREREG_SALIENCE.md.

Architecture A only, same 144 scenarios as the funded run, salience assigned
by a separate relevance rater instead of module self-rating.

    .venv/bin/python track_a/run_salience_arm.py                              # dry run
    .venv/bin/python track_a/run_salience_arm.py --live --i-authorize-spend   # funded
"""

import argparse
import json
import sys
from pathlib import Path

TRACK_A = Path(__file__).resolve().parent
for path in (TRACK_A, TRACK_A.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from conflict.architectures import run_gwt  # noqa: E402
from conflict.funded import FUNDED_MODEL, battery, serialize_trial  # noqa: E402
from conflict.model_modules import ModelController, ModelModule  # noqa: E402
from conflict.rater import RaterModule  # noqa: E402

WORST_CASE_CALLS = 5_904 + 11_520
CALL_CAP = int(WORST_CASE_CALLS * 1.1)


def run(model, rater_model, n_per_cell: int, workers: int, checkpoint):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    scenarios = battery(n_per_cell)

    def module_factory(name, scenario):
        return RaterModule(ModelModule(name, scenario, model), rater_model)

    def one(scenario):
        trial = run_gwt(
            scenario,
            module_factory=module_factory,
            controller_factory=lambda s: ModelController(s, model),
        )
        return serialize_trial(trial, scenario)

    done: dict[int, dict] = {}

    def prefix():
        rows = []
        for index in range(len(scenarios)):
            if index not in done:
                break
            rows.append(done[index])
        return rows

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, s): i for i, s in enumerate(scenarios)}
        for future in as_completed(futures):
            done[futures[future]] = future.result()
            checkpoint(prefix())
    return prefix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-per-cell", type=int, default=72)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--i-authorize-spend", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--out", type=Path, default=TRACK_A / "results" / "salience_arm.json"
    )
    args = parser.parse_args()

    if not args.live:
        print(f"DRY RUN. Worst case {WORST_CASE_CALLS} calls, cap {CALL_CAP}, "
              f"estimate $6 to $8 (see PREREG_SALIENCE.md).")
        return 0
    if not args.i_authorize_spend:
        print("Refusing: --live requires --i-authorize-spend.")
        return 1

    import anthropic

    from gwbench.anthropic_model import AnthropicModel

    client = anthropic.Anthropic(max_retries=8)
    client.messages.count_tokens(
        model=FUNDED_MODEL, messages=[{"role": "user", "content": "ping"}]
    )

    shared = dict(
        client=client,
        model=FUNDED_MODEL,
        effort=None,
        cache_dir=TRACK_A.parent / ".api_cache",
    )
    model = AnthropicModel(max_tokens=400, max_calls=CALL_CAP, **shared)
    rater = AnthropicModel(max_tokens=10, max_calls=CALL_CAP, **shared)

    args.out.parent.mkdir(parents=True, exist_ok=True)

    def checkpoint(rows):
        args.out.write_text(json.dumps({"rows": rows}, indent=2))
        print(
            f"checkpoint: {len(rows)}/{2 * args.n_per_cell} trials, "
            f"module {model.usage.calls} calls, rater {rater.usage.calls} calls",
            flush=True,
        )

    rows = run(model, rater, args.n_per_cell, args.workers, checkpoint)
    checkpoint(rows)
    print(
        f"Done. module: {model.usage.input_tokens} in / {model.usage.output_tokens} out; "
        f"rater: {rater.usage.input_tokens} in / {rater.usage.output_tokens} out"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
