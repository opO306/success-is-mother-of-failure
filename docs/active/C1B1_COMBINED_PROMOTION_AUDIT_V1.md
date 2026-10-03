# Combined production promotion: independent arithmetic review

2026-10-03. Scope: canonical FixedPoint, valid stored raw, exact dt and positive mass.
Original slow Fraction path remains the oracle. This is a separate reviewer context
and independent transformation audit, not an external physical implementation audit.

## Independently executed probes

Production Combined vs original Fraction: exact ratio660, rounded displacement660,
whole drift2310, kick605. Positive/negative/zero, lo/hi, immediately before overflow
and overflow were included. Result, exception class/message/cause matched.
Additional Pilot2 half-boundary/neighbor/common-factor probes2322 matched.

For p=raw/2^Fm, dt=a/b, m=c/e, exact drift is raw*a*e/(2^Fm*b*c).
Python integers preserve this value. Positive common-factor scaling retains nearest-even
quotient, remainder comparison and quotient parity. Stored position is r+round(d),
while the segment guard consumes r+d. Same-grid kick p+-J is exactly raw+-Jraw,
followed by the original component order and range check.

The independently executed domain example has stored positions0 and3 (R²=9), but
exact endpoints9/20 and51/20 and segment R²=441/100. REF and Combined both refuse
the exact segment and preserve the Run. Current production preserves original
step code, segment/domain guard, impulse, precision cap and commit order.

## Findings and resolution

Pilot2 executor binding omitted Run identity. Replacing executor.run with another Run
sharing profiles/dt/species was accepted. This was a provenance/one-Run contract gap;
no wrong numerical result was demonstrated. Production adds `_bound_run` identity
validation before execution. The independent reviewer reproduced its refusal.
Old Pilot2 source is preserved unchanged; this production hardening is separate.

Important evidence gaps were corrected before sealing: exact case/artifact/mode/
benchmark inventory; full step/attempt/result/end/count reconciliation; ordered def-use
trace continuity; independent original impulse recomputation; component recomputation;
raw pstats-derived summary; FULL XML item identity and exact strict xfail identity.

Reviewer fault probes rejected identical displacement/endpoint/guard faults in all modes,
incoming-J def-use faults, and a correlated impulse+1 fault propagated consistently
through the following states. Six parseable FULL faults (FAIL/ERROR/SKIP/wrong xfail/
missing item/short baseline) were rejected. A synthetic valid3865+1 control was accepted;
that synthetic control is not an actual FULL result.

Final independent review: Critical0 / Important0 / Minor1. The minor source-map metadata
finding was fixed by comparing the saved inventory directly with current inventory and
its digest before campaign sealing. That final metadata assertion was applied by the
implementer after the reviewer read the campaign source; numerical code was unchanged.

Reviewed production source SHA256:
`8d82cb4d470b27148f35af31d909c24add37acd39219717bab69cb253aa5d9f8`.
Reviewed campaign before minor metadata assertion:
`fbdabd732b3fd71ce9ccb1a70e4561e6dc7614a78ae848829dd813c4dc3d4ea9`.
Preserved Pilot2 arithmetic:
`d5745e950b22ef4466d44f2bbaf88b1b46d2be6dae944bce73db92e244927c28`.

## Boundaries

Reviewer did not run final FULL, six complete trajectory campaign, timings, profiling,
or final source closure. Those must be separately executed and recorded by the campaign.
One virtual closure fixture was incomplete and stopped with KeyError while checker
requirements were changing; it was not counted as acceptance or a numerical failure.
Shared original profile/impulse code remains a trust assumption; this transformation
audit does not replace the existing endpoint argument, A-EV/native J, approved replay,
physical-model validity, whole domain or infinite-trajectory obligations.

The reviewer read AGENTS/RULES fully, CURRENT_STATE top64 and REPO_MAP related content,
the new production/campaign/tests and original reference functions. No source/index/
HEAD mutations or sub-reviewers were used. Actual campaign result is tracked separately
in [the promotion report](C1B1_COMBINED_PRODUCTION_PROMOTION_V1.md).
