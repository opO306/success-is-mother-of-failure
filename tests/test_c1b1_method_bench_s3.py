"""Method bench S3: orbiting potentials, barrier-top orbit, near-separatrix reference stability (+ planted fault)."""
import mpmath as mm
import pytest

from c1b1_method_bench import orbit, quadref
from c1b1_method_bench.potentials import DE, MU, LennardJones, Morse
from c1b1_method_bench.run import run


@pytest.mark.parametrize('pot', [Morse(), LennardJones()])
def test_derivatives_match_numerical(pot):
    with mm.workdps(50):
        for r in (mm.mpf(5), mm.mpf('7.3'), mm.mpf(12)):
            assert abs(pot.dV(r) - mm.diff(pot.V, r)) < mm.mpf('1e-35')
            assert abs(pot.d2V(r) - mm.diff(pot.V, r, 2)) < mm.mpf('1e-30')


@pytest.mark.parametrize('pot', [Morse(), LennardJones()])
@pytest.mark.parametrize('frac', ['0.3', '0.9'])
def test_orbit_is_unstable_barrier_top(pot, frac):
    with mm.workdps(50):
        E = orbit.e_max(pot) * mm.mpf(frac)
        o = orbit.orbit(pot, MU, E)
        r, L = o['r_star'], o['L']
        veff = lambda x: pot.V(x) + L * L / (2 * MU * x * x)
        assert abs(veff(r) - E) < mm.mpf('1e-40') * DE
        assert abs(mm.diff(veff, r)) < mm.mpf('1e-40')
        assert mm.diff(veff, r, 2) < 0


def test_planted_stable_root_is_rejected():
    """The other root of V + r V'/2 = E is a STABLE circular orbit; picking it must be detectable."""
    pot = LennardJones()
    with mm.workdps(50):
        E = orbit.e_max(pot) * mm.mpf('0.6')
        o = orbit.orbit(pot, MU, E)
        rs = [orbit.RE + (40 - orbit.RE) * mm.mpf(k) / 4000 for k in range(4001)]
        roots = [a for a, b in zip(rs, rs[1:]) if (orbit.g(pot, a) - E) * (orbit.g(pot, b) - E) < 0]
        assert len(roots) == 2
        other = min(roots, key=lambda x: -abs(x - o['r_star']))
        assert pot.d2V(other) + 3 * pot.dV(other) / other > 0


def test_near_separatrix_reference_precision_stable():
    pot = LennardJones()
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf('0.6')
        b = orbit.orbit(pot, MU, E)['b_orb'] * (1 - mm.mpf('1e-4'))
        L = b * mm.sqrt(2 * MU * E)
    a = quadref.reference(pot, MU, E, L, mm.mpf(20))
    old = quadref.DPS
    try:
        quadref.DPS = 100
        c = quadref.reference(pot, MU, E, L, mm.mpf(20))
    finally:
        quadref.DPS = old
    assert a['sweep'] > 2 * mm.pi                          # passes over the barrier and winds around
    assert abs(a['sweep'] - c['sweep']) < mm.mpf('1e-25')


def test_lj_ordinary_kdk_second_order_and_predictor():
    pot = LennardJones()
    e = [run(pot, 'kdk', 2 * DE, 6, h)['err_sweep'] for h in (40, 20, 10)]
    assert 3.3 < e[0] / e[1] < 4.7 and 3.3 < e[1] / e[2] < 4.7
    row = run(pot, 'kdk', 2 * DE, 6, 20)
    mod = quadref.kdk_modified(pot, MU, row['q0'], row['p0'], 20, row['r_exit'])
    L = 6 * mm.sqrt(2 * MU * 2 * DE)
    true = quadref.reference(pot, MU, 2 * DE, L, row['r_exit'])
    with mm.workdps(80):
        assert abs(row['d_sweep'] / float(mod['sweep'] - true['sweep']) - 1) < 0.05
