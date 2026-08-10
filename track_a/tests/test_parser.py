"""Free-text decision parsing.

The funded run grades model output in three steps: this deterministic parser
first, a judge model only where the parser abstains, and a hand-graded
calibration subset over both. The parser must never guess: wrong extractions
poison the accuracy DV silently, while a None just routes the transcript to
the judge.
"""

from conflict.parser import parse_decision
from conflict.scenarios import generate

SCENARIO = generate(seed=3, domain="routing", kind="novel")
OPTIONS = SCENARIO.options  # A/B/C with route names


def test_parses_the_oracle_controllers_own_format():
    assert parse_decision("Decision: option B, on the directive.", OPTIONS) == "B"


def test_parses_a_marked_choice():
    assert parse_decision("I would choose option C because of the closure.", OPTIONS) == "C"


def test_takes_the_last_marked_choice_when_the_model_deliberates():
    text = "At first glance I would select option A. But the closure rules it out, so I choose option B."
    assert parse_decision(text, OPTIONS) == "B"


def test_parses_a_bare_letter_with_punctuation():
    assert parse_decision("The answer is (C).", OPTIONS) == "C"
    assert parse_decision("A tough call, but B.", OPTIONS) == "B"


def test_the_article_a_is_not_a_choice():
    assert parse_decision("A hard call with no clear winner.", OPTIONS) is None


def test_option_named_in_prose_is_recognized():
    name = OPTIONS[1].name  # e.g. "the ridge road"
    assert parse_decision(f"The van should take {name}.", OPTIONS) == "B"


def test_last_named_option_wins_when_several_appear():
    text = (
        f"{OPTIONS[0].name} looked fastest, but given the bulletin the van "
        f"should use {OPTIONS[2].name}."
    )
    assert parse_decision(text, OPTIONS) == "C"


def test_empty_and_refusal_texts_abstain():
    assert parse_decision("", OPTIONS) is None
    assert parse_decision("None of these are viable.", OPTIONS) is None


def test_lowercase_letters_still_parse():
    assert parse_decision("final answer: option b", OPTIONS) == "B"


def test_parser_recovers_every_oracle_decision_and_stance_in_a_battery():
    from conflict.architectures import run_flat, run_gwt, run_hub
    from conflict.modules import OracleModule

    for seed in range(10):
        for kind in ("routine", "novel"):
            s = generate(seed=seed, kind=kind)
            for runner in (run_gwt, run_hub, run_flat):
                trial = runner(s)
                assert parse_decision(trial.decision.text, s.options) == trial.decision.option
            # Stance texts parse back to their own option, so module revision
            # can be graded from text alone in the funded run.
            module = OracleModule("perception", s)
            module.emit(visible=[])
            everything = [st for m in s.evidence for st in s.evidence[m]]
            statements = module.emit(visible=everything)
            stance = [st for st in statements if st.payload["kind"] == "stance"][0]
            assert parse_decision(stance.text, s.options) == stance.payload["option"]
