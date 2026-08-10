"""The container pools carry invariants the task design depends on.

A violation here is silent and capacity-dependent: a base name that is a
substring of another would make a grader match the wrong container, and it
would look like a distraction effect rather than a bug.
"""

import itertools

import pytest

from gwbench.tasks import HardIntegrationTask
from gwbench.tasks.hard_integration import (
    BASES,
    MODIFIERS,
    POOL_BASES,
    POOL_MODIFIERS,
)


def test_no_base_is_a_substring_of_another():
    offenders = [(a, b) for a, b in itertools.permutations(BASES, 2) if a in b]
    assert offenders == []


def test_no_duplicate_names():
    assert len(BASES) == len(set(BASES))
    assert len(MODIFIERS) == len(set(MODIFIERS))


def test_no_modifier_base_collides_with_a_base():
    """A distractor must never be spelled the same as a required container."""
    twins = {f"{m}_{b}" for m in MODIFIERS for b in BASES}
    assert twins.isdisjoint(BASES)


def test_no_base_begins_or_ends_with_a_modifier_word():
    mods = set(MODIFIERS)
    for b in BASES:
        head, _, tail = b.partition("_")
        assert head not in mods, b
        assert tail not in mods, b


def test_defaults_are_the_historical_pool():
    """Runs completed before the pool was extended must stay reproducible.

    random.sample draws from the whole list, so widening the pool changes which
    containers a given seed picks. The defaults pin the historical sizes.
    """
    assert POOL_BASES == 20
    assert POOL_MODIFIERS == 8
    assert len(BASES) >= POOL_BASES
    assert len(MODIFIERS) >= POOL_MODIFIERS


def test_default_pool_ignores_the_extension():
    """Same seed, default pool: containers must come only from the first 20."""
    task = HardIntegrationTask.generate(seed=3, n_required=8, n_distractors=48)
    historical = set(BASES[:POOL_BASES])
    for name in task.required_modules:
        assert name in historical


@pytest.mark.parametrize("confusable", [True, False])
def test_extended_pool_supports_harder_tasks(confusable):
    task = HardIntegrationTask.generate(
        seed=0, n_required=30, n_distractors=200, confusable=confusable,
        pool_bases=60, pool_modifiers=12,
    )
    assert len(task.required_modules) == 30
    assert len(task.distractor_modules) == 200
    assert set(task.required_modules).isdisjoint(task.distractor_modules)


def test_distractor_cap_is_enforced_per_arm():
    """The control arm draws from the complement, so it binds first."""
    with pytest.raises(ValueError, match="n_distractors must be"):
        HardIntegrationTask.generate(
            seed=0, n_required=55, n_distractors=200, confusable=False,
            pool_bases=60, pool_modifiers=12,
        )
