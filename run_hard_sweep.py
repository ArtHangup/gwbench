"""Does filtering distractors help? The main experiment.

Design. From capacity 15 upward the required information is complete and
constant: the oracle scores 1.00 at every one of these capacities. The only
thing the capacity dial changes across that range is how many confusable
distractors reach the controller:

    capacity    15   45   60   90  150  unlimited
    distractors  0    0    9   24   48    48

So any decline across that range is distraction cost, not missing information.
Global workspace theory predicts the narrow conditions win.

Two arms, to separate interference from plain context length:

    confusable  distractors are near-twins of required containers
                ("pale_red_box" against "red_box"), so rejecting them
                takes careful matching.
    control     same count, same text volume, but twins of containers that
                are not on the list, so rejecting them is trivial.

Equal decline in both arms means the effect is text volume and the filtering
story is unsupported. A steeper decline in the confusable arm is interference,
which is the thing a bottleneck would be filtering out.

Capacities 0 and 10 are floor checks: the information is genuinely absent there,
so a non-zero score would mean the model is fabricating.

Refusals are retried, then excluded and counted rather than scored zero. They
are transient and cluster in long prompts, so scoring them zero would
manufacture exactly the result this experiment is looking for.
"""

import argparse
import json
import pathlib
import statistics
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from gwbench.anthropic_model import (
    AnthropicModel,
    CallCapExceeded,
    ModelRefusal,
    TruncatedResponse,
)
from gwbench.architectures import WorkspaceAgent
from gwbench.models import OracleSumModel
from gwbench.tasks import HardIntegrationTask

FLOOR_TRIALS = 10
CONTRAST_TRIALS = 60
CYCLES = 3
MAX_TOKENS = 3072

# effort is rejected by models that predate it, so it is per-model.
MODEL_EFFORT = {
    "claude-haiku-4-5": None,
    "claude-sonnet-5": "low",
    "claude-opus-5": "low",
}
PRICES = {
    "claude-haiku-4-5": (1.00 / 1e6, 5.00 / 1e6),
    "claude-sonnet-5": (3.00 / 1e6, 15.00 / 1e6),
    "claude-opus-5": (5.00 / 1e6, 25.00 / 1e6),
}

# Set by main() once the model and difficulty are known.
MODEL = "claude-opus-5"
EFFORT = "low"

N_REQUIRED = 8
N_DISTRACTORS = 48
FLOOR = [0, 10]
CONTRAST = [15, 45, 60, 90, 150, None]
CAPACITIES = FLOOR + CONTRAST
CALL_CAP = 1000
REFUSAL_RETRIES = 3
# Consecutive API failures before declaring an outage and stopping.
ERROR_BREAKER = 8

CACHE_DIR = pathlib.Path(__file__).parent / ".api_cache"
RESULTS = pathlib.Path(__file__).parent / "hard_sweep_results.json"


def filtered_capacity():
    """Narrowest capacity where the oracle still gets every required fact."""
    for cap in range(5, 300, 5):
        scores = [
            WorkspaceAgent(
                OracleSumModel(), capacity_tokens=cap, n_cycles=CYCLES
            ).run(make_task(seed, True)).score
            for seed in range(12)
        ]
        if statistics.fmean(scores) == 1.0:
            return cap
    raise RuntimeError("oracle never reaches 1.00; task is unsolvable as configured")


def trials_for(capacity):
    return FLOOR_TRIALS if capacity in FLOOR else CONTRAST_TRIALS


def make_task(seed, confusable):
    return HardIntegrationTask.generate(
        seed=seed,
        n_required=N_REQUIRED,
        n_distractors=N_DISTRACTORS,
        confusable=confusable,
    )


def oracle_score(capacity, confusable, trials):
    total = 0.0
    for seed in range(trials):
        task = make_task(seed, confusable)
        total += (
            WorkspaceAgent(
                OracleSumModel(), capacity_tokens=capacity, n_cycles=CYCLES
            )
            .run(task)
            .score
        )
    return total / trials


class Outage(RuntimeError):
    """Too many consecutive API failures: stop rather than burn the sweep."""


def run_one(model, task, capacity, state):
    """Returns (score, refused). None score means the trial produced no datum.

    A single failed call is tolerated and recorded rather than aborting the
    whole sweep: one uncacheable failure part-way through should not block
    replay of every condition after it. Consecutive failures trip a circuit
    breaker, so a real outage or an empty account still stops promptly.
    """
    import anthropic

    for attempt in range(REFUSAL_RETRIES):
        try:
            score = WorkspaceAgent(
                model, capacity_tokens=capacity, n_cycles=CYCLES
            ).run(task).score
            state["consecutive_errors"] = 0
            return score, False
        except ModelRefusal:
            if attempt == REFUSAL_RETRIES - 1:
                state["consecutive_errors"] = 0
                return None, True
            time.sleep(1.5 * (attempt + 1))
        except TruncatedResponse:
            state["consecutive_errors"] = 0
            return None, False
        except anthropic.APIStatusError as e:
            state["consecutive_errors"] += 1
            state["last_error"] = f"{type(e).__name__}: {e.message}"
            if state["consecutive_errors"] >= ERROR_BREAKER:
                raise Outage(state["last_error"]) from None
            return None, False
    state["consecutive_errors"] = 0
    return None, True


def sweep(model, confusable, label, points):
    print(f"\n=== {label} ===")
    print(
        f"{'cap':>6} {'distract':>9} {'oracle':>7} {'model':>7} "
        f"{'n':>4} {'refused':>8}   curve"
    )
    print("-" * 74)

    state = {"consecutive_errors": 0, "last_error": None}

    for capacity in CAPACITIES:
        n = trials_for(capacity)
        scores, refusals = [], 0

        for seed in range(n):
            task = make_task(seed, confusable)
            score, refused = run_one(model, task, capacity, state)
            if refused:
                refusals += 1
            elif score is not None:
                scores.append(score)

        mean = statistics.fmean(scores) if scores else float("nan")
        orc = oracle_score(capacity, confusable, n)
        distract = distractors_admitted(capacity, confusable)
        name = "unlim" if capacity is None else str(capacity)
        bar = "#" * round(mean * 20) if scores else "?"
        print(
            f"{name:>6} {distract:>9.0f} {orc:>7.2f} {mean:>7.2f} "
            f"{len(scores):>4} {refusals:>8}   {bar}"
        )
        points.append(
            {
                "capacity": capacity,
                "distractors_admitted": distract,
                "oracle": orc,
                "mean_score": None if not scores else mean,
                "n": len(scores),
                "refusals": refusals,
                "scores": scores,
            }
        )
    return points


def distractors_admitted(capacity, confusable, trials=10):
    from gwbench.models import RecordingModel

    counts = []
    for seed in range(trials):
        task = make_task(seed, confusable)
        rec = RecordingModel(reply="0")
        WorkspaceAgent(rec, capacity_tokens=capacity, n_cycles=CYCLES).run(task)
        prompt = rec.calls[-1]
        counts.append(
            sum(1 for d in task.distractor_modules if task.module_contents[d] in prompt)
        )
    return statistics.fmean(counts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=float, default=40.0)
    parser.add_argument("--model", default="claude-opus-5")
    parser.add_argument("--required", type=int, default=8)
    parser.add_argument("--distractors", type=int, default=48)
    parser.add_argument("--results", default=None)
    args = parser.parse_args()

    global MODEL, EFFORT, N_REQUIRED, N_DISTRACTORS, FLOOR, CONTRAST, CAPACITIES, RESULTS
    MODEL = args.model
    EFFORT = MODEL_EFFORT.get(MODEL, "low")
    N_REQUIRED = args.required
    N_DISTRACTORS = args.distractors
    if args.results:
        RESULTS = pathlib.Path(__file__).parent / args.results

    # Capacities are pinned to the oracle ceiling for this difficulty, so
    # "filtered" always means every required fact arrives and no distractor does.
    base = filtered_capacity()
    FLOOR = [0, max(5, base - 5)]
    CONTRAST = [base, base * 3, base * 4, base * 6, base * 10, None]
    CAPACITIES = FLOOR + CONTRAST
    print(f"model {MODEL} (effort={EFFORT})  required={N_REQUIRED} "
          f"distractors={N_DISTRACTORS}")
    print(f"oracle ceiling at capacity {base}; sweeping {CAPACITIES}")

    model = AnthropicModel(
        model=MODEL,
        effort=EFFORT,
        max_tokens=MAX_TOKENS,
        cache_dir=CACHE_DIR,
        max_calls=CALL_CAP,
    )

    import anthropic

    results = {"confusable": [], "control": []}
    aborted = None
    try:
        sweep(model, True, "confusable distractors", results["confusable"])
        sweep(model, False, "control (non-confusable)", results["control"])
    except CallCapExceeded:
        aborted = f"call cap {CALL_CAP} reached"
    except Outage as e:
        # Billing exhaustion, rate limits, outages. Completed conditions are
        # still valid data and every response so far is cached, so a resumed
        # run replays them for free.
        aborted = str(e)
    except KeyboardInterrupt:
        aborted = "interrupted"

    if aborted:
        print(f"\n!! stopped early: {aborted}")
        print("   completed conditions below are valid; cached calls replay free")

    u = model.usage
    pin, pout = PRICES.get(MODEL, PRICES["claude-opus-5"])
    cost = u.input_tokens * pin + u.output_tokens * pout
    print("\n=== spend ===")
    print(f"api calls      {u.calls}")
    print(f"input tokens   {u.input_tokens:,}")
    print(f"output tokens  {u.output_tokens:,}")
    print(f"actual cost    ${cost:.2f}  (budget ${args.budget:.0f})")

    out_path.write_text(
        json.dumps(
            {
                "config": {
                    "model": args.model,
                    "effort": args.effort,
                    "max_tokens": MAX_TOKENS,
                    "cycles": CYCLES,
                    "n_required": N_REQUIRED,
                    "effort": EFFORT,
                    "n_distractors": N_DISTRACTORS,
                    "capacities": CAPACITIES,
                    "floor_trials": FLOOR_TRIALS,
                    "contrast_trials": CONTRAST_TRIALS,
                },
                "usage": {
                    "calls": u.calls,
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "estimated_cost_usd": round(cost, 4),
                },
                "aborted": aborted,
                "results": results,
            },
            indent=2,
        )
    )
    print(f"wrote {out_path.name}")


if __name__ == "__main__":
    main()
