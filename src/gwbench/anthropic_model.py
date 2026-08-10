"""Anthropic API adapter.

Satisfies the same one-method `Model` protocol as the fakes, so an architecture
cannot tell a real model from a stub. Everything the sweep needs beyond that is
here: a disk cache so re-running a sweep during development costs nothing, a
hard call cap, and cumulative token accounting.

Thinking is on by default on Claude Opus 5, and `max_tokens` caps thinking plus
response text together. Hence the generous default. Disabling thinking on this
model has documented failure modes, so the cheap path is low effort with
thinking left on, not thinking turned off.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DEFAULT_MODEL = "claude-opus-5"


class ModelRefusal(RuntimeError):
    """The model declined the request. Not a wrong answer, an absent one."""


class TruncatedResponse(RuntimeError):
    """Output hit max_tokens.

    Raised rather than returned because a truncated answer scores 0.0 and would
    be indistinguishable from a genuine capacity effect on the curve.
    """


class CallCapExceeded(RuntimeError):
    """The configured spend ceiling was reached."""


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def add(self, usage: Any) -> None:
        self.calls += 1
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_read_input_tokens += (
            getattr(usage, "cache_read_input_tokens", 0) or 0
        )
        self.cache_creation_input_tokens += (
            getattr(usage, "cache_creation_input_tokens", 0) or 0
        )


class AnthropicModel:
    def __init__(
        self,
        client: Any = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        effort: Optional[str] = "low",
        system: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        max_calls: Optional[int] = None,
    ) -> None:
        self.client = client if client is not None else self._default_client()
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort
        self.system = system
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.max_calls = max_calls
        self.usage = Usage()
        # Thousands of trials run concurrently against one instance, so the
        # usage counters and the call cap are shared mutable state. Without a
        # lock the cap loses updates and overspends by however many threads
        # slip through the check together.
        self._lock = threading.Lock()
        self._reserved = 0

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_client() -> Any:
        import anthropic

        # Concurrency makes 429s likely; the SDK backs off on its own, so give
        # it more headroom than the default of two before surfacing an error.
        return anthropic.Anthropic(max_retries=8)

    def complete(self, prompt: str) -> str:
        cached = self._read_cache(prompt)
        if cached is not None:
            return cached

        # Reserve a slot before the call, not after: checking a counter that is
        # only incremented on completion lets every waiting thread pass at once.
        with self._lock:
            if self.max_calls is not None and self._reserved >= self.max_calls:
                raise CallCapExceeded(
                    f"call cap of {self.max_calls} reached; refusing to spend more"
                )
            self._reserved += 1

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        # effort is rejected by models that predate it (Haiku 4.5, Sonnet 4.5),
        # so it has to be omittable for a cross-model comparison.
        if self.effort is not None:
            kwargs["output_config"] = {"effort": self.effort}
        if self.system is not None:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": self.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        response = self.client.messages.create(**kwargs)
        with self._lock:
            self.usage.add(response.usage)

        if response.stop_reason == "refusal":
            raise ModelRefusal(f"model declined: {getattr(response, 'stop_details', None)}")
        if response.stop_reason == "max_tokens":
            raise TruncatedResponse(
                f"output hit max_tokens ({self.max_tokens}); raise it or lower effort"
            )

        text = "\n".join(
            block.text for block in response.content if block.type == "text"
        )
        self._write_cache(prompt, text)
        return text

    def _cache_path(self, prompt: str) -> Optional[Path]:
        if not self.cache_dir:
            return None
        key = json.dumps(
            {
                "model": self.model,
                "effort": self.effort,
                "max_tokens": self.max_tokens,
                "system": self.system,
                "prompt": prompt,
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, prompt: str) -> Optional[str]:
        path = self._cache_path(prompt)
        if path is None or not path.exists():
            return None
        return json.loads(path.read_text())["response"]

    def _write_cache(self, prompt: str, text: str) -> None:
        path = self._cache_path(prompt)
        if path is None:
            return
        path.write_text(json.dumps({"prompt": prompt, "response": text}))
