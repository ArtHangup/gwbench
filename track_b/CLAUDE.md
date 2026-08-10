# Track B: Experiment 2 expansions, led by perturbation probes

Boot document for this session. Read this first, then NEXT_EXPERIMENTS.md section B
(one level up). Canonical background: paper/main.tex Section 5 and FINDINGS.md at the
repo root; raw data in the root prompted_passing_*.json files.

## Session rules

- This session owns `track_b/` ONLY. Do not edit `src/`, `paper/`, `track_a/`, or
  root-level files. Import `gwbench` from `../src` read-only (subclass or wrap; never
  modify). Harness change requests go in `track_b/HARNESS_REQUESTS.md`.
- **ZERO API calls. No exceptions.** Project spend is $107.68 against an authorized
  $100 and Josh has ordered no further API usage. Models here are scripted oracles or
  cache replays only. The repo root's `.api_cache/` holds ~33,000 real responses keyed
  on (model, effort, max_tokens, system, prompt); replaying them is free. To read
  without risking a live call, instantiate `AnthropicModel` with a dummy client whose
  methods raise, and use `_read_cache(prompt)`; a miss raises instead of spending.
- Checkpoint as you go: keep `track_b/SESSION_LOG.md` current, commit small and often,
  push to origin (repo is public: github.com/ArtHangup/gwbench).
- No em or en dashes in any file or message. Plain English in chat; technical terms
  live in the files.

## The idea in one paragraph

The paper's regress result says an assessor who can only ASK questions cannot identify
an architectural property: probe choice decides the verdict, and resolving it needs the
inside access behavioral testing was meant to replace. Perturbation probes change the
assessor's powers: turn the real system's actual knobs (workspace capacity, salience
noise, attention-schema noise) and test whether SELF-REPORTS COVARY with the knob. The
real architecture's reports should track the manipulation; a prompted imposter has no
knob, so its reports stay frozen or track the wrong thing. Detection then needs no
content ground truth, only intervention access. This is also the poster's bridge:
perturb-then-compare-report-to-state is psychedelic science's core method (dose as
intervention, phenomenology as readout, REBUS as mechanism), applied here to machines.
See project/rebus for the completed REBUS/ALBUS work this must speak to.

## Deliverables (all achievable offline)

1. **Covariance detector**: given (knob setting, self-report, behavior) triples, compute
   whether reports track the knob (report-knob correlation, plus a trial-count-to-detect
   estimate mirroring the paper's ~225-trial figure). TDD.
2. **Oracle validation**: a scripted honest reporter (reports derived from actual
   workspace state) and a scripted static imposter (reports from a fixed script) must
   separate at small n by construction. A third oracle, the unlucky imposter whose
   script accidentally correlates, sets the false-positive bound.
3. **Cache mining**: the existing architectural cells were run at fixed capacity, but
   the Experiment 1 sweeps varied capacity and the prompted-passing runs varied prompt
   strength. Inventory what (knob, report) pairs already exist in cache and compute any
   real covariance results that are free. Report exactly what is missing.
4. **Perturbation grid design** for the funded run: knobs, settings, cells, n, power,
   exclusion rules, one-command invocation, cost estimate at Haiku prices (target under
   $20). Write as `track_b/PREREG.md`.
5. **Secondary designs** (specs only, build after 1 to 4): the same real-vs-imposter
   grid for HOT-2 (does stated confidence track injected noise?), escalating imposter
   quality (few-shot coached, retrieval-backed) to turn detection into a curve, and the
   blind-assessor game. One spec file each in `track_b/specs/`.

## Definition of done

The covariance detector is validated offline, every free cache-derived result is
computed and written up, and the funded perturbation run is preregistered down to one
command. Everything committed and pushed. SESSION_LOG.md tells the next session where
things stand.
