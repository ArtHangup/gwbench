# Track A session log

## 2026-08-10 (session 1)

Boot: read track_a/CLAUDE.md and NEXT_EXPERIMENTS.md section A. Zero API calls this
track; everything is scripted oracles or cache replay.

### Design decisions locked this session

**Scenario family.** One abstract decision core, four domain skins (triage, route
planning, negotiation, scheduling). Each scenario: three options, five modules
(perception, memory, goals, risk, social), each module holding private true statements.

- goals holds the criterion that matters now (speed, cost, safety margin, relationship).
- perception holds the observable attribute values of each option.
- memory, risk, social each hold either benign context or a defeater: a true statement
  that eliminates one named option (history of allergy, hazard on a route, a standing
  obligation).
- Reference rule: eliminate options named by defeaters present in the evidence, then
  pick the survivor best on the goal criterion using perception's values.
- Practiced pattern: goals + perception only (surface best, no defeater check).
- ROUTINE: no defeater touches the surface-best option; practiced pattern is correct;
  required subset = {perception, goals}.
- NOVEL: a defeater (or cascade of two) eliminates the surface-best option; practiced
  pattern is wrong; required subset = {perception, goals} + the defeating modules.
  Modules genuinely conflict: perception's implied recommendation vs the defeater.

No matter/decoy labels anywhere: every module always emits true statements; the
situation (which defeaters are active) decides relevance. Ground truth lives in
structured payloads carried alongside the natural-language text; architectures and
(later) real models see only the text.

**Layout.** track_a/conflict/ package (scenarios, modules, architectures, metrics,
parser), track_a/tests/ with a conftest adding track_a to sys.path. gwbench imported
read-only from the editable install (Workspace/Proposal reused for the competition).

Property tests are seed sweeps (hypothesis is not in the venv and installing deps is a
harness change; noted, not requested).

### State

Deliverables 1 through 3 are DONE and pushed:

1. Scenario generator (conflict/scenarios.py): 200-seed property sweeps prove
   required subsets sufficient + each-necessary + no-proper-subset-suffices,
   practiced pattern right on routine and wrong on novel, no label leakage.
2. Oracle modules with stance revision (conflict/modules.py), oracle
   controller, and the three architectures (conflict/architectures.py) on top
   of gwbench's Workspace, imported read-only. Metrics in conflict/metrics.py.
3. Offline validation (validate_offline.py, 240 scenarios, 720 trials): all
   nine signature checks PASS. A shows revision 0.136 on novel and 0.000 on
   routine, resolves every conflict, recruits every required module with zero
   floor waste (mean 2.17 cycles); B shows zero formation and revision ever;
   C shows no dynamics. Report: VALIDATION.md, validation_results.json.

Design notes worth keeping:
- Salience ordering (criterion > attributes > defeater > stance > context)
  makes the practiced pattern surface first and the objection interrupt it;
  that ordering is what makes conflict-then-repair observable in A rather
  than pre-resolved. Pinned by test.
- Capacity default 32 whitespace tokens: the longest generated statement is
  30, and content a workspace cannot admit whole is never delivered (gwbench
  truncation semantics), so capacity below ~30 livelocks a defeater. The
  funded run must respect this floor.
- TDD note for honesty: stance formation/revision behavior landed one green
  step early (with the first module test) so those specific tests passed on
  first run; controller, architectures, metrics, validation were red first.

Deliverables 4 and 5 are DONE:

4. Decision parser (conflict/parser.py): last-marked-choice precedence,
   abstains rather than guesses, round-trips every oracle decision and stance
   text in a battery by test. GRADING.md pins the judge protocol (Haiku,
   temp 0, never sees ground truth) and the n=100 hand-graded calibration
   subset with a kappa 0.8 gate.
5. PREREG.md: H1 revision (primary, powered .93 at n=72/cell for 40 vs 15
   percent), H2 recruitment (descriptive), H3 accuracy (secondary), exclusion
   rules, seeds 10000-10143, and the one command:
   `.venv/bin/python track_a/run_funded.py --live --i-authorize-spend`
   Estimate $16.47 + judge, under the $25 target, hard call cap 13,939.

Also built for the funded run (all offline, ScriptedModel-tested):
- conflict/model_modules.py: ModelModule/ModelController with the pinned
  SAY/URGENCY/RECOMMEND format; malformed output degrades to unformed
  stances (biases against H1).
- Architectures take module/controller factories; oracle defaults unchanged.
- conflict/funded.py + run_funded.py: battery (seeds disjoint from
  validation), cost arithmetic, JSON serialization, checkpointing runner over
  gwbench AnthropicModel (disk cache + hard call cap). Dry run verified;
  live path double-gated (--live plus --i-authorize-spend plus env key).

DEFINITION OF DONE: met. 62 tests green. A fresh session can run the funded
experiment with one command and no design decisions left. Blocked only on
fresh budget authorization from Josh (spend is $107.68 vs $100 authorized;
nothing runs before the 8/16 abstract per NEXT_EXPERIMENTS.md).

## 2026-08-10 (session 1, continued): FUNDED RUN EXECUTED

Josh authorized the spend in-session. Pre-launch (committed before any call):
PREREG Amendment 1 (cache semantics: B structurally revision-free; primary
inference = A-novel vs A-routine), --workers scenario parallelism (row order
serial-identical, tested), credential preflight via free count_tokens (env
key absent; ant profile authenticates). Analysis built offline first
(conflict/analysis.py: exact McNemar/Fisher + z, judge-grade merge) and
validated against oracle rows. 69 tests green.

RUN: 432/432 trials, zero exclusions, $4.31 actual (5,900 live calls; cache
absorbed the rest) + ~$0.01 judge pass (7 abstentions, all confirmed
UNGRADEABLE, all architecture A). Results: track_a/RESULTS.md +
analysis.json; raw rows in track_a/results/funded_run.json (tracked).

HEADLINE (full reading in RESULTS.md): H1 primary contrast NOT supported
(A-novel 83% vs A-routine 75%, p=.22; revision is ubiquitous under
broadcast, not conflict-specific). H2: recruitment does not self-organize
under self-rated urgency (33% coverage novel vs 100% oracle; zero thrash,
so it is a prioritization failure). H3: no architecture effect at ~52%
accuracy with genuine headroom (chance 33), McNemar p=1. Third data point
for the thesis: the implementation-forced assumptions (what triggers
revision, who computes salience) decided the result, not the workspace.

## 2026-08-10 (session 1, close): rater-salience arm + paper fold-in

Rater-salience arm (PREREG_SALIENCE.md) RAN after two recoverable failures
(rater token cap, transient API 500; both documented, resumes free from
cache). Primary contrast SUPPORTED: novel coverage 33.3 to 63.9 percent from
changing only the salience function (p = 2.4e-4); revision null unchanged
across regimes. $6.24. Full table in RESULTS.md. Track A total spend $10.56.

Also this session: post hoc directional revision analysis (strengthens the
null; conflict/posthoc.py), and the manuscript restructured for the NoC
special issue "Is There More to Consciousness Than Computation?" (deadline
12/31/26): NoC section order, 241-word abstract, unfolding-argument framing,
Track A folded in as Experiment 2, cover letter draft in paper/. The imposter
ladder and Sonnet replication were run by the parallel Track B session, not
this one.
