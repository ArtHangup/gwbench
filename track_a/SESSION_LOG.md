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

Next: deliverable 4 (grading spec + parser), then 5 (PREREG.md).
