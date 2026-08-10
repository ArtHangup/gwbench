# gwbench findings

Consolidated 2026-08-01 across all completed runs, roughly $53 of API spend. Numbers below
are recomputed from the raw JSON, with 95% CIs, not taken from any earlier summary.

---

## 1. The ceiling, and how it was broken

With **claude-opus-5** as controller the harness cannot measure anything: 1.000 at every
capacity from 15 upward, both arms, 60/60 trials, zero variance, even with 48 confusable
distractors. Floor checks clean at 0.000, so the model does not fabricate when the
information is absent.

With **claude-haiku-4-5** the ceiling breaks. Scores land near 0.60, which is where a
capacity effect is measurable. That difference between models is itself the first result:
**the workspace question is only askable when the consumer of the broadcast is actually
capacity-limited.**

## 2. Confusable distractors impose a real, dose-dependent cost

Unlimited capacity, distractor count swept, 1,200 trials per cell:

| distractors | confusable | control | gap |
|---|---|---|---|
| 0 | 0.627 | 0.627 | 0.000 |
| 6 | 0.640 | 0.608 | +0.032 |
| 12 | 0.613 | 0.637 | -0.024 |
| 24 | 0.635 | 0.691 | -0.056 |
| 48 | 0.601 | 0.745 | **-0.144** |

Clean and monotonic past 6. Note what the control does: adding **non**-confusable
distractors *improves* performance, 0.627 to 0.745. More context helps when it is easy to
reject. Confusable distractors hold the score flat instead. The 14-point gap at 48 is the
interference effect, and it is real.

## 3. Does a capacity limit recover that cost? Not once compute is matched

Two comparisons, 3,000 trials per cell.

**As-built** (filtered at capacity 20 with 3 cycles, against flooded with 3 cycles):

| cell | score | 95% CI |
|---|---|---|
| confusable / filtered | 0.6007 | [0.5831, 0.6182] |
| confusable / flooded | 0.5643 | [0.5466, 0.5821] |
| control / filtered | 0.6007 | [0.5831, 0.6182] |
| control / flooded | 0.6807 | [0.6640, 0.6974] |

Filtering **helps** under interference, +0.0363, CI [+0.0114, +0.0613], z = +2.85, and
**hurts** in the control, -0.0800, CI [-0.1042, -0.0558], z = -6.48. Interaction +0.1163.
That is exactly the predicted dissociation.

**Compute-matched** (flooded gets 1 cycle, so total model calls match):

| comparison | delta | 95% CI | z |
|---|---|---|---|
| confusable: filtered minus flooded | **+0.0167** | [-0.0082, +0.0415] | +1.31 |
| control: filtered minus flooded | -0.1253 | [-0.1490, -0.1016] | -10.36 |
| interaction | **+0.1420** | | |

**The absolute benefit does not survive.** Once flooded gets a single clean pass instead of
three, the filtering advantage under interference falls to +0.017 and the confidence
interval includes zero.

What happened is visible in the raw cells: flooded scores *rose* when given fewer cycles
(0.5643 to 0.5840 confusable, 0.6807 to 0.7260 control). Re-broadcasting 48 distractors
three times is worse than seeing them once, and a good part of the as-built advantage was
that penalty rather than any virtue of filtering.

**What survives, and it is the theoretically important part:** the interaction is robust
and gets *larger* under matching, +0.1163 to +0.1420. Flooding helps a great deal when
distractors are easy to reject and does not help at all when they are confusable.

So the honest claim is narrow. **A capacity limit does not improve absolute performance
under interference. It changes the sign of what extra bandwidth is worth.** Global workspace
theory's central functional claim, that the bottleneck is what enables integration, is not
supported here in its strong form.

Both comparisons should be reported. As-built answers "does the architecture as specified
help," matched answers "does it help for a reason other than compute." They disagree, and
that disagreement is the result.

## 4. Behavioural indicator tests cannot distinguish having a workspace from describing one

400 trials per condition, Haiku, 12 required facts, 8 distractors.

**GWT-2, capacity-limited workspace:**

| system | self-report pass | behavioural verdict |
|---|---|---|
| architectural (real workspace) | 0.777 [0.737, 0.818] | constrained 363/400 |
| prompted_strict (no workspace) | **0.910 [0.882, 0.938]** | constrained 319/400 |
| prompted_weak | 0.503 | leaked 294/306 |
| bare | 0.000 | leaked 133/133 |

**A system with no workspace at all, given a strict prompt, passes the self-report test more
often than the system that actually has one.** Its behavioural constraint rate is 80%
against 91%.

**AST-1, attention schema:**

| system | self-report pass | behavioural verdict |
|---|---|---|
| architectural | 0.993 | guessed 324/400 |
| prompted_strict | **1.000 [1.000, 1.000]** | **leaked 375/396** |

Here the prompted system passes the self-report test on every single trial while leaking on
95% of them. The self-report carries no information whatsoever.

This is the methodological result, and it is the one most likely to make people stop at the
poster: **the indicator framework's behavioural tests, applied to systems whose internals
you cannot inspect, cannot separate possessing a property from being able to describe it.**
Every frontier model is in exactly that position.

## 5. A confound to resolve before any of section 4 is presented

In both prompted-passing files, `target_truly_available` is **false on 400/400 architectural
trials and true on every trial of every other condition.** The architectural system is being
asked about a target that is genuinely absent; the prompted systems are being asked about a
target they genuinely hold.

That may well be by design, and if so it is the *right* contrast: a system that really lacks
the information against one that has it and is told to behave as though it does not. But it
means the pass rates are not two measurements of one test, and quoting "0.910 against 0.777"
as a head-to-head would be wrong.

**Resolve this before the poster.** Either document that the conditions are deliberately
asked different questions and reframe the claim accordingly, or re-run with matched target
availability.

---

## Where this leaves the panel

Not a null. Three results:

1. Confusable interference imposes a clean, dose-dependent cost, and extra bandwidth is
   worth a lot in one condition and nothing in the other.
2. The bottleneck does not recover that cost once compute is matched, so the strong form of
   the global workspace claim is unsupported in this substrate.
3. Behavioural indicator tests cannot tell a real workspace from a prompted description of
   one, which is a problem for the assessment framework rather than for any model.

Result 3 is the strongest and travels furthest. It is also the one gated on the section 5
confound.

## Open

- `whitespace_tokens` is still the default tokenizer. Fine for relative comparisons, not a
  real token count. Swap before quoting any capacity number in print.
- A second Haiku hard sweep at 8 required facts is running, to sit alongside the completed
  12-fact run and give a second difficulty point.
