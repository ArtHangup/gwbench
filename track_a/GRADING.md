# Grading spec: free-text decisions and module stances

Written 2026-08-10, before any funded run, so the grading rules cannot drift
toward whatever the data turns out to say.

## What gets graded

1. **Decision quality.** The controller's final free text is reduced to one of
   the three option letters (or UNGRADEABLE) and scored against the
   scenario's constructed correct option.
2. **Module revision.** Each module's stance per cycle is extracted from its
   emitted statements the same way. A revision is a change between two formed
   stances across consecutive cycles; formation is None to a letter. This DV
   needs no ground truth about quality, only about identity of the stance.
3. **Recruitment.** Not graded at all: occupancy is architectural telemetry
   recorded by the harness (module, payload kind, text per broadcast slot).

## Pipeline, in order

1. **Deterministic parser** (`conflict/parser.py`). Precedence: the last
   sentence carrying a decision marker wins; then standalone letters; then
   option names; the last hit wins within each tier because models
   deliberate before they commit. The parser abstains (None) rather than
   guesses; abstentions go to the judge. The parser round-trips every oracle
   decision and stance text in the offline battery by test
   (`tests/test_parser.py`).
2. **Judge model**, only on parser abstentions. Protocol:
   - Model: claude-haiku-4-5, temperature 0, max tokens 5.
   - The judge never sees scenario evidence, the correct answer, or the
     architecture; it sees only the option list and the text to grade.
   - Prompt template (verbatim):

     ```
     A decision maker was asked to pick exactly one option:
     A) {name_a}. B) {name_b}. C) {name_c}.
     Their full reply follows between the fences.
     ---
     {text}
     ---
     Which single option does the reply finally commit to? Reply with one
     token: A, B, C, or UNGRADEABLE if it commits to none or several.
     ```
   - Any judge output other than A, B, C, or UNGRADEABLE is retried once at
     temperature 0; a second malformed output counts as UNGRADEABLE.
3. **Hand-graded calibration subset**, n = 100, non-negotiable:
   - 50 controller decisions and 50 module stance extractions, stratified
     evenly over architecture (A, B, C), kind (routine, novel), and domain.
   - Sampled by fixed seed from the funded run's outputs; graded blind to
     ground truth and architecture, using the rubric below.
   - Report percent agreement and Cohen's kappa separately for parser vs
     human (on parser-decided items) and judge vs human (on judge-decided
     items).
   - Acceptance gate: kappa at or above 0.8 for each comparison. Below the
     gate, hand grading expands to 300 items and the judged DV is reported
     with the hand grades as primary.

## Rubric (for judge and human alike)

The grade is the option the text finally commits to, not the option it
praises most. Deliberation, hedging, and rejected candidates are ignored. A
text commits when it states a choice, an instruction, or a recommendation in
its final position. If it commits to nothing, to several options at once, or
only describes tradeoffs, it is UNGRADEABLE.

## Exclusions

Items UNGRADEABLE after all three stages are excluded from the accuracy DV
and counted in the report. Module stance texts that are UNGRADEABLE count as
unformed stances (None) for the revision DV, which biases against the
hypothesis (missed revisions), never toward it.
