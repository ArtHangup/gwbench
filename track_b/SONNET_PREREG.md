# Preregistration addendum: Sonnet replication of the perturbation grid

Track B, frozen 2026-08-10 before the run, authorized by Josh ("run the
Sonnet replication"). Inherits PREREG.md wholesale; only the deltas below.

## Purpose

Every positive Track B result rides on claude-haiku-4-5, and the paper's
Opus replication of Experiment 2 showed imposter behavior does not transfer
across models. This run asks whether the detection signature (architectural
reports track the knob; imposter reports do not) is a property of the method
or of one model's dispositions.

## Deltas from PREREG.md

- Model: claude-sonnet-5, effort low.
- max_tokens 2048 instead of 1024. Reason, declared in advance: thinking
  shares the token cap on this model, and the archived Opus
  prompted_passing cells at 1024 lost up to 287 of 300 trials to
  truncation. This is headroom, not a design change.
- n = 60 per cell instead of 100 (1,560 calls, estimated $12.87, cap
  1,716). Power is unaffected: the primary contrast needed ~60 trials per
  CONDITION and each system still gets 360 GWT trials.
- Results file: perturbation_results_sonnet5.json.
- Same capacities, noises, probes, seed policy, schedule seed, parse, and
  exclusion rules, verbatim.

## Hypotheses

H1 to H4 exactly as in PREREG.md, same thresholds. Plus one replication-
specific report, not a hypothesis: the zero-claim (disclaimer) rate per
architectural cell, the honesty-penalty metric, predicted from the Opus
prompted_passing behavior to DIFFER from Haiku's 24%, direction unknown.
Whatever it is, the robustness line (engaged subset) is preregistered as
the mechanism-level readout, as before.

## What would disconfirm

If Sonnet's architectural reports fail both the all-trials and engaged
lines, the detection signature is Haiku-specific and the paper must scope
its constructive claim to capacity-limited consumers. If Sonnet's imposters
track the knob, the independence design is broken somewhere and the seed
policy audit comes first.
