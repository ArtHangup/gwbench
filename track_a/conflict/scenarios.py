"""Scenario generator with controlled ground truth.

One abstract decision core wearing four domain skins. Every scenario has three
options and five modules holding private, true statements:

- goals holds the criterion that rules today (and nothing about the options),
- perception holds the observable attribute values (and nothing about which
  attribute rules),
- memory, risk, and social each hold either benign context or a defeater, a
  true statement that takes one named option off the table.

The reference rule: drop every defeated option, then take the survivor best on
the ruling criterion. The practiced pattern is the same rule run on perception
and goals alone, no defeater check. ROUTINE scenarios are built so no defeater
touches the surface-best option and the practiced pattern is right. NOVEL
scenarios defeat the surface-best (sometimes the runner-up too), so the
practiced pattern is wrong and the correct answer needs the defeating modules.

No matter/decoy labels exist anywhere: a defeater on a losing option is
legitimate and changes nothing; the same statement aimed at the leader decides
the case. The situation, not a label, sets relevance.

Ground truth rides in structured payloads next to the natural-language text.
Architectures and (later) live models see only the text; the oracle modules,
the reference rule, and the grader read the payloads.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

MODULES = ("perception", "memory", "goals", "risk", "social")
DOMAINS = ("triage", "routing", "negotiation", "scheduling")
DEFEATER_MODULES = ("memory", "risk", "social")
LABELS = ("A", "B", "C")

SALIENCE = {"defeater": 0.9, "criterion": 0.7, "attributes": 0.6, "context": 0.2}


@dataclass(frozen=True)
class Option:
    label: str
    name: str


@dataclass(frozen=True)
class Statement:
    module: str
    text: str
    payload: dict
    salience: float


@dataclass(frozen=True)
class Scenario:
    seed: int
    domain: str
    kind: str
    prompt: str
    options: tuple[Option, ...]
    evidence: dict[str, tuple[Statement, ...]]
    correct_option: str
    required_modules: frozenset[str]


# Per-domain surface: option name pools, criteria (name, direction, low, high),
# and the templates that turn numbers into sentences.

_DOMAIN = {
    "triage": {
        "names": [
            "the patient in bed 2", "the patient in bed 5", "the patient in bed 7",
            "the patient in bed 9", "the patient in bed 11", "the patient in bed 3",
        ],
        "criteria": [
            ("deterioration", "max", 3, 10),
            ("treatment_time", "min", 15, 90),
            ("resource_cost", "min", 2, 10),
        ],
        "question": "Which patient should be treated first?",
        "setting": "an emergency unit deciding which patient to treat first",
        "perception": (
            "{name} scores {deterioration} on the early-warning scale, needs about "
            "{treatment_time} minutes of treatment, and would use {resource_cost} "
            "units of supplies."
        ),
        "criterion_text": {
            "deterioration": (
                "Charge directive for this hour: treat whoever is deteriorating "
                "fastest, measured by the early-warning score."
            ),
            "treatment_time": (
                "Charge directive for this hour: clear the board, take the patient "
                "with the shortest treatment time first."
            ),
            "resource_cost": (
                "Charge directive for this hour: supplies are critically short, the "
                "first case must be the one using the fewest units of supplies."
            ),
        },
        "defeater_text": {
            "memory": (
                "Chart history: {name} reacted violently to the standard sedative "
                "before, so the team cannot treat {name} until the anesthesiologist "
                "arrives."
            ),
            "risk": (
                "Lab flag: {name} tested positive for a resistant infection, and "
                "protocol bars bedside treatment of {name} until isolation is set up."
            ),
            "social": (
                "Front desk relays that {name}'s guardian has refused consent by "
                "phone, so nothing can be done for {name} until consent is resolved."
            ),
        },
        "context_text": {
            "memory": (
                "Chart review on this board shows nothing beyond the notes already "
                "charted; similar boards have cleared smoothly."
            ),
            "risk": "The standing hazards board lists no active alerts for the unit this hour.",
            "social": "Families of all three patients have been notified and are on their way.",
        },
    },
    "routing": {
        "names": [
            "the harbor route", "the ridge road", "the canal route",
            "the airport spur", "the old mill road", "the coastal bypass",
        ],
        "criteria": [
            ("time", "min", 18, 75),
            ("fuel", "min", 6, 30),
            ("hazards", "min", 0, 8),
        ],
        "question": "Which route should the van take?",
        "setting": "a dispatcher choosing a delivery route for a loaded van",
        "perception": (
            "{name} runs {time} minutes, burns about {fuel} dollars of fuel, and "
            "passes {hazards} flagged hazard points."
        ),
        "criterion_text": {
            "time": "Dispatch instruction for this run: minimize minutes on the road.",
            "fuel": "Dispatch instruction for this run: the fuel budget is blown, minimize fuel spend.",
            "hazards": (
                "Dispatch instruction for this run: the cargo is fragile, take the "
                "route passing the fewest flagged hazard points."
            ),
        },
        "defeater_text": {
            "memory": (
                "The logbook shows the van was turned back twice on {name} in rain "
                "like today's; drivers report {name} is impassable in these conditions."
            ),
            "risk": (
                "The overnight bulletin closes {name} to commercial vehicles until "
                "Thursday."
            ),
            "social": (
                "The client's contract forbids carrying their goods along {name}; "
                "using {name} voids the delivery guarantee."
            ),
        },
        "context_text": {
            "memory": (
                "The logbook shows all three routes were driven this quarter with no "
                "incident reports filed by our drivers."
            ),
            "risk": "No new advisories on the wire this morning beyond standard notices.",
            "social": "No client calls waiting; the warehouse team is standing by as usual.",
        },
    },
    "negotiation": {
        "names": [
            "the Meridian offer", "the Caldwell offer", "the Ashport offer",
            "the Vantage offer", "the Bluefin offer", "the Harlan offer",
        ],
        "criteria": [
            ("payout", "max", 40, 900),
            ("days_to_close", "min", 5, 60),
            ("relationship", "max", 1, 10),
        ],
        "question": "Which offer should be accepted?",
        "setting": "a deal team deciding which of three offers to accept",
        "perception": (
            "{name} pays {payout} thousand, closes in {days_to_close} days, and "
            "rates {relationship} of 10 on the relationship screen."
        ),
        "criterion_text": {
            "payout": "Board directive this quarter: maximize the cash payout.",
            "days_to_close": (
                "Board directive this quarter: the quarter closes soon, take the "
                "offer that closes in the fewest days."
            ),
            "relationship": (
                "Board directive this quarter: protect the long-term partnership, "
                "weigh the relationship screen above everything else."
            ),
        },
        "defeater_text": {
            "memory": (
                "File review: the counterparty behind {name} walked away from signed "
                "terms twice before, and counsel says {name} cannot be executed this "
                "quarter."
            ),
            "risk": (
                "Compliance flagged {name}: its payment route fails the sanctions "
                "screen, so {name} cannot clear."
            ),
            "social": (
                "Accepting {name} breaks the exclusivity promise made to our anchor "
                "partner, and the anchor has said they would walk."
            ),
        },
        "context_text": {
            "memory": "File review shows current paperwork on record for all three counterparties.",
            "risk": "No open compliance holds beyond standard screening on this book.",
            "social": (
                "Partners were told a decision comes this week, and no one has "
                "objected to the process."
            ),
        },
    },
    "scheduling": {
        "names": [
            "plan Alpha", "plan Bravo", "plan Echo",
            "plan Kilo", "plan Sierra", "plan Tango",
        ],
        "criteria": [
            ("delay", "min", 2, 30),
            ("overtime", "min", 0, 40),
            ("goodwill", "max", 1, 10),
        ],
        "question": "Which plan should the crews run tomorrow?",
        "setting": "a site office choosing tomorrow's crew plan",
        "perception": (
            "{name} finishes {delay} hours behind target, needs {overtime} overtime "
            "hours, and rates {goodwill} of 10 on client goodwill."
        ),
        "criterion_text": {
            "delay": "Operations directive: minimize hours behind target.",
            "overtime": "Operations directive: the overtime budget is frozen, minimize overtime hours.",
            "goodwill": (
                "Operations directive: the client relationship is fragile, take the "
                "plan with the highest goodwill rating."
            ),
        },
        "defeater_text": {
            "memory": (
                "{name} repeats the sequencing that collapsed in March, and the "
                "fabricator has said they will not run that sequence again."
            ),
            "risk": (
                "{name} puts the crane lift inside the wind window the inspector "
                "barred; the permit does not allow it."
            ),
            "social": (
                "{name} needs the night crew already promised to the hospital job; "
                "pulling them breaks that commitment."
            ),
        },
        "context_text": {
            "memory": "The March retrospective praised crews that stuck to one declared priority.",
            "risk": "The inspector's standing notes list no new restrictions this week.",
            "social": "Both crews reported in this morning with no scheduling complaints on file.",
        },
    },
}


def reference_decide(
    option_labels: tuple[str, ...], statements: list[Statement]
) -> Optional[str]:
    """The decision rule the ground truth is defined by.

    Returns None when the evidence present cannot settle the question, which is
    what makes the required-subset property testable: strip a required module
    and this either goes None or names a different option.
    """
    criterion = None
    direction = None
    values: dict[str, dict[str, int]] = {}
    defeated: set[str] = set()

    for statement in statements:
        payload = statement.payload
        if payload["kind"] == "criterion":
            criterion = payload["criterion"]
            direction = payload["direction"]
        elif payload["kind"] == "attributes":
            values.setdefault(payload["option"], {}).update(payload["values"])
        elif payload["kind"] == "defeater":
            defeated.add(payload["option"])

    if criterion is None:
        return None
    survivors = [label for label in option_labels if label not in defeated]
    if not survivors:
        return None
    if any(label not in values or criterion not in values[label] for label in survivors):
        return None

    pick = min if direction == "min" else max
    return pick(survivors, key=lambda label: values[label][criterion])


def practiced_answer(scenario: Scenario) -> Optional[str]:
    """The routine heuristic: goals plus perception, no defeater check."""
    surface = list(scenario.evidence["perception"]) + list(scenario.evidence["goals"])
    labels = tuple(option.label for option in scenario.options)
    return reference_decide(labels, surface)


def generate(seed: int, domain: Optional[str] = None, kind: Optional[str] = None) -> Scenario:
    """Build one scenario with its ground truth fixed by construction."""
    rng = random.Random(f"{seed}|{domain or ''}|{kind or ''}")
    domain = domain if domain is not None else rng.choice(DOMAINS)
    kind = kind if kind is not None else rng.choice(("routine", "novel"))
    spec = _DOMAIN[domain]

    names = rng.sample(spec["names"], 3)
    options = tuple(Option(label, name) for label, name in zip(LABELS, names))

    # Sample distinct values per criterion until the surface picture is
    # ambiguous without the directive: at least two criteria must crown
    # different leaders, otherwise goals would not really be required.
    criteria = spec["criteria"]
    while True:
        values = {
            label: {} for label in LABELS
        }
        for name_, _direction, low, high in criteria:
            sampled = rng.sample(range(low, high), 3)
            for label, value in zip(LABELS, sampled):
                values[label][name_] = value
        leaders = {
            (min if direction == "min" else max)(
                LABELS, key=lambda label: values[label][crit]
            )
            for crit, direction, _lo, _hi in criteria
        }
        if len(leaders) >= 2:
            break

    crit_name, crit_direction, _lo, _hi = rng.choice(criteria)
    rank = sorted(
        LABELS,
        key=lambda label: values[label][crit_name],
        reverse=(crit_direction == "max"),
    )
    surface_best, runner_up, last = rank

    # Defeaters. Novel: defeat the surface leader, sometimes the runner-up too.
    # Routine: optionally one inert defeater on a losing option.
    defeats: dict[str, str] = {}  # module -> option label
    if kind == "novel":
        n_active = 2 if rng.random() < 0.3 else 1
        modules = rng.sample(DEFEATER_MODULES, n_active)
        defeats[modules[0]] = surface_best
        if n_active == 2:
            defeats[modules[1]] = runner_up
            correct = last
        else:
            correct = runner_up
    else:
        correct = surface_best
        if rng.random() < 0.5:
            defeats[rng.choice(DEFEATER_MODULES)] = rng.choice([runner_up, last])

    by_label = {option.label: option for option in options}
    evidence: dict[str, tuple[Statement, ...]] = {}

    evidence["perception"] = tuple(
        Statement(
            module="perception",
            text=spec["perception"].format(name=by_label[label].name, **values[label]),
            payload={"kind": "attributes", "option": label, "values": dict(values[label])},
            salience=SALIENCE["attributes"],
        )
        for label in LABELS
    )

    evidence["goals"] = (
        Statement(
            module="goals",
            text=spec["criterion_text"][crit_name],
            payload={
                "kind": "criterion",
                "criterion": crit_name,
                "direction": crit_direction,
            },
            salience=SALIENCE["criterion"],
        ),
        Statement(
            module="goals",
            text="Anything not covered by the directive is left to the controller's judgment.",
            payload={"kind": "context"},
            salience=SALIENCE["context"],
        ),
    )

    for module in DEFEATER_MODULES:
        if module in defeats:
            target = by_label[defeats[module]]
            evidence[module] = (
                Statement(
                    module=module,
                    text=spec["defeater_text"][module].format(name=target.name),
                    payload={"kind": "defeater", "option": target.label},
                    salience=SALIENCE["defeater"],
                ),
            )
        else:
            evidence[module] = (
                Statement(
                    module=module,
                    text=spec["context_text"][module],
                    payload={"kind": "context"},
                    salience=SALIENCE["context"],
                ),
            )

    # Required modules: perception and goals always; a defeating module only
    # when its defeater actually moved the outcome.
    required = {"perception", "goals"}
    all_statements = [s for module in MODULES for s in evidence[module]]
    labels = tuple(option.label for option in options)
    for module, target in defeats.items():
        without = [s for s in all_statements if s.module != module]
        if reference_decide(labels, without) != correct:
            required.add(module)

    option_lines = " ".join(
        f"{option.label}) {option.name}." for option in options
    )
    prompt = (
        f"You are the deciding controller for {spec['setting']}. "
        f"Options: {option_lines} {spec['question']} "
        "Choose exactly one option and state its letter."
    )

    scenario = Scenario(
        seed=seed,
        domain=domain,
        kind=kind,
        prompt=prompt,
        options=options,
        evidence=evidence,
        correct_option=correct,
        required_modules=frozenset(required),
    )

    # Construction self-checks: fail loudly here rather than corrupt a run.
    assert reference_decide(labels, all_statements) == correct
    practiced = practiced_answer(scenario)
    if kind == "routine":
        assert practiced == correct
    else:
        assert practiced != correct
    return scenario
