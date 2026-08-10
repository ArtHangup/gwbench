"""Deterministic extraction of a decision from free text.

Order of preference, each applied to the whole text with the LAST hit
winning (models deliberate, then decide):

1. A letter or option name inside a sentence carrying a decision marker
   (decision, choose, select, recommend, answer, final, take, use, treat,
   accept, run).
2. A standalone option letter. "A" only counts when punctuation or the end
   of text follows, because otherwise it is usually the article.
3. An option referred to by name.

Anything else returns None: the parser abstains rather than guesses, and
abstentions route to the judge model per the grading spec.
"""

from __future__ import annotations

import re
from typing import Optional, Sequence

from conflict.scenarios import Option

_MARKERS = re.compile(
    r"\b(decision|decide|choose|chose|select|selected|recommend|recommends|"
    r"answer|final|take|takes|use|uses|treat|treated|accept|accepts|run)\b",
    re.IGNORECASE,
)
_SENTENCES = re.compile(r"[^.!?\n]+[.!?]?")


def _letters_in(text: str, labels: Sequence[str]) -> list[str]:
    """Standalone letter tokens, in order of appearance."""
    hits = []
    for match in re.finditer(r"\(?\b([A-Za-z])\b\)?", text):
        letter = match.group(1).upper()
        if letter not in labels:
            continue
        rest = text[match.end() :]
        if letter == "A" and match.group(1) == "A" and re.match(r"\s+\w", rest):
            # Capital A followed by a word is almost always the article.
            continue
        if match.group(1) == "a":
            # A lowercase bare "a" is the article; accept it only in an
            # explicit "option a" construction, handled below.
            before = text[: match.start()].lower().rstrip()
            if not before.endswith("option"):
                continue
        hits.append(letter)
    return hits


def _names_in(text: str, options: Sequence[Option]) -> list[str]:
    """Option labels referenced by name, in order of last appearance."""
    lowered = text.lower()
    positions = []
    for option in options:
        name = option.name.lower()
        index = lowered.rfind(name)
        if index < 0 and name.startswith("the "):
            index = lowered.rfind(name[4:])
        if index >= 0:
            positions.append((index, option.label))
    return [label for _index, label in sorted(positions)]


def parse_decision(text: str, options: Sequence[Option]) -> Optional[str]:
    labels = [option.label for option in options]
    if not text.strip():
        return None

    marked: list[str] = []
    for sentence_match in _SENTENCES.finditer(text):
        sentence = sentence_match.group(0)
        if not _MARKERS.search(sentence):
            continue
        found = _letters_in(sentence, labels) or _names_in(sentence, options)
        if found:
            marked.append(found[-1])
    if marked:
        return marked[-1]

    letters = _letters_in(text, labels)
    if letters:
        return letters[-1]

    names = _names_in(text, options)
    if names:
        return names[-1]

    return None
