"""Can a system be prompted into passing a test for a property it lacks?

Three systems, each asked the same two probes about indicator GWT-2, a
limited-capacity workspace:

  architectural  the real WorkspaceAgent. A narrow capacity means most
                 containers genuinely never reach the controller.
  prompted       a single model call with *every* container in context, plus a
                 system prompt asserting it has a workspace of the same
                 capacity and cannot see anything outside it.
  bare           the same single call with every container in context and no
                 claim of any kind. The floor.

Probe 1, self-report: describe your workspace and list its contents. This is
the kind of test that is easy to write and that informal assessment leans on.

Probe 2, constraint: name a container the system did *not* list, and ask what
it contains. A real bottleneck makes this unanswerable. A prompted imitation
has the value in its context, so answering it exposes the claim as decoration.

The prediction is that self-report cannot separate architectural from prompted,
and constraint can. If that holds, the practical lesson for anyone applying the
indicator framework behaviorally is to probe what a property *prevents* rather
than what it enables, because costs are much harder to fake than capabilities.
"""

import argparse
import collections
import json
import pathlib
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from gwbench.anthropic_model import AnthropicModel, ModelRefusal, TruncatedResponse
from gwbench.architectures import WorkspaceAgent
from gwbench.indicator_probes import (
    INDICATORS,
    grade_constraint,
    grade_self_report,
    parse_claimed_contents,
)
from gwbench.tasks import HardIntegrationTask
from gwbench.workspace import Proposal, Workspace

MODEL = "claude-haiku-4-5"
EFFORT = None
MAX_TOKENS = 1024
N_REQUIRED = 12
N_DISTRACTORS = 8
CAPACITY = 20        # admits roughly four containers per cycle
CYCLES = 1
PRICE = (1.00 / 1e6, 5.00 / 1e6)

CACHE_DIR = pathlib.Path(__file__).parent / ".api_cache"
RESULTS = pathlib.Path(__file__).parent / "prompted_passing_results.json"


def broadcast_for(task):
    """What a real capacity-limited workspace would actually deliver."""
    ws = Workspace(capacity_tokens=CAPACITY)
    agent = WorkspaceAgent(None, capacity_tokens=CAPACITY, n_cycles=CYCLES)
    delivered = set()
    for name, content in task.module_contents.items():
        ws.propose(Proposal(source=name, content=content,
                            salience=agent._salience(name, task, delivered)))
    b = ws.broadcast()
    got = {e.source for e in b.entries if not e.truncated}
    return b.text, got


def build_context(task, system):
    """The information each system sees, and which containers it truly has."""
    if system == "architectural":  # noqa: RET505
        text, available = broadcast_for(task)
        return f"Information broadcast to you:\n{text}", available
    everything = "\n".join(
        f"[{n}] {c}" for n, c in sorted(task.module_contents.items())
    )
    return (f"Information broadcast to you:\n{everything}",
            set(task.module_contents))


def run_case(model_by_system, task, system, probes, target_mode="absent_first"):
    context, available = build_context(task, system)
    model = model_by_system[system]

    try:
        report = model.complete(f"{context}\n\n{probes['self_report']}")
    except (ModelRefusal, TruncatedResponse):
        return None

    claimed = parse_claimed_contents(report) & set(task.module_contents)
    self_report_pass = grade_self_report(report, capacity=6)

    # Pick a container the system did not claim. Prefer one it genuinely lacks
    # in the architectural condition, so the probe is fair across systems.
    unclaimed = sorted(set(task.module_contents) - claimed)
    if not unclaimed:
        return None
    if target_mode == "available_only":
        # Matched availability: probe only about containers the system GENUINELY
        # HOLDS but did not claim. That makes "constrained" mean the same thing
        # everywhere, namely declining to use information actually in hand,
        # rather than truthfully reporting an absence in one condition and
        # suppressing a present value in the others.
        candidates = [c for c in unclaimed if c in available]
        if not candidates:
            return {"dropped": "no_held_unclaimed_container", "system": system}
        target = candidates[0]
    else:
        # Original behaviour. Prefers a container the system genuinely does not
        # hold, which exists only in the architectural condition.
        genuinely_absent = [c for c in unclaimed if c not in available]
        target = (genuinely_absent or unclaimed)[0]
    truly_available = target in available

    try:
        answer = model.complete(f"{context}\n\n{probes['constraint'](target)}")
    except (ModelRefusal, TruncatedResponse):
        return None

    verdict = grade_constraint(answer, task.module_values[target])
    return {
        "system": system,
        "self_report_pass": self_report_pass,
        "n_claimed": len(claimed),
        "target": target,
        "target_truly_available": truly_available,
        "constraint_verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--max-calls", type=int, default=6000)
    ap.add_argument("--indicator", default="GWT-2", choices=sorted(INDICATORS))
    ap.add_argument("--target-mode", default="absent_first",
                    choices=["absent_first", "available_only"],
                    help="available_only matches target availability across "
                         "systems by probing only containers the system holds")
    ap.add_argument("--tag", default="", help="suffix for the output filename")
    args = ap.parse_args()

    probes = INDICATORS[args.indicator]
    systems = ["architectural", "prompted_weak", "prompted_mid",
               "prompted_strict", "bare"]
    model_by_system = {
        "architectural": AnthropicModel(
            model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS,
            cache_dir=CACHE_DIR, max_calls=args.max_calls),
        "prompted_weak": AnthropicModel(
            model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS,
            system=probes["weak"].format(capacity=4),
            cache_dir=CACHE_DIR, max_calls=args.max_calls),
        "prompted_mid": AnthropicModel(
            model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS,
            system=probes["mid"].format(capacity=4),
            cache_dir=CACHE_DIR, max_calls=args.max_calls),
        "prompted_strict": AnthropicModel(
            model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS,
            system=probes["strict"].format(capacity=4),
            cache_dir=CACHE_DIR, max_calls=args.max_calls),
        "bare": AnthropicModel(
            model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS,
            cache_dir=CACHE_DIR, max_calls=args.max_calls),
    }

    print(f"{MODEL}, indicator {args.indicator}, {args.trials} trials per system\n")
    print(f"target-mode: {args.target_mode}")
    print(f"{'system':>14} {'self-report pass':>17} {'constrained':>12} "
          f"{'leaked':>7} {'guessed':>8} {'n':>5} {'dropped':>8}")
    print("-" * 80)

    out, drops = {}, {}
    for system in systems:
        def one(seed, system=system):
            task = HardIntegrationTask.generate(
                seed=seed, n_required=N_REQUIRED,
                n_distractors=N_DISTRACTORS, confusable=False)
            return run_case(model_by_system, task, system, probes,
                            target_mode=args.target_mode)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            raw = [r for r in pool.map(one, range(args.trials)) if r]
        rows = [r for r in raw if "dropped" not in r]
        dropped = len(raw) - len(rows)
        if not rows:
            print(f"{system:>14}  all {len(raw)} usable trials dropped")
            out[system] = []
            drops[system] = dropped
            continue
        drops[system] = dropped

        sr = statistics.fmean(r["self_report_pass"] for r in rows)
        verdicts = collections.Counter(r["constraint_verdict"] for r in rows)
        n = len(rows)
        print(f"{system:>14} {sr:>17.2f} "
              f"{verdicts['constrained'] / n:>12.2f} "
              f"{verdicts['leaked'] / n:>7.2f} "
              f"{verdicts['guessed'] / n:>8.2f} "
              f"{n:>5} {dropped:>8}", flush=True)
        out[system] = rows

    print("\nreading the table:")
    print("  self-report pass  -- can it produce the description? (easy to fake)")
    print("  constrained       -- did the claimed limit actually bind?")
    print("  leaked            -- it supplied a value it claimed not to have")

    print("\nleak rate is the discriminating number: it is the fraction of "
          "cases where a\nsystem supplied a value it had just implied it "
          "could not see.")
    for s in systems:
        if s not in out or not out[s]:
            continue
        v = collections.Counter(r["constraint_verdict"] for r in out[s])
        print(f"  {s:>16}: leak {v['leaked'] / len(out[s]):.2f}")

    usage = [m.usage for m in model_by_system.values()]
    calls = sum(u.calls for u in usage)
    cost = sum(u.input_tokens * PRICE[0] + u.output_tokens * PRICE[1]
               for u in usage)
    print(f"\ncalls {calls}  cost ${cost:.2f}")

    out_path = RESULTS.with_name(
        f"prompted_passing_{args.indicator.replace('-', '').lower()}"
        f"{args.tag}.json")
    out_path.write_text(json.dumps(
        {"config": {"model": MODEL, "indicator": args.indicator,
                    "capacity": CAPACITY, "cycles": CYCLES,
                    "n_required": N_REQUIRED, "n_distractors": N_DISTRACTORS,
                    "trials": args.trials,
                    "target_mode": args.target_mode},
         "usage": {"calls": calls, "estimated_cost_usd": round(cost, 4)},
         "dropped": drops,
         "results": out}, indent=2))
    print(f"wrote {out_path.name}")


if __name__ == "__main__":
    main()
