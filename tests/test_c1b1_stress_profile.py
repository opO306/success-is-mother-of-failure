"""Read-only per-decision profile of the C1-B1 stress survey: it must observe, never change, and its records must be
consistent with how _decide works (a boundary inside the 128-bit enclosure is exactly what forces 256 bits)."""
from fractions import Fraction as Q

from a_reference import c1b1_stress_profile as P
from a_reference import c1b1_stress_survey as X
from a_reference import c1b1_two_atom as C


def _sp(e=Q(1, 2), bf=Q(1, 2), steps=40):
    return X.spec('grid', 't', X.canonical(e, bf * X.RE), steps)


def test_flog2_is_exact():
    assert [X._flog2(Q(x)) for x in (1, 2, 3, 4, Q(1, 2), Q(3, 4), Q(1, 3))] == [0, 1, 1, 2, -1, -1, -2]
    assert X._flog2(Q(0)) is None


def test_profile_does_not_change_the_trajectory_and_restores_impulse():
    impulse = C.impulse
    plain = X.run_trajectory(_sp(), trace=True)
    prof = X.run_trajectory(_sp(), trace=True, profile=True)
    assert C.impulse is impulse
    assert prof['trace'] == plain['trace'] and prof['decisions'] == plain['decisions']
    assert sum(v for _, v in prof['profile']['bins']) == prof['decide_calls']


def test_profile_records_are_consistent_with_the_decision_rule():
    rec = X.run_trajectory(_sp(Q(9), Q(1, 2), 400), profile=True)
    seen = set()
    for (M, axis, rbin, w128, dlog), v in rec['profile']['bins']:
        seen.add(M)
        assert axis in (0, 1) and rbin is not None and 6 <= rbin <= 60
        if dlog == 'tie':
            continue
        if M == 128:      # decided at 128: the boundary lies outside the 128-bit enclosure, d > w/2
            assert dlog >= w128 - 1
        else:             # needed 256: a boundary lies inside the 128-bit enclosure, d <= w128/2 (+ tiny)
            assert dlog <= w128
    assert 128 in seen


def test_head_on_decides_only_the_x_axis():
    rec = X.run_trajectory(X.spec('headon', 't', X.canonical(Q(1, 2), Q(0)), 30), profile=True)
    assert {k[1] for k, _ in rec['profile']['bins']} == {0}


def test_hard_case_point_profile():
    s, n = X.hard_case_points((18,))[0]
    rec = P._point_job((s, n))
    assert rec['end'] == 'decided' and rec['profile']['bins'][0][0][0] == 256
    t = P.combine([rec])
    assert t['decisions'] == 1 and t['hardest_10'][0]['kind'] == 'hard_case'
