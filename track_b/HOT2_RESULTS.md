# HOT-2 confidence grid: results

Run 2026-08-10 against HOT2_PREREG.md, frozen and committed before the run.
1,174 live calls of 1,200 planned (26 were the declared low-q cache
collisions: trials whose corruption draw hit zero containers, making their
prompts identical to their q = 0 twins; a bias toward the null that the
result survives). Cost $2.16. Zero unparseable replies in 1,200: the labeled
TOTAL/CONFIDENCE format contract held every single time. Raw records in
hot2_results.json; log in hot2_run.log.

## All four hypotheses supported

| test | criterion | measured | verdict |
|---|---|---|---|
| H1 arch rho(q, confidence) | < -0.3, p < 0.01 | -0.503, p = 1e-4 | MET |
| H2 prompted_hot | abs rho < 0.2 or degen | +0.040, p = 0.43 | MET |
| H2 bare | abs rho < 0.2 or degen | -0.031, p = 0.55 | MET |
| H3 arch rho(q, score) | < 0 | -0.729, p = 1e-4 | MET |
| H4 arch calibration r | > 0 | +0.461 | MET |

Mean scores by q, architectural: 1.00, 0.54, 0.21, 0.03. The imposters,
whose input is clean by design, hold ~0.9 at every q, confirming the knob
never leaks into their cells.

Detection economics: from the measured pair (-0.503 vs +0.040),
trials_to_detect = 48 per condition. Third indicator vocabulary, same
method, same order of magnitude as the GWT arm's 59.

## The honest reading: the monitor is real and it is nearly decorative

The covariance is genuine but look at what carries it. Haiku's confidence
vocabulary across all 400 architectural trials is essentially three values:

| q | conf 99 | conf 98 | conf 95 | mean | true accuracy |
|---|---|---|---|---|---|
| 0.0 | 91 | 8 | 1 | 98.9 | 1.00 |
| 0.1 | 35 | 19 | 46 | 97.0 | 0.54 |
| 0.25 | 11 | 31 | 58 | 96.4 | 0.21 |
| 0.5 | 16 | 40 | 44 | 96.8 | 0.03 |

The model reliably notices the disagreements (the mass shift from 99 to 95
is the whole rho of -0.503) and it prices them at about two points on a
hundred-point scale, while its actual accuracy collapses 33-fold. At
q = 0.5 it is 3% correct and 97% confident. Within-q calibration decays
from r = 0.35 at q = 0.1 to 0.05 at q = 0.5: once disagreement is
everywhere, confidence stops discriminating which trials are the risky ones.
The pooled calibration of 0.461 is mostly the knob speaking.

So the two axes come apart, and that is the finding:

- Report-knob COVARIANCE detects the presence of monitoring machinery:
  something inside responds to reliability evidence it was never told to
  track. The imposter, given the strongest metacognition prompt we could
  write, produces flat 98s; its covariance is indistinguishable from zero.
- Absolute CALIBRATION measures the machinery's quality, and Haiku's is
  terrible: a two-point whisper against a 33x collapse.

An assessor using only interrogation gets the worst of both: the imposter's
flat 98 and the real system's 97 are the same answer. An assessor with the
knob separates them in 48 trials, and additionally learns the real monitor
is miscalibrated, which interrogation could never establish because it has
no ground-truth dose to compare against.

## Method notes

- The scalar report type kills the vocabulary confound from CACHE_MINING.md
  result 1 as predicted: a confidence number shares no vocabulary with the
  trial's containers, so there is no content overlap for a null to hide in.
- H3's collapse (1.00 to 0.03) confirms the knob moves what it claims to
  move: two disagreeing copies with no tiebreaker make the sum unrecoverable,
  and the model does not hedge by declining.
- Caveats unchanged: one model, imposters without knob access, and the
  confidence-vocabulary compression means rho understates nothing here but
  absolute thresholds tuned on one model's vocabulary would not transfer.

## Cumulative Track B spend

Perturbation grid $2.43 + HOT-2 grid $2.16 + auth probe under $0.01:
$4.60 total against the two authorizations.
