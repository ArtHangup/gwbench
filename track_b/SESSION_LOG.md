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
