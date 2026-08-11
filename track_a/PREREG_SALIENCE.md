# Preregistration: the rater-salience arm

Registered 2026-08-10, authorized by Josh, before any call for this arm. This
answers the sharpest objection to the recruitment result: that self-rated
one-shot urgency is an uncharitable reading of GWT's salience competition.

## Question

The funded run found required-module recruitment coverage of 33.3 percent on
novel scenarios when modules rate their own urgency, against an oracle ceiling
of 100 percent. Is that failure a property of the workspace loop, or of the
salience function, the choice the theory never states?

## Design

Architecture A only, same 144 scenarios (seeds 10000 to 10143), same module
and controller prompts, same capacity (32), cycles (8), and model
(claude-haiku-4-5-20251001). One change: the salience attached to each SAY
statement comes not from the emitting module's self-rating but from a separate
relevance rater, the same Haiku model asked, given only the decision question
and the statement text (no private evidence, no ground truth, no knowledge of
which module spoke): "how urgent is it that the whole team hears this
statement now, 0.0 to 1.0". Malformed ratings fall back to 0.5, clamped to
[0, 1]. Stance statements keep salience 0.5 as before. Pinned in
`conflict/rater.py`, covered by offline tests.

## Predictions

1. **Primary.** Required-module coverage on novel scenarios exceeds the
   self-rated arm's 24/72 (33.3 percent). Two-proportion test (Fisher if any
   cell is below 10), alpha .05, two-sided, against the funded run's A-novel
   cell. Either outcome is informative: recovery localizes the failure in the
   salience function and demonstrates the thesis; no recovery generalizes the
   recruitment failure across two salience choices.
2. **Secondary, descriptive.** Coverage on routine scenarios, median latency,
   floor waste, revision rates, and corrective share, reported alongside the
   funded run's values.

## Cost

Worst case 5,904 module and controller calls plus at most 11,520 rater calls
(rater calls deduplicate heavily through the response cache since statements
repeat across cycles). Estimate $6 to $8 at Haiku prices; hard call cap
19,166 (1.1 times worst case).

## Command

```
.venv/bin/python track_a/run_salience_arm.py --live --i-authorize-spend
```

Dry run without flags. Output: track_a/results/salience_arm.json; analysis
appended to RESULTS.md.
