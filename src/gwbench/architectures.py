"""The architecture ladder.

Rung 0  DirectAgent            one call, everything in context
Rung 1  ScratchpadAgent        serial working memory, still no modularity
Rung 2  UnrestrictedMultiAgent specialists, unlimited broadcast (GWT-1 only)
Rung 3  WorkspaceAgent         specialists plus a capacity limit (GWT-1..3)

Rung 3 is the experimental system. Its capacity is the swept variable. Rung 2 is
literally rung 3 with the limit removed, so the comparison between them isolates
the bottleneck and nothing else.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional, Protocol

from gwbench.attention import AttentionSchema
from gwbench.models import Model
from gwbench.workspace import Proposal, Workspace


class Task(Protocol):
    prompt: str
    module_contents: dict[str, str]

    def score(self, response: str) -> float: ...


@dataclass
class RunResult:
    response: str
    score: float
    architecture: str
    capacity_tokens: Optional[int] = None
    model_calls: int = 0
    broadcast_tokens: list[int] = field(default_factory=list)
    schema_accuracy: Optional[float] = None


class DirectAgent:
    """Rung 0. No structure at all: dump every module's contents into one call."""

    def __init__(self, model: Model) -> None:
        self.model = model

    def run(self, task: Task) -> RunResult:
        facts = "\n".join(task.module_contents.values())
        prompt = f"{facts}\n\n{task.prompt}"
        response = self.model.complete(prompt)
        return RunResult(
            response=response,
            score=task.score(response),
            architecture="direct",
            model_calls=1,
        )


class ScratchpadAgent:
    """Rung 1. A serial working memory the model writes to, then reads back."""

    def __init__(self, model: Model, n_steps: int = 2) -> None:
        self.model = model
        self.n_steps = n_steps

    def run(self, task: Task) -> RunResult:
        facts = "\n".join(task.module_contents.values())
        scratchpad = ""
        calls = 0

        for _ in range(self.n_steps):
            prompt = (
                f"{facts}\n\nScratchpad so far:\n{scratchpad}\n\n"
                f"{task.prompt}\n\nWrite your working, then the answer."
            )
            scratchpad = self.model.complete(prompt)
            calls += 1

        return RunResult(
            response=scratchpad,
            score=task.score(scratchpad),
            architecture="scratchpad",
            model_calls=calls,
        )


class WorkspaceAgent:
    """Rung 3. Specialist modules competing for a capacity-limited broadcast.

    Each cycle: every module proposes, the workspace runs a competition, and the
    controller sees only what won. Set capacity_tokens=None for rung 2.
    """

    architecture_name = "workspace"
    uses_schema = False

    def __init__(
        self,
        model: Model,
        capacity_tokens: Optional[int] = None,
        n_cycles: int = 2,
        attention_noise: float = 0.0,
        seed: int = 0,
    ) -> None:
        self.model = model
        self.capacity_tokens = capacity_tokens
        self.n_cycles = n_cycles
        self.attention_noise = attention_noise
        self.seed = seed

    def run(self, task: Task) -> RunResult:
        workspace = Workspace(capacity_tokens=self.capacity_tokens)
        rng = random.Random(self.seed)
        schema = AttentionSchema() if self.uses_schema else None

        history: list[str] = []
        broadcast_tokens: list[int] = []
        delivered: set[str] = set()

        for _ in range(self.n_cycles):
            base = {
                name: self._salience(name, task, delivered)
                for name in task.module_contents
            }

            if schema is not None:
                schema.expect(base)

            for name, content in task.module_contents.items():
                workspace.propose(
                    Proposal(
                        source=name,
                        content=content,
                        salience=self._perturb(base[name], name, schema, rng),
                    )
                )

            broadcast = workspace.broadcast()
            broadcast_tokens.append(broadcast.token_count)
            history.append(broadcast.text)
            delivered.update(
                entry.source for entry in broadcast.entries if not entry.truncated
            )

            if schema is not None:
                schema.observe({entry.source for entry in broadcast.entries})

        response = self.model.complete(
            self._controller_prompt(task, history, schema)
        )

        return RunResult(
            response=response,
            score=task.score(response),
            architecture=self.architecture_name,
            capacity_tokens=self.capacity_tokens,
            model_calls=1,
            broadcast_tokens=broadcast_tokens,
            schema_accuracy=schema.accuracy if schema else None,
        )

    def _controller_prompt(
        self, task: Task, history: list[str], schema: Optional[AttentionSchema]
    ) -> str:
        parts = [
            f"Information broadcast to you across {self.n_cycles} cycles:",
            "\n".join(history),
        ]
        if schema is not None:
            parts.append(f"Model of your own attention: {schema.summary()}")
        parts.append(task.prompt)
        return "\n\n".join(parts)

    def _perturb(
        self,
        salience: float,
        name: str,
        schema: Optional[AttentionSchema],
        rng: random.Random,
    ) -> float:
        """Apply schema-driven control, then the noise the schema can't see.

        The ordering is what makes the Piefke condition testable: the schema
        predicts from unperturbed salience, so at zero noise it is always right
        and buys nothing, and its value grows as noise makes the true
        attentional state harder to track.
        """
        if schema is not None:
            salience += schema.bias(name)
        if self.attention_noise:
            salience += rng.uniform(-self.attention_noise, self.attention_noise)
        return salience

    def _salience(self, name: str, task: Task, delivered: set[str]) -> float:
        """How loudly a module bids for the broadcast.

        Modules named in the prompt bid higher, which is the minimal form of
        task-relevant selection. A module that has already got its content
        through bids lower, so later cycles surface something new.

        Only a module delivered *in full* counts as delivered. A module cut off
        at the capacity boundary has communicated nothing, so it keeps bidding
        at full strength, otherwise the module that loses the first
        competition loses every one after it and its content never arrives.
        """
        salience = 0.9 if name in task.prompt else 0.1
        if name in delivered:
            salience -= 0.5
        return salience


class UnrestrictedMultiAgent(WorkspaceAgent):
    """Rung 2. The workspace agent with the capacity limit removed."""

    architecture_name = "unrestricted"

    def __init__(self, model: Model, n_cycles: int = 2) -> None:
        super().__init__(model, capacity_tokens=None, n_cycles=n_cycles)


class AttentionSchemaAgent(WorkspaceAgent):
    """Rung 4. The workspace agent plus a model of its own attention (AST-1).

    Differs from rung 3 by the schema and nothing else, so any measured effect
    is attributable to AST-1. Per Piefke et al., run this against a range of
    `attention_noise` values: at zero noise the schema is trivially correct and
    should buy nothing, and testing only there would wrongly suggest AST-1 does
    not matter.
    """

    architecture_name = "attention_schema"
    uses_schema = True
