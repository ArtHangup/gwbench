"""Thread safety for the adapter.

Properly powering the headline test needs thousands of calls, which is hours
sequentially. Running them concurrently means several threads share one model
instance, and three pieces of its state are then racy: the usage counters, the
call cap, and the cache write. A lost update on the cap is the dangerous one,
since the cap exists to stop runaway spend.
"""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from gwbench.anthropic_model import AnthropicModel, CallCapExceeded


def response():
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="42")],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=10, output_tokens=5,
            cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


class SlowClient:
    """Yields the GIL mid-call so races actually surface."""

    def __init__(self):
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        import time
        time.sleep(0.001)
        self.calls += 1
        return response()


class TestUsageAccounting:
    def test_counts_every_concurrent_call(self):
        model = AnthropicModel(client=SlowClient())

        with ThreadPoolExecutor(max_workers=16) as pool:
            list(pool.map(model.complete, [f"prompt {i}" for i in range(200)]))

        assert model.usage.calls == 200
        assert model.usage.input_tokens == 2000
        assert model.usage.output_tokens == 1000


class TestCallCapUnderConcurrency:
    def test_cap_is_never_exceeded(self):
        """A lost update here means spending past the ceiling."""
        client = SlowClient()
        model = AnthropicModel(client=client, max_calls=50)

        def attempt(i):
            try:
                model.complete(f"prompt {i}")
                return True
            except CallCapExceeded:
                return False

        with ThreadPoolExecutor(max_workers=16) as pool:
            ok = sum(pool.map(attempt, range(200)))

        assert ok == 50
        assert client.calls == 50


class TestCacheUnderConcurrency:
    def test_concurrent_writes_do_not_corrupt_the_cache(self, tmp_path):
        model = AnthropicModel(client=SlowClient(), cache_dir=tmp_path)

        with ThreadPoolExecutor(max_workers=16) as pool:
            list(pool.map(model.complete, [f"prompt {i}" for i in range(100)]))

        fresh = AnthropicModel(client=SlowClient(), cache_dir=tmp_path)
        for i in range(100):
            assert fresh.complete(f"prompt {i}") == "42"
        assert fresh.usage.calls == 0
