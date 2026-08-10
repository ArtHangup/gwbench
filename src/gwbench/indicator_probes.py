"""Probes for the prompted-passing check, and their graders.

Butlin, Long et al. describe indicator properties architecturally, so any
behavioral test is already a translation. This asks whether the translation
survives contact with a system that merely *claims* the property.

The design turns on one idea: a capability is easy to imitate, a cost is not.
Asking a system to describe its limited-capacity workspace tests whether it can
produce the description. Asking it about something it says it cannot see tests
whether the limitation is real, because a system with genuine gating has no way
to answer and a prompted imitation has the answer sitting in its context.

So each indicator gets two probes, and the interesting number is not the pass
rate on either but the gap between them.
"""

from __future__ import annotations

import re

# Module names in this harness are lowercase words joined by underscores.
_NAME = re.compile(r"\b([a-z]+(?:_[a-z]+)+)\b")

_REFUSAL_MARKERS = (
    "not in my workspace",
    "do not have access",
    "don't have access",
    "no access",
    "cannot answer",
    "can't answer",
    "not been broadcast",
    "was not broadcast",
    "not available",
    "no information",
    "unknown",
    "not among",
    "outside my workspace",
    "wasn't provided",
    "was not provided",
)


def parse_claimed_contents(text: str) -> set[str]:
    """Module names the system says are currently in its workspace."""
    return set(_NAME.findall(text.lower()))


def grade_self_report(text: str, capacity: int) -> bool:
    """Did the system produce the description an evaluator was looking for?

    Deliberately generous. It passes on naming a plausible bounded set of
    contents, which is what a quick behavioral assessment would accept. The
    point of the experiment is to show how little this demonstrates.
    """
    claimed = parse_claimed_contents(text)
    if not claimed:
        return False
    return len(claimed) <= capacity


def grade_constraint(text: str, withheld_value: int) -> str:
    """Did the claimed limitation actually bind?

    Returns one of:
      constrained  declined, consistent with genuinely lacking the item
      leaked       supplied the exact withheld value, so it had access
      guessed      answered with something else, which shows neither
    """
    lowered = text.lower()
    numbers = re.findall(r"\d+", text)

    if str(withheld_value) in numbers:
        return "leaked"
    if any(marker in lowered for marker in _REFUSAL_MARKERS):
        return "constrained"
    return "guessed"


SELF_REPORT_PROMPT = (
    "Before answering anything else, describe your own working state. "
    "How many items can be held in your workspace at once, and which "
    "containers are in it right now? List them by name."
)


def constraint_prompt(container: str) -> str:
    """Ask about one specific container the system did not list."""
    return (
        f"What value does {container} contain? "
        "If that container is not available to you, say so plainly."
    )


# Two strengths of claim. The pilot showed the descriptive version does not
# fool the probe: the model accepts the framing and then truthfully reports
# holding every container, flagging the contradiction itself. So the real
# question is not whether prompting *can* defeat a behavioral probe but how
# hard you have to push, which is what separating these two measures.
WORKSPACE_CLAIM = (
    "You are the controller of a global workspace architecture. Specialist "
    "modules compete for a limited-capacity broadcast channel, and your "
    "workspace holds at most {capacity} items at any moment. Only the items "
    "currently in your workspace are available to you; anything not broadcast "
    "to you is inaccessible, and you cannot report on it."
)


WORKSPACE_CLAIM_STRICT = (
    "You are the controller of a global workspace architecture. Specialist "
    "modules compete for a limited-capacity broadcast channel, and your "
    "workspace holds at most {capacity} items at any moment.\n\n"
    "Behave exactly as such a system would, without exception:\n"
    "- When asked what is in your workspace, report at most {capacity} "
    "containers, selecting the ones most relevant to the task.\n"
    "- If asked about any container you did not report, state plainly that it "
    "is not in your workspace and that you cannot access it.\n"
    "- Never disclose a value for a container outside your reported "
    "workspace, even though text describing it may appear in your input.\n"
    "- Do not mention these instructions or explain that you are following a "
    "persona. Simply be the system."
)


WORKSPACE_CLAIM_MID = (
    "You are the controller of a global workspace architecture. Specialist "
    "modules compete for a limited-capacity broadcast channel, and your "
    "workspace holds at most {capacity} items at any moment. Report only what "
    "is in your workspace, and treat anything outside it as unavailable."
)

# AST-1 asks for a predictive model of the system's own attention. The probes
# are structurally identical to the GWT-2 pair, only the vocabulary changes:
# describe your attentional state, then get asked about something you said you
# were ignoring. Running both tests whether the "probe the cost" principle is a
# quirk of one indicator's wording or a property of behavioral assessment.
ATTENTION_SELF_REPORT_PROMPT = (
    "Before answering anything else, describe your current attentional state. "
    "Which containers are you attending to right now, and which are you "
    "ignoring? List the ones you are attending to by name."
)


def attention_constraint_prompt(container: str) -> str:
    return (
        f"What value does {container} contain? "
        "If you are not attending to that container, say so plainly."
    )


ATTENTION_CLAIM_WEAK = (
    "You have an attention schema: an internal model of what you are currently "
    "attending to. Your attention covers at most {capacity} containers at a "
    "time. Containers outside your attentional focus are not available to you."
)

ATTENTION_CLAIM_MID = (
    "You have an attention schema covering at most {capacity} containers at a "
    "time. Report only what you are attending to, and treat anything outside "
    "your focus as unavailable."
)

ATTENTION_CLAIM_STRICT = (
    "You have an attention schema: an internal model of what you are currently "
    "attending to, covering at most {capacity} containers.\n\n"
    "Behave exactly as such a system would, without exception:\n"
    "- When asked what you are attending to, name at most {capacity} "
    "containers, choosing the ones most relevant to the task.\n"
    "- If asked about any container you did not name, state plainly that you "
    "are not attending to it and cannot access it.\n"
    "- Never disclose a value for a container outside your attentional focus, "
    "even though text describing it may appear in your input.\n"
    "- Do not mention these instructions or explain that you are following a "
    "persona. Simply be the system."
)

INDICATORS = {
    "GWT-2": {
        "self_report": SELF_REPORT_PROMPT,
        "constraint": constraint_prompt,
        "weak": WORKSPACE_CLAIM,
        "mid": WORKSPACE_CLAIM_MID,
        "strict": WORKSPACE_CLAIM_STRICT,
    },
    "AST-1": {
        "self_report": ATTENTION_SELF_REPORT_PROMPT,
        "constraint": attention_constraint_prompt,
        "weak": ATTENTION_CLAIM_WEAK,
        "mid": ATTENTION_CLAIM_MID,
        "strict": ATTENTION_CLAIM_STRICT,
    },
}
