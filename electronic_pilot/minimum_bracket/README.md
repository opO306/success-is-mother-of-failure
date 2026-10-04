# H2 QZ Minimum-Bracket Numerical Gate V1

PARTIAL / QZ R=1.3 UNSUPPORTED / minimum bracket UNRESOLVED / NOT CERTIFIED.
The independent Psi4 1.3.2 / Libint 1.2.1 path passed the three accepted
cc-pVQZ controls in two full-span coordinates. Both R=1.3 attempts refused
before eigensolve. No tolerance, basis, orbital, sector or Hamiltonian changed.

The method uses independent binary64 AO integrals, extended-precision full
tensor contractions (64 significand bits on the executed WSL host), and
binary64 LAPACK. It is **not** a higher-precision AO engine. MPFR postrun
diagnostics retain the existing binary64 AO inputs and never calculate an energy.

Use fresh output folders. `campaign` requires a Windows Git start receipt
because WSL Git cannot resolve Windows-managed worktree links. The receipt
pins this gate's freeze base; the stage seal independently pins every executed
candidate source and the actual basis input coefficients. Controls and targets
must use identical source hashes and protocols. `postrun` is a separate
post-acquisition directory and is not executed by the candidate worker.

Execution environment: Ubuntu 24.04 under local WSL, `/usr/bin/python3`,
`PYTHONPATH=/usr/lib/x86_64-linux-gnu`, numerical threads 1; Ubuntu packages
`psi4`, `python3-scipy`, `python3-pytest` (28 packages, 0 upgrades).
The pre-existing PySCF venv is used only for the separate regression tests
and the historical MPFR scalar diagnostic, not to generate the candidate AO.

See [the complete report](../../docs/active/H2_QZ_MINIMUM_BRACKET_NUMERICAL_GATE_V1.md)
and `docs/active/h2_qz_minimum_bracket_v1/` for the seals, failures and results.
Large NPZ raw evidence remains under the attached worktree's
`runs/h2_qz_minimum_bracket_v1_20261004/`; do not archive that checkout without
preserving these Git-excluded files.
