# C1-B1 Pilot2 exact arithmetic argument

Scope: canonical `type(profile) is FixedPoint` with consistent original fields,
valid stored integer raws, positive exact mass, exact int/Fraction dt. This is
an algebraic argument plus executable differential tests, not a proof-assistant proof.
Other profile representations/subclasses/instance overrides remain on original FAST.
Existing REF, impulse, segment guard, stored-domain guard and commit order stay unchanged.

## Prepared packet

For each component let d=p*dt/m. Original v2 computes d once for the exact endpoint,
then computes d again for the rounded stored displacement. A computes d once,
and carries both d and round_pos(d). It still updates position by pos.add(r,round_pos(d)).
In particular r=1,d=1/2 on the integer grid yields stored r=1, not round(r+d)=2.
Retired v1 delegates to original drift without inserting displacement rounding.

## Unreduced ratio

Let p=p_raw/2^Fmom, dt=a/b, m=c/e, with b,c,e>0.
Then d=(p_raw*a*e)/(2^Fmom*b*c). Products and denominator are Python integers;
no gcd or intermediate rounding is needed. Arbitrary common factors change the
representation, not its value. B stores (n,D) with D>0, and only constructs Fraction(n,D)
where the original exact endpoint r+d is consumed by the unchanged segment guard.
Mass/dt/profile-dependent coefficients are immutable, per bound runtime executor,
never stored in a global cache. Every raw-enabled step validates the original binding
including species, masses, profile identity/fields, dt and drift rule before execution.
Changed bindings are refused without mutating the run; construct a fresh executor.

## Rounding

Stored displacement raw is nearest-even(n*2^Fpos/D). The existing `_div_round` is used.
For a positive common factor g, dividing |g*n*2^Fpos| by g*D has the same quotient;
its remainder is g times the original remainder. Comparisons 2*r versus D, and the
quotient parity at equality, are unchanged. Thus reducing or not reducing gives
identical raw for positive, negative, zero, midpoint and adjacent exact rational inputs.
Sign is restored exactly as in FixedPoint.from_exact; no host floating point is used.
Original displacement and position-add range checks occur separately, in the same
component order, and preserve overflow reason/cause. There is no saturation or wrap.

## Kick

For valid integer p_raw and J_raw in the same canonical momentum profile,
p+-J=(p_raw+-J_raw)/2^Fmom. Scaling the exact sum back by 2^Fmom is already an integer,
so original nearest-even rounding is the identity. The same signed range check suffices.
Check i components before j components, as original `_kick`; no partial run commit.
Profile lookalikes or different semantics must delegate to original `_kick`.

## Guard and integration boundary

The guard receives exact rational endpoints, never the rounded packet field.
Original `segment_min_R2`, stored relative R2, both kicks, impulse enclosure refinement,
precision cap and final assignment remain in the same original step code object.
This establishes the transformation argument under stated preconditions; finite
component/step/trajectory observations are additional evidence, not a general world proof.
