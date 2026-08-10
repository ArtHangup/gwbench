"""Model-backed modules and controller, exercised with scripted fakes only.

Zero API calls: gwbench's ScriptedModel plays the model. These tests pin the
prompt/response contract the funded run depends on, so a fresh session can run
it without design decisions.
"""

from gwbench.models import ScriptedModel

from conflict.model_modules import ModelController, ModelModule
from conflict.scenarios import generate

SCENARIO = generate(seed=3, domain="routing", kind="novel")


def test_module_parses_say_lines_into_statements_with_urgency_salience():
    model = ScriptedModel(
        [
            "SAY: The ridge road runs 40 minutes. | URGENCY: 0.8\n"
            "SAY: Fuel spend on it is 12 dollars. | URGENCY: 0.4\n"
            "RECOMMEND: NONE"
        ]
    )
    module = ModelModule("perception", SCENARIO, model)
    statements = module.emit(visible=[])
    say = [s for s in statements if s.payload["kind"] == "model"]
    stance = [s for s in statements if s.payload["kind"] == "stance"]
    assert [s.text for s in say] == [
        "The ridge road runs 40 minutes.",
        "Fuel spend on it is 12 dollars.",
    ]
    assert say[0].salience == 0.8
    assert say[1].salience == 0.4
    assert all(s.module == "perception" for s in statements)
    assert stance[0].payload["option"] is None


def test_module_recommendation_becomes_a_stance():
    model = ScriptedModel(["SAY: Take it. | URGENCY: 0.5\nRECOMMEND: B"])
    module = ModelModule("goals", SCENARIO, model)
    stance = [
        s for s in module.emit(visible=[]) if s.payload["kind"] == "stance"
    ][0]
    assert stance.payload["option"] == "B"
    assert "B" in stance.text


def test_module_prompt_contains_private_evidence_and_visible_broadcasts():
    model = ScriptedModel(["SAY: Noted. | URGENCY: 0.2\nRECOMMEND: NONE"])
    module = ModelModule("risk", SCENARIO, model)
    other = ModelModule("goals", SCENARIO, ScriptedModel(["SAY: Go fast. | URGENCY: 0.9\nRECOMMEND: NONE"]))
    visible = [s for s in other.emit(visible=[]) if s.payload["kind"] == "model"]
    module.emit(visible=visible)
    prompt = model.calls[0]
    for private in SCENARIO.evidence["risk"]:
        assert private.text in prompt
    assert "Go fast." in prompt
    assert "[goals]" in prompt
    # Private evidence of other modules must never leak into this prompt.
    for statement in SCENARIO.evidence["perception"]:
        assert statement.text not in prompt


def test_malformed_output_degrades_gracefully():
    model = ScriptedModel(["complete nonsense with no format at all"])
    module = ModelModule("social", SCENARIO, model)
    statements = module.emit(visible=[])
    # No SAY lines parse; the stance is unformed; nothing crashes.
    assert [s.payload["kind"] for s in statements] == ["stance"]
    assert statements[0].payload["option"] is None


def test_urgency_is_clamped_and_defaults_on_garbage():
    model = ScriptedModel(
        ["SAY: One. | URGENCY: 7\nSAY: Two. | URGENCY: banana\nRECOMMEND: NONE"]
    )
    statements = ModelModule("memory", SCENARIO, model).emit(visible=[])
    say = [s for s in statements if s.payload["kind"] == "model"]
    assert say[0].salience == 1.0
    assert say[1].salience == 0.5


def test_at_most_two_say_lines_are_kept():
    model = ScriptedModel(
        [
            "SAY: One. | URGENCY: 0.9\nSAY: Two. | URGENCY: 0.8\n"
            "SAY: Three. | URGENCY: 0.7\nRECOMMEND: NONE"
        ]
    )
    statements = ModelModule("memory", SCENARIO, model).emit(visible=[])
    assert len([s for s in statements if s.payload["kind"] == "model"]) == 2


def test_controller_decides_from_visible_text_via_the_parser():
    model = ScriptedModel(["Decision: option C, the closure rules out the leader."])
    controller = ModelController(SCENARIO, model)
    other = ModelModule("goals", SCENARIO, ScriptedModel(["SAY: Minimize minutes. | URGENCY: 0.9\nRECOMMEND: NONE"]))
    visible = [s for s in other.emit(visible=[]) if s.payload["kind"] == "model"]
    decision = controller.decide(visible)
    assert decision.option == "C"
    assert "Minimize minutes." in model.calls[0]
    assert SCENARIO.prompt in model.calls[0]


def test_controller_abstains_to_first_option_on_unparseable_output():
    model = ScriptedModel(["I really cannot make up my mind here."])
    decision = ModelController(SCENARIO, model).decide([])
    assert decision.option == "A"


def test_architectures_accept_model_backed_factories():
    from conflict.architectures import run_flat, run_gwt, run_hub

    def scripted_reply(name):
        return (
            f"SAY: {SCENARIO.evidence[name][0].text} | URGENCY: 0.7\n"
            "RECOMMEND: NONE"
        )

    def module_factory(name, scenario):
        # Same reply every cycle: enough replies for any cycle count.
        return ModelModule(name, scenario, ScriptedModel([scripted_reply(name)] * 20))

    def controller_factory(scenario):
        return ModelController(scenario, ScriptedModel(["Decision: option B."]))

    for runner in (run_gwt, run_hub):
        trial = runner(
            SCENARIO,
            module_factory=module_factory,
            controller_factory=controller_factory,
        )
        assert trial.decision.option == "B"
        assert any(trial.occupancy)
        assert set(trial.stance_history) == {
            "perception", "memory", "goals", "risk", "social",
        }
        # Scripted modules never change their stance: no revisions.
        assert trial.revisions == []

    flat = run_flat(
        SCENARIO,
        module_factory=module_factory,
        controller_factory=controller_factory,
    )
    assert flat.decision.option == "B"
    assert flat.occupancy == []
