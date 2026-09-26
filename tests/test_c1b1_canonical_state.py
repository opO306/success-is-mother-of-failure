"""The ONE canonical state generator of C1-B1 (designer verdict on 7532788): Pt is rounded first, Pr is computed from
the stored Pt, and the generator is idempotent on the b a state represents -- exactly, no tolerance:

    S = canonical_initial_state(E, b);  canonical_initial_state_b2(E, b_from_state(S, E)) == S"""
from __future__ import annotations

from fractions import Fraction as Q

import pytest

import a_reference.c1b1_canonical_state as G
import a_reference.c1b1_inner_validation as I

ENERGIES = ("3/20", "1/5", "3/10", "1/2", "7/10", "9/10", "99/100")
RHOS = (Q(-99, 100), Q(-1, 5), Q(-1, 100), Q(-5, 1000), Q(-3, 10000), Q(-1, 10 ** 6), Q(0),
        Q(1, 10 ** 6), Q(123, 10 ** 6), Q(1, 100), Q(3, 100))


@pytest.mark.parametrize("e", ENERGIES)
def test_the_generator_is_idempotent_on_its_own_b(e) -> None:
    bo = I.orbiting(Q(e))[0]
    for rho in RHOS:
        S = G.canonical_initial_state(e, bo * (1 + rho))
        assert G.canonical_initial_state_b2(e, G.b_from_state(S, e)) == S, rho


def test_pt_is_projected_first_and_pr_is_computed_from_the_stored_pt() -> None:
    e, b = "1/2", I.orbiting(Q(1, 2))[0] * Q(995, 1000)
    S = G.canonical_initial_state(e, b)
    pr, pt, pz = S["p_j"]
    assert pz == 0 and S["p_i"] == (-pr, -pt, Q(0)) and S["r_i"] == (-I.R_START / 2, Q(0), Q(0))
    assert (pt / G.MOM_ULP).denominator == 1 and (pr / G.MOM_ULP).denominator == 1          # on the FX(96,80) grid
    target = b * b * 2 * I.MU * Q(e) * G.DE / I.R_START ** 2                                  # Pt_target^2
    assert (pt - G.MOM_ULP / 2) ** 2 <= target <= (pt + G.MOM_ULP / 2) ** 2                   # Pt = round(Pt_target)
    T = G.shell(e) - pt * pt                                                                  # from the STORED Pt
    assert (pr + G.MOM_ULP / 2) ** 2 <= T <= (pr - G.MOM_ULP / 2) ** 2 and pr < 0             # Pr = round(-sqrt(T))


def test_rounding_is_exact_and_refuses_ties() -> None:
    assert G.round_sqrt_ulps(Q(9)) == 3 and G.round_sqrt_ulps(Q(25, 4)) == 2 and G.round_sqrt_ulps(Q(49, 4)) == 4
    assert G.round_sqrt_ulps(Q(2)) == 1 and G.round_sqrt_ulps(Q(3)) == 2
    with pytest.raises(ValueError):
        G.radial_momentum("1/2", Q(10))                                                        # no inbound momentum
