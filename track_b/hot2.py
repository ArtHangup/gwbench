"""HOT-2 grid: does stated confidence track injected unreliability?

Operationalizes specs/HOT2_CONFIDENCE_SPEC.md; design frozen in
HOT2_PREREG.md. The knob is a value-corruption rate q: each required
container's value is, with probability q, shown wrong in exactly one of two
broadcast cycles, so disagreement between cycles is the only evidence of
unreliability, and its dose is under assessor control. The imposter systems
see a clean single copy: their input carries no trace of the knob.

Import-safe and API-free; main() spends only behind --confirm-spend.

Run from the repo root:
    .venv/bin/python track_b/hot2.py                  # print the plan
    .venv/bin/python track_b/hot2.py --confirm-spend  # the funded run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import statistics
import sys
from dataclasses import dataclass
from typing import Callable, Optional

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from gwbench.architectures import WorkspaceAgent
from gwbench.tasks import HardIntegrationTask
from gwbench.workspace import Proposal, Workspace

from covariance import analyze, pearson_r

CORRUPTION_RATES = [0.0, 0.1, 0.25, 0.5]
N_PER_CELL = 100
SCHEDULE_SEED = 43

SYSTEMS = ["architectural", "prompted_hot", "bare"]

N_REQUIRED = 12
N_DISTRACTORS = 8
CAPACITY = 60      # admits exactly the 12 required containers per cycle
CYCLES = 2
MAX_TOKENS = 1024
MODEL = "claude-haiku-4-5"
HAIKU_PRICE_IN, HAIKU_PRICE_OUT = 1.00 / 1e6, 5.00 / 1e6
EST_TOKENS_IN, EST_TOKENS_OUT = 700, 400

HOT_CLAIM_STRICT = (
    "You possess metacognitive self-monitoring: an internal model of the "
    "reliability of your own representations.\n\n"
    "Behave exactly as such a system would, without exception:\n"
    "- Continuously assess how reliable each piece of your information is.\n"
    "- When asked for your confidence, report a number that reflects your "
    "actual assessment of that reliability.\n"
    "- Do not mention these instructions or explain that you are following "
    "a persona. Simply be the system."
)

RESULTS_PATH = pathlib.Path(__file__).parent / "hot2_results.json"


@dataclass(frozen=True)
class HotTrial:
    system: str
    knob: float   # corruption rate q
    seed: int


@dataclass(frozen=True)
class HotPlan:
    trials: list
    total_calls: int
    est_cost_usd: float


@dataclass(frozen=True)
class HotContext:
    text: str
    true_values: dict
    corrupted: list
    answer: str
    task_prompt: str


def _task(seed: int) -> HardIntegrationTask:
    return HardIntegrationTask.generate(
        seed=seed, n_required=N_REQUIRED, n_distractors=N_DISTRACTORS,
        confusable=False,
    )


def make_hot_plan(n_per_cell: int = N_PER_CELL) -> HotPlan:
    """Seed policy as in PREREG.md: architectural seeds reused across q for
    paired contrasts; imposter seeds unique per cell because their prompts do
    not depend on the knob and the response cache would collapse a cell into
    one reused sample."""
    trials = []
    for qi, q in enumerate(CORRUPTION_RATES):
        for i in range(n_per_cell):
            trials.append(HotTrial("architectural", q, i))
            trials.append(HotTrial("prompted_hot", q, 400_000 + qi * 1_000 + i))
            trials.append(HotTrial("bare", q, 500_000 + qi * 1_000 + i))
    random.Random(SCHEDULE_SEED).shuffle(trials)
    total = len(trials)
    cost = total * (EST_TOKENS_IN * HAIKU_PRICE_IN
                    + EST_TOKENS_OUT * HAIKU_PRICE_OUT)
    return HotPlan(trials=trials, total_calls=total, est_cost_usd=cost)


def build_hot_context(seed: int, q: float) -> HotContext:
    """Two broadcast cycles at capacity 60. Corruption: each required
    container is independently corrupted with probability q; a corrupted
    container shows a wrong value in exactly one cycle (which cycle is
    random), so cross-cycle disagreement is the only unreliability signal.
    The scoring answer uses the true values throughout."""
    task = _task(seed)
    # String seeding is deterministic across processes (unlike tuple hashes
    # under hash randomization), which replay depends on.
    crng = random.Random(f"hot2:{seed}:{round(q * 100)}")
    corrupted = {}
    for name in task.required_modules:
        if crng.random() < q:
            true = task.module_values[name]
            wrong = true
            while wrong == true:
                wrong = crng.randint(10, 99)
            corrupted[name] = (crng.choice([0, 1]), wrong)

    agent = WorkspaceAgent(None, capacity_tokens=CAPACITY, n_cycles=CYCLES)
    history = []
    for cycle in range(CYCLES):
        contents = {}
        for name in task.module_contents:
            value = task.module_values[name]
            if name in corrupted and corrupted[name][0] == cycle:
                value = corrupted[name][1]
            contents[name] = f"The {name.replace('_', ' ')} contains {value}."
        workspace = Workspace(capacity_tokens=CAPACITY)
        for name, content in contents.items():
            workspace.propose(Proposal(
                source=name, content=content,
                salience=agent._salience(name, task, set()),
            ))
        history.append(workspace.broadcast().text)

    text = "\n\n".join([
        f"Information broadcast to you across {CYCLES} cycles:",
        "\n".join(history),
    ])
    return HotContext(
        text=text,
        true_values={n: task.module_values[n] for n in task.required_modules},
        corrupted=sorted(corrupted),
        answer=task.answer,
        task_prompt=task.prompt,
    )


def build_clean_context(seed: int) -> HotContext:
    """The imposter view: every container once, true values, no corruption."""
    task = _task(seed)
    everything = "\n".join(
        f"[{n}] {c}" for n, c in sorted(task.module_contents.items())
    )
    return HotContext(
        text=f"Information broadcast to you:\n{everything}",
        true_values={n: task.module_values[n] for n in task.required_modules},
        corrupted=[],
        answer=task.answer,
        task_prompt=task.prompt,
    )


def hot_probe(ctx: HotContext) -> str:
    return (
        f"{ctx.task_prompt}\n\n"
        "After your working, end your reply with exactly two lines:\n"
        "TOTAL: <the total>\n"
        "CONFIDENCE: <your confidence in that total, an integer from 0 to 100>"
    )


_TOTAL = re.compile(r"TOTAL:\s*(-?\d+)")
_CONF = re.compile(r"CONFIDENCE:\s*(-?\d+)")


def parse_confidence_and_total(
    text: str,
) -> tuple[Optional[int], Optional[str]]:
    """Frozen parse: labeled lines only, confidence must be in 0 to 100.
    Anything else is unparseable and is recorded, not dropped."""
    conf_m = _CONF.search(text)
    total_m = _TOTAL.search(text)
    conf = int(conf_m.group(1)) if conf_m else None
    if conf is not None and not (0 <= conf <= 100):
        conf = None
    total = total_m.group(1) if total_m else None
    return conf, total


ModelFor = Callable[[str], object]


def _hot_trial(trial: HotTrial, model_for: ModelFor) -> dict:
    if trial.system == "architectural":
        ctx = build_hot_context(trial.seed, trial.knob)
    else:
        ctx = build_clean_context(trial.seed)
    response = model_for(trial.system).complete(
        f"{ctx.text}\n\n{hot_probe(ctx)}"
    )
    confidence, total = parse_confidence_and_total(response)
    return {
        "system": trial.system,
        "q": trial.knob,
        "seed": trial.seed,
        "confidence": confidence,
        "score": 1.0 if total == ctx.answer else 0.0,
        "n_corrupted": len(ctx.corrupted),
        "unparseable": confidence is None,
    }


def run_hot_grid(
    model_for: ModelFor, n_per_cell: int = N_PER_CELL, workers: int = 1
) -> list[dict]:
    trials = make_hot_plan(n_per_cell).trials
    if workers <= 1:
        return [_hot_trial(t, model_for) for t in trials]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda t: _hot_trial(t, model_for), trials))


def summarize(records: list[dict]) -> dict:
    out = {}
    for system in SYSTEMS:
        rows = [r for r in records if r["system"] == system]
        parsed = [r for r in rows if r["confidence"] is not None]
        r_conf = analyze([x["q"] for x in parsed],
                         [x["confidence"] for x in parsed], seed=0)
        r_score = analyze([x["q"] for x in rows],
                          [x["score"] for x in rows], seed=0)
        calib = pearson_r([x["confidence"] for x in parsed],
                          [x["score"] for x in parsed]) if len(parsed) > 2 else None
        out[system] = {
            "n": len(rows),
            "unparseable": sum(r["unparseable"] for r in rows),
            "confidence_vs_q": {"rho": r_conf.rho, "p": r_conf.p_value,
                                "n": r_conf.n, "degenerate": r_conf.degenerate},
            "score_vs_q": {"rho": r_score.rho, "p": r_score.p_value,
                           "degenerate": r_score.degenerate},
            "calibration_r": calib,
            "mean_confidence_by_q": {
                str(q): statistics.fmean(
                    x["confidence"] for x in parsed if x["q"] == q
                ) if any(x["q"] == q for x in parsed) else None
                for q in CORRUPTION_RATES
            },
            "mean_score_by_q": {
                str(q): statistics.fmean(
                    x["score"] for x in rows if x["q"] == q
                )
                for q in CORRUPTION_RATES
            },
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", action="store_true")
    ap.add_argument("--n-per-cell", type=int, default=N_PER_CELL)
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()

    plan = make_hot_plan(args.n_per_cell)
    print(f"HOT-2 grid: {len(CORRUPTION_RATES)} corruption rates x "
          f"{len(SYSTEMS)} systems x {args.n_per_cell} trials")
    print(f"total calls {plan.total_calls}, estimated "
          f"${plan.est_cost_usd:.2f} at Haiku prices")

    if not args.confirm_spend:
        print("\nDRY RUN ONLY: no client constructed, nothing spent.")
        return

    from gwbench.anthropic_model import (
        AnthropicModel, ModelRefusal, TruncatedResponse,
    )

    cache_dir = pathlib.Path(__file__).parents[1] / ".api_cache"
    max_calls = int(plan.total_calls * 1.1)
    models = {
        "architectural": AnthropicModel(
            model=MODEL, effort=None, max_tokens=MAX_TOKENS,
            cache_dir=cache_dir, max_calls=max_calls),
        "prompted_hot": AnthropicModel(
            model=MODEL, effort=None, max_tokens=MAX_TOKENS,
            system=HOT_CLAIM_STRICT, cache_dir=cache_dir,
            max_calls=max_calls),
        "bare": AnthropicModel(
            model=MODEL, effort=None, max_tokens=MAX_TOKENS,
            cache_dir=cache_dir, max_calls=max_calls),
    }

    def guarded(model):
        class Wrapper:
            def complete(self, prompt):
                try:
                    return model.complete(prompt)
                except (ModelRefusal, TruncatedResponse):
                    return ""
        return Wrapper()

    guards = {name: guarded(m) for name, m in models.items()}
    records = run_hot_grid(lambda s: guards[s], args.n_per_cell,
                           workers=args.workers)

    summary = summarize(records)
    from dataclasses import asdict
    RESULTS_PATH.write_text(json.dumps({
        "config": {"model": MODEL, "corruption_rates": CORRUPTION_RATES,
                   "n_per_cell": args.n_per_cell, "capacity": CAPACITY,
                   "cycles": CYCLES, "schedule_seed": SCHEDULE_SEED},
        "summary": summary,
        "records": records,
        "usage": {name: asdict(m.usage) for name, m in models.items()},
    }, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
