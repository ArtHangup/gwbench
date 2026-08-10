"""Integration under distraction.

Facts are scattered across specialist modules. Answering requires combining a
few specific ones while ignoring the rest. This is the condition where global
workspace theory predicts a capacity limit earns its keep, by forcing selection
instead of letting everything through undifferentiated.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

CONTAINERS = [
    "red_box", "blue_box", "green_box", "black_box", "white_box",
    "amber_jar", "copper_tin", "glass_vial", "iron_crate", "linen_sack",
    "oak_chest", "pewter_cup", "silver_case", "stone_urn", "tin_pail",
    "velvet_pouch", "walnut_drawer", "wicker_basket", "zinc_bucket",
    "brass_canister", "cedar_trunk", "clay_pot", "denim_bag", "enamel_bowl",
]


@dataclass(frozen=True)
class IntegrationTask:
    prompt: str
    module_contents: dict[str, str]
    module_values: dict[str, int]
    required_modules: list[str]
    distractor_modules: list[str]
    answer: str

    @property
    def required_values(self) -> list[int]:
        return [self.module_values[m] for m in self.required_modules]

    @classmethod
    def generate(
        cls, seed: int, n_required: int, n_distractors: int
    ) -> "IntegrationTask":
        total = n_required + n_distractors
        if total > len(CONTAINERS):
            raise ValueError(
                f"need {total} modules but only {len(CONTAINERS)} names available"
            )

        rng = random.Random(seed)
        names = rng.sample(CONTAINERS, total)
        required = sorted(names[:n_required])
        distractors = sorted(names[n_required:])

        values = {name: rng.randint(10, 99) for name in names}
        contents = {
            name: f"The {name.replace('_', ' ')} contains {value}."
            for name, value in values.items()
        }

        answer = str(sum(values[m] for m in required))
        listed = ", ".join(required)
        prompt = (
            "Report the sum of the values held in exactly these containers: "
            f"{listed}. Ignore every other container. "
            "End your reply with the total on its own line."
        )

        return cls(
            prompt=prompt,
            module_contents=contents,
            module_values=values,
            required_modules=required,
            distractor_modules=distractors,
            answer=answer,
        )

    def score(self, response: str) -> float:
        numbers = re.findall(r"-?\d+", response)
        return 1.0 if numbers and numbers[-1] == self.answer else 0.0
