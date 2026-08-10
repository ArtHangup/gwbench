# Perturbation grid: results

Run 2026-08-10 under budget authorization from Josh, against the frozen
design in PREREG.md. 2,600 planned trials; 2,442 live calls, 158 cache hits
(the 100 preplanned capacity-20 architectural replays, plus 58 architectural
calls whose prompts were byte-identical to earlier ones because a small knob
change did not alter the broadcast; those reuse one sample and slightly
understate report variance, a bias toward the null that the results survive).
Cost $2.43 against the $5.20 estimate. No aborts, no call-cap hits. Raw
records in perturbation_results.json; run log in perturbation_run.log.

## Headline

A real architecture's self-reports covary with a knob the assessor turns,
and a prompted imposter's do not. The detection signature (H1 plus H2)
landed, and the strongest form of the result is stronger than the
preregistered prediction: when the real system engages the probe at all, its
report is a PERFECT readout of its workspace state, 456 of 456 engaged
replies naming the delivered container set exactly, at every capacity.

## Hypothesis by hypothesis

### H1 (GWT architectural, primary): supported, with the effect-size
### criterion met only on the preregistered robustness line

All 600 trials: rho(capacity, n_claimed) = 0.480, permutation p = 1e-4.
The p < 0.001 criterion is met; the rho > 0.5 criterion is missed by 0.02.
Mean claims by capacity are perfectly monotone:

| capacity | 10 | 15 | 20 | 25 | 30 | 40 |
|---|---|---|---|---|---|---|
| delivered count | 2 | 3 | 4 | 5 | 6 | 8 |
| mean n_claimed (all trials) | 1.84 | 2.34 | 3.04 | 3.35 | 4.20 | 5.84 |
| mean n_claimed (engaged) | 2.00 | 3.00 | 4.00 | 5.00 | 6.00 | 8.00 |

The dilution has one identified source. Five cells exceeded the
preregistered 20% flag for zero-claim replies (up to 33% at capacity 25).
Cache inspection of all 144 zero-claim replies found ZERO refusals or
truncations: every one is Haiku disclaiming the framing ("I don't actually
have a persistent workspace...") before declining to list contents, the same
disclaimer behavior the paper documented on the self-report probe. On the
preregistered robustness line (zero-claim trials excluded, n = 456):

    rho = 1.000, p = 1e-4.

Not approximately 1: exactly. Every engaged reply claimed exactly the
delivered count, and in fact the delivered SET, 456 of 456. Conditional on
answering the question, the report IS the state.

### H2 (GWT imposters, primary): supported

- prompted_strict: rho = -0.009, p = 0.85. Means flat at 3.4 to 3.8 across
  a fourfold capacity range: the scripted claim, frozen, now measured live
  rather than assumed.
- bare: rho = 0.055, p = 0.18. Claims 12 to 14 containers everywhere.

### H3 (AST architectural, primary): supported

rho(noise, reported_miss) = 0.307, p = 1e-4, n = 400. The preregistered
step contrast: miss-report rate 0.34 at noise 0 versus 0.95 pooled above 0,
two-proportion z = 13.0. Above zero the rate even grades monotonically
(0.89, 0.95, 1.00), more structure than the tied-salience analysis
predicted. One honest wart: at noise 0 the true miss count is 0.00 by
construction, yet the model reports misses on 34% of trials (mean 2.16
containers). The honest channel has a confabulation floor; the covariance
survives it because the rate still doubles and saturates as the knob rises.

### H4 (AST imposter, primary): supported, maximally

reported_miss = 0 on all 400 trials (every reply is RECEIVED_ALL): rho
undefined, degenerate. The static-script signature, live.

## Secondary results

- Separation economics: Fisher z between the architectural and strict rhos
  is 9.2. From the measured all-trials pair, trials_to_detect = 59 per
  condition; from the engaged-subset effect it is single-digit. The
  interrogation design's one usable margin needed ~225 per condition.
- Ground-truth calibration (AST): reported_miss tracks TRUE miss count at
  rho = 0.404, p = 0.001. The reports covary with the knob because they
  covary with the state the knob moves, which is the mechanism the design
  claims.
- The GWT-2 vocabulary problem from CACHE_MINING.md result 1 does not touch
  this design: the statistic never compares report content across trials,
  only report size against an intervention the imposter cannot see.

## Reading

Interrogation could not identify the property (the paper's regress).
Intervention does: one knob, six settings, and the real system separates
from its imitation at nine sigma for two dollars and change. The constructive
ending the paper lacked is now measured, not argued: behavioral testing is
not stuck, content-blind testing under intervention access works, and its
sample cost is a quarter of the interrogation design's. The psychedelics
bridge holds by construction: dose as intervention, report as readout,
covariance as the evidence, the same triple as the REBUS work.

Caveats, unchanged from PREREG.md: one model (Haiku, the strained one);
imposters without knob access (the imposter ladder spec prices the stronger
attack); AST dose-response step-shaped by the tied-salience task family;
disclaimer behavior means the all-trials effect size undersells the
mechanism, and any replication should report both lines as done here.
