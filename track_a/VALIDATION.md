# Offline validation: oracle modules, three architectures

Battery: 240 scenarios (30 per domain x kind cell), 720 trials, zero API calls.

## Signature checks

- PASS: gwt_novel_revises
- PASS: gwt_novel_resolves
- PASS: gwt_routine_no_revision
- PASS: gwt_recruits_all_required
- PASS: gwt_no_floor_waste
- PASS: hub_zero_revision
- PASS: hub_zero_formation
- PASS: flat_no_dynamics
- PASS: all_architectures_decide_correctly

## Summary table

| architecture/kind | n | accuracy | revision rate | formations | resolved |
|---|---|---|---|---|---|
| flat/novel | 120 | 1.00 | 0.000 | 0.0 | 0.00 |
| flat/routine | 120 | 1.00 | 0.000 | 0.0 | 0.00 |
| gwt/novel | 120 | 1.00 | 0.136 | 5.0 | 1.00 |
| gwt/routine | 120 | 1.00 | 0.000 | 5.0 | 1.00 |
| hub/novel | 120 | 1.00 | 0.000 | 0.0 | 0.00 |
| hub/routine | 120 | 1.00 | 0.000 | 0.0 | 0.00 |

## Recruitment (architecture A)

- mean cycles to full required-module coverage: 2.17
- max: 5
- broadcast slots wasted on repeats before coverage: 0

Oracle decision quality is at ceiling everywhere by design; the architectures separate on the non-accuracy DVs, which is the point.
