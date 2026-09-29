"""D4: the rigorous |J| upper bound (a_reference/c1b1_impulse_magnitude_bound.py). The full cover runs once as evidence in
runs/; these tests check the construction and plant defects: the cover is gap-free and spans [r_min, 2^49], each interval
enclosure contains independent point values of V', the edge constant is the FX(96,80) half-ulp overflow edge, and a cover
with a gap or an enclosure that misses a point value is caught.
"""
from fractions import Fraction as Q

import mpmath as mp
import pytest

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_impulse_magnitude_bound as B
import a_reference.c1b1_point_prover as P


def test_the_cover_spans_r_min_to_2_49_without_gaps_or_overlap_beyond_end_points():
    cov = B.cover()
    assert cov[0][0] == B.R_MIN == Q("1.2") / Q("0.529177210903") and cov[-1][1] == B.R_TOP == Q(1 << 49)
    assert all(a < b for a, b in cov)
    assert all(cov[i][1] == cov[i + 1][0] for i in range(len(cov) - 1))


def test_every_fx_relative_position_is_below_r_top():
    biggest = Q(3 * ((1 << 96) - 1) ** 2, 1 << 96)                   # R^2 of the largest |dr_raw| < 2^96 per axis
    assert biggest < B.R_TOP ** 2


def test_the_edge_is_the_fx_96_80_overflow_edge():
    assert B.EDGE == (Q(P.RAW_MAX) + Q(1, 2)) / (1 << 80)


def _mp_dv(R):
    with mp.workdps(60):
        dv, _ = P._dv_mp(Q(R) ** 2)
        return dv


@pytest.mark.parametrize("a,b", [(B.R_MIN, Q(229, 100)), (Q(7), Q(7) + Q(1, 64)), (Q(31), Q(32)), (Q(1000), Q(1250)),
                                 (Q(10 ** 9), Q(10 ** 9) * Q(5, 4))])
def test_each_interval_enclosure_contains_independent_point_values(a, b):
    ctx = K2._Ctx(K2.Limits(seconds_max=10 ** 9, bits_max=10 ** 9, order_max=10 ** 6))
    dv = B.dv_enclosure(a, b, ctx)
    for t in (Q(0), Q(1, 3), Q(1, 2), Q(1)):
        R = a + (b - a) * t
        v = _mp_dv(R)
        assert dv.lo <= Q(str(mp.nstr(v, 40, strip_zeros=False))) + Q(1, 10 ** 30) and \
            Q(str(mp.nstr(v, 40, strip_zeros=False))) - Q(1, 10 ** 30) <= dv.hi, (a, b, t)


def test_a_planted_gap_in_the_cover_is_caught(monkeypatch):
    real = B.cover

    def gapped():
        cov = real()
        return cov[:5] + cov[6:]
    monkeypatch.setattr(B, "cover", gapped)
    with pytest.raises(AssertionError, match="gap"):
        B.bound()


def test_the_adaptive_leaves_of_the_hardest_interval_are_gap_free_below_target_and_contain_point_values():
    """The first cover interval (at r_min) is where cancelling terms made a uniform 1/64 cover overestimate |V'| by a
    factor ~1000 (first run kept in runs/, it failed the edge). The adaptive leaves must tile it and bound it."""
    ctx = K2._Ctx(K2.Limits(seconds_max=10 ** 9, bits_max=10 ** 9, order_max=10 ** 6))
    a, b = B.cover()[0]
    leaves = B._leaves(a, b, ctx)
    assert leaves[0][0] == a and leaves[-1][1] == b
    assert all(leaves[i][1] == leaves[i + 1][0] for i in range(len(leaves) - 1))
    assert len(leaves) > 1 and all(m <= B.TARGET for _, _, m in leaves)
    for lo, hi, m in leaves[:: max(1, len(leaves) // 5)]:
        assert abs(Q(str(mp.nstr(_mp_dv((lo + hi) / 2), 30)))) <= m


def test_the_bound_constants_give_the_claimed_margin():
    assert B.TARGET * B.DT_KICK < B.EDGE / 20            # the leaf target alone keeps |J| under 5% of the edge
