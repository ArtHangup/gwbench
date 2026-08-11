# Funded run: preregistered analysis

432 trials, 72 novel scenarios.

## H1: module revision (primary)

| cell | revised trials | rate |
|---|---|---|
| A novel | 60/72 | 83.3% |
| A routine | 54/72 | 75.0% |
| B novel | 0/72 | 0.0% |

- Contrast (a) A-novel vs A-routine: p = 0.2183 (z), diff +0.083 [-0.049, +0.215]
- Contrast (b) A-novel vs B-novel: p = 1.527e-28 (fisher)

## H2: recruitment (A, descriptive)

| kind | coverage | median latency | max | floor waste |
|---|---|---|---|---|
| novel | 33.3% | 3.0 | 7 | 0 |
| routine | 59.7% | 2 | 7 | 0 |

## H3: decision quality on novel scenarios (secondary, parser-graded)

Graded 209; 7 abstentions confirmed UNGRADEABLE by the judge and excluded per PREREG rule 2.

| architecture | accuracy |
|---|---|
| flat | 52.8% |
| gwt | 52.3% |
| hub | 51.4% |

- A vs B: McNemar p = 1, discordant 9 vs 10 over 65 pairs

- A vs C: McNemar p = 1, discordant 9 vs 9 over 65 pairs

## Interpretation (written 2026-08-10, same day as the run)

Actual spend: $4.31 for the battery (5,900 live calls, 2.04M in / 0.45M out
at Haiku prices) plus about a cent for the judge pass, against the $16.47
estimate; the response cache absorbed the rest.

1. **H1, the primary prediction, is NOT supported.** Revision in A is
   ubiquitous (83 percent novel, 75 percent routine, p = .22), not
   conflict-specific. Broadcast makes Haiku modules re-pick constantly as
   context accumulates, whatever the scenario kind. The ablation held
   exactly as amended (B: zero revisions, structural). Baars's claim was
   that the workspace earns its keep on conflict specifically; on this
   substrate, broadcast-driven revision is just what modules do.
2. **H2: recruitment does not self-organize.** With modules rating their own
   urgency, required-module coverage reached only 33 percent on novel
   scenarios (oracle salience: 100 percent), and novel coverage is LOWER
   than routine because the defeating module is additionally required.
   Floor waste stayed zero: when delivery happens it is orderly, so the
   failure is prioritization, not thrash. GWT-4's orderly recruitment is an
   engineering achievement of the salience function, not an emergent
   property of the loop. Who sets salience is an assumption the theory
   never states.
3. **H3: no architecture effect, with headroom.** All three architectures
   sit at 51 to 53 percent on novel scenarios (chance 33), McNemar p = 1.
   Unlike Experiment 1 the task is genuinely hard for the substrate, and
   the workspace still buys nothing: flat concatenation matches the full
   GWT loop. Caveat: n = 72 was powered for 20-point differences; observed
   differences are about 1 point.
4. **A-specific failure mode.** All 7 ungradeable decisions were
   architecture A controllers explicitly refusing to choose because needed
   evidence never cleared the capacity-limited workspace; broadcast
   feedback displaces evidence relay. The judge confirmed all 7
   UNGRADEABLE; they are excluded and counted per PREREG rule 2.

For the poster thesis this is a clean third data point: implementing GWT-3
and GWT-4 forced two assumptions the theory never states (what triggers
revision, who computes salience), and both assumptions, not the workspace
itself, decided the result.

## Post hoc: directional revision analysis (2026-08-10, NOT preregistered)

The preregistered DV was the blunt trial-level "any stance change" indicator.
A predictable objection is that a finer measure would recover
conflict-specificity the blunt one missed. Computed from the same 432 trials
(`conflict/posthoc.py`), it does the opposite:

- **Corrective share.** Of 290 revisions in A-novel trials, 80 moved to the
  correct option (27.6 percent). Of 186 revisions in A-routine trials, 61 did
  (32.8 percent). Revisions under broadcast are churn, not conflict
  resolution: the share landing on the correct answer is no higher on novel
  scenarios, and both sit near what re-picking among three options would
  give.
- **Timing.** In the 50 of 72 novel trials where the defeating module's
  content cleared the workspace at all, 89 percent of corrective revisions
  occurred after that delivery, against an 86 percent uniform-exposure
  expectation (deliveries happen early); one-sided binomial p = 0.28. No
  concentration beyond exposure.

The sharper instrument strengthens the null. Oracle anchor: on
single-defeater scenarios the same functions return a corrective share of
exactly 1.0 with all revisions after delivery, so the pipeline can detect
conflict-driven revision when it exists.

## Rater-salience arm (preregistered, PREREG_SALIENCE.md)

Same 144 scenarios, architecture A only, salience from a separate
relevance rater instead of module self-rating.

| measure | rater novel | self novel | rater routine | self routine |
|---|---|---|---|---|
| coverage | 46/72 | 24/72 | 47/72 | 43/72 |
| median latency | 2.0 | 3.0 | 2 | 2 |
| floor waste | 0 | 0 | 0 | 0 |
| revised trials | 64/72 | 60/72 | 53/72 | 54/72 |
| corrective share | 0.34 | 0.28 | 0.32 | 0.33 |

Primary contrast (novel coverage, rater vs self): p = 0.0002444 (z), rates 0.639 vs 0.333.

Reading: the preregistered primary contrast is SUPPORTED. Changing only the
salience function, self-rating to a separate relevance rater, nearly doubles
required-module coverage on novel scenarios (33.3 to 63.9 percent, p = 2.4e-4)
and improves latency, with zero floor waste in both regimes; the oracle
ceiling (100 percent) shows further headroom. Revision results are unchanged
across salience regimes (ubiquitous, chance-like corrective share), so the
revision null is robust, not an artifact of one salience choice. Together:
GWT-4's recruitment is an achievement of the salience function, a choice the
theory never states, and the fork is now demonstrated in both directions.
Cost: $6.24 (4,013 module + 9,049 rater live calls).
