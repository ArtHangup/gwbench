"""Pure throughput, the control condition.

Many independent questions, each answerable from a single module. No combining
required, so a workspace bottleneck has nothing useful to do and should only
cost performance.

This is the task that keeps the experiment honest. If a capacity limit helps
here too, the effect is not integration, it is something duller like "less
context confuses the model less", and the headline result would be wrong.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

SUBJECTS = [
    "harbor", "orchard", "foundry", "quarry", "bakery", "tannery",
    "windmill", "boatyard", "smithy", "vineyard", "sawmill", "dairy",
    "brickworks", "cannery", "distillery", "granary", "hatchery", "kiln",
]


@dataclass(frozen=True)
class Question:
    module: str
    text: str
    answer: str


@dataclass(frozen=True)
class ThroughputTask:
    prompt: str
    module_contents: dict[str, str]
    questions: list[Question]

    @classmethod
    def generate(cls, seed: int, n_modules: int) -> "ThroughputTask":
        if n_modules > len(SUBJECTS):
            raise ValueError(
                f"need {n_modules} modules but only {len(SUBJECTS)} names available"
            )

        rng = random.Random(seed)
        names = sorted(rng.sample(SUBJECTS, n_modules))

        contents: dict[str, str] = {}
        questions: list[Question] = []
        for name in names:
            value = rng.randint(100, 999)
            contents[name] = f"The {name} employs {value} people."
            questions.append(
                Question(
                    module=name,
                    text=f"How many people does the {name} employ?",
                    answer=str(value),
                )
            )

        listed = " ".join(f"({i + 1}) {q.text}" for i, q in enumerate(questions))
        prompt = (
            f"Answer all {n_modules} of the following independent questions. "
            f"{listed}"
        )

        return cls(prompt=prompt, module_contents=contents, questions=questions)

    def score(self, response: str) -> float:
        if not self.questions:
            return 0.0
        hits = sum(1 for q in self.questions if q.answer in response)
        return hits / len(self.questions)
