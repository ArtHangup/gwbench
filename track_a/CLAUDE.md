# Track A: the conflict-and-recruitment experiment (GWT-3 / GWT-4)

Boot document for this session. Read this first, then NEXT_EXPERIMENTS.md section A
(one level up) for the full design rationale. Canonical background: paper/main.tex and
FINDINGS.md at the repo root.

## Session rules

- This session owns `track_a/` ONLY. Do not edit `src/`, `paper/`, `track_b/`, or
  root-level files. Import `gwbench` from `../src` read-only; if the harness needs a
  change, write the need into `track_a/HARNESS_REQUESTS.md` instead of editing.
- **ZERO API calls. No exceptions.** Project spend is $107.68 against an authorized
  $100 and Josh has ordered no further API usage. Every model in this track is either
  a scripted oracle or a cache replay. To read the existing cache without risking a
  live call, instantiate `AnthropicModel` with a dummy client object whose methods
  raise, and call its `_read_cache(prompt)`; a miss raises instead of spending.
- Checkpoint as you go: keep `track_a/SESSION_LOG.md` current, commit small and often,
  push to origin (repo is public: github.com/ArtHangup/gwbench).
- No em or en dashes in any file or message. Plain English in chat; technical terms
  live in the files.

## The experiment in one paragraph

Baars says the workspace is for novelty, conflict resolution, and recruiting
specialists, not for filtering junk. So: four to six specialist modules (perception,
memory, goals, risk, social), each holding PRIVATE evidence about a shared scenario.
Every statement they emit is legitimate; the situation decides relevance (no
matter/decoy labels anywhere in the design; that was Experiment 1's mistake). Tasks are
text decisions (triage, planning, negotiation), split routine vs novel, where novel
means modules genuinely conflict or a practiced pattern fails. Architectures: (A) full
GWT loop with broadcast back to modules, (B) hub-only workspace with no broadcast back
(ablates GWT-3), (C) flat concatenation. Dependent variables, in priority order: module
revision after broadcast, recruitment sequences on multi-step problems, decision
quality on novel vs routine. The first two are not accuracy, so model ceilings cannot
erase them.

## Deliverables (all achievable offline)

1. **Scenario generator** with controlled ground truth: each scenario fixes the correct
   decision, which module subset is needed, and whether it is routine or novel.
   Property-based tests on the generator's invariants.
2. **Module framework and the three architectures**, built TDD against scripted oracle
   modules (deterministic emitters with configurable conflict) and an oracle controller.
3. **Offline validation run**: with oracle modules, architecture A must show revision
   and orderly recruitment, B must show zero revision (it is an ablation), C must show
   neither. This verifies the pipeline and the DVs discriminate by construction, no
   model needed.
4. **Grading spec**: rubric for free-text decisions, judge-model protocol, and the
   hand-graded calibration subset design (n=100). Build the rubric and the parser now;
   the judge runs later.
5. **Preregistration** (`track_a/PREREG.md`): hypotheses, cells, n per cell, power
   analysis, exclusion rules, and the exact one-command invocation for the funded run,
   with a cost estimate at Haiku prices (target: first readable result under $25).

## Definition of done

A fresh session could run the funded experiment with one command and no design
decisions left. Everything committed and pushed. SESSION_LOG.md tells the next session
where things stand.
