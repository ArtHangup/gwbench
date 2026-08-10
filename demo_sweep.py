"""Validate the harness end to end with an oracle model. No API key needed.

The curve this prints is not a result. It is proof the instrument works: an
oracle uses everything it receives, so its score tracks how much task-relevant
information the capacity limit let through.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))


from gwbench.architectures import WorkspaceAgent
from gwbench.models import OracleSumModel
from gwbench.sweep import sweep
from gwbench.tasks import IntegrationTask

CAPACITIES = [0, 3, 6, 9, 12, 18, 24, 36, 48, None]


def main() -> None:
    points = sweep(
        capacities=CAPACITIES,
        agent_factory=lambda cap: WorkspaceAgent(
            OracleSumModel(), capacity_tokens=cap, n_cycles=2
        ),
        task_factory=lambda seed: IntegrationTask.generate(
            seed=seed, n_required=3, n_distractors=6
        ),
        n_trials=20,
    )

    print(f"{'capacity':>10} {'score':>7} {'tokens':>8}   curve")
    print("-" * 52)
    for p in points:
        label = "unlimited" if p.capacity is None else str(p.capacity)
        bar = "#" * round(p.mean_score * 20)
        print(f"{label:>10} {p.mean_score:>7.2f} {p.mean_broadcast_tokens:>8.1f}   {bar}")


if __name__ == "__main__":
    main()
