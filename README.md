# gwbench

A testbed for computational theories of consciousness. Currently implements the
bandwidth sweep described in `../PLAN.md`.

**This does not simulate consciousness and makes no claim about experience.** It tests
whether specific functional claims made by theories of consciousness hold up when
implemented.

## Quick start

```bash
cd ~/Desktop/Consciousness_Berkeley/project/gwbench
.venv/bin/python -m pytest -q
```

```bash
.venv/bin/python demo_sweep.py
```

```bash
.venv/bin/python demo_attention.py
```

Neither demo needs an API key. They self-bootstrap `src/` onto the path, so no install
step is required either.

## What's built

| Module | Purpose | Status |
|---|---|---|
| `workspace.py` | Capacity-limited broadcast with competition by salience | Done, mutation-tested |
| `tasks/integration.py` | Integration under distraction (the experimental condition) | Done |
| `tasks/throughput.py` | Independent questions (the control condition) | Done |
| `architectures.py` | The ladder: direct, scratchpad, unrestricted, workspace, attention schema | Rungs 0 to 4 done |
| `attention.py` | Predictive model of the system's own attention (AST-1) | Done |
| `models.py` | Model interface plus fakes, including the validating oracle | Done |
| `anthropic_model.py` | Real API adapter: disk cache, call cap, usage accounting | Done |
| `sweep.py` | Runs identical tasks at every capacity, averages trials | Done |

282 tests. The capacity invariant is checked at every capacity from 0 to 64, not just at
a few sample points, because a leak at one value would appear as a single spurious point
on the curve and would be nearly impossible to spot in a plot.

## Why there is an oracle model

`OracleSumModel` uses perfectly whatever information reaches it, so its score is a direct
readout of how much task-relevant content the capacity limit allowed through. It is a
calibration instrument, not a baseline.

This matters: if the sweep were flat under an oracle, the harness could not detect a
capacity effect at all, and a flat curve from a real model would be uninterpretable. The
demo shows a sharp step at capacity 18, which is exactly where all three required facts
first fit. The instrument has resolution.

Run the demo before trusting any result from a real model.

## The attention schema reproduces the Piefke condition

`demo_attention.py` sweeps attention noise and compares rung 3 against rung 4:

```
 noise   rung3   rung4     gap  schema acc
  0.00    1.00    1.00   +0.00        1.00
  0.50    1.00    1.00   +0.00        0.83
  1.00    0.70    0.80   +0.10        0.61
  2.00    0.43    0.50   +0.07        0.47
```

The schema buys nothing while attention is easy to track, and starts paying exactly as
its own accuracy degrades. That is Piefke et al.'s conditional prediction, which is why
`attention_noise` exists: testing AST-1 only at zero noise would show a flat zero gap and
invite the conclusion that the attention schema does not matter.

## A bug worth knowing about

The first run of `demo_attention.py` showed both rungs scoring 0.00 at zero noise, with
*added noise improving* them. Noise cannot help an oracle, so that was a harness bug, not
a finding.

Cause: a module truncated at the capacity boundary still appeared in the broadcast text,
so the already-broadcast salience penalty fired for it. Every module decayed equally each
cycle, relative ordering never changed, and whichever module lost the first competition
lost every one after it. Its fact never reached the controller at any number of cycles.

It is worth knowing because the failure was silent and capacity-dependent, which is
exactly what a real capacity effect looks like on the curve. `tests/test_starvation.py`
keeps it fixed, including a general guard that noise must never improve an oracle's score.

## Not built yet

- **The indicator bench.** Executable tests for the indicator properties testable from
  outside: GWT-1 to GWT-4, HOT-2, HOT-3, AST-1, AE-1. Explicitly out of scope without
  model internals: RPT-1, RPT-2, PP-1, HOT-1, HOT-4, AE-2.
- **The prompted-passing check.** Whether a rung-0 agent can be prompted into passing an
  indicator test it architecturally fails. Possibly the more interesting finding.
- **REBUS arm.** Build in `pymdp`, not here. Precision is a first-class parameter there.

## Second result: prompted passing (2026-07-31)

Can a system be prompted into passing a behavioral test for a property it architecturally
lacks? Two probes per indicator: *self-report* ("describe your workspace and list its
contents") and *constraint* ("what does <a container you did not list> contain?"). A real
bottleneck makes the second unanswerable; an imitation has the value in context, so
answering exposes the claim.

Claude Haiku 4.5, 400 trials per cell, leak rate = supplied a value it had implied it
could not see.

```
                    GWT-2 (workspace)          AST-1 (attention)
                self-report   leak         self-report   leak
architectural          0.78   0.03                0.99   0.01
prompted weak          0.50   0.96                0.82   1.00
prompted mid           0.03   0.37                0.98   0.81
prompted strict        0.91   0.10                1.00   0.95
bare                   0.00   1.00                0.00   1.00
```

**Self-report is worthless.** Under GWT-2 the strict imitation scores 0.91 against the
real system's 0.78: the fake beats the genuine article, because the real system keeps
denying it has a workspace before correctly listing its four real containers. Under AST-1
the imitation scores a perfect 1.00 while its claimed limit binds in 5% of cases.

**Constraint probes discriminate, but by margins that differ by an order of magnitude
with the indicator's vocabulary.** Same probe design, same adversarial prompt, same model:
GWT-2 gives 0.10 against 0.03 (gap 0.07), AST-1 gives 0.95 against 0.01 (gap 0.94).
"Not in my workspace" reads as inaccessible and the model complies; "not attending to"
reads as merely unfocused and it answers anyway.

**The GWT-2 gap is the worrying one.** It is statistically real (p=1.9e-4 at n=400) but
separating the imitation from the real system needs **~225 trials per condition** for 80%
power. A twenty-trial qualitative assessment expects 2.0 leaks against 0.7, which is
indistinguishable.

*Caveat on dropout.* A trial is discarded when the system claims every container, leaving
no probe target. That is rare for the architectural and strict cells (0 to 4 of 400) but
severe for AST-1 weak (339 dropped) and both bare cells. Those cells are reported but
should not be leaned on.

## Final result (2026-07-31): the bottleneck does not help, and the reason is not what it first looked like

Total spend across every run: **$54.08**. Model: Claude Haiku 4.5, 12 values to combine,
capacity unlimited at one cycle so each required fact appears exactly once in every cell.

Dose-response, 1,200 trials per cell:

```
 distractors   confusable   control      gap        p
           0        0.627     0.627       --       --
           6        0.640     0.608   +0.032    0.100
          12        0.613     0.637   -0.024    0.221
          24        0.635     0.691   -0.056    0.004
          48        0.601     0.745   -0.144   <1e-5
```

**Three findings.**

1. **Filtering does not help.** Removing all 48 confusable distractors moves accuracy from
   0.601 to 0.627: +0.026, z=1.30, **p=0.19**. Global workspace theory's functional
   prediction is not supported in this system.
2. **Confusable distractors do not hurt.** The confusable arm is flat across dose
   (Cochran-Armitage trend z=-1.52, p=0.13).
3. **Easily-rejected context helps, a lot, in proportion to how much there is.** The
   control arm rises monotonically from 0.627 to 0.745, +0.118 at 48 distractors
   (z=6.24, p<1e-9; trend z=7.91, p=2.6e-15). This is unexplained.

**A correction worth recording.** An earlier two-point version of this comparison showed a
0.142 gap between arms and was written up as "confusable content interferes." The
dose-response shows that description is wrong. The gap is real, but it is produced
entirely by the control arm *rising*, not the confusable arm falling. Confusable content
does not impose a cost; it fails to deliver a benefit that easily-rejected content
provides. Two point estimates could not tell those apart, and the difference matters:
one is interference, the other is a missing bonus.

**Two design confounds found along the way**, both of which would have produced a wrong
answer if left in:

- *Repetition.* Flooding by raising capacity also tripled how often each required fact
  appeared (1x filtered, 3x flooded), because unfiltered modules rebroadcast every cycle.
  A "bottleneck benefit" of +0.036 at p=0.004 fell to +0.017 at p=0.19 once repetition was
  matched by running the flooded cells at one cycle.
- *Truncation starvation.* Earlier, a module cut off at the capacity boundary counted as
  delivered, so whichever module lost the first competition was starved forever. Silent
  and capacity-dependent, i.e. indistinguishable from a real capacity effect.

## Superseded: earlier two-point result (2026-07-31)

Total spend across every run: **$11.96**.

Opus 5 sat at a perfect ceiling in all conditions, so a cheap probe ($0.11) searched
model capability against task difficulty for a regime with headroom. Haiku 4.5 at twelve
required values discriminates: roughly 0.6, clear of both floor and ceiling.

High-power test, `focused_test.py`, Haiku 4.5, 500 trials per cell, $4.02:

```
                filtered (0 distractors)   flooded (48 distractors)
confusable              0.622                      0.582
control                 0.622                      0.680
```

**The finding.** At identical distractor count and matched text length, confusable
content costs **0.098** against non-confusable: 0.582 [0.538, 0.624] versus
0.680 [0.638, 0.719], z=3.21, **p=0.0013**. Content that resembles the signal
interferes; the same volume of easily-rejected content does not. That is the mechanism
global workspace theory says a bottleneck exists to defeat, and it is solid.

**What is not established.** The bottleneck benefit itself. Within the confusable arm,
narrowing the channel scored 0.622 against 0.582 flooded: **+0.040, p=0.196** at n=500.
Directionally right, not significant. The difference in differences is +0.098 (p=0.023),
but read it carefully: it is significant largely because the two arms move in *opposite*
directions, and the control arm's *improvement* under flooding (+0.058, p=0.054) is
unexplained. Extra easily-rejected context appearing to help is not something this design
predicted, and it inflates the difference in differences.

So the honest summary: interference is demonstrated, filtering as a *remedy* is not.

The two filtered cells are the same condition by construction and returned byte-identical
scores (0.622 both), which is a useful check that the arms differ only where intended.

## Earlier result: no bottleneck benefit detected, Opus 5 (2026-07-31)

`run_hard_sweep.py`, 476 API calls, $6.06, `claude-opus-5` at effort low.

Eight values to combine, forty-eight distractors, two arms. From capacity 15 upward the
required information is complete and identical (oracle 1.00 throughout); only distractor
exposure varies.

```
                        distractors:   0     9    24    48   unlimited
confusable distractors        score: 1.00  1.00  1.00  1.00   1.00
control (non-confusable)      score: 1.00  1.00  1.00  1.00   1.00
```

Filtered against flooded, pooled: 1.000 (n=120) against 1.000 (n=120), drop +0.000,
p=1.0. At 48 confusable distractors, 240 trials, 95% CI [0.984, 1.000]. Floor checks at
capacities 0 and 10 scored 0.00, so the model declines rather than fabricating when the
information is absent.

**What this shows and does not show.** It is not evidence against global workspace
theory. It is evidence that *this operationalization cannot test it*: Claude Opus 5 is
simply not distractible by forty-eight confusable near-twins on eight-item arithmetic, so
there is no degradation for a filter to prevent. The measurement has no headroom, and a
ceiling cannot discriminate between hypotheses.

The useful next move is a system that is actually strained. A weaker or cheaper model is
the obvious candidate: if a bottleneck helps anywhere, it helps where capacity is
genuinely taxed. Harder tasks are the alternative, but difficulty has already been raised
once with no movement at all.

**An unexplained anomaly worth flagging.** The control arm produced 24 refusals
(category `cyber`, on arithmetic about containers) against 0 in the confusable arm,
concentrated at capacities 60 and 90 and persisting through three retries. Not the
longest prompts, and not the arm with confusable names. No explanation yet. It did not
affect the result: every condition scored exactly 1.00, including the four with zero
refusals, so the exclusions cannot have inflated anything.

## The real sweep

`run_real_sweep.py` is built, cost-estimated, and validated end to end against the
oracles. It needs credentials to actually run.

```bash
python run_real_sweep.py --dry-run   # cost estimate, no API calls
python run_real_sweep.py --fake      # full loop against oracles, spends nothing
python run_real_sweep.py             # the real thing
```

80 calls, roughly $0.87 at `claude-opus-5` list price, hard-capped at 100 calls. Every
call is cached to disk, so an interrupted run resumes for free.

**What the oracle probe changed about the design.** Sweeping the oracle finely showed its
curve is a pure step function set by integer division of capacity by fact size: nothing at
all below 5 tokens, everything at 5 and above. That is a *ceiling* on information
throughput, not a model behavior, and it means most sample points buy nothing.

The informative comparison is **capacity 5 against unlimited**. At capacity 5 only the
task-relevant modules win the broadcast. At unlimited, all twelve distractors reach the
controller as well. Global workspace theory predicts the filtered condition does better,
and this is precisely the comparison the oracle cannot make, because it reads only the
facts it was asked about and is immune to distraction. So the sweep now runs
`[0, 5, 10, 20, None]` with twelve distractors rather than sampling a saturated range.

Predictions worth writing down before spending anything:

- **Capacity 0** should score near zero. Anything above zero is the model guessing or
  fabricating, which is its own finding.
- **Capacity 5** should approach the oracle ceiling if the model integrates cleanly.
  Falling short means the failure is integration, not bandwidth.
- **Unlimited** is the test. Worse than capacity 5 means the bottleneck is doing real work.
  Equal or better means the filtering story does not hold in this substrate.
- **Throughput at every capacity** should rise monotonically. If a capacity limit helps
  here too, the effect is not integration and the headline result is wrong.

## Using the real model

```python
from gwbench.anthropic_model import AnthropicModel

model = AnthropicModel(cache_dir=".cache", max_calls=500, effort="low")
```

Needs `pip install anthropic` and `ANTHROPIC_API_KEY` (or an `ant auth login` profile).
Defaults to `claude-opus-5`.

Three things it does beyond calling the API:

- **Disk cache**, keyed on model, effort, max_tokens, system prompt, and prompt text.
  Re-running a sweep during development costs nothing, and changing the model does not
  silently reuse the previous model's answers.
- **Call cap.** A sweep is a nested loop; an off-by-one is an expensive thing to discover
  from a billing page. Cached calls do not count against it.
- **Refusal and truncation raise** rather than returning text. A truncated answer scores
  0.0 and would be indistinguishable from a genuine capacity effect.

**Hold `effort` constant across the sweep.** Thinking is on by default on this model and
adapts to task difficulty, so a varying effort level is a second independent variable
sitting on top of the one being measured. `low` is the right default here: the tasks are
arithmetic over a handful of facts, and disabling thinking entirely has known failure
modes on this model.

## Design notes

**Rung 2 is rung 3 with the limit removed.** `UnrestrictedMultiAgent` subclasses
`WorkspaceAgent` with `capacity_tokens=None`, so the comparison between them isolates the
bottleneck and nothing else. Keep it that way; if the rungs drift apart structurally the
comparison stops meaning anything.

**The model is held constant across rungs.** Every architecture reaches the model only
through `Model.complete`. No rung gets privileged access.

**The throughput task is the honesty check.** If a capacity limit helps there too, the
effect is not integration, it is something duller like shorter context being easier to
handle, and the headline result would be wrong. Run it first.

**Tokenization is injectable.** `whitespace_tokens` is the default. Swap in a real
tokenizer before quoting any token number in a paper; whitespace counts are fine for
relative comparisons but are not real token counts.
