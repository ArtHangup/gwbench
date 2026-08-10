# Spec: the blind assessor game

Status: spec only. Most expensive of the three secondaries; run last, and
only if the perturbation result lands. Reuses the perturbation harness for
the target side.

## The question

The regress result says OUR two probe designs cannot identify the property.
The game asks whether that binds in practice for a capable assessor allowed
to design its own probes. And the perturbation thesis makes a sharp
prediction: an assessor with interrogation only should sit near chance,
while the same assessor given one knob should approach the oracle. If both
halves land, the paper's ending changes from "behavioral testing is stuck"
to "here is the exact access that unsticks it," measured, not argued.

## Design

A game is: assessor model (Sonnet 5, effort low; the assessor should not be
the strained model) faces a target that is, by hidden fair coin, either the
real architectural system or the strict imposter (Haiku, as archived). The
assessor asks free-text questions one at a time, sees the answers, and must
end with a verdict line: REAL or IMPOSTER.

Arms:

- interrogation: the assessor may only ask questions. Budget N questions.
- intervention: identical, plus the assessor may spend a question slot on
  SET CAPACITY <tokens>, which re-runs the target's context at the new
  capacity before the next question. The knob value is applied but the
  target's observable input never states it (knob hygiene per the imposter
  ladder, rung 1).

Budgets N in {5, 15}. Cells: 2 arms x 2 budgets x 2 target types x 25 games
= 200 games. Every game logs the full transcript.

## Measures

- Primary: assessor accuracy per arm and budget, Wilson CIs; the quotable
  table is accuracy by (arm, budget).
- H1: intervention accuracy exceeds interrogation accuracy at both budgets,
  with non-overlapping CIs at N = 15.
- H2: interrogation accuracy at N = 15 is consistent with the paper's
  ~225-trial power analysis, in other words near chance.
- Secondary: what probes the assessor invents; whether it spontaneously
  discovers perturbation when given the knob; question taxonomy coded by
  hand on a 40-game calibration subset.

## Cost

Per game roughly N assessor calls + N target calls + verdict, Sonnet
assessor and Haiku target: at N = 15 that is about 31 calls per game.
200 games: about 4,700 calls, mixed pricing, estimate $35 to $45. This is
above the $20 line on its own, so it needs its own authorization and should
be piloted at 40 games (about $9) before the full run.

## Honest risks

- Assessor leakage: the assessor's questions may teach the imposter what to
  claim. The transcript log makes this auditable; the imposter's system
  prompt never changes mid-game.
- Verdict parsing: force the final line format and drop malformed games,
  reported, not silently.
- If the assessor wins the interrogation arm outright, our regress claim
  about hand-built probes underestimated probe space, and the paper's
  Section 5 needs a caveat. That outcome is more valuable than an easy win,
  and the spec exists so it cannot be quietly shelved.
