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
