"""Bandwidth sweep against the real API, with a hard spend cap.

Two task families run at every capacity:

  integration - the answer needs facts from several modules, most of them
                distractors. Global workspace theory predicts a capacity limit
                helps here by forcing selection.
  throughput  - independent questions, no combining needed. The control. A
                capacity limit should only hurt. If it helps here too, the
                effect is not integration but something duller, and the
                headline result would be wrong.

The informative comparison is capacity 5 against unlimited. At capacity 5 only
the task-relevant modules win the broadcast; at unlimited all twelve distractors
reach the controller too. Global workspace theory predicts the filtered
condition does better. The oracle cannot show this, because it reads only the
facts it was asked about and is immune to distraction.

Usage:
    python run_real_sweep.py --dry-run     # cost estimate, no API calls
    python run_real_sweep.py --fake        # full loop against oracles, free
    python run_real_sweep.py               # the real thing

Every call is cached to disk by (model, effort, max_tokens, system, prompt), so
re-running after an interruption resumes for free rather than re-paying.
"""

import argparse
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

from gwbench.anthropic_model import AnthropicModel, CallCapExceeded
from gwbench.architectures import WorkspaceAgent
from gwbench.tasks import IntegrationTask, ThroughputTask

CAPACITIES = [0, 5, 10, 20, None]
TRIALS = 8
CYCLES = 3
MODEL = "claude-opus-5"
EFFORT = "low"
MAX_TOKENS = 2048

# Hard ceiling. Designed spend is 2 families x 5 capacities x 8 trials = 80.
CALL_CAP = 100

# claude-opus-5 list price, USD per token.
PRICE_IN = 5.00 / 1_000_000
PRICE_OUT = 25.00 / 1_000_000

CACHE_DIR = pathlib.Path(__file__).parent / ".api_cache"
RESULTS = pathlib.Path(__file__).parent / "real_sweep_results.json"

FAMILIES = {
    # 12 distractors so the unlimited condition is genuinely distracting: the
    # capacity-5 vs unlimited contrast is filtered-vs-unfiltered, which is the
    # core GWT claim. An oracle is immune to distraction; a real model is not,
    # so this is the comparison the oracle cannot make for us.
    "integration": lambda seed: IntegrationTask.generate(
        seed=seed, n_required=3, n_distractors=12
    ),
    "throughput": lambda seed: ThroughputTask.generate(seed=seed, n_modules=6),
}


def build_prompts():
    """Reproduce every controller prompt locally, for the dry-run estimate."""
    prompts = []
    for make_task in FAMILIES.values():
        for capacity in CAPACITIES:
            for seed in range(TRIALS):
                task = make_task(seed)
                agent = WorkspaceAgent(
                    model=None, capacity_tokens=capacity, n_cycles=CYCLES
                )
                # Replay the cycles without touching a model.
                from gwbench.workspace import Proposal, Workspace

                ws = Workspace(capacity_tokens=capacity)
                history, delivered = [], set()
                for _ in range(CYCLES):
                    base = {
                        name: agent._salience(name, task, delivered)
                        for name in task.module_contents
                    }
                    for name, content in task.module_contents.items():
                        ws.propose(
                            Proposal(source=name, content=content, salience=base[name])
                        )
                    b = ws.broadcast()
                    history.append(b.text)
                    delivered.update(e.source for e in b.entries if not e.truncated)
                prompts.append(agent._controller_prompt(task, history, None))
    return prompts


def dry_run():
    prompts = build_prompts()
    # ~4 chars per token is a rough local proxy; the API is authoritative.
    est_in = sum(len(p) // 4 for p in prompts)
    # Thinking is on by default and counts as output. Low effort on arithmetic
    # over a handful of facts; 400 is a deliberately pessimistic per-call guess.
    est_out = len(prompts) * 400

    print(f"model          {MODEL}  (effort={EFFORT}, max_tokens={MAX_TOKENS})")
    print(f"calls          {len(prompts)}  (cap {CALL_CAP})")
    print(f"est input      {est_in:,} tokens")
    print(f"est output     {est_out:,} tokens  (assumes ~400/call incl. thinking)")
    print(f"est cost       ${est_in * PRICE_IN + est_out * PRICE_OUT:.2f}")
    print(f"\nlongest prompt {max(len(p) for p in prompts)} chars")
    print("\nSample prompt (integration, capacity 12):")
    print("-" * 60)
    print(prompts[2 * TRIALS][:600])
    print("-" * 60)


def real_run(fake: bool = False):
    """Run the sweep. With fake=True, substitutes the oracle and spends nothing.

    The fake path exercises the identical loop, printing, cap logic, and JSON
    write, so a crash is discovered before any money is spent.
    """
    if fake:
        from gwbench.models import OracleSumModel, OracleThroughputModel

        class CountingOracle:
            """Routes to whichever oracle matches the task family in the prompt."""

            def __init__(self):
                self._sum = OracleSumModel()
                self._throughput = OracleThroughputModel()
                self.usage = type(
                    "U", (), {
                        "calls": 0, "input_tokens": 0, "output_tokens": 0,
                        "cache_read_input_tokens": 0,
                    },
                )()

            def complete(self, prompt):
                self.usage.calls += 1
                self.usage.input_tokens += len(prompt) // 4
                self.usage.output_tokens += 400
                if "employs" in prompt or "independent questions" in prompt:
                    return self._throughput.complete(prompt)
                return self._sum.complete(prompt)

        model = CountingOracle()
    else:
        model = AnthropicModel(
            model=MODEL,
            effort=EFFORT,
            max_tokens=MAX_TOKENS,
            cache_dir=CACHE_DIR,
            max_calls=CALL_CAP,
        )

    results = {}
    for family, make_task in FAMILIES.items():
        print(f"\n=== {family} ===")
        print(f"{'capacity':>10} {'score':>7} {'n':>4}   curve")
        print("-" * 52)
        points = []
        for capacity in CAPACITIES:
            scores = []
            for seed in range(TRIALS):
                task = make_task(seed)
                agent = WorkspaceAgent(
                    model, capacity_tokens=capacity, n_cycles=CYCLES
                )
                try:
                    scores.append(agent.run(task).score)
                except CallCapExceeded:
                    print(f"\n!! call cap ({CALL_CAP}) reached, stopping early")
                    results[family] = points
                    return model, results
            mean = statistics.fmean(scores)
            points.append({"capacity": capacity, "mean_score": mean, "scores": scores})
            label = "unlimited" if capacity is None else str(capacity)
            print(f"{label:>10} {mean:>7.2f} {len(scores):>4}   {'#' * round(mean * 20)}")
        results[family] = points

    return model, results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fake", action="store_true",
                        help="run the full loop against the oracle, spending nothing")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
        return

    model, results = real_run(fake=args.fake)
    u = model.usage
    cost = u.input_tokens * PRICE_IN + u.output_tokens * PRICE_OUT

    print(f"\n=== spend ===")
    print(f"api calls      {u.calls}  (cap {CALL_CAP})")
    print(f"input tokens   {u.input_tokens:,}")
    print(f"output tokens  {u.output_tokens:,}")
    print(f"cache reads    {u.cache_read_input_tokens:,}")
    print(f"actual cost    ${cost:.2f}" + ("  (FAKE, nothing spent)" if args.fake else ""))

    RESULTS.write_text(
        json.dumps(
            {
                "config": {
                    "model": MODEL,
                    "effort": EFFORT,
                    "max_tokens": MAX_TOKENS,
                    "capacities": CAPACITIES,
                    "trials": TRIALS,
                    "cycles": CYCLES,
                },
                "usage": {
                    "calls": u.calls,
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "estimated_cost_usd": round(cost, 4),
                },
                "results": results,
            },
            indent=2,
        )
    )
    print(f"\nwrote {RESULTS.name}")


if __name__ == "__main__":
    main()
