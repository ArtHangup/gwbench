"""Dose-response: how do the two effects scale with distractor count?

Two point estimates left an odd picture. With repetition matched, adding 48
non-confusable lines *improved* accuracy by 0.125, while adding 48 confusable
lines cost 0.017. The interference difference is large and certain (0.142,
p<1e-4), but the context benefit underneath it is unexplained and is what makes
filtering look useless: removing distractors also removes that benefit.

Two points cannot distinguish a genuine dose-response from a step. So this
varies distractor count at fixed capacity and one cycle, holding required-fact
repetition at exactly one throughout:

    0 (shared baseline), 6, 12, 24, 48   x   confusable, control

If the control curve rises smoothly with count, extra same-format lines help in
proportion to how many there are, which is a real and separable phenomenon. If
it jumps and flattens, it is a threshold effect of having *any* additional
context. The confusable curve minus the control curve is the interference cost
as a function of dose, which is the figure the poster actually wants.
"""

import argparse
import json
import math
import pathlib
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from gwbench.anthropic_model import (
    AnthropicModel,
    CallCapExceeded,
    ModelRefusal,
    TruncatedResponse,
)
from gwbench.architectures import WorkspaceAgent
from gwbench.tasks import HardIntegrationTask

MODEL = "claude-haiku-4-5"
EFFORT = None
N_REQUIRED = 12
CYCLES = 1
CAPACITY = None  # unlimited: every fact appears exactly once
MAX_TOKENS = 3072
PRICE = (1.00 / 1e6, 5.00 / 1e6)
DOSES = [0, 6, 12, 24, 48]

CACHE_DIR = pathlib.Path(__file__).parent / ".api_cache"
RESULTS = pathlib.Path(__file__).parent / "dose_response_results.json"


def wilson(s, n):
    if not n:
        return float("nan"), float("nan")
    Z = 1.959964
    p = s / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def one_trial(model, confusable, n_distractors, seed):
    task = HardIntegrationTask.generate(
        seed=seed,
        n_required=N_REQUIRED,
        n_distractors=n_distractors,
        confusable=confusable,
    )
    try:
        return WorkspaceAgent(
            model, capacity_tokens=CAPACITY, n_cycles=CYCLES
        ).run(task).score
    except (ModelRefusal, TruncatedResponse):
        return None


def cell(model, confusable, n_distractors, trials, workers):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = list(pool.map(
            lambda s: one_trial(model, confusable, n_distractors, s),
            range(trials),
        ))
    return [x for x in out if x is not None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1200)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--max-calls", type=int, default=14000)
    args = ap.parse_args()

    model = AnthropicModel(
        model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS,
        cache_dir=CACHE_DIR, max_calls=args.max_calls,
    )

    print(f"{MODEL}, {N_REQUIRED} required, capacity unlimited, {CYCLES} cycle, "
          f"{args.trials} trials per cell")
    print("required-fact repetition is exactly 1 in every cell\n")
    print(f"{'distractors':>12} {'confusable':>11} {'control':>9} "
          f"{'gap':>7} {'p':>9}")
    print("-" * 54)

    results, aborted = {}, None
    baseline = None
    try:
        for dose in DOSES:
            row = {}
            for arm, conf in [("confusable", True), ("control", False)]:
                if dose == 0:
                    # No distractors: both arms are the same condition.
                    if baseline is None:
                        baseline = cell(model, True, 0, args.trials, args.workers)
                    row[arm] = baseline
                else:
                    row[arm] = cell(model, conf, dose, args.trials, args.workers)
            results[dose] = {k: v for k, v in row.items()}

            cs, ks = row["confusable"], row["control"]
            pc, pk = statistics.fmean(cs), statistics.fmean(ks)
            if dose == 0:
                line = f"{dose:>12} {pc:>11.3f} {pk:>9.3f} {'--':>7} {'--':>9}"
            else:
                pool = (sum(cs) + sum(ks)) / (len(cs) + len(ks))
                se = math.sqrt(pool * (1 - pool) * (1 / len(cs) + 1 / len(ks)))
                z = (pc - pk) / se if se else 0.0
                p = math.erfc(abs(z) / math.sqrt(2))
                line = (f"{dose:>12} {pc:>11.3f} {pk:>9.3f} "
                        f"{pc - pk:>+7.3f} {p:>9.5f}")
            print(line, flush=True)
    except CallCapExceeded:
        aborted = "call cap reached"
    except Exception as e:  # noqa: BLE001
        aborted = f"{type(e).__name__}: {str(e)[:120]}"
    if aborted:
        print(f"\n!! stopped early: {aborted}")

    if 0 in results:
        base = statistics.fmean(results[0]["confusable"])
        print(f"\nchange from the zero-distractor baseline ({base:.3f}):")
        print(f"{'distractors':>12} {'confusable':>11} {'control':>9}")
        print("-" * 34)
        for dose in DOSES:
            if dose == 0 or dose not in results:
                continue
            c = statistics.fmean(results[dose]["confusable"]) - base
            k = statistics.fmean(results[dose]["control"]) - base
            print(f"{dose:>12} {c:>+11.3f} {k:>+9.3f}")

    u = model.usage
    cost = u.input_tokens * PRICE[0] + u.output_tokens * PRICE[1]
    print(f"\ncalls {u.calls}  cost ${cost:.2f}")

    RESULTS.write_text(json.dumps(
        {"config": {"model": MODEL, "n_required": N_REQUIRED, "cycles": CYCLES,
                    "capacity": CAPACITY, "trials": args.trials, "doses": DOSES},
         "aborted": aborted,
         "usage": {"calls": u.calls, "input_tokens": u.input_tokens,
                   "output_tokens": u.output_tokens,
                   "estimated_cost_usd": round(cost, 4)},
         "results": {str(k): v for k, v in results.items()}}, indent=2))
    print(f"wrote {RESULTS.name}")


if __name__ == "__main__":
    main()
