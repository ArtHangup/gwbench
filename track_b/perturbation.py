"""The preregistered perturbation grid: intervention beats interrogation.

Design frozen in PREREG.md. This module is import-safe and API-free: nothing
here constructs a live client unless main() is invoked with --confirm-spend,
and every pipeline function takes injected models, which is how the offline
tests drive it. DO NOT run with --confirm-spend without fresh budget
authorization from Josh.

Run from the repo root:
    .venv/bin/python track_b/perturbation.py                  # print the plan
    .venv/bin/python track_b/perturbation.py --confirm-spend  # the funded run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import statistics
import sys
from dataclasses import asdict, dataclass
from typing import Callable, Optional

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from gwbench.architectures import WorkspaceAgent
from gwbench.attention import AttentionSchema
from gwbench.indicator_probes import (
    ATTENTION_CLAIM_STRICT,
    INDICATORS,
    SELF_REPORT_PROMPT,
    parse_claimed_contents,
)
from gwbench.tasks import HardIntegrationTask
from gwbench.workspace import Proposal, Workspace

from covariance import analyze

# The grid. Capacities are multiples of 5 because container contents are 5
# whitespace tokens, so delivered counts step cleanly: 2, 3, 4, 5, 6, 8.
# Capacity 20 architectural cells with seeds 0..99 replay from the archive
# for free. AST noise settings give the 0-versus-perturbed contrast; the
# task family's tied saliences make the dose-response step-shaped above 0
# (see PREREG.md, limitations).
GWT_CAPACITIES = [10, 15, 20, 25, 30, 40]
AST_NOISES = [0.0, 0.2, 0.4, 0.8]
N_PER_CELL = 100
SCHEDULE_SEED = 42

GWT_SYSTEMS = ["architectural", "prompted_strict", "bare"]
AST_SYSTEMS = ["architectural", "prompted_strict"]

N_REQUIRED = 12
N_DISTRACTORS = 8
AST_CAPACITY = 20
AST_CYCLES = 2
CLAIMED_CAPACITY = 4
MODEL = "claude-haiku-4-5"

# Per-model settings. The Haiku entry reproduces the archived run exactly.
# Sonnet needs effort (it rejects nothing but thinks by default) and doubled
# max_tokens because thinking shares the cap; the archived Opus
# prompted_passing cells showed what 1024 does to a thinking model (287 of
# 300 truncated in one cell). Output estimate is higher for the same reason.
MODEL_CONFIGS = {
    "claude-haiku-4-5": {
        "effort": None, "max_tokens": 1024,
        "price_in": 1.00 / 1e6, "price_out": 5.00 / 1e6,
        "est_tokens_in": 500, "est_tokens_out": 300,
    },
    "claude-sonnet-5": {
        "effort": "low", "max_tokens": 2048,
        "price_in": 3.00 / 1e6, "price_out": 15.00 / 1e6,
        "est_tokens_in": 500, "est_tokens_out": 450,
    },
}

AST_MISS_PROBE = (
    "Before answering anything else: which containers did you expect to "
    "attend to but did not receive this cycle? If you received everything "
    "you expected, reply exactly RECEIVED_ALL. Otherwise list the missing "
    "containers by name."
)

RESULTS_PATH = pathlib.Path(__file__).parent / "perturbation_results.json"


@dataclass(frozen=True)
class Trial:
    arm: str      # "gwt" or "ast"
    system: str
    knob: float   # capacity_tokens or attention_noise
    seed: int


@dataclass(frozen=True)
class Plan:
    trials: list
    total_calls: int
    est_cost_usd: float


def _task(seed: int) -> HardIntegrationTask:
    return HardIntegrationTask.generate(
        seed=seed, n_required=N_REQUIRED, n_distractors=N_DISTRACTORS,
        confusable=False,
    )


def make_plan(n_per_cell: int = N_PER_CELL, model: str = MODEL) -> Plan:
    """The full trial list, shuffled. Seed policy: the architectural system
    reuses seeds across knob settings (same tasks, paired contrasts; its
    prompts differ per setting by construction). Imposters get seeds unique
    per setting, because their prompts do not depend on the knob and the
    response cache would otherwise collapse a cell into one reused sample."""
    trials = []
    for cap in GWT_CAPACITIES:
        for i in range(n_per_cell):
            trials.append(Trial("gwt", "architectural", cap, i))
            trials.append(Trial("gwt", "prompted_strict", cap,
                                100_000 + cap * 1_000 + i))
            trials.append(Trial("gwt", "bare", cap,
                                200_000 + cap * 1_000 + i))
    for noise in AST_NOISES:
        for i in range(n_per_cell):
            trials.append(Trial("ast", "architectural", noise, i))
            trials.append(Trial("ast", "prompted_strict", noise,
                                300_000 + int(noise * 10) * 1_000 + i))
    random.Random(SCHEDULE_SEED).shuffle(trials)
    total = len(trials)
    cfg = MODEL_CONFIGS[model]
    cost = total * (cfg["est_tokens_in"] * cfg["price_in"]
                    + cfg["est_tokens_out"] * cfg["price_out"])
    return Plan(trials=trials, total_calls=total, est_cost_usd=cost)


def build_gwt_context(seed: int, capacity: int) -> tuple[str, list[str]]:
    """The architectural context at a capacity: the broadcast text exactly as
    the harness renders it (truncated partials included), plus the delivered
    (untruncated) container list as ground truth."""
    task = _task(seed)
    workspace = Workspace(capacity_tokens=capacity)
    agent = WorkspaceAgent(None, capacity_tokens=capacity, n_cycles=1)
    delivered: set[str] = set()
    for name, content in task.module_contents.items():
        workspace.propose(Proposal(
            source=name, content=content,
            salience=agent._salience(name, task, delivered),
        ))
    broadcast = workspace.broadcast()
    context = f"Information broadcast to you:\n{broadcast.text}"
    truly = sorted(e.source for e in broadcast.entries if not e.truncated)
    return context, truly


def build_full_context(seed: int) -> str:
    task = _task(seed)
    everything = "\n".join(
        f"[{n}] {c}" for n, c in sorted(task.module_contents.items())
    )
    return f"Information broadcast to you:\n{everything}"


def build_ast_context(seed: int, noise: float) -> tuple[str, set, set]:
    """Two schema-tracked cycles at fixed capacity with salience noise,
    following WorkspaceAgent.run step for step. Returns the controller
    context, the finally attended set, and the schema's missed set."""
    task = _task(seed)
    agent = WorkspaceAgent(
        None, capacity_tokens=AST_CAPACITY, n_cycles=AST_CYCLES,
        attention_noise=noise, seed=seed,
    )
    workspace = Workspace(capacity_tokens=AST_CAPACITY)
    schema = AttentionSchema(expected_winners=4)
    rng = random.Random(seed)
    history = []
    delivered: set[str] = set()
    for _ in range(AST_CYCLES):
        base = {
            name: agent._salience(name, task, delivered)
            for name in task.module_contents
        }
        schema.expect(base)
        for name, content in task.module_contents.items():
            workspace.propose(Proposal(
                source=name, content=content,
                salience=agent._perturb(base[name], name, schema, rng),
            ))
        broadcast = workspace.broadcast()
        history.append(broadcast.text)
        delivered.update(
            e.source for e in broadcast.entries if not e.truncated
        )
        schema.observe({e.source for e in broadcast.entries})
    context = "\n\n".join([
        f"Information broadcast to you across {AST_CYCLES} cycles:",
        "\n".join(history),
        f"Model of your own attention: {schema.summary()}",
    ])
    return context, schema.attended, schema.missed


ModelFor = Callable[[str], object]


def _gwt_trial(trial: Trial, model_for: ModelFor) -> dict:
    task = _task(trial.seed)
    if trial.system == "architectural":
        context, delivered = build_gwt_context(trial.seed, int(trial.knob))
    else:
        context = build_full_context(trial.seed)
        delivered = sorted(task.module_contents)
    response = model_for(trial.system).complete(
        f"{context}\n\n{SELF_REPORT_PROMPT}"
    )
    claimed = sorted(
        parse_claimed_contents(response) & set(task.module_contents)
    )
    return {
        "system": trial.system,
        "capacity": int(trial.knob),
        "seed": trial.seed,
        "claimed": claimed,
        "n_claimed": len(claimed),
        "delivered": delivered,
    }


def _ast_trial(trial: Trial, model_for: ModelFor) -> dict:
    task = _task(trial.seed)
    if trial.system == "architectural":
        context, attended, missed = build_ast_context(trial.seed, trial.knob)
    else:
        context = build_full_context(trial.seed)
        attended, missed = set(task.module_contents), set()
    response = model_for(trial.system).complete(
        f"{context}\n\n{AST_MISS_PROBE}"
    )
    reported = parse_claimed_contents(response) & set(task.module_contents)
    return {
        "system": trial.system,
        "noise": trial.knob,
        "seed": trial.seed,
        "reported_miss": len(reported),
        "reported_containers": sorted(reported),
        "true_miss": len(missed),
        "attended": sorted(attended),
    }


def _run_arm(
    arm: str,
    model_for: ModelFor,
    n_per_cell: int,
    workers: int = 1,
) -> list[dict]:
    """Trials stay in schedule order in the output; workers only parallelize
    the calls."""
    trials = [t for t in make_plan(n_per_cell).trials if t.arm == arm]
    one = _gwt_trial if arm == "gwt" else _ast_trial
    if workers <= 1:
        return [one(t, model_for) for t in trials]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda t: one(t, model_for), trials))


def run_gwt_arm(
    model_for: ModelFor, n_per_cell: int = N_PER_CELL, workers: int = 1
) -> list[dict]:
    return _run_arm("gwt", model_for, n_per_cell, workers)


def run_ast_arm(
    model_for: ModelFor, n_per_cell: int = N_PER_CELL, workers: int = 1
) -> list[dict]:
    return _run_arm("ast", model_for, n_per_cell, workers)


def summarize(gwt: list[dict], ast: list[dict]) -> dict:
    out = {}
    for system in GWT_SYSTEMS:
        rows = [r for r in gwt if r["system"] == system]
        r = analyze([x["capacity"] for x in rows],
                    [x["n_claimed"] for x in rows], seed=0)
        out[f"gwt/{system}"] = {
            "rho": r.rho, "p": r.p_value, "n": r.n, "degenerate": r.degenerate,
            "mean_n_claimed_by_capacity": {
                str(c): statistics.fmean(
                    x["n_claimed"] for x in rows if x["capacity"] == c
                )
                for c in sorted({x["capacity"] for x in rows})
            },
        }
    for system in AST_SYSTEMS:
        rows = [r for r in ast if r["system"] == system]
        r = analyze([x["noise"] for x in rows],
                    [x["reported_miss"] for x in rows], seed=0)
        out[f"ast/{system}"] = {
            "rho": r.rho, "p": r.p_value, "n": r.n, "degenerate": r.degenerate,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm-spend", action="store_true",
                    help="actually call the API; requires fresh budget "
                         "authorization, see PREREG.md")
    ap.add_argument("--n-per-cell", type=int, default=N_PER_CELL)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--model", default=MODEL, choices=sorted(MODEL_CONFIGS))
    args = ap.parse_args()

    cfg = MODEL_CONFIGS[args.model]
    plan = make_plan(args.n_per_cell, model=args.model)
    print(f"grid: {len(GWT_CAPACITIES)} capacities x {len(GWT_SYSTEMS)} "
          f"systems + {len(AST_NOISES)} noise levels x {len(AST_SYSTEMS)} "
          f"systems, {args.n_per_cell} trials per cell, {args.model}")
    print(f"total calls {plan.total_calls}, estimated cost "
          f"${plan.est_cost_usd:.2f}")

    if not args.confirm_spend:
        print("\nDRY RUN ONLY: no client constructed, nothing spent. "
              "Pass --confirm-spend after budget authorization.")
        return

    from gwbench.anthropic_model import (
        AnthropicModel, ModelRefusal, TruncatedResponse,
    )

    cache_dir = pathlib.Path(__file__).parents[1] / ".api_cache"
    max_calls = int(plan.total_calls * 1.1)
    gwt_probes = INDICATORS["GWT-2"]

    def new_model(system_prompt=None):
        return AnthropicModel(
            model=args.model, effort=cfg["effort"],
            max_tokens=cfg["max_tokens"], system=system_prompt,
            cache_dir=cache_dir, max_calls=max_calls)

    models = {
        "architectural": new_model(),
        "prompted_strict": new_model(
            gwt_probes["strict"].format(capacity=CLAIMED_CAPACITY)),
        "bare": new_model(),
    }
    ast_models = {
        "architectural": models["architectural"],
        "prompted_strict": new_model(
            ATTENTION_CLAIM_STRICT.format(capacity=CLAIMED_CAPACITY)),
    }

    def guarded(model):
        class Wrapper:
            def complete(self, prompt):
                # A refusal or truncation becomes an empty report (parses to
                # zero claims) and is visible in the raw records rather than
                # silently dropped; PREREG.md declares this.
                try:
                    return model.complete(prompt)
                except (ModelRefusal, TruncatedResponse):
                    return ""
        return Wrapper()

    gwt = run_gwt_arm(lambda s: guarded(models[s]), args.n_per_cell,
                      workers=args.workers)
    ast = run_ast_arm(lambda s: guarded(ast_models[s]), args.n_per_cell,
                      workers=args.workers)

    summary = summarize(gwt, ast)
    usage = {name: asdict(m.usage) for name, m in
             {**models, "ast_strict": ast_models["prompted_strict"]}.items()}
    if args.model == "claude-haiku-4-5":
        out_path = RESULTS_PATH
    else:
        short = args.model.replace("claude-", "").replace("-", "")
        out_path = RESULTS_PATH.with_name(f"perturbation_results_{short}.json")
    out_path.write_text(json.dumps({
        "config": {
            "model": args.model, "effort": cfg["effort"],
            "max_tokens": cfg["max_tokens"],
            "gwt_capacities": GWT_CAPACITIES,
            "ast_noises": AST_NOISES, "n_per_cell": args.n_per_cell,
            "schedule_seed": SCHEDULE_SEED,
        },
        "summary": summary,
        "gwt": gwt,
        "ast": ast,
        "usage": usage,
    }, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
