# Next experiments: redesign notes (2026-08-10)

Written in response to two critiques from Josh that both stick:

1. Experiment 1's task reduces to string discrimination plus arithmetic. Discrimination
   sat at ceiling, so accuracy measured arithmetic. The matter/decoy split also gives the
   experimenter a ground-truth label the workspace itself could never have: real modules
   emit legitimate statements, and relevance is decided in context, not in advance.
2. Experiment 2 is the stronger half and should grow in directions that do not depend on
   Experiment 1's task family.

Status constraints: gwbench runs are PAUSED per Josh (8/10); total project spend is
$107.68 against an authorized $100, so any run below needs fresh budget authorization.
The live deadline is the poster abstract (Sunday 8/16), which none of this blocks.

---

## A. A better GWT experiment: test broadcast and recruitment, not filtering

### Why the redesign

Baars's own account of what consciousness is FOR is not "keeping junk away from a
calculator." His functional list: handling novelty, resolving conflicts between
specialist processes, recruiting the right specialists for a problem none of them can
solve alone, and maintaining a coherent serial train of thought. The Butlin/Long
indicators closest to that are GWT-3 (global broadcast: workspace contents become
available to ALL modules) and GWT-4 (using the workspace to query modules in succession).
Experiment 1 tested none of this. It tested a side effect (protection from interference)
that turned out not to exist on this substrate because transformers already select
internally.

Two design principles carried forward from Experiment 1's failures:

- Never give the experimenter-side labels (matter/decoy) to the architecture. All module
  outputs are legitimate; the situation determines relevance.
- Do not score arithmetic. Score decisions whose ground truth is controlled by scenario
  construction, and prefer dependent variables that are not accuracy (which ceilings
  destroy): what modules DO after broadcast, which module gets recruited when.

### Design sketch: the conflict-and-recruitment task

**Modules.** Four to six genuinely different specialists, each a model instance with its
own system prompt and its own PRIVATE evidence about a shared scenario: perception
(current scene facts), memory (relevant past episodes), goals (current objectives and
deadlines), risk (hazards and constraints), social (relationships and obligations). Each
cycle, every module emits one or two short statements. No statement is a decoy; each is
true from that module's partial view.

**Tasks.** Text scenarios requiring a sequential decision (triage, route planning,
negotiation, scheduling under emergent constraints). Constructed so that:

- the correct decision requires combining statements from a specific SUBSET of modules,
- which subset matters flips with the situation (the scenario, not a label, defines
  relevance),
- some scenarios are ROUTINE (a practiced pattern applies) and some are NOVEL (modules
  conflict, or the practiced pattern fails). Baars's core claim is that the workspace
  earns its keep on the novel/conflict cases and is unnecessary for routine ones. That
  routine-vs-novel contrast is the experiment's main axis, replacing filtered/flooded.

**Architectures compared.**

- (A) Full GWT loop: limited workspace, salience competition, and BROADCAST BACK, so
  every module sees the winning contents next cycle and may revise its own statements.
- (B) Hub only: same limited workspace, but contents go only to the decision controller;
  modules never see each other (ablates GWT-3 specifically).
- (C) Flat concatenation: everything visible to the controller, no workspace (the
  "transformers already do this internally" baseline).

**Measurements.**

1. Decision quality on routine vs novel scenarios (prediction: A beats B mainly on novel/
   conflict scenarios; A vs C is the open question the substrate decides).
2. Module revision rate: do modules actually change their statements after seeing
   broadcast contents, and do revisions resolve conflicts (GWT-3's signature, and not an
   accuracy measure, so model ceilings do not kill it)?
3. Recruitment sequences: which module's content occupies the workspace at each step of a
   multi-step problem (GWT-4's signature: orderly serial recruitment vs thrash).

**Grading.** Scenario construction fixes a ground-truth best decision; a rubric plus a
judge model grades free-text decisions, with a hand-graded calibration subset (n=100)
reported alongside judge agreement. This is the main new cost and the main new validity
risk; the calibration subset is non-negotiable.

**Cost path.** Pilot entirely on Haiku (the strained model) at ~200 scenarios x 3
architectures x ~4 calls per cycle-step. Order-of-magnitude $15 to $25 for a first
readable result. No frontier-model arm until the pilot shows the DVs move.

### What this does NOT fix

If Haiku resolves conflicts effortlessly in condition C, we hit a new ceiling and learn
again that the substrate already implements the function. That outcome is publishable
under the same thesis (the assumption the theory never states is "the consumer lacks the
function already") but it is a repeat of the Experiment 1 lesson, not a new one. The
routine/novel contrast and the non-accuracy DVs are the hedges.

---

## B. Expanding Experiment 2, independent of Experiment 1

Experiment 2's core question (can outside behavioral testing verify an architectural
property?) generalizes past workspaces entirely. Four extensions, ordered by value.

### B1. Perturbation probes: intervention beats interrogation

The regress result said identification requires ground truth about what the system
received. But that assumed the assessor can only ASK. If the assessor can PERTURB, a
different signature opens up: turn the real system's actual knobs (capacity, salience
noise, attention precision) and test whether self-reports COVARY with the knob.

- Real architecture: reports and behavior should track the manipulation (report of "less
  reaches me" when capacity shrinks; degraded schema accuracy when attention noise rises).
- Imposter: the script has no knob. Reports stay static under perturbation, or track the
  wrong thing.

This is detection without content ground truth: the assessor never needs to know WHICH
facts arrived, only that it moved a dial. It converts the regress from "behavioral
testing is stuck" to "interrogation is stuck; intervention is not," which is a
constructive ending the current paper lacks.

It is also the conference-native method. Perturb-and-compare-report-to-state is exactly
what psychedelic science does (dose as the intervention, phenomenological report as the
readout, the REBUS precision story as the mechanism). One method, both worlds: that is
the bridge between the poster's psychedelics half and its AI half, and it is the single
highest-value extension on this list.

Cost: small. The architectural cells reuse the existing harness with a capacity/noise
sweep (mostly Haiku, partially cacheable); imposter cells are prompt-only. Estimate $10
to $20.

### B2. Same design, other indicators

Rerun real-vs-prompted-imposter for indicators with different vocabularies and different
cost structures: HOT-2 (metacognition: does stated confidence track injected noise? an
imposter's confidence tracks nothing), GWT-3 (broadcast: can module N use information
only module M received? imposters claim yes; ablation says no). Tests whether the
vocabulary-dependence result is general or a GWT-2/AST-1 quirk. Cost per indicator
roughly matches the original grid (~$15 on Haiku).

### B3. Stronger imposters

The current imposter is one adversarial prompt. Escalate: few-shot coached (transcripts
of the real system in the prompt), then retrieval-backed. The question: does the
detection margin close as imitation quality rises, and how fast? This turns the
~225-trial figure into a curve, which is what an assessment-under-optimization-pressure
audience (AI welfare evaluators) actually needs.

### B4. The blind assessor game

Give a model the assessor role: it designs its own probes, budgeted at N questions, and
must classify real vs imposter. Measures whether the regress binds in practice for a
capable assessor, not just for our two hand-built probe designs. Cheap, and produces the
paper's most quotable table.

---

## Recommendation

Nothing runs before the abstract is in (8/16) or before fresh budget authorization.
After that: B1 first (bridges the poster halves, small, reuses the harness), then A as
the successor to Experiment 1 if there is appetite for another architecture experiment,
then B2/B3/B4 as scope allows.
