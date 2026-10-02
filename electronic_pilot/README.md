# Isolated H₂ static reference pilot

This directory is numerical research outside A-world execution, certification,
and B observations. It adds no bond/molecule ID or fitted H-H potential.
See [the report](../docs/active/H2_STATIC_REFERENCE_PILOT_V1.md).

The executor requires NumPy, SciPy, PySCF 2.12.1. The observed Linux environment
and actual H basis coefficients are pinned in the campaign seal, with package
versions. Local WSL was used; no remote machine or GPU was used. The study is
singlet-only and refuses ill-conditioned or numerically non-Hermitian problems.
It has no dynamics, force, nuclear motion, excited-sector, or production API.

Use a new output directory for every execution, never replace previous results:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m electronic_pilot.campaign --protocol electronic_pilot/protocol_v2.json --output runs/NEW_UNIQUE_DIRECTORY
python -m electronic_pilot.check_reference --results runs/NEW_UNIQUE_DIRECTORY/results.json --protocol electronic_pilot/protocol_v2.json --reference electronic_pilot/reference_pachucki_v2.csv --output runs/NEW_COMPARISON.json
python -m pytest tests/test_h2_static_pilot.py electronic_pilot/test_integration.py -q
```

The Windows production suite contains the dependency-light structural tests.
The PySCF-dependent integration file is separately run under local WSL, and
is not silently skipped or counted in LOCAL FULL. Direct LAPACK iteration
counts are unavailable; records explicitly use `null / not iterative`.

`solver.py` has no external-reference imports. The standard-library comparison
tool has no executor import. The published correlated-exponential reference
is independent of our Gaussian/dense evaluator; optional PySCF FCI checks
share Gaussian integrals and are deliberately labeled secondary checks.
`verify_reference_transcription.py` separately requires pypdf for source checks.

V1 sanity stopped at a numerical refusal. V2 kept the same grid, physics,
bases, arithmetic, and tolerances, while collecting failures and continuing
only independent other points. V2 produced 116/132 energies, 13 intentional
refusals, and three erroneous refusal messages. The message was fixed after
the campaign; original executed source and failure records are retained.
The highest basis cannot establish its minimum because R<=1.4 was unsupported.
No full-curve agreement, formal certificate, or foundation approval is claimed.
