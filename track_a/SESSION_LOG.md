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

- Scaffolding started. Next: TDD on the scenario generator.
