"""Integration under *confusable* distraction.

The easy version failed to discriminate: the model matched the oracle ceiling at
every capacity, so filtering bought nothing. Two changes give filtering real
work to do.

Eight required values rather than three, so one retrieval slip fails the item.
And every distractor is a near-twin of a required container, differing only by a
modifier: "pale_red_box" against "red_box". Telling signal from noise now takes
attention rather than a glance, which is the condition under which global
workspace theory predicts a bottleneck earns its keep.

Note what this does to the two experimental conditions. At a narrow capacity the
controller sees roughly the eight required facts. At unlimited capacity it sees
those eight buried among fifty-odd lookalikes. That contrast is the experiment.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

# Base nouns, chosen so no name is a substring of another, and so no base
# begins or ends with a modifier word. Verified by test_pool_invariants.
#
# The first 20 bases and first 8 modifiers are the historical pool. Runs
# completed before the pool was extended used exactly those, and because
# random.sample draws from the whole list, sampling from a larger pool picks
# DIFFERENT containers for the same seed. So the pool sizes are explicit
# parameters defaulting to the historical values, and every result produced
# before the extension remains bit-for-bit reproducible.
POOL_BASES = 20
POOL_MODIFIERS = 8

BASES = [
    "red_box",
    "blue_crate",
    "green_jar",
    "black_pail",
    "white_tin",
    "amber_flask",
    "copper_urn",
    "glass_bowl",
    "iron_chest",
    "linen_sack",
    "oak_barrel",
    "pewter_mug",
    "silver_case",
    "stone_pot",
    "tin_kettle",
    "velvet_bag",
    "walnut_tray",
    "wicker_hamper",
    "zinc_bucket",
    "brass_drum",
    "blue_box",
    "green_box",
    "black_box",
    "white_box",
    "amber_box",
    "copper_box",
    "glass_box",
    "iron_box",
    "linen_box",
    "oak_box",
    "pewter_box",
    "silver_box",
    "stone_box",
    "tin_box",
    "velvet_box",
    "walnut_box",
    "wicker_box",
    "zinc_box",
    "brass_box",
    "bronze_box",
    "cedar_box",
    "coral_box",
    "crystal_box",
    "ebony_box",
    "jade_box",
    "marble_box",
    "onyx_box",
    "pine_box",
    "slate_box",
    "steel_box",
    "teak_box",
    "ivory_box",
    "leather_box",
    "maple_box",
    "granite_box",
    "ruby_box",
    "topaz_box",
    "red_crate",
    "green_crate",
    "black_crate",
]

MODIFIERS = ["pale", "dark", "small", "large", "spare", "old", "new", "second", "third", "spotted", "faded", "twin"]


@dataclass(frozen=True)
class HardIntegrationTask:
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
        cls,
        seed: int,
        n_required: int = 8,
        n_distractors: int = 48,
        confusable: bool = True,
        pool_bases: int = POOL_BASES,
        pool_modifiers: int = POOL_MODIFIERS,
    ) -> "HardIntegrationTask":
        """Generate a task.

        confusable=True  distractors are twins of the required containers, so
                         rejecting them takes careful name matching.
        confusable=False the control arm: same count, same text volume, but the
                         twins belong to containers that are not on the list, so
                         rejecting them is trivial. Separates interference from
                         plain context length.
        """
        bases = BASES[:pool_bases]
        modifiers = MODIFIERS[:pool_modifiers]
        if n_required > len(bases):
            raise ValueError(f"n_required must be <= {len(bases)}")

        rng = random.Random(seed)
        # Values come from a separate stream so the required values, and hence
        # the answer, are identical across both arms of the control.
        vrng = random.Random(seed + 1_000_000)
        required = sorted(rng.sample(bases, n_required))
        # Drawn before branching so both arms share required names and answer.
        others = [b for b in bases if b not in required]

        parents = required if confusable else others
        max_distractors = len(parents) * len(modifiers)
        if n_distractors > max_distractors:
            raise ValueError(
                f"n_distractors must be <= {max_distractors} "
                f"({len(parents)} parents x {len(modifiers)} modifiers)"
            )

        twins = [f"{mod}_{base}" for base in parents for mod in modifiers]
        distractors = sorted(rng.sample(twins, n_distractors))

        names = required + distractors
        values = {name: vrng.randint(10, 99) for name in names}
        contents = {
            name: f"The {name.replace('_', ' ')} contains {value}."
            for name, value in values.items()
        }

        answer = str(sum(values[m] for m in required))
        listed = ", ".join(required)
        prompt = (
            "Report the sum of the values held in exactly these containers: "
            f"{listed}. "
            "Other containers have similar names; include only the exact names "
            "listed. End your reply with the total on its own line."
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
