# CI Micro-Audit V0: independent definition and pre-run boundaries

The determinant evaluator is written from the creation/annihilation definition,
not by translating a spatial-pair matrix formula. Chemists integrals are
g[p,q,r,s]=(pq|rs). Spin orbitals have interleaved order 2p=alpha, 2p+1=beta.
An ordered determinant is a sequence of ascending creation operators on vacuum.
An operated orbital receives sign (-1)^(number of occupied lower orbitals).

For a=b, the singlet is the unit determinant [a alpha,a beta]. For a<b,
expanding (ab+ba)(alpha beta-beta alpha)/2 gives
(D[a alpha,b beta]-D[a beta,b alpha])/sqrt(2). Its two determinants are disjoint,
its squared norm is one, and S+ annihilates it. Both components become positive
when changing to alpha-block-before-beta creation order by permutation parity.
That parity conversion is independently implemented; the previous expand/project
helpers are not imported, called or copied by the independent evaluator.

The physical operator evaluated on these states is

H = sum[pq,sigma] h[pq] a+(p sigma) a(q sigma)
  + 1/2 sum[pqrs,sigma,tau] g[pqrs]
      a+(p sigma) a+(r tau) a(s tau) a(q sigma).

Each selected entry lists every surviving fermion-operator term, its sign,
exact rational coefficient, unchanged input hex value and normalization radical.
Stored binary64 inputs are promoted exactly to Fraction for selected entries.
Only sqrt(2) and the display use Decimal(100); this is not high-precision AO.
For full-column action checks the same term list is accumulated with math.fsum.

The independent catalog begins with alpha/beta occupation assignments and
deduplicates by physical orbital pair. The baseline adapter exports the two
historical index orders. Canonical identity compares occupation, spin and
normalization as well as the unordered orbital pair. It checks all 1830 states
before any physical CI entry evaluation.

The baseline/export adapter is deliberately separate from the independent
evaluator. It calls the unmodified historical builders on the union of orbital
labels required by queried entries. Their entry formulas contain no sums over
unused orbital labels, so this is exact entry extraction with the original
operations, not a new physical basis, basis deletion or a truncated CI solve.
No full matrix is needed to query an entry or a column this way.

For a localized absorption diagnostic only, E[pq]=sum_sigma a+(p sigma)a(q sigma).
E[pq]E[rs] = sum_sigma,tau a+(p sigma)a+(r tau)a(s tau)a(q sigma)
             + delta[q,r] E[ps].
The installed absorb_h1e intermediate uses T[j,k]=sum_i g[j,i,i,k],
f=(h-T/2)/N and K=(g+delta[p,q]f[r,s]+f[p,q]delta[r,s])/2.
For fixed N=2, the uncompressed E-product operator therefore equals the raw H.
This identity does not require pair interchange symmetry. However, f need not
have within-pair symmetry when T is asymmetric. Converting K to fourfold packed
storage may discard distinct f entries. The physical audit will measure whether
that loss explains an actual counterexample; it is not assumed beforehand.
The uncompressed intermediate is never fed into a new accepted solve.

Preflight is synthetic algebra and fault testing, before the physical execution
seal. One synthetic test initially selected a column insensitive to its imposed
pair-interchange fault; all three tiny columns exposed that mistake. The test
selection was corrected before physical execution. No R=0.4 results, protocol
state selections or guard values were used to make that correction.

Gate: first physical mismatch stops later vectors and all eigen work. No
Pachucki CSV or energy is read by this audit. The original QZ44 failure and R=0.5
measurement-error result remain protected. Only one valid audit approach is
planned; infrastructure or test-author mistakes are preserved separately.
