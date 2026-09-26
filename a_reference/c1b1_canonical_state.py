"""C1-B1 canonical initial state: the ONE state generator of the orbital-capture boundary measurement AND of D_valid's
new_run identification (designer verdict on 7532788: "측정한 상태 = 인정하는 상태").

A scattering state at relative position (R_START, 0, 0), nominal energy E = e De, impact parameter b:

    Pt_q = round(b sqrt(2 mu E) / R_START)                     the sideways momentum that will be STORED
    Pr_q = round(-sqrt(2 mu (E - V0) - Pt_q^2))                 the radial momentum, computed FROM Pt_q
    p_j = (Pr_q, Pt_q, 0), p_i = -p_j, atoms at -+R_START/2 on x, V0 = potential_high(R_START^2, 512) (exact)

round = half-even to the FX(96,80) grid, decided in exact rational arithmetic (an undecided rounding raises / refuses).
The continuous intention (E, b) is projected ONCE onto what the computer stores: Pt first, then everything else from
the stored Pt. The retired constructor (c1b1_inner_validation.state, 60-digit mpmath, Pr from the UNROUNDED Pt) is kept
for the section 20-22 records only; its states were one Pr grid unit off this rule for 32 of 181 boundary probes.

b_from_state gives the b a stored state represents, as b^2 (exact rational): b^2 = R_START^2 Pt_q^2 / (2 mu E). The
generator is idempotent on it -- canonical_initial_state_b2(e, b_from_state(S, e)) == S exactly -- because Pt(b_current)
is exactly the stored Pt_q.
"""
from __future__ import annotations

import functools
from fractions import Fraction as Q
from math import isqrt

import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_two_atom as C

GENERATOR_VERSION = "c1b1-canonical-state-v1"
DE = I.S.DE_GRID
MOM_ULP = Q(1, 1 << 80)                    # the FX(96,80) momentum grid
SQRT_BITS = 256
SPEC = {"generator": GENERATOR_VERSION, "module": "a_reference.c1b1_canonical_state", "R_start": str(I.R_START),
        "positions": "atom i (-R_start/2, 0, 0), atom j (+R_start/2, 0, 0)",
        "Pt_q": "round(b sqrt(2 mu E) / R_start)", "Pr_q": "round(-sqrt(2 mu (E - V0) - Pt_q^2))",
        "momenta": "p_j = (Pr_q, Pt_q, 0), p_i = -p_j; round = half-even on FX(96,80), decided exactly",
        "V0": "potential_high(R_start^2, 512), exact", "b": "b_orb (1 + rho), b_orb = orbiting(e)[0]",
        "b_orb_dps": [I.ORBIT_WORK_DPS, I.ORBIT_CANONICAL_DPS]}


class Undecided(ValueError):
    """A rounding the exact enclosure could not separate from a tie (fail-closed)."""


def sqrt_bounds(x: Q) -> tuple[Q, Q]:
    """lo <= sqrt(x) <= hi, rationals with 2^-SQRT_BITS resolution (x >= 0)."""
    n = x.numerator << (2 * SQRT_BITS)
    lo = isqrt(n // x.denominator)
    hi = isqrt(-(-n // x.denominator))
    if hi * hi * x.denominator < n:
        hi += 1
    return Q(lo, 1 << SQRT_BITS), Q(hi, 1 << SQRT_BITS)


def _round_half_even(x: Q) -> int:
    q, r = divmod(x.numerator, x.denominator)
    if 2 * r > x.denominator or (2 * r == x.denominator and q & 1):
        q += 1
    return q


def round_sqrt_ulps(x2: Q) -> int:
    """round_half_even(sqrt(x2)) for x2 >= 0, exact; Undecided if no enclosure separates it from a tie."""
    lo, hi = sqrt_bounds(x2)
    if lo == hi:
        return _round_half_even(lo)
    a, b = _round_half_even(lo), _round_half_even(hi)
    if a != b:
        raise Undecided("rounding of a square root at a tie")
    return a


@functools.lru_cache(maxsize=None)
def shell(e: str) -> Q:
    """2 mu (E - V0), exact."""
    return 2 * I.MU * (Q(e) * DE - C.potential_high(I.R_START ** 2, 512))


def radial_momentum(e: str, pt: Q) -> Q:
    """Pr_q = round(-sqrt(2 mu (E - V0) - pt^2)) for a STORED pt; ValueError if no inbound momentum exists."""
    T = shell(str(e)) - pt * pt
    if T <= 0:
        raise ValueError("no inbound radial momentum at this Pt")
    return -round_sqrt_ulps(T / (MOM_ULP * MOM_ULP)) * MOM_ULP


def canonical_initial_state_b2(e: str, b2: Q) -> dict:
    """The canonical state at E = e De for the impact parameter b = sqrt(b2) (b2 >= 0, exact rational)."""
    e, b2 = str(e), Q(b2)
    pt = round_sqrt_ulps(b2 * 2 * I.MU * Q(e) * DE / (I.R_START ** 2 * MOM_ULP * MOM_ULP)) * MOM_ULP
    pj = (radial_momentum(e, pt), pt, Q(0))
    half = I.R_START / 2
    return {"r_i": (-half, Q(0), Q(0)), "p_i": tuple(-x for x in pj), "r_j": (half, Q(0), Q(0)), "p_j": pj}


def canonical_initial_state(e: str, b: Q) -> dict:
    return canonical_initial_state_b2(e, Q(b) ** 2)


def b_from_state(state: dict, e: str) -> Q:
    """b^2 (exact) the stored state represents at nominal energy e: R_START^2 Pt_q^2 / (2 mu E)."""
    pt = state["p_j"][1]
    return I.R_START ** 2 * pt * pt / (2 * I.MU * Q(str(e)) * DE)


def measurement_state(e: Q, b: Q) -> dict:
    """The canonical state plus what the boundary measurement needs (the same keys c1b1_inner_validation.state
    returned): realized E_rep (midpoint of a 2^-512 enclosure) and its width, L_rep = R_START Pt_q, E_nom."""
    st = canonical_initial_state(str(e), b)
    run = C.new_run(I.POS, 40, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=I.MOM,
                    validated_only=False)
    lo, hi = C.relative_energy_enclosure(run, 512)
    assert lo > 0, "represented state is not a scattering state"
    return {**st, "E_nom": Q(e) * DE, "E_rep": (lo + hi) / 2, "E_rep_width": hi - lo, "L_rep": I.R_START * st["p_j"][1]}
