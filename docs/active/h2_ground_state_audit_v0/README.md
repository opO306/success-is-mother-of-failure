# H₂ R=0.4 ground-state independent validation evidence

[설계자 보고서](../H2_R04_GROUND_STATE_INDEPENDENT_VALIDATION_V0.md).

Stage A: GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED.
Stage B: INDEPENDENT_GROUND_STATE_ENERGY_SUPPORTED.
Same saved raw-MO/full singlet only; NOT CERTIFIED / AO-MO-basis accuracy UNRESOLVED.
Pachucki comparison still exceeds 0.001 hartree; prior QZ44 NUMERICAL FAIL unchanged.
STOP / DESIGNER DECISION REQUIRED / no push.

`evidence/`: actual replay vector, source/input seals, canonical mapping, residuals,
full independent spectrum/vector, runtime, post-A/B physical comparison and regression.
`source/`: exact execution source copies. `validation/`: logs, JUnit, byte checks and
separate author design-alignment review. `H_SC.npy` stays in raw runs, bound by manifest.
The vector is **reproduced from sealed replay**, not archived from the original QZ44 run.
