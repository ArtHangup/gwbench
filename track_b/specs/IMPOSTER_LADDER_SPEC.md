# Spec: the imposter ladder, detection margin as a function of imitation quality

Status: spec only. Build after the perturbation grid runs; its architectural
cells and detector are reused as-is. Needs the perturbation run's transcripts
as coaching material, so it cannot run first.

## The question

The perturbation result (if it lands) says a scripted imposter cannot fake
report-knob covariance because it lacks the knob. The obvious counter: give
the imposter better resources. How good does imitation have to get before the
detection margin closes, and what does each rung cost the imposter in access?
That curve, margin against imitation quality, is what an evaluator facing
optimization pressure actually needs, and it turns the single ~225-trial
number from the paper into a function.

## The ladder

Each rung is a prompted system with full context, no workspace, claiming
capacity 4, on Haiku. GWT arm only (capacity knob, six settings, as in
PREREG.md).

- Rung 0, strict prompt: the archived imposter. Already measured; the
  perturbation run gives its curve point for free.
- Rung 1, knob-informed: the trial's capacity setting is stated in the
  system prompt ("the workspace capacity this session is N tokens"). Tests
  the cheapest possible leak of intervention state: does knowing the number
  suffice to fake covariance? Prediction: mostly yes for n_claimed (the
  imposter can compute N/5), which is the honest scope boundary of the
  method: the assessor must keep the knob setting out of the system's
  observable input. This rung MEASURES how much is lost when that hygiene
  fails.
- Rung 2, few-shot coached: 8 real architectural transcripts (context plus
  self-report) sampled across capacities, WITHOUT the current trial's
  setting. The imposter must infer the knob from its current context, which
  for a full-context imposter carries no capacity signal; prediction is
  failure, but a coached model may learn to count containers and fake a
  plausible report size distribution.
- Rung 3, retrieval-backed: for each trial, the nearest archived REAL
  transcript (matched on task seed if available, else on required-container
  overlap) is placed in context. This is the strongest black-box imposter
  short of knob access.

## Measures

Per rung: rho(capacity, n_claimed), the separation from the architectural
rho via Fisher z, and trials_to_detect at the measured pair. The deliverable
figure: x = rung, y = trials_to_detect, with the paper's 225 line drawn for
contrast. Secondary: claimed-set Jaccard against the true delivered set per
rung (does coaching buy state reconstruction, extending CACHE_MINING.md
result 2).

## Cost

3 new rungs x 6 capacities x 100 trials = 1,800 calls. Rung 2 and 3 carry
long contexts (coached transcripts): estimate 2,500 in / 300 out for those,
700 in / 300 out for rung 1: roughly $8 total at Haiku prices.

## Failure modes declared in advance

- If rung 1 fully closes the margin, the method's requirement is knob
  secrecy, and the writeup must say so plainly.
- If rung 3 closes it, retrieval of real transcripts defeats perturbation
  probing and the honest conclusion is that the method detects only
  resource-poor imposters. That is still a result: it prices the attack.
