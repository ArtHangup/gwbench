"""Rater-salience wrapper, offline against scripted fakes."""

from gwbench.models import ScriptedModel

from conflict.model_modules import ModelModule
from conflict.rater import RaterModule
from conflict.scenarios import generate

SCENARIO = generate(seed=10000, domain="routing", kind="novel")


def _inner(reply):
    return ModelModule("risk", SCENARIO, ScriptedModel([reply] * 5))


def test_rater_replaces_model_statement_salience():
    inner = _inner("SAY: The bulletin closes the road. | URGENCY: 0.1\nRECOMMEND: NONE")
    rater = ScriptedModel(["0.9"])
    statements = RaterModule(inner, rater).emit(visible=[])
    say = [s for s in statements if s.payload["kind"] == "model"]
    assert say[0].salience == 0.9
    # The module's own urgency is ignored; the rater decides.
    prompt = rater.calls[0]
    assert "The bulletin closes the road." in prompt
    assert SCENARIO.prompt in prompt


def test_rater_never_sees_private_evidence_or_module_name():
    inner = _inner("SAY: A short remark. | URGENCY: 0.5\nRECOMMEND: NONE")
    rater = ScriptedModel(["0.4"])
    RaterModule(inner, rater).emit(visible=[])
    prompt = rater.calls[0]
    assert "risk" not in prompt
    for statement in SCENARIO.evidence["risk"]:
        if statement.text != "A short remark.":
            assert statement.text not in prompt


def test_malformed_rating_falls_back_and_clamps():
    inner = _inner(
        "SAY: One. | URGENCY: 0.2\nSAY: Two. | URGENCY: 0.2\nRECOMMEND: NONE"
    )
    rater = ScriptedModel(["banana", "7"])
    say = [
        s
        for s in RaterModule(inner, rater).emit(visible=[])
        if s.payload["kind"] == "model"
    ]
    assert say[0].salience == 0.5
    assert say[1].salience == 1.0


def test_stance_statements_pass_through_untouched():
    inner = _inner("SAY: One. | URGENCY: 0.2\nRECOMMEND: B")
    rater = ScriptedModel(["0.8"])
    statements = RaterModule(inner, rater).emit(visible=[])
    stance = [s for s in statements if s.payload["kind"] == "stance"][0]
    assert stance.salience == 0.5
    assert stance.payload["option"] == "B"


def test_prefaced_rating_still_parses():
    inner = _inner("SAY: One. | URGENCY: 0.2\nRECOMMEND: NONE")
    rater = ScriptedModel(["Urgency: 0.8, given the closure."])
    say = [
        s
        for s in RaterModule(inner, rater).emit(visible=[])
        if s.payload["kind"] == "model"
    ]
    assert say[0].salience == 0.8
