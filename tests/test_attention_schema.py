"""Rung 4: the attention schema (indicator AST-1).

AST-1 asks for "a predictive model representing and enabling control over the
current state of attention." Both halves matter: a log of what was attended is
not a schema, because it predicts nothing and controls nothing.

The design follows Piefke, Doerig, Kietzmann & Thorat (CogSci 2024), whose
result is conditional: the benefit of an attention schema scales with the
agent's uncertainty about its own attentional state. So the schema is a model
that can be wrong, and the agent has a tunable `attention_noise` that makes the
true attentional state harder to track. Testing the schema at zero noise would
show nothing and invite the wrong conclusion.
"""

import pytest

from gwbench.attention import AttentionSchema
from gwbench.architectures import AttentionSchemaAgent, WorkspaceAgent
from gwbench.models import RecordingModel
from gwbench.tasks import IntegrationTask


@pytest.fixture
def task():
    return IntegrationTask.generate(seed=11, n_required=3, n_distractors=5)


class TestSchemaIsPredictive:
    def test_predicts_before_seeing_the_broadcast(self):
        schema = AttentionSchema()
        schema.expect({"a": 0.9, "b": 0.1})

        assert schema.predicted == {"a"}

    def test_scores_itself_against_what_was_actually_attended(self):
        schema = AttentionSchema()
        schema.expect({"a": 0.9, "b": 0.1})

        schema.observe(attended={"a"})

        assert schema.accuracy == 1.0

    def test_a_wrong_prediction_lowers_accuracy(self):
        schema = AttentionSchema()
        schema.expect({"a": 0.9, "b": 0.1})

        schema.observe(attended={"b"})

        assert schema.accuracy == 0.0

    def test_accuracy_averages_over_cycles(self):
        schema = AttentionSchema()
        schema.expect({"a": 0.9, "b": 0.1})
        schema.observe(attended={"a"})
        schema.expect({"a": 0.9, "b": 0.1})
        schema.observe(attended={"b"})

        assert schema.accuracy == pytest.approx(0.5)

    def test_capacity_bounds_how_many_it_expects_to_win(self):
        schema = AttentionSchema(expected_winners=2)
        schema.expect({"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.1})

        assert schema.predicted == {"a", "b"}


class TestSchemaEnablesControl:
    def test_boosts_a_module_it_expected_but_did_not_get(self):
        schema = AttentionSchema()
        schema.expect({"a": 0.9, "b": 0.1})
        schema.observe(attended={"b"})

        assert schema.bias("a") > 0

    def test_does_not_boost_a_module_that_already_won(self):
        schema = AttentionSchema()
        schema.expect({"a": 0.9, "b": 0.1})
        schema.observe(attended={"a"})

        assert schema.bias("a") == 0

    def test_unknown_modules_get_no_bias(self):
        schema = AttentionSchema()

        assert schema.bias("never-seen") == 0


class TestSchemaIsLegibleToTheController:
    def test_summary_names_what_is_being_attended(self):
        schema = AttentionSchema()
        schema.expect({"vision": 0.9, "audio": 0.1})
        schema.observe(attended={"vision"})

        assert "vision" in schema.summary()

    def test_summary_flags_what_was_missed(self):
        schema = AttentionSchema()
        schema.expect({"vision": 0.9, "audio": 0.1})
        schema.observe(attended={"audio"})

        assert "vision" in schema.summary()


class TestAttentionSchemaAgent:
    def test_controller_receives_the_schema_summary(self, task):
        model = RecordingModel(reply="0")
        agent = AttentionSchemaAgent(model, capacity_tokens=8, n_cycles=2)

        agent.run(task)

        assert "attention" in model.calls[-1].lower()

    def test_reports_schema_accuracy_in_the_result(self, task):
        model = RecordingModel(reply="0")
        agent = AttentionSchemaAgent(model, capacity_tokens=8, n_cycles=2)

        result = agent.run(task)

        assert result.schema_accuracy is not None
        assert 0.0 <= result.schema_accuracy <= 1.0

    def test_is_still_bound_by_the_capacity_limit(self, task):
        """Adding a schema must not smuggle extra content past the bottleneck."""
        model = RecordingModel(reply="0")
        agent = AttentionSchemaAgent(model, capacity_tokens=5, n_cycles=2)

        result = agent.run(task)

        assert all(t <= 5 for t in result.broadcast_tokens)

    def test_records_the_architecture_name(self, task):
        model = RecordingModel(reply="0")

        result = AttentionSchemaAgent(model, capacity_tokens=8).run(task)

        assert result.architecture == "attention_schema"


class TestUncertaintyIsTunable:
    """Without this, the Piefke condition cannot be tested at all."""

    def test_zero_noise_makes_attention_perfectly_predictable(self, task):
        model = RecordingModel(reply="0")
        agent = AttentionSchemaAgent(
            model, capacity_tokens=8, n_cycles=3, attention_noise=0.0, seed=1
        )

        result = agent.run(task)

        assert result.schema_accuracy == 1.0

    def test_noise_degrades_predictability(self, task):
        model = RecordingModel(reply="0")
        quiet = AttentionSchemaAgent(
            model, capacity_tokens=8, n_cycles=6, attention_noise=0.0, seed=2
        ).run(task)
        noisy = AttentionSchemaAgent(
            RecordingModel(reply="0"),
            capacity_tokens=8,
            n_cycles=6,
            attention_noise=2.0,
            seed=2,
        ).run(task)

        assert noisy.schema_accuracy < quiet.schema_accuracy

    def test_noise_is_reproducible_for_a_seed(self, task):
        def run(seed):
            return AttentionSchemaAgent(
                RecordingModel(reply="0"),
                capacity_tokens=8,
                n_cycles=4,
                attention_noise=1.5,
                seed=seed,
            ).run(task)

        assert run(7).schema_accuracy == run(7).schema_accuracy

    def test_the_plain_workspace_agent_also_accepts_noise(self, task):
        """Rung 3 and rung 4 must differ only by the schema, not by noise."""
        model = RecordingModel(reply="0")
        agent = WorkspaceAgent(
            model, capacity_tokens=8, n_cycles=2, attention_noise=1.0, seed=3
        )

        result = agent.run(task)

        assert result.schema_accuracy is None
