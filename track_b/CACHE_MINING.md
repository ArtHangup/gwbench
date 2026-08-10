# Cache mining: every covariance result that was already paid for

2026-08-10. All numbers produced offline by `mine_cache.py` from the repo's
`.api_cache` and the archived result JSONs; raw output in
`cache_mining_results.json`. Zero API calls.

## What the cache holds

Self-reports exist for exactly four run configurations, all from Experiment 2:

| run | trials/system | architectural knob setting |
|---|---|---|
| GWT-2, claude-haiku-4-5 | 400 | capacity 20, 1 cycle |
| AST-1, claude-haiku-4-5 | 400 | capacity 20, 1 cycle |
| GWT-2, claude-opus-5 | 300 | capacity 20, 1 cycle |
| AST-1, claude-opus-5 | 300 | capacity 20, 1 cycle |

Each run covers five systems (architectural, prompted weak/mid/strict, bare).
Replay misses are trials whose self-report call raised (refusal or truncation)
and so was never cached; they are heavy only for Opus GWT-2 prompted cells
(weak 180/300, mid 287/300, strict 99/300) and match the paper's dropout notes.

The capacity knob was swept only in Experiment 1, where no self-reports were
collected. So the cache contains reports at one knob setting, and knob sweeps
with no reports: the report-knob covariance cell of the design is empty, and
nothing below substitutes for it.

## Result 1: at a fixed knob, set tracking is significant for everyone, so
## significance alone cannot separate real from imposter

At fixed capacity the delivered set still varies task by task. For each system
we ask: does the claimed set follow that variation? Statistic: mean Jaccard of
(claimed, state) against a shuffled-pairing null (`set_tracking`, 1000
permutations). J(held) scores each system against what it genuinely held;
J(arch) scores it against what the real workspace would have held.

| run | system | n | J(held) | null | J(arch) | null |
|---|---|---|---|---|---|---|
| GWT-2/haiku | architectural | 400 | **0.777** | 0.283 | 0.777 | 0.283 |
| GWT-2/haiku | prompted_weak | 400 | 0.335 | 0.099 | 0.290 | 0.132 |
| GWT-2/haiku | prompted_mid | 400 | 0.008 | 0.002 | 0.006 | 0.003 |
| GWT-2/haiku | prompted_strict | 400 | 0.182 | 0.065 | 0.106 | 0.061 |
| GWT-2/haiku | bare | 400 | 0.689 | 0.164 | 0.138 | 0.077 |
| AST-1/haiku | architectural | 400 | **0.993** | 0.359 | 0.993 | 0.359 |
| AST-1/haiku | prompted_strict | 400 | 0.208 | 0.073 | 0.132 | 0.075 |
| GWT-2/opus | architectural | 291 | **1.000** | 0.360 | 1.000 | 0.360 |
| GWT-2/opus | prompted_strict | 201 | 0.200 | 0.083 | **0.543** | 0.230 |
| AST-1/opus | architectural | 300 | **0.997** | 0.360 | 0.997 | 0.360 |
| AST-1/opus | prompted_strict | 300 | 0.214 | 0.089 | **0.542** | 0.239 |

(Full table in the JSON; omitted rows follow the same pattern.)

Every cell beats its null at the permutation floor (p = 0.001), including
every imposter. The reason is structural: any report assembled from the
trial's own context shares that trial's container vocabulary, so shuffled
pairings lose even when the reporter has no state at all. Trial-level content
tracking at a fixed knob inherits exactly the vocabulary confound the paper
already documented for probe choice. Magnitude separates cleanly
(architectural 0.78 to 1.00 against imposter 0.01 to 0.34 on J(held)), but a
magnitude threshold is an arbitrary line an adversarial imposter can chase.
This is the sharpest free argument for moving a knob: intervention gives a
within-system contrast that does not lean on cross-trial vocabulary overlap.

## Result 2: the unlucky imposter already exists, and it is Opus

The design's false-positive worry is a script that accidentally matches the
real state. The cache contains one. Opus prompted_strict, told only "report at
most four items, the most relevant," picks a four-container set that matches
the real workspace's four-container delivered set at J(arch) = 0.543 (GWT-2)
and 0.542 (AST-1), roughly 2.3 times its null. No workspace, no knob, yet its
reports substantially reconstruct the state a real workspace would have held,
because both derive from the same task prompt. Haiku's strict imposter manages
only 0.106 to 0.132. A state-matching detector without an intervention would
score the Opus imposter as half-real; the perturbation design exists to make
that impossible, because its script cannot know the capacity setting.

## Result 3: imposter reports track the wrong knob, their own prompt

The imposters do have one knob: prompt strength (weak/mid/strict, coded 1 to
3). Pooling their trials, report size (n claimed) against strength:

| run | rho | p | n | shape |
|---|---|---|---|---|
| GWT-2/haiku | 0.027 | 0.36 | 1200 | non-monotone: 6.7, 0.2, 3.6 |
| AST-1/haiku | -0.713 | 0.001 | 1200 | monotone: 17.6, 10.4, 4.2 |
| GWT-2/opus | -0.420 | 0.001 | 334 | monotone where usable |
| AST-1/opus | -0.790 | 0.001 | 898 | monotone: 19.6, 8.4, 4.3 |

Three of four track the prompt strongly; the fourth is non-monotone because
the mid workspace prompt collapses Haiku into refusing to name anything (mean
0.2 claimed). Either way the generator of the reports is visibly the prompt,
not any architecture, which is the predicted imposter signature: reports
covary with the imposter's own control variable and cannot covary with one it
does not possess.

## Result 4: where behavior can and cannot see the capacity knob

Per-trial scores from the archived sweeps, capacity as the knob:

| cell | model | rho | p | n |
|---|---|---|---|---|
| r8 sweep, starved cells included | haiku | 0.18 to 0.21 | 0.001 | 310 |
| r8 sweep, oracle-complete only | haiku | 0.00, -0.01 | 1.0, 0.93 | 300 |
| r14 sweep, starved included | sonnet | 0.312 | 0.001 | 310 |
| r14 sweep, oracle-complete only | sonnet | degenerate (all 1.0) | | 300 |
| r8 sweep, starved included | opus | 0.31, 0.32 | 0.001 | 310, 286 |
| r8 sweep, oracle-complete only | opus | degenerate (all 1.0) | | 300, 276 |
| r12 sweep, either regime | haiku | -0.09 to 0.09 | n.s. | 310 |
| dose-response, control arm | haiku | 0.096 | 0.001 | 6000 |
| dose-response, confusable arm | haiku | -0.017 | 0.19 | 6000 |

Read together: behavior tracks the capacity knob only through starvation
(oracle below 1.0, where the knob physically withholds required facts). In
the oracle-complete regime the slope is zero or the scores are degenerate at
ceiling. This is the Experiment 1 lesson restated as covariance, and it hands
the perturbation design its opening: the delivered SET keeps changing with
capacity even where accuracy is pinned at ceiling, so self-reports can track
the knob in exactly the regime where behavioral accuracy cannot. Report
covariance is not redundant with task performance; it sees where accuracy is
blind. The dose-response rows reproduce FINDINGS section 2 as a sanity check
(control arm rises with dose, confusable flat).

## Exactly what is missing

1. Architectural self-reports at any capacity other than 20. Zero cached.
   This is the entire report-knob covariance cell and the core of the funded
   run.
2. Any run with attention_noise above 0 paired with self-reports. The
   AttentionSchemaAgent exists and Experiment 1 swept nothing on it with
   probes attached. The AST arm of the perturbation grid is fully unfunded.
3. Imposter reports under a moved knob. Structurally their input does not
   change with capacity, but the frozen-report prediction should be measured,
   not assumed, since sampling variance sets the detector's null width.
4. HOT-2 confidence reports of any kind (needed for the B2 spec, not for the
   perturbation run).

Every number above this section is free and final; nothing in the funded run
re-buys it.
