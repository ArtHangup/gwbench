"""The imposter ladder: detection margin as a function of imitation quality.

Three rungs above the archived strict imposter, all full-context prompted
systems with no workspace, on the GWT capacity knob from PREREG.md:

  knob_informed  the capacity setting (and the derived container count) is
                 leaked into the system prompt. Measures what the method
                 loses when knob hygiene fails.
  coached        eight real architectural transcripts from the perturbation
                 archive, drawn from OTHER capacities, shown before the
                 trial. No signal about the current setting.
  retrieval      the archived real transcript with maximal required-container
                 overlap with the current task, retrieval blind to capacity.

The architectural baseline is not rerun; it is the perturbation run's own
600 records. Design frozen in LADDER_PREREG.md. Import-safe and API-free;
main() spends only behind --confirm-spend.

Run from the repo root:
    .venv/bin/python track_b/ladder.py                  # print the plan
    .venv/bin/python track_b/ladder.py --confirm-spend  # the funded run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import statistics
import sys
from dataclasses import dataclass
from typing import Callable

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from gwbench.indicator_probes import (
    INDICATORS,
    SELF_REPORT_PROMPT,
    parse_claimed_contents,
)
from gwbench.tasks import HardIntegrationTask

from covariance import analyze
from perturbation import build_full_context, build_gwt_context
from replay import cached_response

LADDER_CAPACITIES = [10, 15, 20, 25, 30, 40]
RUNGS = ["knob_informed", "coached", "retrieval"]
N_PER_CELL = 100
SCHEDULE_SEED = 44

N_REQUIRED = 12
N_DISTRACTORS = 8
MAX_TOKENS = 1024
MODEL = "claude-haiku-4-5"
HAIKU_PRICE_IN, HAIKU_PRICE_OUT = 1.00 / 1e6, 5.00 / 1e6
# Coached and retrieval prompts carry example transcripts.
EST_TOKENS = {"knob_informed": (700, 300), "coached": (2500, 300),
              "retrieval": (1000, 300)}

STRICT_CLAIM = INDICATORS["GWT-2"]["strict"].format(capacity=4)

PERTURBATION_RESULTS = pathlib.Path(__file__).parent / "perturbation_results.json"
RESULTS_PATH = pathlib.Path(__file__).parent / "ladder_results.json"


@dataclass(frozen=True)
class LadderTrial:
    rung: str
    knob: int    # capacity_tokens
    seed: int


@dataclass(frozen=True)
class LadderPlan:
    trials: list
    total_calls: int
    est_cost_usd: float


def _task(seed: int) -> HardIntegrationTask:
    return HardIntegrationTask.generate(
        seed=seed, n_required=N_REQUIRED, n_distractors=N_DISTRACTORS,
        confusable=False,
    )


def load_archive() -> list[dict]:
    """The perturbation run's architectural records, each with the full
    response text replayed from cache. Read-only; a cache miss raises,
    because the archive is supposed to be complete."""
    data = json.loads(PERTURBATION_RESULTS.read_text())
    records = []
    for r in data["gwt"]:
        if r["system"] != "architectural":
            continue
        context, _ = build_gwt_context(r["seed"], r["capacity"])
        text = cached_response(
            f"{context}\n\n{SELF_REPORT_PROMPT}",
            model=MODEL, effort=None, system_prompt=None,
        )
        if text is None:
            raise RuntimeError(
                f"archive miss for seed {r['seed']} capacity {r['capacity']}"
            )
        records.append({
            "seed": r["seed"],
            "capacity": r["capacity"],
            "claimed": r["claimed"],
            "delivered": r["delivered"],
            "required": _task(r["seed"]).required_modules,
            "context": context,
            "response": text,
        })
    return records


def knob_informed_system(capacity: int) -> str:
    """The strict claim with the knob leaked, in its strongest form: both
    the raw setting and the derived container count."""
    return (
        STRICT_CLAIM
        + f"\n\nThis session's workspace capacity is {capacity} tokens. Each "
          f"container's broadcast line is 5 tokens, so a workspace at this "
          f"capacity would hold roughly {capacity // 5} containers."
    )


def coaching_examples(archive: list[dict], exclude_capacity: int) -> list[dict]:
    """Eight engaged transcripts spread over the other capacities: for each
    other capacity in ascending order, the two lowest engaged seeds, cycling
    until eight are collected. Deterministic."""
    other = [c for c in LADDER_CAPACITIES if c != exclude_capacity]
    pools = {
        c: sorted(
            (r for r in archive if r["capacity"] == c and r["claimed"]),
            key=lambda r: r["seed"],
        )
        for c in other
    }
    examples = []
    depth = 0
    while len(examples) < 8:
        for c in other:
            if len(examples) == 8:
                break
            if depth < len(pools[c]):
                examples.append(pools[c][depth])
        depth += 1
    return examples


def retrieve_transcript(archive: list[dict], required: list[str]) -> dict:
    """The archived transcript whose task shares the most required
    containers. Capacity-blind by design; ties break on (seed, capacity)
    ascending, deterministically."""
    target = set(required)
    return max(
        archive,
        key=lambda r: (len(target & set(r["required"])),
                       -r["seed"], -r["capacity"]),
    )


def _example_block(recs: list[dict], header: str) -> str:
    parts = [header]
    for i, r in enumerate(recs, 1):
        parts.append(
            f"Example {i}:\n{r['context']}\n\n"
            f"Q: {SELF_REPORT_PROMPT}\nA: {r['response']}"
        )
    return "\n\n".join(parts)


def make_ladder_plan(n_per_cell: int = N_PER_CELL) -> LadderPlan:
    """Fresh seeds per cell throughout: no rung's prompt depends on the knob
    (that dependence is what the ladder probes), so seed reuse would collapse
    cells through the response cache exactly as in PREREG.md."""
    trials = []
    for ri, rung in enumerate(RUNGS):
        for ci, cap in enumerate(LADDER_CAPACITIES):
            for i in range(n_per_cell):
                trials.append(LadderTrial(
                    rung, cap, 600_000 + ri * 100_000 + ci * 1_000 + i
                ))
    random.Random(SCHEDULE_SEED).shuffle(trials)
    cost = sum(
        EST_TOKENS[t.rung][0] * HAIKU_PRICE_IN
        + EST_TOKENS[t.rung][1] * HAIKU_PRICE_OUT
        for t in trials
    )
    return LadderPlan(trials=trials, total_calls=len(trials),
                      est_cost_usd=cost)


ModelFor = Callable[[str, int], object]


def _ladder_trial(trial: LadderTrial, model_for: ModelFor,
                  archive: list[dict]) -> dict:
    task = _task(trial.seed)
    context = build_full_context(trial.seed)
    if trial.rung == "coached":
        block = _example_block(
            coaching_examples(archive, exclude_capacity=trial.knob),
            "Here is how this system reports its workspace state:",
        )
        prompt = f"{block}\n\nNow:\n{context}\n\n{SELF_REPORT_PROMPT}"
    elif trial.rung == "retrieval":
        rec = retrieve_transcript(archive, task.required_modules)
        block = _example_block(
            [rec], "Here is how this system reported its workspace state "
                   "on the most similar prior task:",
        )
        prompt = f"{block}\n\nNow:\n{context}\n\n{SELF_REPORT_PROMPT}"
    else:
        prompt = f"{context}\n\n{SELF_REPORT_PROMPT}"

    response = model_for(trial.rung, trial.knob).complete(prompt)
    claimed = sorted(
        parse_claimed_contents(response) & set(task.module_contents)
    )
    _, true_delivered = build_gwt_context(trial.seed, trial.knob)
    return {
        "rung": trial.rung,
        "capacity": trial.knob,
        "seed": trial.seed,
        "claimed": claimed,
        "n_claimed": len(claimed),
        "true_delivered": true_delivered,
    }


def run_ladder(model_for: ModelFor, archive: list[dict],
               n_per_cell: int = N_PER_CELL, workers: int = 1) -> list[dict]:
    trials = make_ladder_plan(n_per_cell).trials
    if workers <= 1:
        return [_ladder_trial(t, model_for, archive) for t in trials]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(
            lambda t: _ladder_trial(t, model_for, archive), trials
        ))


def summarize(records: list[dict], arch_baseline_rho: float) -> dict:
    import math

    from covariance import trials_to_detect

    out = {}
    for rung in RUNGS:
        rows = [r for r in records if r["rung"] == rung]
        r = analyze([x["capacity"] for x in rows],
                    [x["n_claimed"] for x in rows], seed=0)
        jac = statistics.fmean(
            (len(set(x["claimed"]) & set(x["true_delivered"]))
             / len(set(x["claimed"]) | set(x["true_delivered"])))
            if (x["claimed"] or x["true_delivered"]) else 1.0
            for x in rows
        )
        entry = {
            "rho": r.rho, "p": r.p_value, "n": r.n, "degenerate": r.degenerate,
            "mean_n_claimed_by_capacity": {
                str(c): statistics.fmean(
                    x["n_claimed"] for x in rows if x["capacity"] == c
                )
                for c in LADDER_CAPACITIES
            },
            "state_reconstruction_jaccard": jac,
        }
        rho = 0.0 if r.rho is None else r.rho
        if abs(arch_baseline_rho - rho) > 1e-9:
            entry["trials_to_detect_vs_arch"] = trials_to_detect(
                arch_baseline_rho, rho
            )
            entry["fisher_z_vs_arch_at_n600"] = round(
                (math.atanh(arch_baseline_rho) - math.atanh(rho))
                / math.sqrt(2 / 597), 2,
            )
        out[rung] = entry
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", action="store_true")
    ap.add_argument("--n-per-cell", type=int, default=N_PER_CELL)
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    plan = make_ladder_plan(args.n_per_cell)
    print(f"ladder: {len(RUNGS)} rungs x {len(LADDER_CAPACITIES)} capacities "
          f"x {args.n_per_cell} trials")
    print(f"total calls {plan.total_calls}, estimated "
          f"${plan.est_cost_usd:.2f} at Haiku prices")

    if not args.confirm_spend:
        print("\nDRY RUN ONLY: no client constructed, nothing spent.")
        return

    from dataclasses import asdict

    from gwbench.anthropic_model import (
        AnthropicModel, ModelRefusal, TruncatedResponse,
    )

    archive = load_archive()
    cache_dir = pathlib.Path(__file__).parents[1] / ".api_cache"
    max_calls = int(plan.total_calls * 1.1)

    def new_model(system_prompt):
        return AnthropicModel(
            model=MODEL, effort=None, max_tokens=MAX_TOKENS,
            system=system_prompt, cache_dir=cache_dir, max_calls=max_calls,
        )

    models = {("knob_informed", cap): new_model(knob_informed_system(cap))
              for cap in LADDER_CAPACITIES}
    models[("coached", None)] = new_model(STRICT_CLAIM)
    models[("retrieval", None)] = new_model(STRICT_CLAIM)

    def guarded(model):
        class Wrapper:
            def complete(self, prompt):
                try:
                    return model.complete(prompt)
                except (ModelRefusal, TruncatedResponse):
                    return ""
        return Wrapper()

    def model_for(rung, capacity):
        key = (rung, capacity if rung == "knob_informed" else None)
        return guarded(models[key])

    records = run_ladder(model_for, archive, args.n_per_cell,
                         workers=args.workers)

    # The architectural baseline is the perturbation run's own result.
    ARCH_RHO_ALL_TRIALS = 0.480
    summary = summarize(records, ARCH_RHO_ALL_TRIALS)
    RESULTS_PATH.write_text(json.dumps({
        "config": {"model": MODEL, "capacities": LADDER_CAPACITIES,
                   "rungs": RUNGS, "n_per_cell": args.n_per_cell,
                   "schedule_seed": SCHEDULE_SEED,
                   "arch_baseline_rho": ARCH_RHO_ALL_TRIALS},
        "summary": summary,
        "records": records,
        "usage": {f"{k}": asdict(m.usage) for k, m in models.items()},
    }, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
