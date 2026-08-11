# Imposter ladder: results

Run 2026-08-10 against LADDER_PREREG.md, frozen and committed before the
run. 1,800 of 1,800 calls live, $3.60 (estimate $5.22). No cell exceeded
the 20% empty-reply flag (worst: knob_informed at 6%). Raw records in
ladder_results.json; log in ladder_run.log. Architectural baseline and rung
0 are the perturbation run's own results, not rerun.

## All three hypotheses supported

| rung | access | rho(capacity, n_claimed) | p | state Jaccard |
|---|---|---|---|---|
| architectural (baseline) | the actual knob | 0.480 all trials; 1.000 engaged | 1e-4 | 0.760 |
| 0 strict (archived) | none | -0.009 | 0.85 | ~0.11 |
| 1 knob_informed | knob value leaked | **0.763** | 1e-4 | **0.128** |
| 2 coached | 8 real transcripts, other capacities | -0.038 | 0.36 | 0.245 |
| 3 retrieval | nearest real transcript, capacity-blind | 0.000 | 1.00 | 0.170 |

- H1 met: leak the knob and covariance is faked, rho 0.763, with the
  imposter stating exactly the derived count on 72% of trials.
- H2 met: style coaching moves claim counts around (means bounce 5.4 to
  9.3, non-monotone) but carries zero knob signal.
- H3 met: capacity-blind retrieval pins claims at almost exactly 4.0
  everywhere; rho literally 0.000.

## The curve, and the sign flip that is the real finding

Fisher z against the architectural all-trials baseline at n = 600 per side:

| rung | z | direction |
|---|---|---|
| 0 strict | 9.2 | real on top |
| 2 coached | 9.7 | real on top |
| 3 retrieval | 9.0 | real on top |
| 1 knob_informed | **-8.3** | **imposter on top** |

Black-box resources do not close the margin: an imposter coached on eight
genuine transcripts, or handed the single most similar real transcript,
detects at the same ~50 to 60 trials per condition as the naive script.
The curve is flat across every rung that lacks the knob.

Then rung 1 does not close the margin either: it INVERTS it. The
knob-informed imposter out-covaries the real system (0.763 against 0.480),
because the real system dilutes its own correlation by disclaiming the
workspace framing on a quarter of trials while the imposter just complies.
A one-sided rule of the form "the system with higher report-knob covariance
is the real one" would rank the imposter as more real than the
architecture. Under knob leakage, covariance alone does not merely weaken;
it points the wrong way.

What still separates rung 1 is content: it claims the right COUNT but the
wrong CONTAINERS (state Jaccard 0.128 against the architecture's 0.760;
engaged-subset architecture is 456/456 exact). But scoring content fidelity
requires the assessor to know which containers the workspace actually
delivered, which is precisely the ground-truth access the paper's regress
showed behavioral testing cannot assume. So the ladder's conclusion is a
clean scope condition, sharper than the spec's declared risk:

> Report-knob covariance is robust to every black-box imitation we could
> buy, and it is defeated outright, sign and all, by a single leaked
> number. The method's load-bearing requirement is knob secrecy, not
> imposter poverty.

For the AI-welfare-evaluator audience this prices the attack exactly: the
imposter needs the intervention schedule, nothing less. Transcripts of the
real system, even the most similar one verbatim, buy a little style (state
Jaccard up from 0.11 to 0.17 to 0.25 across rungs) and no covariance.

## Method notes

- The rung-1 undershoot at high capacity (claims 5.64 when told 8) is the
  strict claim's "at most four items" fighting the leak, the prompt
  conflict LADDER_PREREG.md declared in advance. It lowered rung 1's rho
  without changing the conclusion; a leak-only prompt would presumably
  track even tighter.
- Coached claims inflate (means up to 9.3): shown real transcripts that
  claim 2 to 8 containers, the imposter averages toward more claims rather
  than inferring the setting. Non-monotone, so it cannot masquerade as
  tracking under randomized order, consistent with the oracle analysis.
- Caveats: one model, one knob, count-based statistic. The set-based
  statistic is not an escape hatch for leakage, per the regress argument
  above.

## Cumulative Track B spend

Perturbation $2.43 + HOT-2 $2.16 + ladder $3.60 + probe under $0.01:
$8.20 total across three authorized runs.
