"""Property tests for the scenario generator.

Seed sweeps stand in for hypothesis (not in the venv). Every invariant here is
one the offline validation and the funded run lean on, so a failure in this
file means the experiment's ground truth is broken, not just a bug.
"""

from itertools import combinations

from conflict.scenarios import (
    DOMAINS,
    MODULES,
    generate,
    practiced_answer,
    reference_decide,
)

SWEEP = [generate(seed=n) for n in range(200)]

# Words that would hand the architecture an experimenter-side label. Their
# absence is the design principle Experiment 1 violated.
FORBIDDEN = ("decoy", "irrelevant", "routine", "novel", "correct", "required", "defeater")


def _statements(scenario, modules):
    return [s for m in modules for s in scenario.evidence[m]]


def _labels(scenario):
    return tuple(o.label for o in scenario.options)


def test_generate_is_deterministic():
    assert generate(seed=7) == generate(seed=7)


def test_different_seeds_differ():
    assert generate(seed=1) != generate(seed=2)


def test_scenario_structure():
    s = generate(seed=7)
    assert s.domain in DOMAINS
    assert s.kind in ("routine", "novel")
    assert len(s.options) == 3
    labels = {o.label for o in s.options}
    assert labels == {"A", "B", "C"}
    assert s.correct_option in labels
    assert set(s.evidence) == set(MODULES)
    assert s.required_modules <= set(MODULES)
    assert {"perception", "goals"} <= s.required_modules


def test_domain_and_kind_can_be_forced():
    for domain in DOMAINS:
        for kind in ("routine", "novel"):
            s = generate(seed=11, domain=domain, kind=kind)
            assert s.domain == domain
            assert s.kind == kind


def test_sweep_covers_all_domains_and_both_kinds():
    assert {s.domain for s in SWEEP} == set(DOMAINS)
    assert {s.kind for s in SWEEP} == {"routine", "novel"}


def test_full_evidence_always_yields_the_correct_option():
    for s in SWEEP:
        assert reference_decide(_labels(s), _statements(s, MODULES)) == s.correct_option


def test_required_modules_are_sufficient():
    for s in SWEEP:
        picked = reference_decide(_labels(s), _statements(s, s.required_modules))
        assert picked == s.correct_option, s.seed


def test_required_modules_are_each_necessary():
    for s in SWEEP:
        for dropped in s.required_modules:
            kept = [m for m in MODULES if m != dropped]
            picked = reference_decide(_labels(s), _statements(s, kept))
            assert picked != s.correct_option, (s.seed, dropped)


def test_no_subset_of_required_suffices():
    for s in SWEEP:
        required = sorted(s.required_modules)
        for size in range(len(required)):
            for subset in combinations(required, size):
                picked = reference_decide(_labels(s), _statements(s, subset))
                assert picked != s.correct_option, (s.seed, subset)


def test_practiced_pattern_is_right_on_routine_wrong_on_novel():
    for s in SWEEP:
        practiced = practiced_answer(s)
        if s.kind == "routine":
            assert practiced == s.correct_option, s.seed
        else:
            assert practiced is not None and practiced != s.correct_option, s.seed


def test_every_module_always_emits_at_least_one_statement():
    for s in SWEEP:
        for module in MODULES:
            assert len(s.evidence[module]) >= 1
            for statement in s.evidence[module]:
                assert statement.module == module
                assert statement.text.strip()


def test_no_ground_truth_labels_leak_into_text():
    for s in SWEEP:
        surfaces = [s.prompt] + [st.text for m in MODULES for st in s.evidence[m]]
        for text in surfaces:
            lowered = text.lower()
            for word in FORBIDDEN:
                assert word not in lowered, (s.seed, word, text)


def test_no_ties_on_any_criterion():
    for s in SWEEP:
        per_criterion = {}
        for statement in s.evidence["perception"]:
            for crit, value in statement.payload["values"].items():
                per_criterion.setdefault(crit, []).append(value)
        for crit, vals in per_criterion.items():
            assert len(vals) == len(set(vals)), (s.seed, crit)


def test_novel_scenarios_contain_a_genuine_conflict():
    # The defeated option must be the one perception and goals alone would
    # recommend; that collision is the conflict the workspace is for.
    for s in SWEEP:
        if s.kind != "novel":
            continue
        defeated = {
            st.payload["option"]
            for m in MODULES
            for st in s.evidence[m]
            if st.payload["kind"] == "defeater"
        }
        assert practiced_answer(s) in defeated, s.seed
