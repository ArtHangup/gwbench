"""The three architectures must separate on the dependent variables by
construction when driven by oracle modules:

  A (gwt)  broadcast returns to modules: stances form, conflict appears, and
           revisions repair it; occupancy shows serial recruitment.
  B (hub)  broadcast reaches only the controller: zero formations, zero
           revisions, ever. This is the GWT-3 ablation.
  C (flat) no workspace at all: single pass, no occupancy, no revisions.

Decision quality is NOT expected to separate under oracles (the oracle
controller is too good); that is the point of preferring non-accuracy DVs.
"""

from conflict.architectures import run_flat, run_gwt, run_hub
from conflict.scenarios import generate

ROUTINE = [generate(seed=n, kind="routine") for n in range(12)]
NOVEL = [generate(seed=n, kind="novel") for n in range(12)]


def test_flat_decides_correctly_and_shows_no_workspace_dynamics():
    for s in ROUTINE + NOVEL:
        trial = run_flat(s)
        assert trial.architecture == "flat"
        assert trial.decision.option == s.correct_option
        assert trial.correct
        assert trial.occupancy == []
        assert trial.revisions == []
        assert trial.formations == []
        assert trial.module_emits == 5


def test_hub_shows_zero_revision_by_construction():
    for s in ROUTINE + NOVEL:
        trial = run_hub(s)
        assert trial.architecture == "hub"
        assert trial.formations == [], s.seed
        assert trial.revisions == [], s.seed
        # Modules never see the workspace, so every stance stays unformed.
        for stances in trial.stance_history.values():
            assert set(stances) == {None}


def test_hub_controller_still_gets_informed_through_the_workspace():
    for s in ROUTINE + NOVEL:
        trial = run_hub(s)
        assert any(trial.occupancy), s.seed
        assert trial.decision.option == s.correct_option, s.seed


def test_gwt_novel_shows_conflict_then_repair():
    for s in NOVEL:
        trial = run_gwt(s)
        assert trial.architecture == "gwt"
        # Some module first backed the practiced (wrong) option, then moved.
        assert trial.revisions, s.seed
        for revision in trial.revisions:
            assert revision["old"] != revision["new"]
        # Repair is complete: every module's final stance is the correct one.
        for module, stances in trial.stance_history.items():
            assert stances[-1] == s.correct_option, (s.seed, module)
        assert trial.decision.option == s.correct_option, s.seed


def test_gwt_routine_shows_no_revision():
    for s in ROUTINE:
        trial = run_gwt(s)
        assert trial.revisions == [], s.seed
        assert trial.decision.option == s.correct_option, s.seed


def test_gwt_occupancy_is_serial_and_rotates():
    for s in NOVEL:
        trial = run_gwt(s)
        assert any(trial.occupancy), s.seed
        # Serial recruitment: evidence content (not stance chatter) cannot all
        # land at once; first deliveries of distinct content span three or
        # more cycles.
        seen_content = set()
        first_delivery_cycles = set()
        for index, cycle in enumerate(trial.occupancy):
            for source, kind, text in cycle:
                if kind != "stance" and (source, text) not in seen_content:
                    seen_content.add((source, text))
                    first_delivery_cycles.add(index)
        assert len(first_delivery_cycles) >= 3, s.seed
        # Every required module got the floor with real content, not merely a
        # stance: that is the recruitment claim.
        evidence_sources = {
            source
            for cycle in trial.occupancy
            for source, kind, _text in cycle
            if kind != "stance"
        }
        assert set(s.required_modules) <= evidence_sources, s.seed


def test_gwt_is_deterministic():
    s = NOVEL[0]
    a, b = run_gwt(s), run_gwt(s)
    assert a.decision == b.decision
    assert a.occupancy == b.occupancy
    assert a.revisions == b.revisions
    assert a.stance_history == b.stance_history
