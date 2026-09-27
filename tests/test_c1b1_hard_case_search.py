"""④-4c-5 shell-18 hard-case search survey: completeness against brute force,
rigorous interpolation bounds, fault injection and generator/checker separation.

survey_only: nothing here certifies a region or changes ④-4b.
"""
import ast
import json
from fractions import Fraction as F
from pathlib import Path

import pytest

from a_reference import c1b1_hard_case_search as H
from a_reference import c1b1_hard_case_checker as C
from a_reference import c1b1_hard_case_survey as V

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'a_reference/fixtures/c1b1_hard_case_survey_v1.json'
SYN = V.SYNTHETIC
TAU = F(1, 100)
# a quadratic-like target with an interior maximum near n=1500
PEAK = ({3: -1, 2: 3000, 0: 7}, {1: 2000, 0: 1})
# exactly linear (zero curvature, delta = 0) with hazards exactly on the threshold
LINE = ({1: 1}, {0: 7})
# curvature grows 65-fold across the first block: a left-endpoint bound is too small
CUBE = ({3: 1}, {0: 10**7})


def _found(rows):
    return [iv for r in rows for iv in r['candidate_intervals']]


def _missed(p, q, degree, points, lo=1, hi=5000, tau=TAU):
    rows = H.search(H.Target(p, q), lo, hi, tau, degree, points, hi)
    return C.compare_with_brute_force(C.Rational(p, q), lo, hi, tau, _found(rows))


@pytest.fixture(scope='module')
def shell():
    return H.load_shell()


def test_interpolation_constants_are_upper_bounds():
    assert 27*H.W3*H.W3 >= 4 and H.W3-F(3849, 10000) < F(1, 10000)
    # u = t^2-3t on [0,3] ranges over [-9/4, 0]; u(u+2) >= -1 and <= 9/16
    grid = [F(i, 400) for i in range(1201)]
    assert max(abs(t*(t-1)*(t-2)*(t-3)) for t in grid) <= H.W4
    grid = [F(i, 600) for i in range(1201)]
    assert max(abs(t*(t-1)*(t-2)) for t in grid) <= H.W3


@pytest.mark.parametrize('degree,points', [(1, 65), (2, 65), (2, 33)])
@pytest.mark.parametrize('index', range(3))
def test_interpolant_stays_within_the_rigorous_error(index, degree, points):
    target = H.Target(*SYN[index])
    for a in (1, 700, 2300, 4800):
        b = a+points-1
        bound = H.derivative_bound(target, degree+1, a, b)
        delta = H.interpolation_error(degree, bound, b-a)
        y = {n: target.value(n) for n in range(a, b+1)}
        if degree == 1:
            q = {n: y[a]+(y[b]-y[a])*(n-a)/(b-a) for n in y}
        else:
            h = (b-a)//2
            c2 = (y[b]-2*y[a+h]+y[a])/(2*h*h)
            c1 = (y[a+h]-y[a])/h-c2*h
            q = {n: y[a]+c1*(n-a)+c2*(n-a)**2 for n in y}
        assert max(abs(y[n]-q[n]) for n in y) <= delta


def test_ratio_bound_encloses_every_derivative_value(shell):
    target = H.Target(*SYN[2])
    for k in (2, 3):
        bound = H.derivative_bound(target, k, 40, 140)
        assert all(abs(F(H.at(target.numerators[k], n), H.at(target.q, n)**(k+1))) <= bound for n in range(40, 141))
    real, lo, hi, _, _ = shell
    a, b = lo+10**15, lo+10**15+2**40
    bound = H.derivative_bound(real, 3, a, b)
    for n in (a, (a+b)//2, b):
        assert abs(F(H.at(real.numerators[3], n), H.at(real.q, n)**4)) <= bound


def test_checker_numerators_and_bounds_agree_with_generator():
    for p, q in SYN:
        g, c = H.Target(p, q), C.Rational(p, q)
        assert all(g.numerators[k] == c.num[k] for k in range(5))
        assert H.derivative_bound(g, 3, 10, 400) == C.ratio_bound(c, 3, 10, 400)


@pytest.mark.parametrize('degree,points', V.POLICY['synthetic_settings'])
@pytest.mark.parametrize('index', range(3))
def test_synthetic_search_misses_nothing_and_checker_agrees(index, degree, points):
    p, q = SYN[index]
    rows = H.search(H.Target(p, q), 1, 5000, TAU, degree, points, 5000)
    C.verify_rows(C.Rational(p, q), 1, 5000, TAU, degree, points, 5000, rows)
    result = C.compare_with_brute_force(C.Rational(p, q), 1, 5000, TAU, _found(rows))
    assert result['hazards'] > 0 and result['missed'] == 0


def test_non_monotone_quadratic_blocks_are_split_not_trusted():
    rows = H.search(H.Target(*PEAK), 1, 3000, TAU, 2, 257, 3000)
    result = C.compare_with_brute_force(C.Rational(*PEAK), 1, 3000, TAU, _found(rows))
    assert result['hazards'] > 0 and result['missed'] == 0
    assert sum(r['pieces'] for r in rows) > sum(r['blocks'] for r in rows)


def test_real_shell18_windows_have_hazards_and_no_miss(shell):
    target, lo, hi, _, _ = shell
    chk = C.frozen_target()
    for i in (0, 5):
        centre, slope = V._crossing_near(target, lo+(hi-lo)*(2*i+1)//16)
        a, b, tau = centre-1024, centre+1023, slope*64
        for degree, points in ((1, 257), (2, 513)):
            rows = H.search(target, a, b, tau, degree, points, 1)
            C.verify_rows(chk, a, b, tau, degree, points, 1, rows)
            result = C.compare_with_brute_force(chk, a, b, tau, _found(rows))
            assert result['hazards'] >= 64 and result['missed'] == 0


def test_guess_never_changes_the_bracket_answer():
    pred = lambda t: t*t >= 5000
    truth = H._first(0, 1000, pred)
    assert truth == 71
    assert all(H._first(0, 1000, pred, g) == truth for g in (-50, 0, 3, 70, 71, 72, 500, 999, 5000))
    assert H._first(0, 10, lambda t: False, 4) == 11 and H._first(0, 10, lambda t: True, 7) == 0


def test_dyadic_threshold_only_grows():
    for x in (F(1, 3), F(7, 2**300), F(-5, 7), F(2**-40)*F(10**40, 3**50)):
        up = H.dyadic_up(x)
        assert up >= x and up-x < F(1, 2**H.DYADIC_BITS) and (up*2**H.DYADIC_BITS).denominator == 1


def test_exact_distance_matches_between_generator_and_checker(shell):
    target, lo, hi, _, _ = shell
    chk = C.frozen_target()
    for n in (lo, lo+12345, (lo+hi)//2, hi):
        assert target.distance(n) == chk.half_distance(n)
    for p, q in SYN:
        g, c = H.Target(p, q), C.Rational(p, q)
        assert all(g.distance(n) == c.half_distance(n) for n in range(1, 400))


# ---- fault injection: each broken generator must miss a real hazard ----

def _any_miss(settings):
    return any(_missed(*SYN[i], d, pts)['missed'] for i in range(3) for d, pts in settings)


def test_fault_dropping_interpolation_error_is_caught(monkeypatch):
    monkeypatch.setattr(H, 'interpolation_error', lambda degree, bound, length: F(0))
    assert _any_miss(((1, 65), (2, 65)))


def test_honest_search_on_fault_toys_misses_nothing():
    for degree in (1, 2):
        line = _missed(*LINE, degree, 65, tau=F(1, 7))
        cube = _missed(*CUBE, degree, 257, hi=3000)
        assert line['hazards'] > 1000 and line['missed'] == 0
        assert cube['hazards'] > 40 and cube['missed'] == 0


def test_fault_off_by_one_interval_end_is_caught(monkeypatch):
    original = H._interval
    monkeypatch.setattr(H, '_interval', lambda a, t_lo, t_hi, length: original(a, t_lo, t_hi-1, length))
    assert all(_missed(*LINE, degree, 65, tau=F(1, 7))['missed'] for degree in (1, 2))


def test_fault_derivative_bound_from_left_endpoint_only_is_caught(monkeypatch):
    def endpoint(target, k, a, b):
        return abs(F(H.at(target.numerators[k], a), H.at(target.q, a)**(k+1)))
    monkeypatch.setattr(H, 'derivative_bound', endpoint)
    assert _missed(*CUBE, 1, 65, hi=3000)['missed'] > 0


def test_fault_trusting_a_non_monotone_quadratic_is_caught(monkeypatch):
    original = H.quadratic_block

    def trusting(target, a, b, tau, bound):
        found = original(target, a, b, tau, bound)
        return found if found is not None else {'kind': 'quadratic', 'a': a, 'b': b, 'crossings': 0,
                                                'delta': F(0), 'intervals': []}
    monkeypatch.setattr(H, 'quadratic_block', trusting)
    rows = H.search(H.Target(*PEAK), 1, 3000, TAU, 2, 257, 3000)
    assert C.compare_with_brute_force(C.Rational(*PEAK), 1, 3000, TAU, _found(rows))['missed'] > 0


def test_checker_rejects_tampered_rows():
    p, q = SYN[0]
    rows = H.search(H.Target(p, q), 1, 5000, TAU, 2, 65, 64)
    chk = C.Rational(p, q)
    C.verify_rows(chk, 1, 5000, TAU, 2, 65, 64, rows)
    victim = next(i for i, r in enumerate(rows) if r['candidate_intervals'])
    tamper = [
        lambda r: r[victim].update(candidate_intervals=r[victim]['candidate_intervals'][1:]),
        lambda r: r[victim].update(derivative_bound=r[victim]['derivative_bound']/2),
        lambda r: r[victim].update(crossings=r[victim]['crossings']+1),
        lambda r: r.pop(),
        lambda r: r[0].update(superblock=(r[0]['superblock'][0]+1, r[0]['superblock'][1])),
    ]
    for change in tamper:
        bad = [dict(r) for r in rows]
        change(bad)
        with pytest.raises(H.O.NotCertified):
            C.verify_rows(chk, 1, 5000, TAU, 2, 65, 64, bad)


def test_checker_does_not_import_the_generator_or_driver():
    tree = ast.parse((ROOT/'a_reference/c1b1_hard_case_checker.py').read_text(encoding='utf-8'))
    names = {a.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for a in node.names}
    assert not names & {'c1b1_hard_case_search', 'c1b1_hard_case_survey'}


# ---- fixture: survey status and reproduction of stored rows ----

@pytest.fixture(scope='module')
def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_fixture_keeps_every_certification_state(fixture):
    assert fixture['status'] == 'survey_only' and fixture['global_4_4b'] == 'NotCertified'
    assert fixture['new_certified_regions'] == 0 and fixture['coverage_modified'] is False
    assert fixture['precision_cap'] == 16384 and fixture['extended_to_other_shells'] is False
    assert fixture['prior_coverage'] == {'used_regions': 11, 'region_budget': 64, 'gap_count': 84}


def test_fixture_full_run_is_internally_consistent(fixture):
    run = fixture['full_run']
    assert run['checker_superblocks_agree'] == run['superblocks'] == V.POLICY['full_run_superblocks']
    assert run['exact_recheck_count'] == run['candidate_count'] == run['independent_recheck']['exact_recheck_count']
    assert run['false_positive_count']+len(run['hazards']) == run['exact_recheck_count']
    assert run['independent_recheck']['hazards'] == len(run['hazards'])
    assert abs(run['crossings']-run['half_ulp_fixture_boundary_count']) <= run['blocks']
    assert all(s['missed'] == 0 and s['hazards'] > 0 for s in fixture['synthetic_brute_force'])
    assert all(s['missed'] == 0 and s['hazards'] > 0 for s in fixture['shell18_window_brute_force'])


def test_fixture_rows_reproduce_at_both_ends(fixture, shell):
    target, _, _, guard, _ = shell
    stored = fixture['superblock_rows']
    for row in (stored[0], stored[-1]):
        a0, b0 = row['superblock']
        mine = H.run_superblock(target, a0, b0, guard, 2, V.POLICY['full_run_points'])
        assert str(mine['derivative_bound']) == row['derivative_bound']
        assert mine['crossings'] == row['crossings'] and mine['record_sha256'] == row['record_sha256']
        assert [list(x) for x in mine['candidate_intervals']] == row['candidate_intervals']


def test_fixture_cost_table_reproduces(fixture, shell):
    target, lo, hi, guard, _ = shell
    bounds = V.derivative_table(target, lo, hi)
    table = V.cost_table(bounds, hi-lo+1, guard)
    assert json.loads(json.dumps(H.D.serial(table))) == fixture['cost_table']
