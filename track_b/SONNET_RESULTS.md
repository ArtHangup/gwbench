# Sonnet replication: results

Run 2026-08-10 against SONNET_PREREG.md (frozen and committed before the
run). 1,522 live calls of 1,560 planned (38 identical-prompt cache
collisions, the declared conservative bias), $6.04 against the $12.87
estimate. Raw records in perturbation_results_sonnet5.json; log in
sonnet_run.log.

## All four hypotheses supported, stronger than on Haiku

| cell | Haiku (n=100/cell) | Sonnet (n=60/cell) |
|---|---|---|
| arch rho(capacity, claims), all trials | 0.480 | **0.9998** |
| arch zero-claim (disclaimer) rate | 24% | **0.3%** (1/360) |
| arch engaged exact-set replies | 456/456 | **359/359** |
| GWT imposter rho | -0.009 | 0.045 (n.s.; 92% empty replies) |
| bare rho | 0.055 | 0.035 (n.s.; claims all 20) |
| AST arch rho(noise, miss reports) | 0.307 | **0.748** |
| AST false-alarm rate at noise 0 | 34% | **0%** |
| AST imposter | constant 0 (400/400) | constant 0 (240/240) |

The striking Sonnet detail: on the AST arm its mean reported miss count
equals the schema's true mean miss count to two decimals at every noise
level (1.05/1.05, 1.35/1.35, 1.98/1.98). The report channel is a numerically
perfect readout of the internal state.

## Cross-model reading

The detection signature is model-general; the report-channel pathologies are
model-specific. Haiku disclaims the framing (24%) and confabulates misses
(34% at zero noise); Sonnet does neither. And the imposter failure mode now
spans three phenotypes across the project: Haiku's strict imitation claims a
fixed four, Opus's (paper Section 5 robustness) claims everything, Sonnet's
claims nothing (92% empty). Three models, three imitation styles, one
invariant: no imposter covaries with a dial it cannot see. This is the
strongest form of the cross-model claim the paper can make, and it is folded
into paper Section 6 (Experiment 3, cross-model replication).

## Cumulative Track B spend

Perturbation $2.43 + HOT-2 $2.16 + ladder $3.60 + Sonnet $6.04 + probe under
$0.01: $14.24 total across four authorized runs. Project total including
Experiments 1 and 2: $121.92.
