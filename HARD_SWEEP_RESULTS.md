# Hard sweep: the bottleneck does not help, and we cannot yet say why

Run 2026-08-01. 476 calls, 853k input tokens, $6.06. claude-opus-5 at low effort,
8 required facts, 48 distractors, 60 trials per contrast point.

## The result

| capacity | distractors admitted | oracle | model | n | refused |
|---|---|---|---|---|---|
| 0 | 0 | 0.00 | **0.000** | 10 | 0 |
| 10 | 0 | 0.00 | **0.000** | 10 | 0 |
| 15 | 0 | 1.00 | 1.000 | 60 | 0 |
| 45 | 0 | 1.00 | 1.000 | 60 | 0 |
| 60 | 9 | 1.00 | 1.000 | 60 | 0 |
| 90 | 24 | 1.00 | 1.000 | 60 | 0 |
| 150 | 48 | 1.00 | 1.000 | 60 | 0 |
| unlimited | 48 | 1.00 | 1.000 | 60 | 0 |

Identical in the control arm with non-confusable distractors, except for 11 and 12 transient
refusals at capacities 60 and 90, which were retried, then excluded and counted rather than
scored zero.

**Flat at 1.000, every capacity, both arms, 60 out of 60 trials, zero variance.** Admitting
48 confusable near-twins of the required containers alongside the answer costs this model
nothing at all.

## What did work

The floor checks behaved exactly as designed. At capacities 0 and 10 the required
information is genuinely absent and the model scored **0.000**, not above chance. It did not
fabricate. That is a small clean result in its own right and it confirms the harness scores
what it claims to score.

## What this is and is not

**It is not** evidence that a capacity bottleneck fails to aid integration. You cannot
distinguish "no effect" from "an effect this task cannot resolve" when every cell is at
ceiling. A null at ceiling is weak evidence and should be reported as weak.

**It is** evidence for something narrower and more interesting: across the whole accessible
range of this task family, from 0 to 48 confusable distractors, there is no distraction
regime in which the bottleneck earns its keep for a frontier model.

## The interpretation worth testing

Araya's embodied result came from an agent whose working memory was genuinely small. Global
workspace theory says the limit is functional because the thing consuming the broadcast is
itself capacity-limited. **That assumption is invisible when the consumer is not
capacity-limited.** A frontier model reading 48 distractors is not straining.

So the prediction is: **the workspace advantage should appear as the controller gets weaker,
and vanish as it gets stronger.** If that holds, the null above is not a failure. It is one
end of a curve, and the theory's claim turns out to be conditional on a boundedness
assumption it does not state.

## Next run

Re-run this identical sweep with a substantially weaker controller. `claude-haiku-4-5` is
the obvious first choice: same harness, same tasks, same capacities, one line changed in
`run_hard_sweep.py`, and roughly a tenth the cost. If the curve bends, this becomes a
positive result about when the bottleneck matters rather than a null about whether it does.

Escalating distractor count further on the strong model is the weaker option. It chases a
ceiling that has already survived a 4x increase.

## Standing caveat

`whitespace_tokens` is still the default tokenizer. Fine for relative comparisons, not a
real token count. Swap in a real tokenizer before quoting any capacity number in print.
