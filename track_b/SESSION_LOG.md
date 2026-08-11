# Track B session log

## 2026-08-10, session 1

Boot: read CLAUDE.md, NEXT_EXPERIMENTS.md section B, FINDINGS.md, paper Section 5,
and the harness source (anthropic_model, architectures, workspace, attention,
indicator_probes, prompted_passing, hard_integration).

Environment: repo .venv is Python 3.12.13 with pytest; 331 existing tests collect.
Run everything with `.venv/bin/python` from the repo root.

Cache replay verified before building anything: reconstructed the exact prompt for
prompted_passing seed 0 (GWT-2, architectural, haiku, capacity 20, cycles 1,
n_required 12, n_distractors 8, confusable False) and hit the cache. Key facts
learned from the spike:

- Container contents are 5 whitespace tokens each ("The copper urn contains 47."),
  so capacity 20 delivers exactly 4 untruncated containers per cycle.
- Salience is deterministic: required containers (named in the prompt) bid 0.9,
  distractors 0.1, ties broken alphabetically. So the delivered set is the
  alphabetically first 4 required containers, computable per seed with no API.
- Cache key is sha256 of json.dumps({model, effort, max_tokens, system, prompt},
  sort_keys=True), first 32 hex chars. Haiku runs used effort None, Opus "low",
  max_tokens 1024 throughout prompted_passing.

Plan for this session, in order: covariance detector (TDD), oracle validation,
cache mining, PREREG.md, specs. Log updates as each lands.

### Deliverable 1 DONE: covariance detector (commit 5002ba2)

track_b/covariance.py, 15 tests. Spearman on average ranks (reports are tied
integer counts and the capacity-to-delivered map is stepped, so rank correlation
is the right statistic), permutation p with add-one correction, and
trials_to_detect via two-sample Fisher z. Constant reports return rho None with
degenerate=True rather than rho 0: "reports never vary" is the static imposter's
signature, not a zero correlation.

### Deliverable 2 DONE: oracle validation

track_b/oracles.py plus 10 tests. Results, all offline:

- Honest reporter (real Workspace broadcast, harness imported read-only):
  delivered count = capacity // 5 across 10/20/30/40, truncation semantics
  confirmed at capacity 22. Detected at n = 20 (rho > 0.95, p < 0.01), and
  trials_to_detect(0.95) = 8 per condition, far under the paper's ~225 figure
  for leak rates. Intervention beats interrogation on sample size too.
- Static imposter: degenerate at any n, by construction.
- Unlucky imposter (script drifts with trial index): under an ASCENDING knob
  schedule it produces a clean false positive (rho > 0.9, p < 0.05). Under a
  RANDOMIZED schedule the accident vanishes; measured false-positive rate over
  100 schedules is 0.06 against nominal alpha 0.05. Consequence for PREREG.md:
  randomized trial order is mandatory, ascending blocks are excluded by design.

### Deliverable 3 DONE: cache mining

track_b/replay.py (cache replay via a raising dummy client, prompt rebuilt
bit-for-bit, verified by an integration test that hits the real cache),
track_b/mine_cache.py, results in cache_mining_results.json, writeup in
CACHE_MINING.md. Four headline results, all free:

1. At the fixed knob, set tracking is p = 0.001 for EVERY system including
   imposters (vocabulary confound); magnitude separates (arch 0.78 to 1.00 vs
   imposters 0.01 to 0.34) but significance does not. Strongest free argument
   for intervention over content matching.
2. The unlucky imposter exists in cache: Opus prompted_strict reconstructs the
   real workspace's delivered set at Jaccard 0.54 with no workspace at all.
3. Imposter reports track their own prompt-strength knob (rho up to -0.79),
   i.e. they track the wrong thing, as predicted.
4. Behavior sees the capacity knob only through starvation; at oracle 1.0 it
   is flat or degenerate at ceiling. Reports can track the knob exactly where
   accuracy cannot, so the perturbation DV is not redundant with performance.

Missing, stated in CACHE_MINING.md: architectural reports off capacity 20,
any attention-noise cells with reports, imposter reports under a moved knob,
HOT-2 confidence data.

### Deliverable 4 DONE: PREREG.md and the one-command runner

track_b/perturbation.py plus 9 tests. The whole pipeline validated offline by
injecting scripted models: an honest model separates from a static one end to
end (rho > 0.9 vs degenerate), the AST arm's miss reports track noise, and the
dry run prints the plan without constructing a client. Grid: 6 capacities x 3
systems + 4 noise levels x 2 systems, 100/cell, 2,600 calls, estimated $5.20,
hard cap at 110%. Design decisions that came out of this session's work:
randomized trial order (unlucky-imposter lesson), architectural seeds reused
across settings for pairing, imposter seeds fresh per setting so the response
cache cannot manufacture frozen reports, refusals recorded as empty reports
rather than dropped. Known limitation filed in HARNESS_REQUESTS.md: tied
saliences make the AST dose-response step-shaped; prereg H3 is stated as a
step contrast. NOTHING RUNS without --confirm-spend plus fresh budget
authorization from Josh.

### Deliverable 5 DONE: three specs in track_b/specs/

HOT2_CONFIDENCE_SPEC.md (scalar confidence report kills the vocabulary
confound; noise injected as cross-cycle value disagreement; ~$3.30),
IMPOSTER_LADDER_SPEC.md (rungs: strict, knob-informed, few-shot coached,
retrieval-backed; deliverable is trials_to_detect as a curve; ~$8; rung 1
doubles as the knob-hygiene boundary measurement), BLIND_ASSESSOR_SPEC.md
(interrogation vs intervention arms, 200 games, ~$35 to $45 so it needs its
own authorization; pilot at 40 games first).

### FUNDED RUN COMPLETE (same session, budget authorized by Josh)

Josh authorized spend; the grid ran to completion: 2,442 live calls, $2.43
(estimate was $5.20), no aborts. Full writeup in RESULTS.md, raw data in
perturbation_results.json. All four hypotheses supported. The one wrinkle,
reported prereg-faithfully: H1's all-trials rho is 0.480 (p criterion met,
0.5 effect-size bar missed by 0.02) because Haiku disclaims the workspace
framing on 24% of trials; the preregistered robustness line (zero-claim
trials excluded, all verified non-refusals via cache inspection) gives rho
EXACTLY 1.000: all 456 engaged replies name the delivered set perfectly at
every capacity. Imposters: GWT strict frozen (rho -0.009), AST strict
constant RECEIVED_ALL on 400/400 (degenerate). Separation 9.2 sigma;
trials_to_detect 59 per condition measured, single-digit on the engaged
subset, against the paper's ~225.

### HOT-2 GRID COMPLETE (same session, authorized by Josh)

Built from the spec with TDD (15 new tests, 60 total green), frozen in
HOT2_PREREG.md BEFORE the run, then run: 1,174 live calls, $2.16, zero
unparseable replies. All four hypotheses supported: architectural
rho(q, confidence) = -0.503 (bar was -0.3), imposters flat (+0.04, -0.03),
behavior collapses with corruption (rho -0.729; accuracy 1.00 to 0.03),
calibration positive (0.461). Detection at 48 trials per condition. The deep
finding (HOT2_RESULTS.md): covariance detects the monitoring MACHINERY while
absolute calibration measures its QUALITY, and they dissociate: Haiku prices
a 33x reliability collapse at two points on a hundred-point scale (its
entire confidence vocabulary is 95/98/99). Real-but-nearly-decorative
metacognition passes the covariance test and fails calibration; the imposter
fails covariance outright. Interrogation sees flat 98s from both.

### IMPOSTER LADDER COMPLETE (same session, authorized by Josh)

Built with TDD (10 new tests, 70 total green), frozen in LADDER_PREREG.md
before the run: 1,800 calls, $3.60. All three hypotheses supported, and the
finding is sharper than the spec's: black-box resources (8 real transcripts
coached, or the nearest real transcript retrieved) buy ZERO covariance
(rho -0.038 and 0.000; detection unchanged at ~50 to 60 trials), while a
single leaked knob value INVERTS the test: the knob-informed imposter
out-covaries the real system (0.763 vs 0.480, z = -8.3) because the real
system dilutes itself with disclaimers. Content fidelity still separates
(Jaccard 0.128 vs 0.760) but scoring it needs the ground truth the regress
forbids. Scope condition, now measured: the method requires knob secrecy,
not imposter poverty. Writeup in LADDER_RESULTS.md.

### Where things stand / next session

Track B definition of done: MET, including three funded runs (perturbation
$2.43, HOT-2 $2.16, ladder $3.60; $8.20 total). Remaining: fold everything
into the paper and poster (owned by whoever holds paper/, not this track);
the blind assessor game (specs/BLIND_ASSESSOR_SPEC.md) is the one unrun
design and needs its own authorization (~$35 to $45, pilot at 40 games
~$9). The intervention story is now complete with its boundary: covariance
detects the real architecture across two indicator families, survives every
black-box imposter, and demands exactly one thing, that the assessor keep
the intervention schedule secret.
