"""Method bench S1: closed forms vs independent quadrature, convergence orders, planted faults, determinism."""
import ast
from pathlib import Path

import mpmath as mm
import pytest

from c1b1_method_bench import exact, methods
from c1b1_method_bench.potentials import DE, MU, Coulomb, Free, InvSquare, force
from c1b1_method_bench.run import R0, run

PKG = Path(__file__).resolve().parents[1] / 'c1b1_method_bench'


def quad_reference(V, mu, E, L, r1):
    """Radial quadrature with r = r_turn + u^2 (no closed form used).

    Run at 90 digits: a turning-point error d shifts the integral by O(sqrt(d)), so a 40-digit root
    (d ~ 1e-40) limits the reference to ~1e-20 (S1 first run, 9 failures of ~5.6e-21 even for free flight).
    """
    with mm.workdps(90):
        return [mm.mpf(x) for x in _quad_reference(V, mu, mm.mpf(E), mm.mpf(L), mm.mpf(r1))]


def _quad_reference(V, mu, E, L, r1):
    g = lambda r: 2 * mu * (E - V(r)) - L * L / (r * r)
    lo, hi = mm.mpf('1e-6'), mm.mpf(R0)
    for _ in range(600):
        mid = (lo + hi) / 2
        if g(mid) > 0: hi = mid
        else: lo = mid
    rt = (lo + hi) / 2
    def leg(R, kind):
        f = lambda u: 2 * u * ((L / (rt + u * u) ** 2) if kind == 'angle' else mu) / mm.sqrt(g(rt + u * u))
        return mm.quad(f, [0, mm.sqrt(R - rt) / 4, mm.sqrt(R - rt)])
    return leg(R0, 'angle') + leg(r1, 'angle'), leg(R0, 'time') + leg(r1, 'time'), rt


@pytest.mark.parametrize('pot,form', [(InvSquare(), 'inv'), (Coulomb(), 'coul'), (Free(), 'free')])
@pytest.mark.parametrize('e,b', [(2, 6), (10, 3), (mm.mpf('0.5'), 10)])
def test_closed_forms_match_quadrature(pot, form, e, b):
    with mm.workdps(40):
        E = e * DE; L = b * mm.sqrt(2 * MU * E); r1 = mm.mpf('20.013')
        if form == 'inv': ref = exact.inv_square(pot.alpha, MU, E, L, R0, r1)
        elif form == 'coul': ref = exact.coulomb(pot.alpha, MU, E, L, R0, r1)
        else: ref = exact.free(MU, E, L, R0, r1)
        sweep, time, rt = quad_reference(pot.V, MU, E, L, r1)
        assert abs(ref['sweep'] - sweep) < mm.mpf('1e-25')
        assert abs(ref['time'] - time) / time < mm.mpf('1e-25')
        assert abs(ref['r_turn'] - rt) < mm.mpf('1e-25')


def test_planted_closed_form_fault_is_detected():
    """A wrong K (mass factor dropped) must disagree with the quadrature."""
    with mm.workdps(40):
        pot = InvSquare(); E = 2 * DE; L = 6 * mm.sqrt(2 * MU * E); r1 = mm.mpf(R0)
        p = mm.sqrt(2 * MU * E); K = mm.sqrt(L * L + 2 * pot.alpha)
        wrong = (L / K) * (mm.acos(K / (p * R0)) + mm.acos(K / (p * r1)))
        sweep, _, _ = quad_reference(pot.V, MU, E, L, r1)
        assert abs(wrong - sweep) > mm.mpf('1e-3')


def test_free_flight_has_no_integrator_error():
    out = run(Free(), 'kdk', 2 * DE, 6, 40)
    assert out['status'] == 'ok'
    assert out['err_chi'] < 1e-30 and out['err_sweep'] < 1e-30


def errors(method, hs, pot=None, e=2, b=6):
    pot = pot or InvSquare()
    return [run(pot, method, e * DE, b, h)['err_sweep'] for h in hs]


@pytest.mark.parametrize('pot', [InvSquare(), Coulomb()])
def test_kdk_second_order(pot):
    e = errors('kdk', [80, 40, 20], pot)
    assert 3.3 < e[0] / e[1] < 4.7 and 3.3 < e[1] / e[2] < 4.7


@pytest.mark.parametrize('method', ['yoshida4', 'chin4a'])
@pytest.mark.parametrize('pot', [InvSquare(), Coulomb()])
def test_fourth_order(method, pot):
    e = errors(method, [160, 80, 40], pot)
    assert 12 < e[0] / e[1] < 20 and 12 < e[1] / e[2] < 20


def test_planted_kdk_missing_half_kick_is_detected():
    def broken(pot, q, p, h, mu):
        f = force(pot, q)
        p = [p[0] + h / 2 * f[0], p[1] + h / 2 * f[1]]
        return [q[0] + h * p[0] / mu, q[1] + h * p[1] / mu], p
    good = run(InvSquare(), 'kdk', 2 * DE, 6, 40)['err_sweep']
    bad = run(InvSquare(), 'kdk', 2 * DE, 6, 40, step=broken)['err_sweep']
    assert bad > 100 * good


def test_planted_chin_gradient_sign_is_detected():
    """Flipping the force-gradient sign must drop Chin 4A from fourth to second order."""
    flipped = lambda pot, q, p, h, mu: _chin_with_sign(pot, q, p, h, mu, -1)
    e = [run(InvSquare(), 'chin4a', 2 * DE, 6, h, step=flipped)['err_sweep'] for h in (160, 80)]
    assert e[0] / e[1] < 8


def _chin_with_sign(pot, q, p, h, mu, sign):
    """Separate hand-written Chin 4A with a selectable gradient-term sign (+1 = published)."""
    f = force(pot, q)
    p = [p[0] + h / 6 * f[0], p[1] + h / 6 * f[1]]
    q = [q[0] + h / 2 * p[0] / mu, q[1] + h / 2 * p[1] / mu]
    r = mm.sqrt(q[0] ** 2 + q[1] ** 2); d1 = pot.dV(r)
    c = -d1 / r + sign * h * h * d1 * pot.d2V(r) / (24 * mu * r)
    p = [p[0] + 2 * h / 3 * c * q[0], p[1] + 2 * h / 3 * c * q[1]]
    q = [q[0] + h / 2 * p[0] / mu, q[1] + h / 2 * p[1] / mu]
    f = force(pot, q)
    return q, [p[0] + h / 6 * f[0], p[1] + h / 6 * f[1]]


def test_chin_reference_sign_matches_bench_implementation():
    a = run(InvSquare(), 'chin4a', 2 * DE, 6, 80)
    b = run(InvSquare(), 'chin4a', 2 * DE, 6, 80, step=lambda *x: _chin_with_sign(*x, 1))
    assert a['sweep'] == b['sweep']


def test_planted_yoshida_swapped_weights_is_detected():
    def swapped(pot, q, p, h, mu):
        w, z = methods.yoshida_weights()
        for c in (z, w, z):
            q, p = methods.kdk(pot, q, p, c * h, mu)
        return q, p
    good = run(InvSquare(), 'yoshida4', 2 * DE, 6, 40)['err_sweep']
    bad = run(InvSquare(), 'yoshida4', 2 * DE, 6, 40, step=swapped, max_steps=20000)   # net step < 0: never exits
    assert bad['status'] != 'ok' or bad['err_sweep'] > 1000 * good


def test_yoshida_weights_match_sealed_benchmark():
    from c1b1_integrator_benchmark.methods import coefficients
    with mm.workdps(40):
        w, z = methods.yoshida_weights()
        sealed = coefficients()['yoshida4']
        assert abs(sealed['drift'][0] - w) < mm.mpf('1e-35') and abs(sealed['drift'][1] - z) < mm.mpf('1e-35')


def test_kdk_time_reversible():
    with mm.workdps(40):
        pot = InvSquare(); q = [mm.mpf(9), mm.mpf(2)]; p = [mm.mpf(-3), mm.mpf('0.5')]
        q1, p1 = methods.kdk(pot, q, p, mm.mpf(40), MU)
        q2, p2 = methods.kdk(pot, q1, p1, mm.mpf(-40), MU)
        assert max(abs(a - b) for a, b in zip(q + p, q2 + p2)) < mm.mpf('1e-30')


def test_deterministic_repeat():
    assert run(Coulomb(), 'chin4a', 10 * DE, 3, 40) == run(Coulomb(), 'chin4a', 10 * DE, 3, 40)


def test_package_imports_no_production_or_reference_code():
    banned = ('a_reference', 'a_numeric', 'engine', 'audit', 'c1b1_integrator_benchmark', 'c1b1_o1', 'c1b1_replay')
    for path in PKG.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ''] if isinstance(node, ast.ImportFrom) else []
            assert not any(n.split('.')[0] in banned for n in names), (path.name, names)
