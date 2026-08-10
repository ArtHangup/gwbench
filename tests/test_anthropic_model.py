"""The real model adapter.

Tests run against a fake client, so the suite stays offline and deterministic.
What is being tested is the adapter's own logic: text extraction, refusal and
truncation handling, usage accounting, the disk cache, and the spend cap.

The spend cap matters more than it looks. A bandwidth sweep is a nested loop
over capacities and trials; an off-by-one in the loop is an expensive mistake
to discover from a billing page.
"""

from types import SimpleNamespace

import pytest

from gwbench.anthropic_model import (
    AnthropicModel,
    CallCapExceeded,
    ModelRefusal,
    TruncatedResponse,
)


def block(kind: str, **fields):
    return SimpleNamespace(type=kind, **fields)


def response(
    blocks,
    stop_reason: str = "end_turn",
    input_tokens: int = 10,
    output_tokens: int = 5,
    cache_read: int = 0,
):
    return SimpleNamespace(
        content=blocks,
        stop_reason=stop_reason,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=0,
        ),
    )


class FakeClient:
    """Stands in for anthropic.Anthropic, recording the kwargs it was called with."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class TestTextExtraction:
    def test_returns_text_from_a_text_block(self):
        client = FakeClient([response([block("text", text="42")])])

        result = AnthropicModel(client=client).complete("what is it")

        assert result == "42"

    def test_ignores_thinking_blocks(self):
        """Thinking is on by default on this model; it is not the answer."""
        client = FakeClient(
            [
                response(
                    [
                        block("thinking", thinking="let me work through this"),
                        block("text", text="42"),
                    ]
                )
            ]
        )

        result = AnthropicModel(client=client).complete("what is it")

        assert result == "42"

    def test_joins_multiple_text_blocks(self):
        client = FakeClient(
            [response([block("text", text="first"), block("text", text="second")])]
        )

        result = AnthropicModel(client=client).complete("go")

        assert result == "first\nsecond"

    def test_sends_the_prompt_as_a_user_message(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client).complete("the prompt")

        assert client.calls[0]["messages"] == [
            {"role": "user", "content": "the prompt"}
        ]


class TestModelConfiguration:
    def test_defaults_to_opus_5(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client).complete("go")

        assert client.calls[0]["model"] == "claude-opus-5"

    def test_model_is_overridable(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client, model="claude-sonnet-5").complete("go")

        assert client.calls[0]["model"] == "claude-sonnet-5"

    def test_sends_effort_so_it_is_held_constant_across_the_sweep(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client, effort="low").complete("go")

        assert client.calls[0]["output_config"] == {"effort": "low"}

    def test_caches_the_system_prompt_when_one_is_given(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client, system="stable preamble").complete("go")

        assert client.calls[0]["system"] == [
            {
                "type": "text",
                "text": "stable preamble",
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def test_omits_system_when_none_is_given(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client).complete("go")

        assert "system" not in client.calls[0]


class TestFailureModes:
    def test_refusal_raises_rather_than_returning_empty_text(self):
        client = FakeClient([response([], stop_reason="refusal")])

        with pytest.raises(ModelRefusal):
            AnthropicModel(client=client).complete("go")

    def test_truncation_raises_rather_than_scoring_a_partial_answer(self):
        """A truncated answer scoring 0.0 would look like a capacity effect."""
        client = FakeClient([response([block("text", text="the sum is 1")],
                                      stop_reason="max_tokens")])

        with pytest.raises(TruncatedResponse):
            AnthropicModel(client=client).complete("go")


class TestUsageAccounting:
    def test_accumulates_tokens_across_calls(self):
        client = FakeClient(
            [
                response([block("text", text="a")], input_tokens=10, output_tokens=5),
                response([block("text", text="b")], input_tokens=20, output_tokens=7),
            ]
        )
        model = AnthropicModel(client=client)

        model.complete("one")
        model.complete("two")

        assert model.usage.input_tokens == 30
        assert model.usage.output_tokens == 12
        assert model.usage.calls == 2

    def test_tracks_cache_reads(self):
        client = FakeClient(
            [response([block("text", text="a")], cache_read=900)]
        )
        model = AnthropicModel(client=client)

        model.complete("one")

        assert model.usage.cache_read_input_tokens == 900


class TestCallCap:
    def test_raises_once_the_cap_is_reached(self):
        client = FakeClient([response([block("text", text="a")])] * 3)
        model = AnthropicModel(client=client, max_calls=2)

        model.complete("one")
        model.complete("two")

        with pytest.raises(CallCapExceeded):
            model.complete("three")

    def test_the_capped_call_is_never_sent(self):
        client = FakeClient([response([block("text", text="a")])] * 3)
        model = AnthropicModel(client=client, max_calls=1)
        model.complete("one")

        with pytest.raises(CallCapExceeded):
            model.complete("two")

        assert len(client.calls) == 1


class TestResponseCache:
    def test_identical_prompts_hit_the_cache_instead_of_the_api(self, tmp_path):
        client = FakeClient([response([block("text", text="42")])])
        model = AnthropicModel(client=client, cache_dir=tmp_path)

        first = model.complete("same prompt")
        second = model.complete("same prompt")

        assert first == second == "42"
        assert len(client.calls) == 1

    def test_different_prompts_do_not_collide(self, tmp_path):
        client = FakeClient(
            [response([block("text", text="a")]), response([block("text", text="b")])]
        )
        model = AnthropicModel(client=client, cache_dir=tmp_path)

        assert model.complete("one") == "a"
        assert model.complete("two") == "b"

    def test_cache_is_keyed_on_model_and_effort_too(self, tmp_path):
        """Changing the model must not silently reuse the old model's answers."""
        client_a = FakeClient([response([block("text", text="from-opus")])])
        client_b = FakeClient([response([block("text", text="from-sonnet")])])

        a = AnthropicModel(client=client_a, cache_dir=tmp_path, model="claude-opus-5")
        b = AnthropicModel(client=client_b, cache_dir=tmp_path, model="claude-sonnet-5")

        assert a.complete("same") == "from-opus"
        assert b.complete("same") == "from-sonnet"

    def test_cached_calls_do_not_count_against_the_cap(self, tmp_path):
        client = FakeClient([response([block("text", text="a")])])
        model = AnthropicModel(client=client, cache_dir=tmp_path, max_calls=1)

        model.complete("same")
        model.complete("same")

        assert len(client.calls) == 1

    def test_cache_survives_a_new_model_instance(self, tmp_path):
        client = FakeClient([response([block("text", text="42")])])
        AnthropicModel(client=client, cache_dir=tmp_path).complete("same")

        fresh_client = FakeClient([])
        fresh = AnthropicModel(client=fresh_client, cache_dir=tmp_path)

        assert fresh.complete("same") == "42"
        assert fresh_client.calls == []


class TestEffortIsOptional:
    """`effort` errors on models that predate it (Haiku 4.5, Sonnet 4.5).

    The adapter has to be able to omit it entirely so the same harness can drive
    a cross-model comparison.
    """

    def test_none_effort_omits_output_config(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client, effort=None).complete("go")

        assert "output_config" not in client.calls[0]

    def test_an_effort_value_is_still_sent(self):
        client = FakeClient([response([block("text", text="ok")])])

        AnthropicModel(client=client, effort="low").complete("go")

        assert client.calls[0]["output_config"] == {"effort": "low"}

    def test_effort_none_is_a_distinct_cache_key(self):
        """Otherwise a no-effort run would reuse a low-effort run's answers."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            a = FakeClient([response([block("text", text="with-effort")])])
            b = FakeClient([response([block("text", text="no-effort")])])

            assert AnthropicModel(client=a, cache_dir=tmp, effort="low").complete("q") \
                == "with-effort"
            assert AnthropicModel(client=b, cache_dir=tmp, effort=None).complete("q") \
                == "no-effort"
