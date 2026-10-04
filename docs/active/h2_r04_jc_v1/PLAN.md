# R=.4 symmetric James--Coolidge B1 V1 — pre-energy plan

Status: implementation/preflight followed by immutable execution seal. Numerical pilot only. NOT_CERTIFIED / NOT_PRODUCTION_APPROVED. No push.

The designer replaces the previous all-five lowest-root condition with per-target independent validation. JC asymmetric intended root remains UNRESOLVED: README/input/source say EN targets a desired eigenvalue, but do not state that example's ground/excited intent. H--He+ indefinite S, General unresolved SPD, asymmetric count 1→2 and MAXIT silent exit remain historical evidence, unchanged.

Physical input: ZA=ZB=1, R=.4 bohr, two electrons, clamped nonrelativistic Coulomb, spatial symmetric/singlet, gerade 1Sigma_g+. x=y=0, u=w>0. Nuclear repulsion is already in HAM; no second 1/R. Vendor reads decimal R through REAL*16; nominal .4 is consequently represented with that input rounding, not an exact rational Hamiltonian.

Energy-blind enumeration Omega1..9 is independently enumerated and compared tuple-for-tuple/order-for-order with a native copy that exports DT and STOPs before CALCEN. SMALL Omega3/N20 is low-cost; MEDIUM Omega5/N78 intermediate; LARGE Omega7/N228 matches the existing practical vendor JC dimension. Only these three will be solved. At common u their degree-prefix spaces are nested; no claim that the nonlinear search is globally optimal.

Calibration: MEDIUM at generic u=1. NMAX60,80,100,120 at ND60; then ND80 at fixed NMAX120. Integrals remain MPIPL80 / 384 bits. Native linear matrices ND60=320 bits, ND80=384 bits. Compare each axis separately. Pilot threshold |delta E|<=1e-10 Eh is empirical, not formal. Choose N80 if 80/100 and 100/120 stable; otherwise N100 if 100/120 stable; ND60 only if 60/80 precision comparison stable. Otherwise STOP without extension.

Optimization: own accepted finite MEDIUM energy, seed1, interval[.5,1.5], deterministic bounded pattern search, step1/4,1/8,1/16. At each level evaluate BOTH current-best neighbors, choose lowest energy (tie smaller u), at most7 evaluations including cached calibrated seed. Three levels then STOP, no global/local-optimality assertion. No literature seed; transfer ONE resulting u to all three final representations to preserve nested spaces. No per-Omega hand tuning. Any rejected trial after bounded retry stops campaign.

EN: initial -2. Subsequent hint is latest accepted own E minus1/256. Each point allows one retry using that point's own returned finite E minus1/256. A MAXIT result can provide a hint only; never an accepted physical energy. No independent reference values in optimizer/runner/contract. No retry on failed S. No unbounded root search. Source ITMAX40/convergence and every calculation line remain unchanged in copies; observers and clocks are additive and strip to the original source hash.

Acceptance: actual native eigenvalue-test branch, no MAXIT, all factor/solve error codes zero, independent original stored S SPD and positive metric margin, initial shift inertia agrees with WA1, unchanged sealed V1 returned-E enclosure with count0→1 and E inside, independent 240-digit residual, vTSv and Rayleigh, all four earlier consistency checks. No new checker tolerance. A non-lowest root is NOT_GROUND_ROOT; unresolved/rejected point is REFUSED. Stored-matrix certification is distinct from Coulomb/series/physical certification.

Fresh final SMALL/MEDIUM/LARGE each, fresh NMAX+20 spot each at same ND. Scientific stdout and wf must match a fresh unmodified vendor binary for every final point. Existing binary/source/checker/proofs remain hash-bound. Do not expand Omega or R after seeing results.

Cost: GNU /usr/bin/time + Windows outer wall for both WSL JC and unchanged Gaussian cardinal V5Z; OMP, OPENBLAS, MKL=1. New copy clocks separate integral, matrix/allocation, precision/setup, snapshot and observed invsg. Windows HP controller RSS sampled separately; GNU native peak is not aggregate host peak. Include numerical calibration, shared parameter search, independent validation, spots, failed/retry and vendor noninterference work. Preserve both solver-only and complete measured cost; unequal validation workloads preclude a pure representation-speed claim.

Seal all B1 energies and hashes before invoking separate compare.py. Fixed designer reference -0.120230341178823, target .001 Eh; historical QZ baseline, V5Z main target comparator. Only if a final B1 target meets criterion, run the unchanged hash-bound V5Z code/basis/guards on the same host/wrapper. Its historical energy remains unchanged. No fresh Gaussian execution before this gate.

Scope excludes R1.4/6, whole curve, B2 independent implementation, A adoption, multi-electron/dynamics claims and production. End with report and local commit; no push. Related tests replace LOCAL FULL because new isolated wrappers/tests/docs only; frozen A/common/fixtures unchanged and official baseline untouched.
