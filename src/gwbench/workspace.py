"""A capacity-limited global workspace.

Specialist modules submit proposals. Only what fits inside the capacity budget is
broadcast back to every module. That budget is the independent variable of the
experiment, so it is enforced here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

Tokenizer = Callable[[str], list[str]]


def whitespace_tokens(text: str) -> list[str]:
    return text.split()


@dataclass(frozen=True)
class Proposal:
    """A bid from one specialist module for a slot in the broadcast."""

    source: str
    content: str
    salience: float = 0.5


@dataclass(frozen=True)
class Entry:
    """A proposal that won a slot, as it actually appeared in the broadcast."""

    source: str
    content: str
    salience: float
    truncated: bool


@dataclass(frozen=True)
class Broadcast:
    entries: list[Entry] = field(default_factory=list)
    rejected: list[Proposal] = field(default_factory=list)
    token_count: int = 0

    @property
    def text(self) -> str:
        return "\n".join(f"[{e.source}] {e.content}" for e in self.entries)


class Workspace:
    def __init__(
        self,
        capacity_tokens: Optional[int],
        tokenizer: Tokenizer = whitespace_tokens,
    ) -> None:
        if capacity_tokens is not None and capacity_tokens < 0:
            raise ValueError("capacity_tokens must be non-negative or None")
        self.capacity_tokens = capacity_tokens
        self._tokenizer = tokenizer
        self._pending: list[Proposal] = []

    def propose(self, proposal: Proposal) -> None:
        self._pending.append(proposal)

    def broadcast(self) -> Broadcast:
        """Run one competition and clear the pending queue."""
        pending, self._pending = self._pending, []

        ordered = sorted(pending, key=lambda p: (-p.salience, p.source))

        entries: list[Entry] = []
        rejected: list[Proposal] = []
        used = 0

        for proposal in ordered:
            tokens = self._tokenizer(proposal.content)
            remaining = self._remaining(used)

            if remaining == 0:
                rejected.append(proposal)
                continue

            truncated = remaining is not None and len(tokens) > remaining
            kept = tokens[:remaining] if truncated else tokens

            entries.append(
                Entry(
                    source=proposal.source,
                    content=" ".join(kept),
                    salience=proposal.salience,
                    truncated=truncated,
                )
            )
            used += len(kept)

        return Broadcast(entries=entries, rejected=rejected, token_count=used)

    def _remaining(self, used: int) -> Optional[int]:
        if self.capacity_tokens is None:
            return None
        return max(0, self.capacity_tokens - used)
