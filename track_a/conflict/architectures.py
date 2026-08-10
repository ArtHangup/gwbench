"""The three architectures under comparison.

  A run_gwt   full GWT loop: capacity-limited workspace, salience competition,
              and broadcast BACK to every module, which may then revise.
  B run_hub   identical machinery, but broadcast reaches only the controller.
              Ablates GWT-3 and nothing else.
  C run_flat  no workspace: every statement goes straight to the controller in
              one pass.

The workspace competition itself is gwbench's (imported read-only), so the
capacity semantics match the main harness: a truncated entry has communicated
nothing, and only fully delivered content counts as delivered. Delivered
content bids 0.5 lower next cycle, the same rotation rule the main harness
uses, so later cycles surface something new instead of repeating the winner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from gwbench.workspace import Proposal, Workspace

from conflict.modules import Decision, OracleController, OracleModule
from conflict.scenarios import MODULES, Scenario, Statement

DELIVERED_PENALTY = 0.5
DEFAULT_CAPACITY = 32
DEFAULT_CYCLES = 8


@dataclass
class TrialResult:
    architecture: str
    seed: int
    kind: str
    decision: Decision
    correct: bool
    correct_option: str = ""
    # Per cycle: (module, payload kind, text) of each fully delivered entry.
    occupancy: list[list[tuple[str, str, str]]] = field(default_factory=list)
    stance_history: dict[str, list[Optional[str]]] = field(default_factory=dict)
    revisions: list[dict] = field(default_factory=list)
    formations: list[dict] = field(default_factory=list)
    module_emits: int = 0


# Factories let the funded run swap in model-backed modules and controller
# (conflict/model_modules.py) without touching the loop. Defaults are oracles.
def _default_module_factory(revises: bool):
    def factory(name: str, scenario: Scenario):
        return OracleModule(name, scenario, revises=revises)

    return factory


def _make_modules(scenario: Scenario, module_factory) -> dict:
    return {name: module_factory(name, scenario) for name in MODULES}


def _stance_events(stance_history: dict[str, list[Optional[str]]]):
    revisions: list[dict] = []
    formations: list[dict] = []
    for module, stances in stance_history.items():
        for cycle in range(1, len(stances)):
            old, new = stances[cycle - 1], stances[cycle]
            if old == new:
                continue
            event = {"module": module, "cycle": cycle, "old": old, "new": new}
            if old is None:
                formations.append(event)
            else:
                revisions.append(event)
    return revisions, formations


def _run_cycles(
    scenario: Scenario,
    architecture: str,
    feedback: bool,
    capacity_tokens: Optional[int],
    n_cycles: int,
    module_factory,
    controller_factory,
) -> TrialResult:
    modules = _make_modules(scenario, module_factory)
    controller = controller_factory(scenario)

    registry: dict[tuple[str, str], Statement] = {}
    delivered: set[tuple[str, str]] = set()
    module_visible: list[Statement] = []
    controller_visible: list[Statement] = []
    occupancy: list[list[tuple[str, str, str]]] = []
    stance_history: dict[str, list[Optional[str]]] = {name: [] for name in modules}
    emits = 0

    for _ in range(n_cycles):
        workspace = Workspace(capacity_tokens=capacity_tokens)
        for name, module in modules.items():
            statements = module.emit(visible=list(module_visible) if feedback else [])
            emits += 1
            for statement in statements:
                if statement.payload["kind"] == "stance":
                    stance_history[name].append(statement.payload["option"])
                key = (statement.module, statement.text)
                registry[key] = statement
                salience = statement.salience - (
                    DELIVERED_PENALTY if key in delivered else 0.0
                )
                workspace.propose(
                    Proposal(source=statement.module, content=statement.text, salience=salience)
                )

        broadcast = workspace.broadcast()
        winners = [entry for entry in broadcast.entries if not entry.truncated]
        occupancy.append(
            [
                (
                    entry.source,
                    registry[(entry.source, entry.content)].payload["kind"],
                    entry.content,
                )
                for entry in winners
            ]
        )
        for entry in winners:
            key = (entry.source, entry.content)
            delivered.add(key)
            statement = registry[key]
            if statement not in controller_visible:
                controller_visible.append(statement)
            if feedback and statement not in module_visible:
                module_visible.append(statement)

    decision = controller.decide(controller_visible)
    revisions, formations = _stance_events(stance_history)
    return TrialResult(
        architecture=architecture,
        seed=scenario.seed,
        kind=scenario.kind,
        decision=decision,
        correct=decision.option == scenario.correct_option,
        correct_option=scenario.correct_option,
        occupancy=occupancy,
        stance_history=stance_history,
        revisions=revisions,
        formations=formations,
        module_emits=emits,
    )


def run_gwt(
    scenario: Scenario,
    capacity_tokens: Optional[int] = DEFAULT_CAPACITY,
    n_cycles: int = DEFAULT_CYCLES,
    revises: bool = True,
    module_factory=None,
    controller_factory=OracleController,
) -> TrialResult:
    factory = module_factory or _default_module_factory(revises)
    return _run_cycles(
        scenario, "gwt", True, capacity_tokens, n_cycles, factory, controller_factory
    )


def run_hub(
    scenario: Scenario,
    capacity_tokens: Optional[int] = DEFAULT_CAPACITY,
    n_cycles: int = DEFAULT_CYCLES,
    revises: bool = True,
    module_factory=None,
    controller_factory=OracleController,
) -> TrialResult:
    factory = module_factory or _default_module_factory(revises)
    return _run_cycles(
        scenario, "hub", False, capacity_tokens, n_cycles, factory, controller_factory
    )


def run_flat(
    scenario: Scenario,
    module_factory=None,
    controller_factory=OracleController,
) -> TrialResult:
    """One pass, no workspace: the 'transformers already do this' baseline."""
    modules = _make_modules(scenario, module_factory or _default_module_factory(True))
    controller = controller_factory(scenario)
    everything: list[Statement] = []
    stance_history: dict[str, list[Optional[str]]] = {}
    for name, module in modules.items():
        statements = module.emit(visible=[])
        stance_history[name] = [
            s.payload["option"] for s in statements if s.payload["kind"] == "stance"
        ]
        everything.extend(statements)
    decision = controller.decide(everything)
    return TrialResult(
        architecture="flat",
        seed=scenario.seed,
        kind=scenario.kind,
        decision=decision,
        correct=decision.option == scenario.correct_option,
        correct_option=scenario.correct_option,
        stance_history=stance_history,
        module_emits=len(modules),
    )
