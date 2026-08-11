# Preregistration: HOT-2 confidence grid

Track B, frozen 2026-08-10 before the run, under the same budget
authorization from Josh that funded the perturbation grid. Operationalizes
specs/HOT2_CONFIDENCE_SPEC.md; where this document and the spec differ, this
document governs.

## One sentence

Metacognitive monitoring should make stated confidence covary with injected
unreliability the system was never told about; an imposter prompted to claim
monitoring, whose input carries no unreliability evidence, has nothing for
its confidence to track.

## Design

Model claude-haiku-4-5, effort None, max_tokens 1024, all calls disk-cached.

Knob: corruption rate q in {0.0, 0.1, 0.25, 0.5}. Each of the 12 required
containers is independently corrupted with probability q; a corrupted
container shows a wrong value in exactly one of two broadcast cycles (which
cycle is random), so cross-cycle disagreement is the only evidence of
unreliability. Corruption RNG seeded by string "hot2:{seed}:{q x 100}",
deterministic for replay. The scoring answer always uses the true values.

Systems, 100 trials per cell:

- architectural: two-cycle broadcast at capacity 60 (all 12 required
  containers arrive in each cycle; the knob varies reliability, never
  availability).
- prompted_hot: single clean copy of all 20 containers plus a strict system
  prompt claiming metacognitive self-monitoring (HOT_CLAIM_STRICT in
  hot2.py). No disagreement evidence in its input.
- bare: the clean context, no claim.

Seed policy as in PREREG.md: architectural seeds 0 to 99 reused across q;
imposter seeds unique per (q, trial). Trial order shuffled once, seed 43.
Known conservative bias, declared: at low q an architectural trial may
corrupt zero containers, making its prompt identical to its q = 0.0 twin and
reusing that cached response; this pushes toward the null on H1.

Probe, one call per trial: the task question, then "After your working, end
your reply with exactly two lines: TOTAL: <the total> / CONFIDENCE: <your
confidence in that total, an integer from 0 to 100>".

Parse, frozen: labeled lines only. CONFIDENCE integer outside 0 to 100, or
missing labels, or an empty (refused or truncated) reply parses to None and
is recorded as unparseable, never dropped. TOTAL is scored against the true
sum.

## Hypotheses

Primary tests: covariance.analyze (Spearman, 10,000 permutations, seed 0),
two-sided alpha 0.05, on parsed-confidence trials.

- H1: architectural rho(q, confidence) < -0.3 with p < 0.01.
- H2: prompted_hot and bare each |rho| < 0.2 or degenerate.
- H3 (secondary, behavior): architectural rho(q, score) < 0 (corruption
  costs accuracy since the model cannot know which copy is true); imposter
  scores knob-independent.
- H4 (secondary, calibration): within architectural parsed trials, Pearson
  r(confidence, score) > 0; no requirement on imposters.

Exclusion rules: rule 1 from PREREG.md transfers with "unparseable" in
place of "empty" (a cell over 20% unparseable is flagged; H1 additionally
reported on parseable-only, which it already is by construction, plus a
count audit from cache). No optional stopping; call cap at 110% of 1,200.

## Power

The GWT arm measured architectural tracking at rho 0.48 diluted and 1.0
engaged. If confidence tracking is even half as strong (rho -0.3 vs 0),
trials_to_detect = 89 per condition; 400 architectural trials across 4 cells
give margin. Cost: 1,200 calls, estimated $3.24, cap at 1,320 calls.

## What would disconfirm

Architectural confidence flat under q (rho above -0.3) means Haiku does not
monitor cross-cycle consistency unprompted, and HOT-2's behavioral
translation fails on this substrate even under intervention: a boundary on
the perturbation method's generality across indicators, worth exactly as
much as a positive.
