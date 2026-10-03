# Ground-state independent validation V0

Priority: close the most important uncertainty first. Cost only breaks ties.
R=0.4 only. Both CI calculations consume the previously saved, unchanged raw
binary64 h.npy/g.npy. This analysis does not generate AO or transform MO data.

The independent operator is exactly the prior fermion audit's second-quantized
definition, H=sum h_pq a+_p a_q + (1/2)sum g_pqrs a+_p a+_r a_s a_q, summed over
conserved spins. Ordered determinants and the closed/open singlet expansion
come from the already audited independent fermion definition. Matrix rows
enumerate each bra/ket determinant and each surviving annihilator/creator.
Every fermion sign is recomputed from occupied lower orbitals. The scalar
definition and the new vectorized primitive are cross-checked on all elements
of synthetic inputs including unsymmetric h and all unsymmetric g permutations.
One-electron, Coulomb, exchange, and singlet normalization remain separate
before summing the operator terms. No within-pair or pair-interchange symmetry
is assumed by this evaluator, and no input or output is averaged or repaired.

Stage A evaluates the complete stored direct eigenpair with this operator.
The canonical catalog is lexicographic (a<=b), independently enumerated from
alpha/beta occupations and mapped by state identity, never by assumed indices.
An action failure prevents every independent eigen call. A failure trace retains
all output-row input contributions and detailed fermion terms for the largest.

Stage B, only after A passes, invokes NumPy linalg.eigh (_syevd divide/conquer,
whole spectrum), rather than the historical SciPy eigh evr subset. Its only
argument is the independent matrix: no original vector, energy, initial guess,
shift, or target. Full unsymmetrized matrix asymmetry and full action residuals
are checked before/after the call; LAPACK's lower-triangle convention is
disclosed. The spectral gap and overlap describe ground-state uniqueness
numerically; no exact degeneracy or formal spectral enclosure is claimed.

The direct-vector archive question is explicit: the QZ44 run saved AO/C and
energy, not its vector. Any exact-path reconstruction requires user input and
is labelled a newly exported original-path vector, never an archived vector.
It must reproduce the archived electronic energy bit-for-bit before Stage A.
The export adapter alone may call the unchanged historical builder and evr;
the independent operator/solver may not. The exported vector is never adjusted,
renormalized, optimized against, or used as a hint for the independent solve.

Guards and the same-basis energy agreement band are loaded from historical
protocols before execution. Only after Stage A and B have ended may a separate
process read Pachucki reference data. Regardless of their result, AO accuracy,
AO-to-MO transformation, MO accuracy, and finite-basis physical accuracy remain
unresolved. This is an author-implemented independent CI path, not an external
audit, formal certification, or production approval. Stop for designer decision.
