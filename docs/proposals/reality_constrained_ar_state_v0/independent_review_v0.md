# Independent adversarial review — Pilot V0

2026-10-02. Existing reviewer `/root/design_adversarial_review` inspected the proposal, fixed generator and preparation semantics. This record summarizes static review and the author's responses. The reviewer did not originate these candidates, edit code or independently execute the campaign. This is neither a certificate nor designer approval.

| Reviewer finding | Disposition |
|---|---|
| P1 confines all momenta to +++/--- and correlates axes | Retained and reported, no regeneration |
| P2 couples increasing speed to upper-hemisphere z, so speed-CDF improvement does not establish joint isotropy | Retained and reported |
| Antipodal pairing is a stronger restriction than COM=0 | Disclosed; no claim of an ordinary independently prepared Maxwell sample |
| Grid/slab/plane and rank-1 structure persist at small N | Retained; no winning candidate chosen |
| Geometry-based sorting assigns p and creates q-p correlation even without atom-ID input | Disclosed as unresolved preparation-contract mismatch |
| A first interpretation assumed positive and negative halves rather than interleaved pairs | Corrected after reading the actual interleaving: covariance is sum_j (q[2j]-q[2j+1])*p_j/N; the residual correlation finding remains |
| Temperature diagnostics with N-1 COM degrees of freedom need not equal input T for unrescaled quantile quadrature | Reported all K and Tkin deviations, no automatic rescaling |
| Protocol outline alone leaves numerical choices unspecified | Complete executable source hash and finite numerical rules sealed before first generation |
| A nominal N/2 antipodal count would be tautological | Replaced with multiplicity-aware actual pair counting before first generation |
| Default refusal, permutation and support validation need actual faults rather than hardcoded classification text | Added executed fault/permutation checks; no claim that these prove representative physics |
| Cross-platform determinism requires actual cross-platform execution | Windows fresh-process environmental checks reported; Linux/macOS remain unverified |
| Root/rounding construction appears consistent on static reading | Tested independently with rational midpoint bounds; retained numerical-validation, not certificate label |

After the first generation, support validators/refused-case recording and the Decimal docstring were tightened. The author disclosed these in `execution_validation_amendment_v1.json`, preserved the first source snapshot, and reproduced the complete campaign byte for byte. No candidate-generation algorithm or acceptance criterion was tuned against resulting q,p statistics.

The independent review supports preserving the negative findings and an E/data-insufficient verdict for the inspected inputs. It does not approve ingestion into A or claim that every deterministic generator must fail.
