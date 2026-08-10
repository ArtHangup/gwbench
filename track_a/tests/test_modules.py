"""Oracle module and controller behavior.

The oracle module is a deterministic emitter: private statements plus a stance
statement giving its current recommendation, computed by the reference rule
over its own evidence united with whatever broadcast statements it has seen.
Revision is therefore mechanical: show it new decisive evidence and its stance
moves; show it nothing and its stance cannot move. That is the property the
architecture comparison leans on.
"""

from conflict.modules import OracleModule
from conflict.scenarios import generate


def _novel():
    return generate(seed=3, domain="routing", kind="novel")


def test_initial_emission_contains_private_statements_and_a_stance():
    scenario = _novel()
    module = OracleModule("perception", scenario)
    statements = module.emit(visible=[])
    texts = [s.text for s in statements]
    for private in scenario.evidence["perception"]:
        assert private.text in texts
    stances = [s for s in statements if s.payload["kind"] == "stance"]
    assert len(stances) == 1
    # Perception alone has values but no ruling criterion: no basis to pick.
    assert stances[0].payload["option"] is None


def test_no_module_alone_can_form_a_recommendation():
    scenario = _novel()
    for name in scenario.evidence:
        module = OracleModule(name, scenario)
        stance = [
            s for s in module.emit(visible=[]) if s.payload["kind"] == "stance"
        ][0]
        assert stance.payload["option"] is None, name


def _criterion(scenario):
    return scenario.evidence["goals"][0]


def _defeaters(scenario):
    return [
        s
        for m in scenario.evidence
        for s in scenario.evidence[m]
        if s.payload["kind"] == "defeater"
    ]


def test_perception_forms_the_surface_stance_once_the_criterion_arrives():
    from conflict.scenarios import practiced_answer

    scenario = _novel()
    module = OracleModule("perception", scenario)
    module.emit(visible=[])
    statements = module.emit(visible=[_criterion(scenario)])
    stance = [s for s in statements if s.payload["kind"] == "stance"][0]
    assert stance.payload["option"] == practiced_answer(scenario)
    assert stance.payload["option"] != scenario.correct_option


def test_perception_revises_to_correct_once_the_defeaters_arrive():
    scenario = _novel()
    module = OracleModule("perception", scenario)
    module.emit(visible=[])
    seen = [_criterion(scenario)]
    module.emit(visible=seen)
    seen += _defeaters(scenario)
    statements = module.emit(visible=seen)
    stance = [s for s in statements if s.payload["kind"] == "stance"][0]
    assert stance.payload["option"] == scenario.correct_option


def test_stubborn_module_never_revises_after_forming():
    scenario = _novel()
    module = OracleModule("perception", scenario, revises=False)
    module.emit(visible=[])
    first = [
        s
        for s in module.emit(visible=[_criterion(scenario)])
        if s.payload["kind"] == "stance"
    ][0]
    after = [
        s
        for s in module.emit(visible=[_criterion(scenario)] + _defeaters(scenario))
        if s.payload["kind"] == "stance"
    ][0]
    assert first.payload["option"] is not None
    assert after.payload["option"] == first.payload["option"]
    assert after.payload["option"] != scenario.correct_option


def test_controller_decides_correctly_from_full_evidence():
    from conflict.modules import OracleController

    scenario = _novel()
    everything = [s for m in scenario.evidence for s in scenario.evidence[m]]
    controller = OracleController(scenario)
    decision = controller.decide(everything)
    assert decision.option == scenario.correct_option
    assert decision.option in decision.text


def test_controller_falls_back_to_stance_majority_when_evidence_is_thin():
    from conflict.modules import OracleController
    from conflict.scenarios import Statement

    scenario = _novel()
    stances = [
        Statement("memory", "memory recommends option B.", {"kind": "stance", "option": "B"}, 0.5),
        Statement("risk", "risk recommends option B.", {"kind": "stance", "option": "B"}, 0.5),
        Statement("social", "social recommends option C.", {"kind": "stance", "option": "C"}, 0.5),
    ]
    controller = OracleController(scenario)
    assert controller.decide(stances).option == "B"


def test_controller_with_nothing_visible_abstains_to_first_option():
    from conflict.modules import OracleController

    scenario = _novel()
    decision = OracleController(scenario).decide([])
    assert decision.option == "A"


def test_controller_counts_only_the_latest_stance_per_module():
    from conflict.modules import OracleController
    from conflict.scenarios import Statement

    scenario = _novel()
    transcript = [
        Statement("perception", "perception recommends option B.", {"kind": "stance", "option": "B"}, 0.5),
        Statement("memory", "memory recommends option B.", {"kind": "stance", "option": "B"}, 0.5),
        # Both modules later revise; the stale B votes must not outvote C.
        Statement("perception", "perception recommends option C.", {"kind": "stance", "option": "C"}, 0.5),
        Statement("memory", "memory recommends option C.", {"kind": "stance", "option": "C"}, 0.5),
    ]
    assert OracleController(scenario).decide(transcript).option == "C"
