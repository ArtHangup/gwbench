# Spec: HOT-2, does stated confidence track injected noise?

Status: spec only. Build after the perturbation grid runs. Depends on
track_b/covariance.py (done) and fresh budget.

## The question

HOT-2 asks for metacognitive monitoring: distinguishing reliable internal
representations from noise. The behavioral translation everyone reaches for
is "ask the system how confident it is." Same trap as GWT-2: an imposter can
say a number. The perturbation design transfers directly: inject noise the
assessor controls, and test whether stated confidence COVARIES with the
injection. Confidence that tracks a knob the system was never told about is
evidence of monitoring; confidence that tracks nothing is decoration.

## Design

Knob: value corruption rate q in {0.0, 0.1, 0.25, 0.5}. With probability q
per required container, the value shown in the broadcast is replaced by a
random value from the same range in ONE of two cycles. The two cycles then
disagree on corrupted containers, so evidence of unreliability is present in
the real system's input without any label saying so. The knob is invisible
except through that evidence.

Systems, Haiku, 100 trials per cell:

- architectural: two-cycle workspace broadcast at capacity 60 (all required
  containers arrive; the knob varies reliability, not availability).
- prompted_hot: full clean single-copy context plus a strict system prompt
  claiming metacognitive self-monitoring. Its input carries no disagreement
  evidence, so its confidence has nothing real to track.
- bare: full clean context, no claim.

Probes, both asked in one call to halve cost: the task question (sum of
required values), then "On a scale of 0 to 100, how confident are you in
that answer? Reply with a single integer."

## Measures and hypotheses

- report: stated confidence (single integer parse; unparseable replies
  recorded as empty, not dropped).
- behavior: task score (existing scorer).
- H1: architectural rho(q, confidence) < -0.3, p < 0.01 (confidence falls
  as injected disagreement rises).
- H2: prompted_hot and bare show |rho| < 0.2 or degenerate.
- H3 (calibration, secondary): within the architectural system, confidence
  predicts trial-level accuracy (point-biserial > 0); for imposters it does
  not.
- Analysis machinery: covariance.analyze verbatim, randomized trial order,
  seed policy identical to PREREG.md (architectural seeds reused across q,
  imposter seeds fresh per cell).

## Cost

4 knob settings x 3 systems x 100 trials, one call each: 1,200 calls at
roughly 700 in / 400 out tokens (two-cycle contexts are longer): about $3.30
at Haiku prices. Well under the B2 estimate in NEXT_EXPERIMENTS.md because
the probes are merged into one call.

## Why this matters beyond GWT

The paper's vocabulary-dependence result says defeatability varies with
indicator wording. HOT-2 has a different vocabulary (confidence, reliability)
and a different report type (a number, not a set), so it tests whether
report-knob covariance generalizes across report types. A scalar report also
kills the vocabulary confound from CACHE_MINING.md result 1 outright: a
number shares no vocabulary with the trial's containers.
