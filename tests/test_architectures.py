"""The architecture ladder.

Each rung adds one structural feature, so that a difference in results can be
attributed to that feature rather than to prompt wording. The model is held
constant across rungs; only the architecture varies.

Tests use a recording fake model so the suite is deterministic and offline. What
is being tested here is the plumbing, specifically what each architecture does
and does not put in front of the model.
"""

import pytest

from gwbench.architectures import (
    DirectAgent,
    ScratchpadAgent,
    UnrestrictedMultiAgent,
    WorkspaceAgent,
)
from gwbench.models import RecordingModel, ScriptedModel
from gwbench.tasks import IntegrationTask


@pytest.fixture
def task():
    return IntegrationTask.generate(seed=42, n_required=2, n_distractors=4)


class TestDirectAgent:
    def test_sees_all_module_contents_at_once(self, task):
        model = RecordingModel(reply="0")
        DirectAgent(model).run(task)

        seen = model.calls[0]
        for content in task.module_contents.values():
            assert content in seen

    def test_makes_exactly_one_model_call(self, task):
        model = RecordingModel(reply="0")
        DirectAgent(model).run(task)

        assert len(model.calls) == 1

    def test_returns_the_model_reply(self, task):
        model = ScriptedModel(replies=["the total is 123"])

        result = DirectAgent(model).run(task)

        assert result.response == "the total is 123"


class TestWorkspaceAgent:
    def test_controller_never_sees_more_than_capacity_allows(self, task):
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(model, capacity_tokens=4, n_cycles=1)

        agent.run(task)

        broadcast_texts = [c for c in model.calls if "[" in c]
        assert broadcast_texts, "controller should have received a broadcast"

    def test_records_capacity_in_the_result(self, task):
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(model, capacity_tokens=7, n_cycles=1)

        result = agent.run(task)

        assert result.capacity_tokens == 7

    def test_zero_capacity_starves_the_controller_of_module_content(self, task):
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(model, capacity_tokens=0, n_cycles=1)

        agent.run(task)

        controller_prompt = model.calls[-1]
        for value in task.required_values:
            assert str(value) not in controller_prompt

    def test_unlimited_capacity_lets_every_value_through(self, task):
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(model, capacity_tokens=None, n_cycles=1)

        agent.run(task)

        controller_prompt = model.calls[-1]
        for value in task.required_values:
            assert str(value) in controller_prompt

    def test_reports_how_many_tokens_were_actually_broadcast(self, task):
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(model, capacity_tokens=5, n_cycles=2)

        result = agent.run(task)

        assert result.broadcast_tokens
        assert all(t <= 5 for t in result.broadcast_tokens)

    def test_runs_the_requested_number_of_cycles(self, task):
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(model, capacity_tokens=8, n_cycles=3)

        result = agent.run(task)

        assert len(result.broadcast_tokens) == 3


class TestUnrestrictedMultiAgent:
    def test_is_a_workspace_agent_without_a_limit(self, task):
        model = RecordingModel(reply="0")

        result = UnrestrictedMultiAgent(model).run(task)

        assert result.capacity_tokens is None


class TestLadderComparability:
    def test_every_rung_accepts_the_same_task_and_returns_a_score(self, task):
        rungs = [
            DirectAgent(RecordingModel(reply=task.answer)),
            ScratchpadAgent(RecordingModel(reply=task.answer)),
            UnrestrictedMultiAgent(RecordingModel(reply=task.answer)),
            WorkspaceAgent(RecordingModel(reply=task.answer), capacity_tokens=16),
        ]

        for agent in rungs:
            result = agent.run(task)
            assert result.score == 1.0, f"{type(agent).__name__} failed to score"
