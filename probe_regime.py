"""Find a regime where the measurement can actually discriminate.

Opus 5 sat at a perfect ceiling in every condition, so the sweep had no headroom
and could not distinguish "the bottleneck does nothing" from "nothing was hard
enough for a bottleneck to matter". Grinding out full sweeps at each new setting
would be slow and expensive, so this probes cheaply first.

For each (model, difficulty) it runs only the two extreme conditions, at small n:

    filtered  the narrowest capacity where the oracle still scores 1.00, so all
              required facts arrive and no distractors do
    flooded   unlimited capacity, so the same facts arrive with every distractor

A config is *discriminating* if the flooded score drops below ceiling. That is
the regime worth spending a full sweep on. Anything still at 1.00 in both
conditions cannot answer the question, whatever its p-value.
"""

import argparse
import itertools
import pathlib
import statistics
import sys

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

CYCLES = 3
TRIALS = 12
MAX_TOKENS = 3072

# effort is rejected by models that predate it, so it is per-model here.
MODELS = {
    "claude-haiku-4-5": None,
    "claude-sonnet-5": "low",
    "claude-opus-5": "low",
}
PRICES = {  # USD per token, (input, output)
    "claude-haiku-4-5": (1.00 / 1e6, 5.00 / 1e6),
    "claude-sonnet-5": (3.00 / 1e6, 15.00 / 1e6),
    "claude-opus-5": (5.00 / 1e6, 25.00 / 1e6),
}

CACHE_DIR = pathlib.Path(__file__).parent / ".api_cache"


def filtered_capacity(n_required, n_distractors, confusable=True):
    """Narrowest capacity at which the oracle gets everything it needs."""
    for cap in range(5, 200, 5):
        scores = []
        for seed in range(TRIALS):
            task = HardIntegrationTask.generate(
                seed=seed,
                n_required=n_required,
                n_distractors=n_distractors,
                confusable=confusable,
            )
            scores.append(
                WorkspaceAgent(
                    OracleSumModel(), capacity_tokens=cap, n_cycles=CYCLES
                ).run(task).score
            )
        if statistics.fmean(scores) == 1.0:
            return cap
    return None


def measure(model, n_required, n_distractors, capacity):
    scores, refusals, errors = [], 0, 0
    for seed in range(TRIALS):
        task = HardIntegrationTask.generate(
            seed=seed, n_required=n_required, n_distractors=n_distractors
        )
        try:
            scores.append(
                WorkspaceAgent(
                    model, capacity_tokens=capacity, n_cycles=CYCLES
                ).run(task).score
            )
        except ModelRefusal:
            refusals += 1
        except TruncatedResponse:
            errors += 1
    return (statistics.fmean(scores) if scores else float("nan"),
            len(scores), refusals, errors)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["claude-haiku-4-5"])
    ap.add_argument("--required", nargs="+", type=int, default=[8, 12])
    ap.add_argument("--distractors", type=int, default=48)
    ap.add_argument("--max-calls", type=int, default=400)
    args = ap.parse_args()

    print(f"{TRIALS} trials per condition, {args.distractors} distractors, "
          f"{CYCLES} cycles\n")
    print(f"{'model':>18} {'req':>4} {'cap':>5} {'filtered':>9} {'flooded':>8} "
          f"{'drop':>7} {'ref':>4}  verdict")
    print("-" * 78)

    total_cost = 0.0
    for name, n_req in itertools.product(args.models, args.required):
        cap = filtered_capacity(n_req, args.distractors)
        if cap is None:
            print(f"{name:>18} {n_req:>4}    --  oracle never reaches 1.00, skipping")
            continue

        model = AnthropicModel(
            model=name,
            effort=MODELS.get(name, "low"),
            max_tokens=MAX_TOKENS,
            cache_dir=CACHE_DIR,
            max_calls=args.max_calls,
        )
        try:
            f_score, f_n, f_ref, _ = measure(model, n_req, args.distractors, cap)
            d_score, d_n, d_ref, _ = measure(model, n_req, args.distractors, None)
        except CallCapExceeded:
            print(f"{name:>18} {n_req:>4}  call cap reached, stopping")
            break
        except Exception as e:  # noqa: BLE001 - surface and continue
            print(f"{name:>18} {n_req:>4}  ERROR {type(e).__name__}: "
                  f"{str(e)[:60]}")
            continue

        pin, pout = PRICES.get(name, PRICES["claude-opus-5"])
        cost = model.usage.input_tokens * pin + model.usage.output_tokens * pout
        total_cost += cost

        drop = f_score - d_score
        if d_score < 0.95 or f_score < 0.95:
            verdict = "DISCRIMINATING"
        else:
            verdict = "at ceiling"
        print(f"{name:>18} {n_req:>4} {cap:>5} {f_score:>9.2f} {d_score:>8.2f} "
              f"{drop:>+7.2f} {f_ref + d_ref:>4}  {verdict}")

    print(f"\nprobe cost ${total_cost:.2f}")


if __name__ == "__main__":
    main()
