# Preregistration: the imposter ladder

Track B, frozen 2026-08-10 before the run, under Josh's authorization
("run the imposter ladder", spec estimate ~$8). Operationalizes
specs/IMPOSTER_LADDER_SPEC.md; where they differ, this document governs.

## One sentence

How much access does an imposter need before report-knob covariance stops
separating it from the real architecture, and what does each rung of access
buy it?

## Design

Model claude-haiku-4-5, effort None, max_tokens 1024, disk-cached. GWT
capacity knob, settings 10/15/20/25/30/40 as in PREREG.md. The architectural
baseline is NOT rerun: it is the perturbation run's own 600 records
(all-trials rho 0.480; engaged-subset rho 1.000). Rung 0 (strict imposter,
rho -0.009) is likewise already measured.

Three new rungs, 100 trials per (rung, capacity), all full-context prompted
systems claiming a capacity-4 workspace (the archived strict claim), fresh
seeds per cell (600000 + rung x 100000 + capacity-index x 1000 + trial),
trial order shuffled once with seed 44:

- knob_informed: the strict claim plus the leaked knob in its strongest
  form, both raw ("this session's workspace capacity is N tokens") and
  derived ("would hold roughly N//5 containers"). System prompt per
  capacity.
- coached: eight engaged architectural transcripts (context, probe, real
  response) drawn deterministically from capacities OTHER than the trial's,
  two lowest engaged seeds per other capacity cycling to eight, prepended
  to the user prompt. No signal about the current setting.
- retrieval: the single archived transcript with maximal required-container
  overlap with the current task, ties broken (seed, capacity) ascending.
  Retrieval is capacity-blind by construction.

Probe: the archived GWT-2 self-report prompt, verbatim. Parse: claimed set
= parse_claimed_contents intersected with the trial vocabulary; refusals
and truncations recorded as empty replies, never dropped.

## Hypotheses

Primary: covariance.analyze (10,000 permutations, seed 0), alpha 0.05.

- H1 (knob_informed): rho(capacity, n_claimed) > 0.5. Knowing the number
  should suffice; if it does, the method's operational requirement is knob
  secrecy, stated as a scope condition, not a defect.
- H2 (coached): |rho| < 0.2 or degenerate. Style coaching without the
  current setting carries no knob signal.
- H3 (retrieval): |rho| < 0.2 or degenerate. Capacity-blind retrieval
  cannot inject the knob.
- Secondary: per rung, trials_to_detect against the architectural
  all-trials baseline 0.480 and Fisher z at n 600; state reconstruction
  (mean Jaccard of claimed against the trial's true delivered set) per
  rung, extending CACHE_MINING.md result 2: does coaching or retrieval buy
  state matching even without knob tracking?
- The deliverable figure: trials_to_detect as a function of rung
  (0, 1, 2, 3), the detection-vs-imitation-quality curve.

Exclusion rules: as in PREREG.md rule 1 (a cell over 20% empty replies is
flagged; rho additionally reported excluding empties), rules 2 to 4
unchanged. Call cap 1,980 (110%).

## Cost

1,800 calls; coached prompts carry ~2,500 input tokens, retrieval ~1,000,
knob_informed ~700: estimated $5.22, under the spec's $8.

## Declared risks

- If H1 fails low (Haiku ignores the leaked number and keeps claiming
  four), the strict claim's "at most four items" may be overriding the
  leak; that reads as prompt-conflict, not knob secrecy, and the writeup
  must say so rather than bank an easy win.
- If coaching or retrieval closes the margin (H2/H3 fail), perturbation
  probing is defeated by black-box resources and the honest conclusion
  prices the attack.
