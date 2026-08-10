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
