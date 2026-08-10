"""Does the attention schema earn its keep, and only under uncertainty?

Piefke et al. (CogSci 2024) found the benefit of an attention schema scales
with the agent's uncertainty about its own attentional state. This sweeps
attention noise and compares rung 3 (workspace) against rung 4 (workspace plus
schema) on identical tasks.

The prediction: no gap at zero noise, a widening gap as noise rises. As with
demo_sweep, this is instrument validation under an oracle, not a result.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))


import statistics

from gwbench.architectures import AttentionSchemaAgent, WorkspaceAgent
from gwbench.models import OracleSumModel
from gwbench.tasks import IntegrationTask

NOISE = [0.0, 0.25, 0.5, 1.0, 2.0]
TRIALS = 30
CAPACITY = 12
CYCLES = 3


def run(agent_cls, noise, seed):
    task = IntegrationTask.generate(seed=seed, n_required=3, n_distractors=6)
    agent = agent_cls(
        OracleSumModel(),
        capacity_tokens=CAPACITY,
        n_cycles=CYCLES,
        attention_noise=noise,
        seed=seed,
    )
    return agent.run(task)


def main() -> None:
    print(f"capacity={CAPACITY} tokens, {CYCLES} cycles, {TRIALS} trials\n")
    print(f"{'noise':>6} {'rung3':>7} {'rung4':>7} {'gap':>7} {'schema acc':>11}")
    print("-" * 44)

    for noise in NOISE:
        r3 = [run(WorkspaceAgent, noise, s).score for s in range(TRIALS)]
        r4 = [run(AttentionSchemaAgent, noise, s) for s in range(TRIALS)]
        r4_scores = [r.score for r in r4]
        acc = statistics.fmean(
            r.schema_accuracy for r in r4 if r.schema_accuracy is not None
        )
        a, b = statistics.fmean(r3), statistics.fmean(r4_scores)
        print(f"{noise:>6.2f} {a:>7.2f} {b:>7.2f} {b - a:>+7.2f} {acc:>11.2f}")


if __name__ == "__main__":
    main()
