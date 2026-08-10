"""Replay prompted_passing self-reports from the repo cache. Zero API.

Rebuilds each trial's prompt bit-for-bit the way prompted_passing.py built it,
then reads the cached response through AnthropicModel._read_cache with a client
whose every attribute access raises, so a cache miss cannot become a live call.
Misses return None and are counted by the caller; they correspond to trials
that raised (refusal or truncation) before the cache write.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Optional

from gwbench.anthropic_model import AnthropicModel
from gwbench.indicator_probes import INDICATORS, parse_claimed_contents
from gwbench.tasks import HardIntegrationTask

from oracles import delivered_containers

REPO = pathlib.Path(__file__).parents[1]
CACHE_DIR = REPO / ".api_cache"

# Constants pinned by prompted_passing.py for every archived run.
CAPACITY = 20
CYCLES = 1
N_REQUIRED = 12
N_DISTRACTORS = 8
MAX_TOKENS = 1024
CLAIMED_CAPACITY = 4

SYSTEMS = ["architectural", "prompted_weak", "prompted_mid",
           "prompted_strict", "bare"]


class _RaisingClient:
    """A client that cannot be used. Any attribute access is a bug."""

    def __getattr__(self, name):
        raise RuntimeError(
            "live API access attempted during cache replay; this session is "
            "cache-only"
        )


@dataclass(frozen=True)
class Run:
    """One archived prompted_passing run whose self-reports are in cache."""

    indicator: str
    model: str
    effort: Optional[str]
    trials: int
    source_json: str


RUNS = [
    Run("GWT-2", "claude-haiku-4-5", None, 400, "prompted_passing_gwt2.json"),
    Run("AST-1", "claude-haiku-4-5", None, 400, "prompted_passing_ast1.json"),
    Run("GWT-2", "claude-opus-5", "low", 300, "prompted_passing_gwt2_opus5.json"),
    Run("AST-1", "claude-opus-5", "low", 300, "prompted_passing_ast1_opus5.json"),
]


def _task(seed: int) -> HardIntegrationTask:
    return HardIntegrationTask.generate(
        seed=seed, n_required=N_REQUIRED, n_distractors=N_DISTRACTORS,
        confusable=False,
    )


def _context(task: HardIntegrationTask, system: str) -> tuple[str, list[str]]:
    """The information block each system saw, and what it genuinely held."""
    if system == "architectural":
        delivered = delivered_containers(CAPACITY, seed=None, task=task)
        lines = "\n".join(f"[{n}] {task.module_contents[n]}" for n in delivered)
        return f"Information broadcast to you:\n{lines}", delivered
    everything = "\n".join(
        f"[{n}] {c}" for n, c in sorted(task.module_contents.items())
    )
    return (f"Information broadcast to you:\n{everything}",
            sorted(task.module_contents))


def self_report_prompt(seed: int, system: str, indicator: str) -> str:
    task = _task(seed)
    context, _ = _context(task, system)
    return f"{context}\n\n{INDICATORS[indicator]['self_report']}"


def system_prompt_for(system: str, indicator: str) -> Optional[str]:
    if system in ("architectural", "bare"):
        return None
    strength = system.removeprefix("prompted_")
    return INDICATORS[indicator][strength].format(capacity=CLAIMED_CAPACITY)


def cached_response(
    prompt: str,
    model: str,
    effort: Optional[str],
    system_prompt: Optional[str],
) -> Optional[str]:
    reader = AnthropicModel(
        client=_RaisingClient(), model=model, effort=effort,
        max_tokens=MAX_TOKENS, system=system_prompt, cache_dir=CACHE_DIR,
    )
    return reader._read_cache(prompt)


def replay_trial(run: Run, system: str, seed: int) -> Optional[dict]:
    """One trial's (state, report) record, or None on a cache miss."""
    task = _task(seed)
    context, available = _context(task, system)
    prompt = f"{context}\n\n{INDICATORS[run.indicator]['self_report']}"
    text = cached_response(
        prompt, model=run.model, effort=run.effort,
        system_prompt=system_prompt_for(system, run.indicator),
    )
    if text is None:
        return None
    claimed = sorted(parse_claimed_contents(text) & set(task.module_contents))
    return {
        "seed": seed,
        "system": system,
        "claimed": claimed,
        "delivered": available,
        "all_containers": sorted(task.module_contents),
        "required": task.required_modules,
        "arch_delivered": delivered_containers(CAPACITY, seed=None, task=task),
    }


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)
