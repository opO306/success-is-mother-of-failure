"""Method bench S2: quadrature reference, T4 wall orders, adaptive KDK, modified-Hamiltonian predictor (+ planted faults)."""
import functools

import mpmath as mm
import pytest

from c1b1_method_bench import exact, quadref
from c1b1_method_bench.methods import adaptive_kdk, kdk
from c1b1_method_bench.potentials import DE, MU, Coulomb, ExpWall, InvSquare
from c1b1_method_bench.run import R0, run


@pytest.mark.parametrize('pot,form', [(InvSquare(), 'inv'), (Coulomb(), 'coul')])
def test_quadref_matches_closed_forms(pot, form):
    with mm.workdps(60):
        E = 2 * DE; L = 6 * mm.sqrt(2 * MU * E); r1 = mm.mpf('20.004')
        ref = (exact.inv_square if form == 'inv' else exact.coulomb)(pot.alpha, MU, E, L, R0, r1)
        q = quadref.reference(pot, MU, E, L, r1)
        assert abs(q['sweep'] - ref['sweep']) < mm.mpf('1e-28')
        assert abs(q['time'] - ref['time']) / ref['time'] < mm.mpf('1e-28')


def test_quadref_t4_precision_stable():
    pot = ExpWall(); E = 20 * DE; L = 2 * mm.sqrt(2 * MU * E)
    a = quadref.reference(pot, MU, E, L, mm.mpf(20))
    old = quadref.DPS
    try:
        quadref.DPS = 80
        b = quadref.reference(pot, MU, E, L, mm.mpf(20))
    finally:
        quadref.DPS = old
    assert abs(a['sweep'] - b['sweep']) < mm.mpf('1e-30')


def test_t4_kdk_second_and_chin_fourth_order():
    e = [run(ExpWall(), 'kdk', 20 * DE, 2, h)['err_sweep'] for h in (40, 20, 10)]
    assert 3.3 < e[0] / e[1] < 4.7 and 3.3 < e[1] / e[2] < 4.7
    c = [run(ExpWall(), 'chin4a', 20 * DE, 2, h)['err_sweep'] for h in (80, 40)]
    assert 12 < c[0] / c[1] < 20


def test_adaptive_deterministic_and_tightening_helps():
    step = lambda tol: functools.partial(adaptive_kdk, tol=mm.mpf(tol), h_min=mm.mpf(40) / 1024)
    a = run(ExpWall(), 'adaptive', 20 * DE, 2, 40, step=step('1e-9'))
    assert a == run(ExpWall(), 'adaptive', 20 * DE, 2, 40, step=step('1e-9'))
    b = run(ExpWall(), 'adaptive', 20 * DE, 2, 40, step=step('1e-11'))
    assert b['err_sweep'] < a['err_sweep'] and b['n_force'] > a['n_force']


def test_planted_adaptive_estimator_fault_is_detected():
    """An estimator that never splits degenerates to KDK h=20; the real one at a tight tolerance must beat it."""
    never = functools.partial(adaptive_kdk, tol=mm.mpf('1e9'), h_min=mm.mpf(40) / 1024)
    real = functools.partial(adaptive_kdk, tol=mm.mpf('1e-11'), h_min=mm.mpf(40) / 1024)
    k20 = run(ExpWall(), 'kdk', 20 * DE, 2, 20)['sweep']
    assert run(ExpWall(), 'adaptive', 20 * DE, 2, 40, step=never)['sweep'] == k20
    assert run(ExpWall(), 'adaptive', 20 * DE, 2, 40, step=real)['err_sweep'] < \
        run(ExpWall(), 'kdk', 20 * DE, 2, 20)['err_sweep'] / 10


def _predict(pot, e, b, h):
    row = run(pot, 'kdk', e * DE, b, h)
    mod = quadref.kdk_modified(pot, MU, row['q0'], row['p0'], h, row['r_exit'])
    E = e * DE; L = mm.mpf(b) * mm.sqrt(2 * MU * E)
    true = quadref.reference(pot, MU, E, L, row['r_exit'])
    with mm.workdps(60):
        return row['d_sweep'], float(mod['sweep'] - true['sweep'])


@pytest.mark.parametrize('pot,e,b', [(InvSquare(), 2, 6), (ExpWall(), 20, 2)])
def test_modified_hamiltonian_predicts_kdk_error(pot, e, b):
    measured, predicted = _predict(pot, e, b, 20)
    assert abs(measured / predicted - 1) < 0.05


def test_planted_predictor_sign_fault_is_detected():
    """Flipping the sign of U'' inside H3 (the U'' p_r^2 term) must spoil the prediction."""
    pot = ExpWall(); e, b, h = 20, 2, 20
    row = run(pot, 'kdk', e * DE, b, h)
    E = e * DE; L = mm.mpf(b) * mm.sqrt(2 * MU * E)
    true = quadref.reference(pot, MU, E, L, row['r_exit'])
    orig = quadref.kdk_modified
    def faulty(pot, mu, q0, p0, h, r1):
        wrapped = type('W', (), dict(V=pot.V, dV=pot.dV, d2V=lambda self, r: -pot.d2V(r)))()
        return orig(wrapped, mu, q0, p0, h, r1)
    with mm.workdps(60):
        bad = float(faulty(pot, MU, row['q0'], row['p0'], h, row['r_exit'])['sweep'] - true['sweep'])
    assert abs(row['d_sweep'] / bad - 1) > 0.2


def test_s2_failure_case_now_real_and_matches_measurement():
    """Regression for the S2 M7 error (T3 Coulomb, 2 De, b = 6, h = 40): result must be real and predict KDK."""
    measured, predicted = _predict(Coulomb(), 2, 6, 40)
    assert isinstance(predicted, float) and abs(measured / predicted - 1) < 0.01


def test_complex_quadrature_fails_closed(monkeypatch):
    """A turning point placed below the true root (p_r^2 < 0 near it) must raise, not return a complex number."""
    pr2 = lambda r: 1 - 4 / (r * r)                       # true turning point r = 2
    monkeypatch.setattr(quadref, 'turning', lambda f, r0: mm.mpf('1.9'))
    with mm.workdps(40):
        with pytest.raises(ValueError):
            quadref.legs(pr2, lambda r, pr: 1 / pr, lambda r, pr: 1 / pr, mm.mpf(20), mm.mpf(20))
