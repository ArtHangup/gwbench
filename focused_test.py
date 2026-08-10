"""High-power test of the one comparison that matters.

The full sweep found the right regime but could not settle the headline
question: within the confusable arm, filtered scored 0.600 and flooded 0.533,
a +0.067 benefit at p=0.30. An effect that size needs roughly 866 trials per
condition for 80% power, and the sweep had 120.

So this drops every intermediate capacity and spends the trials on four
conditions only:

                    filtered (cap 20, 0 distractors)   flooded (unlimited, 48)
    confusable                    A                              B
    control                       C                              D

A-B is the bottleneck benefit. Comparing it against C-D is the difference in
differences, which is what separates interference from context length: flooding
also lengthens the prompt, and only the control arm holds that constant.

Powering the difference in differences is the binding constraint, since its
variance is the sum of four conditions rather than two. At the observed effect
that needs roughly 500 per cell.
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
N_DISTRACTORS = 48
CYCLES = 3
MAX_TOKENS = 3072
FILTERED_CAP = 20
FLOODED_CAP = None
PRICE = (1.00 / 1e6, 5.00 / 1e6)

CACHE_DIR = pathlib.Path(__file__).parent / ".api_cache"
RESULTS = pathlib.Path(__file__).parent / "focused_results.json"


def z2p(s1, n1, s2, n2):
    p1, p2 = s1 / n1, s2 / n2
    pool = (s1 + s2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return p1, p2, 0.0, 1.0
    z = (p1 - p2) / se
    return p1, p2, z, math.erfc(abs(z) / math.sqrt(2))


def one_trial(model, confusable, capacity, seed, cycles=None):
    task = HardIntegrationTask.generate(
        seed=seed,
        n_required=N_REQUIRED,
        n_distractors=N_DISTRACTORS,
        confusable=confusable,
    )
    try:
        return WorkspaceAgent(
            model, capacity_tokens=capacity, n_cycles=cycles or CYCLES
        ).run(task).score
    except ModelRefusal:
        return "refused"
    except TruncatedResponse:
        return None


def cell(model, confusable, capacity, trials, seed0, workers, cycles=None):
    """Run one cell concurrently.

    Trials are independent, so the only shared state is the model's counters
    and cache, which are locked. Concurrency is what makes a properly powered
    run finish in minutes rather than hours.
    """
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = list(pool.map(
            lambda s: one_trial(model, confusable, capacity, s, cycles),
            range(seed0, seed0 + trials),
        ))
    scores = [x for x in out if isinstance(x, float)]
    refusals = sum(1 for x in out if x == "refused")
    return scores, refusals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=500)
    ap.add_argument("--max-calls", type=int, default=12000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--flooded-cycles", type=int, default=None,
                    help="cycles for the flooded cells; use 1 to match the "
                         "filtered cells on required-fact repetition")
    ap.add_argument("--results", default=None)
    args = ap.parse_args()

    global RESULTS
    if args.results:
        RESULTS = pathlib.Path(__file__).parent / args.results

    model = AnthropicModel(
        model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS,
        cache_dir=CACHE_DIR, max_calls=args.max_calls,
    )

    print(f"{MODEL}, {N_REQUIRED} required, {N_DISTRACTORS} distractors, "
          f"{args.trials} trials per cell\n")

    cells, aborted = {}, None
    try:
        for arm, conf in [("confusable", True), ("control", False)]:
            for cond, cap in [("filtered", FILTERED_CAP), ("flooded", FLOODED_CAP)]:
                cyc = args.flooded_cycles if cond == "flooded" else None
                t0 = time.time()
                scores, refusals = cell(
                    model, conf, cap, args.trials, 0, args.workers, cyc)
                cells[f"{arm}/{cond}"] = {"scores": scores, "refusals": refusals}
                print(f"  {arm:>11} {cond:>8}: {statistics.fmean(scores):.3f} "
                      f"(n={len(scores)}, refused {refusals}, "
                      f"{time.time() - t0:.0f}s)", flush=True)
    except CallCapExceeded:
        aborted = "call cap reached"
    except Exception as e:  # noqa: BLE001
        aborted = f"{type(e).__name__}: {str(e)[:120]}"
    if aborted:
        print(f"\n!! stopped early: {aborted}")

    def tot(key):
        c = cells.get(key)
        return (sum(c["scores"]), len(c["scores"])) if c else (0, 0)

    have = all(k in cells for k in
               ("confusable/filtered", "confusable/flooded",
                "control/filtered", "control/flooded"))
    if have:
        a, na = tot("confusable/filtered")
        b, nb = tot("confusable/flooded")
        c, nc = tot("control/filtered")
        dd, nd = tot("control/flooded")

        print("\n=== the headline ===")
        p1, p2, z, p = z2p(a, na, b, nb)
        print(f"confusable: filtered {p1:.3f} vs flooded {p2:.3f}   "
              f"benefit {p1 - p2:+.3f}  z={z:.2f}  p={p:.4f}")
        q1, q2, z2, p2v = z2p(c, nc, dd, nd)
        print(f"   control: filtered {q1:.3f} vs flooded {q2:.3f}   "
              f"benefit {q1 - q2:+.3f}  z={z2:.2f}  p={p2v:.4f}")

        did = (p1 - p2) - (q1 - q2)
        se = math.sqrt(sum(x * (1 - x) / n for x, n in
                           ((p1, na), (p2, nb), (q1, nc), (q2, nd))))
        zd = did / se if se else 0.0
        pd = math.erfc(abs(zd) / math.sqrt(2))
        print(f"\ndifference in differences: {did:+.3f}  z={zd:.2f}  p={pd:.4f}")
        print("  positive and significant -> the bottleneck removes interference")
        print("  near zero                -> flooding costs only context length")

    u = model.usage
    cost = u.input_tokens * PRICE[0] + u.output_tokens * PRICE[1]
    print(f"\ncalls {u.calls}  cost ${cost:.2f}")

    RESULTS.write_text(json.dumps(
        {"config": {"model": MODEL, "n_required": N_REQUIRED,
                    "n_distractors": N_DISTRACTORS, "trials": args.trials,
                    "filtered_cap": FILTERED_CAP, "cycles": CYCLES,
                    "flooded_cycles": args.flooded_cycles},
         "aborted": aborted,
         "usage": {"calls": u.calls, "input_tokens": u.input_tokens,
                   "output_tokens": u.output_tokens,
                   "estimated_cost_usd": round(cost, 4)},
         "cells": cells}, indent=2))
    print(f"wrote {RESULTS.name}")


if __name__ == "__main__":
    main()
