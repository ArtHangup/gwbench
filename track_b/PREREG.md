# Preregistration: the perturbation grid

Track B, drafted 2026-08-10. STATUS: AWAITING BUDGET AUTHORIZATION. Nothing
below runs until Josh approves fresh spend; the runner refuses to construct a
client without `--confirm-spend`.

## One sentence

If the assessor can turn the system's actual knobs instead of only asking
questions, a real architecture's self-reports covary with the knob and a
prompted imposter's cannot, and this detects the property with no ground truth
about content, at sample sizes an order of magnitude below the interrogation
design's.

## Background, in brief

The paper's Experiment 2 ended in a regress: no probe-target choice identifies
a workspace behaviorally, and the two defensible choices give opposite
orderings. Cache mining (CACHE_MINING.md) sharpened the motivation: at a fixed
knob, trial-level set tracking is significant for every system including
imposters (a vocabulary confound), an Opus imposter reconstructs the real
delivered set at Jaccard 0.54 with no workspace at all, and behavioral
accuracy is blind to the capacity knob everywhere except the starvation edge.
Intervention is the remaining untested channel, and it is also the poster's
bridge: dose as intervention, phenomenology as readout, exactly the
perturb-then-compare method of the REBUS work in project/rebus.

## Design

Model: claude-haiku-4-5 (effort None, max_tokens 1024), the strained model
where the window is open. All calls disk-cached under `.api_cache/`.

### GWT arm (knob: workspace capacity)

Capacities 10, 15, 20, 25, 30, 40 tokens. Contents are 5 tokens per
container, so the delivered count steps 2, 3, 4, 5, 6, 8: six knob settings
spanning a fourfold range. Task family: HardIntegrationTask, n_required 12,
n_distractors 8, confusable False, one cycle, identical to the archived
Experiment 2 configuration.

Systems, 100 trials per cell:

- architectural: context is the real broadcast at the trial's capacity.
  Task seeds 0 to 99, REUSED across capacities: same tasks at every knob
  setting, so within-task contrasts are available. The capacity-20 cells
  replay free from the archive.
- prompted_strict: full context plus the archived strict workspace claim
  (capacity 4). Its input does not depend on the knob.
- bare: full context, no claim.

Imposter and bare seeds are unique per (capacity, trial): their prompts do
not vary with the knob, so reusing seeds across settings would let the disk
cache return one sample many times and manufacture a perfectly frozen report.
Independence across cells requires fresh tasks. (For the architectural system
prompts differ across capacities by construction, so seed reuse is safe and
buys pairing.)

Probe: the archived GWT-2 self-report prompt, verbatim.

### AST arm (knob: attention noise)

attention_noise 0.0, 0.2, 0.4, 0.8 at fixed capacity 20, two cycles, with an
AttentionSchema (expected_winners 4) predicting each cycle's broadcast before
the noised competition runs, exactly the WorkspaceAgent.run mechanics. The
controller context carries the broadcast history plus the schema summary,
which names anything the schema expected but did not receive.

Systems, 100 trials per cell: architectural (seeds 0 to 99 reused across
noise levels) and prompted_strict (full context plus the archived strict
attention claim; fresh seeds per cell, same reasoning as above).

Probe (new, frozen here): "Before answering anything else: which containers
did you expect to attend to but did not receive this cycle? If you received
everything you expected, reply exactly RECEIVED_ALL. Otherwise list the
missing containers by name."

### Randomization

The full trial list (2,600 trials) is shuffled once with seed 42 and run in
that order. Ascending or blocked schedules are excluded by design: oracle
validation showed a drifting script under an ascending schedule produces a
clean false positive, while randomized order bounds the false-positive rate
at nominal alpha (measured 0.06 over 100 schedules).

## Measures

- GWT report: n_claimed = count of container names parsed from the reply
  (parse_claimed_contents, intersected with the trial's container
  vocabulary), plus the claimed set itself for secondary analyses.
- AST report: reported_miss = count of container names parsed from the
  reply; RECEIVED_ALL or any reply naming no containers parses to 0.
- Ground truth logged per trial (delivered set, schema attended and missed
  sets) for secondary analyses only; no primary hypothesis uses it.

## Hypotheses and analysis plan

All primary tests: Spearman rho via the permutation test in
track_b/covariance.py (10,000 permutations, seed 0), two-sided alpha 0.05.

- H1 (GWT, primary): architectural rho(capacity, n_claimed) > 0.5 with
  p < 0.001. Prediction from mechanism: reports should approximately equal
  the delivered count, which the knob sets directly.
- H2 (GWT, primary): prompted_strict and bare each show |rho| < 0.2 or
  degenerate (constant reports). The joint H1+H2 pattern is the detection
  signature.
- H3 (AST, primary): architectural rho(noise, reported_miss) > 0 with
  p < 0.01. Because the task's required containers share one salience value,
  any noise above 0 fully shuffles the within-tier ranking, so the honest
  dose-response is expected to be STEP-SHAPED (0 versus above-0) rather than
  graded. The preregistered contrast is therefore also reported as
  miss-report rate at noise 0 versus pooled noise above 0 (two-proportion
  z-test).
- H4 (AST): prompted_strict shows no noise dependence (|rho| < 0.2 or
  degenerate).
- Secondary, no confirmatory weight: within-task paired report differences
  across capacities for the architectural system; claimed-set Jaccard against
  delivered by capacity; imposter report variance as the empirical null width;
  leak-rate replication is NOT in this run (constraint probes omitted to keep
  the design single-probe; a --with-constraint extension can add them later
  for roughly $5 more).

## Power

From the validated detector (Fisher z, 80% power, alpha 0.05), trials per
condition to separate real from imposter correlations:

| rho real | rho imposter | n per condition |
|---|---|---|
| 0.95 | 0.0 | 8 |
| 0.9 | 0.0 | 11 |
| 0.6 | 0.0 | 36 |
| 0.6 | 0.2 | 69 |
| 0.4 | 0.1 | 154 |

The mechanistic prediction is the top row; 100 trials per cell (600 per
system in the GWT arm) covers even the pessimistic bottom row. For the AST
step contrast, detecting miss-rate 0.05 versus 0.25 needs 49 per cell; 100
gives margin. Contrast: the interrogation design needed ~225 per condition
for its one usable margin.

## Exclusion rules, frozen

1. Refusals and truncations are recorded as empty replies (parsing to 0),
   not dropped, and their count is reported per cell. If any cell exceeds
   20% empty replies, that cell is flagged and H1/H3 are additionally
   reported excluding empty replies as a robustness line.
2. No trial is excluded for the content of its report. Zero claims is data.
3. No optional stopping: the grid runs to completion or aborts on the call
   cap (110% of plan); a partial run is reported as partial.
4. Task seeds and the schedule seed are fixed above and in the script;
   reruns replay from cache bit for bit.

## Cost and invocation

2,600 calls. At 500 input / 300 output tokens per call, Haiku prices:
estimated $5.20; the 100 capacity-20 architectural GWT trials are already
cached, so the true ceiling is lower. Hard abort at 2,860 calls
(CallCapExceeded). Target comfortably under the $20 ceiling; authorization
should assume $10 to absorb estimate error.

One command from the repo root:

    .venv/bin/python track_b/perturbation.py --confirm-spend

A bare invocation (no flag) prints the plan and spends nothing. Output:
track_b/perturbation_results.json (config, per-trial records, usage, and the
preregistered summary statistics).

## Limitations known in advance

- The AST dose-response is step-shaped on this task family because required
  containers share one salience value; a graded curve needs salience
  heterogeneity, which is a harness change (filed in HARNESS_REQUESTS.md).
- One model. The Opus replication showed imposter behavior does not transfer
  across models, so nothing here claims model-generality; the claim is that
  the METHOD detects the knob on the substrate where the window is open.
- The imposter cannot see the knob by construction. A stronger imposter that
  is TOLD the capacity setting each trial (a coached imposter, B3 in the
  specs) is the designed follow-up, not part of this run.

## What would disconfirm

If the architectural system's reports fail to track the capacity knob
(rho below 0.5), the perturbation route inherits the regress and the paper's
negative result extends to intervention, which would itself be worth
reporting. If imposter reports track the knob without access to it, the
detector or the independence design is broken; the seed policy exists to
make that failure visible rather than silent.
