"""The bandwidth limiter is the independent variable of the whole experiment.

If it does not actually truncate, every result downstream is meaningless. These
tests exist to make that failure mode impossible to miss.
"""

import pytest

from gwbench.workspace import Proposal, Workspace


def prop(source: str, content: str, salience: float = 0.5) -> Proposal:
    return Proposal(source=source, content=content, salience=salience)


class TestCapacityIsEnforced:
    def test_broadcast_never_exceeds_capacity(self):
        ws = Workspace(capacity_tokens=10)
        ws.propose(prop("vision", "word " * 100))

        broadcast = ws.broadcast()

        assert broadcast.token_count <= 10

    def test_content_longer_than_capacity_is_truncated_not_dropped(self):
        ws = Workspace(capacity_tokens=5)
        ws.propose(prop("vision", "alpha beta gamma delta epsilon zeta eta theta"))

        broadcast = ws.broadcast()

        assert broadcast.token_count == 5
        assert "alpha" in broadcast.text

    def test_zero_capacity_broadcasts_nothing(self):
        ws = Workspace(capacity_tokens=0)
        ws.propose(prop("vision", "something important"))

        broadcast = ws.broadcast()

        assert broadcast.token_count == 0
        assert broadcast.entries == []

    def test_unlimited_capacity_broadcasts_everything(self):
        ws = Workspace(capacity_tokens=None)
        ws.propose(prop("vision", "word " * 100))
        ws.propose(prop("audio", "sound " * 100))

        broadcast = ws.broadcast()

        assert len(broadcast.entries) == 2
        assert broadcast.token_count == 200


class TestCompetition:
    def test_higher_salience_wins_scarce_capacity(self):
        ws = Workspace(capacity_tokens=2)
        ws.propose(prop("loud", "AAA BBB", salience=0.9))
        ws.propose(prop("quiet", "CCC DDD", salience=0.1))

        broadcast = ws.broadcast()

        assert [e.source for e in broadcast.entries] == ["loud"]

    def test_losing_proposals_are_reported_for_auditing(self):
        ws = Workspace(capacity_tokens=2)
        ws.propose(prop("loud", "AAA BBB", salience=0.9))
        ws.propose(prop("quiet", "CCC DDD", salience=0.1))

        broadcast = ws.broadcast()

        assert [p.source for p in broadcast.rejected] == ["quiet"]

    def test_ties_are_broken_deterministically_by_source_name(self):
        ws = Workspace(capacity_tokens=2)
        ws.propose(prop("zebra", "ZZZ ZZZ", salience=0.5))
        ws.propose(prop("apple", "AAA AAA", salience=0.5))

        broadcast = ws.broadcast()

        assert [e.source for e in broadcast.entries] == ["apple"]


class TestCycleSemantics:
    def test_broadcast_clears_pending_proposals(self):
        ws = Workspace(capacity_tokens=None)
        ws.propose(prop("vision", "first"))
        ws.broadcast()

        second = ws.broadcast()

        assert second.entries == []

    def test_capacity_must_not_be_negative(self):
        with pytest.raises(ValueError):
            Workspace(capacity_tokens=-1)
