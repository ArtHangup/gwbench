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
