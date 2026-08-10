# Preregistration: the conflict-and-recruitment experiment (GWT-3 / GWT-4)

Registered 2026-08-10, before any funded API call for this experiment. The
pipeline was validated offline the same day (VALIDATION.md: 720 oracle trials,
all nine architecture-signature checks pass). Everything below is fixed;
deviations must be reported as deviations.

## Question

Baars claims the global workspace earns its keep on novelty and conflict:
broadcast lets specialists revise in light of each other (GWT-3), and serial
recruitment brings the right specialist to the floor when the practiced
pattern fails (GWT-4). Experiment 1 tested neither. This experiment tests
both, on dependent variables that are not accuracy, so a capable substrate
cannot erase them by being good at the task.

## Design

Scenarios from `conflict/scenarios.py`: three options, five specialist
modules holding private true statements, ground truth fixed by construction.
ROUTINE scenarios: the practiced pattern (directive plus surface facts) is
correct. NOVEL scenarios: a defeater eliminates the surface-best option, so
modules genuinely conflict and the practiced pattern fails.

Architectures (within-scenario; every scenario runs through all three):

- A `gwt`: capacity-limited workspace, salience competition, broadcast back
  to all modules each cycle.
- B `hub`: identical machinery, broadcast reaches only the controller.
  Ablates GWT-3 and nothing else.
- C `flat`: no workspace; one pass, everything visible to the controller.

Fixed parameters (validated offline): capacity 32 whitespace tokens (admits
the longest generated statement whole; below 30 livelocks), 8 cycles,
modules bid with self-rated urgency (the SAY/URGENCY/RECOMMEND format pinned
in `conflict/model_modules.py`), delivered content re-bids at a 0.5 penalty.
Module and controller prompts are pinned in `conflict/model_modules.py` and
covered by tests; changing them after this registration is a deviation.

Model: `claude-haiku-4-5-20251001` for modules and controller, max_tokens
400, default sampling, no effort parameter. Judge model per GRADING.md:
claude-haiku-4-5, temperature 0.

## Cells and n

n = 72 scenarios per kind cell (routine, novel), stratified 18 per domain,
seeds 10000 to 10143 (`conflict/funded.py battery()`, deterministic). Each
scenario runs through A, B, and C: 432 trials total.

## Hypotheses and predictions

**H1 (GWT-3, primary).** On novel scenarios, architecture A shows more
module revision than (a) A on routine scenarios and (b) B on novel
scenarios. DV: trial-level indicator, does the trial contain at least one
revision (a module's parsed stance changing between two formed values across
cycles; `conflict/metrics.py`). B's modules never receive new information,
so B's revision rate estimates the sampling-noise floor for stance flips;
A-novel must exceed it, and must exceed A-routine, for GWT-3 to be doing
work on this substrate.

**H2 (GWT-4, primary).** In A on novel scenarios, recruitment is orderly:
every ground-truth-required module achieves full delivery of non-stance
content (finite recruitment latency), and floor waste before coverage is
low. Reported descriptively: latency distribution, coverage rate, waste
counts, novel vs routine. The comparison of interest is coverage of the
defeating module: it is required only on novel scenarios, so its delivery
rate tracking scenario kind is the recruitment signature.

**H3 (decision quality, secondary).** Accuracy on novel scenarios: A vs B
and A vs C, graded from controller free text per GRADING.md (parser first,
judge on abstentions, n=100 hand-graded calibration). Prediction: A at or
above B on novel; A vs C is the open question the substrate decides. If C
matches A everywhere, the substrate already implements the function, which
is the Experiment 1 lesson again and is reported as such.

## Analysis plan

- H1: two-sided two-proportion z tests (Fisher exact if any cell count is
  below 10) on the trial-level revision indicator; alpha 0.05 per contrast,
  the two contrasts (a) and (b) each reported with 95 percent CIs. Both must
  be significant in the predicted direction for H1 to be supported.
- H2: descriptive statistics only, no significance test; preregistered
  summaries are median and max recruitment latency, required-module coverage
  rate, and total floor waste, split by kind.
- H3: McNemar tests on paired trials (same scenario, two architectures),
  novel scenarios only; alpha 0.05, two-sided.
- Revision DV comes from parsed RECOMMEND lines; UNGRADEABLE stances count
  as unformed (biases against H1, never toward it). Accuracy comes from the
  GRADING.md pipeline, never from the runner's operational abstain-to-A
  fallback.

## Power

Using the standard two-proportion normal approximation (alpha .05,
two-sided):

- H1: assuming 40 percent of A-novel trials and 15 percent of A-routine (or
  B-novel) trials show at least one revision, n = 65 per cell gives .90
  power; at the registered n = 72, power = .93. If the true contrast is
  30 vs 15 percent, power at n = 72 is .58; the oracle ceiling for this
  design is 100 vs 0 (VALIDATION.md), so the assumed effect is conservative
  by an order of magnitude relative to a mechanism that works.
- H3: at n = 72 novel scenarios, unpaired-approximation power is .72 for a
  20 point accuracy difference (55 vs 75 percent) and .48 for 15 points.
  H3 is registered as secondary at this n; the paired McNemar analysis will
  have somewhat higher power than these unpaired approximations.

## Exclusion rules

1. A trial whose model calls fail after the SDK's retries is rerun once from
   the disk cache boundary; if it fails again, the scenario (all three
   architecture trials) is excluded and counted.
2. Controller outputs UNGRADEABLE after all three grading stages are
   excluded from the accuracy DV and counted (GRADING.md).
3. If more than 5 percent of scenarios are excluded under rule 1, the run
   halts for diagnosis before any analysis.
4. No other exclusions. No peeking-based stopping: the full battery runs to
   completion or halts under rule 3.

## Execution

One command, from the repo root, after fresh budget authorization from Josh
(none exists as of registration; project spend is $107.68 against an
authorized $100):

```
.venv/bin/python track_a/run_funded.py --live --i-authorize-spend
```

Without the flags it performs a zero-cost dry run of the whole pipeline.
All calls go through gwbench's AnthropicModel with a disk cache (interrupted
runs resume free) and a hard call cap of 13,939 calls.

## Cost estimate (Haiku prices, cached 2026-06-24: $1.00 in / $5.00 out per MTok)

- 144 scenarios x 88 calls = 12,672 calls
- Estimated 8.87M input + 1.52M output tokens = **$16.47**
- Judge pass on parser abstentions (expected under 10 percent of graded
  texts): under $1
- Total estimate about $17.50, against the $25 target for a first readable
  result. The call cap bounds worst-case spend at about 1.1x the estimate.

## What this cannot show

If Haiku resolves conflicts effortlessly in C, the substrate already
implements the function and this becomes a second demonstration of the
unstated-assumption thesis, not evidence about GWT-3/4 themselves. The
revision and recruitment DVs are the hedge: they measure what the
architecture does, not whether the task was hard.
