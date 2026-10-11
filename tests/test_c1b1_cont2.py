"""Continuous reference V2 (c1b1_cont2): closed forms, narrow-band inputs where the sealed V1 stopped, Ar agreement
with the sealed V1 where V1 works, precision stability, planted fault, independence."""
import ast
import os
from fractions import Fraction
from pathlib import Path

import mpmath as mm
import pytest

from c1b1_cont2 import scatter as c2

PKG = Path(__file__).resolve().parents[1] / 'c1b1_cont2'


def test_package_imports_mpmath_only():
    for path in PKG.glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            assert all(n.split('.')[0] == 'mpmath' for n in names), (path.name, names)


def _bench_state(pot, E, b):
    from c1b1_method_bench.potentials import MU
    from c1b1_method_bench.run import initial
    with mm.workdps(80):
        q, p, L = initial(pot, MU, mm.mpf(E), mm.mpf(b))
    return MU, q, p, L


@pytest.mark.parametrize('kind', ['inv_square', 'coulomb'])
def test_closed_forms(kind):
    from c1b1_method_bench import exact
    from c1b1_method_bench.potentials import DE, Coulomb, InvSquare
    pot = InvSquare() if kind == 'inv_square' else Coulomb()
    E, b = 2 * DE, 6
    mu, q, p, L = _bench_state(pot, E, b)
    # dps 60: the design accuracy is 10^-(dps/2) (precision check); at dps 40 the observed error was 1.4e-28 (run 1)
    got = c2.scatter(pot.V, mu, q, p, 20, dps=60)
    with mm.workdps(80):
        ref = getattr(exact, kind)(pot.alpha, mu, mm.mpf(E), L, 20, mm.mpf(20))
        assert abs(mm.mpf(got['sweep']) - ref['sweep']) < mm.mpf('1e-30')
        assert abs(mm.mpf(got['time']) - ref['time']) / ref['time'] < mm.mpf('1e-30')


# inputs where the sealed c1b1_o1.continuous stopped in S3c (X check): rho > 0 just outside the barrier, plus one inside
NARROW = [('T5_morse', '0.6', '1e-8'), ('T6_lennard_jones', '0.3', '1e-9'), ('T5_morse', '0.9', '1e-10'),
          ('T6_lennard_jones', '0.6', '-1e-10')]


def _narrow(potname, frac, rho):
    from c1b1_method_bench import orbit
    from c1b1_method_bench.potentials import MU, LennardJones, Morse
    pot = {'T5_morse': Morse, 'T6_lennard_jones': LennardJones}[potname]()
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf(frac)
        b = orbit.orbit(pot, MU, E)['b_orb'] * (1 + mm.mpf(rho))
    return pot, E, b


@pytest.mark.parametrize('potname,frac,rho', NARROW)
def test_narrow_band_agrees_with_bench_reference(potname, frac, rho):
    from c1b1_method_bench import quadref
    pot, E, b = _narrow(potname, frac, rho)
    mu, q, p, L = _bench_state(pot, E, b)
    got = c2.scatter(pot.V, mu, q, p, 20, dps=40)
    with mm.workdps(80):
        E0 = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + pot.V(mm.mpf(20))
    ref = quadref.reference(pot, mu, E0, L, mm.mpf(20))
    with mm.workdps(80):
        assert abs(mm.mpf(got['sweep']) - ref['sweep']) < mm.mpf('1e-18')
        assert abs(mm.mpf(got['time']) - ref['time']) / ref['time'] < mm.mpf('1e-18')
    assert mm.mpf(got['precision_diff']) < mm.mpf('1e-25')
    if not rho.startswith('-'):
        assert len(got['barrier_tops']) == 0 or all(mm.mpf(m) < mm.mpf(got['r_min']) for m in got['barrier_tops'])


def test_planted_missing_barrier_check_is_detected():
    """Without the interior-minimum search V2 falls back to the first non-positive grid bracket. Where that bracket is
    the inner wall (the band at the barrier top fell between grid points), the result must stop or disagree; it must
    not silently agree. Run 1 showed a grid point can land inside the band by chance (then the fallback is right), so
    at least one of the rho > 0 inputs must actually exercise the inner-wall case."""
    from c1b1_method_bench import orbit
    from c1b1_method_bench.potentials import MU
    exercised = 0
    for potname, frac, rho in [x for x in NARROW if not x[2].startswith('-')]:
        pot, E, b = _narrow(potname, frac, rho)
        mu, q, p, L = _bench_state(pot, E, b)
        with mm.workdps(60):
            r_star = orbit.orbit(pot, MU, E)['r_star']
            H = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + pot.V(mm.mpf(20))
            g = lambda r: 2 * mu * (H - pot.V(r)) - L * L / (r * r)
            rt_bad, _ = c2.turning_point(g, mm.mpf(20), 40, use_minima=False)
            rt_good, _ = c2.turning_point(g, mm.mpf(20), 40)
            assert rt_good > r_star
            if rt_bad > r_star:
                continue                                   # a grid point landed inside the band: fallback was right
        exercised += 1
        good = c2.scatter(pot.V, mu, q, p, 20, dps=40)
        try:
            bad = c2.scatter(pot.V, mu, q, p, 20, dps=40, use_minima=False)
        except c2.Unresolved:
            continue
        with mm.workdps(60):
            assert abs(mm.mpf(bad['sweep']) - mm.mpf(good['sweep'])) > mm.mpf('1e-12')
    assert exercised >= 1


def test_deterministic_repeat():
    pot, E, b = _narrow('T6_lennard_jones', '0.6', '-1e-10')
    mu, q, p, L = _bench_state(pot, E, b)
    assert c2.scatter(pot.V, mu, q, p, 20, dps=30) == c2.scatter(pot.V, mu, q, p, 20, dps=30)


def _lang_path():
    path = Path(os.environ.get('C1B1_LANG_PES', 'D:/reference/ar2_lang2024/S2_ar2_pot.f90'))
    if not path.exists():
        pytest.fail(f'Lang PES file not found at {path} (set C1B1_LANG_PES); this test must not be skipped')
    return path


# b_orb(E = 1/2 De) from a_reference/fixtures/c1b1_orbit_boundary_v3.json (static copy, as in the P3 tool)
AR = [('1/2', 11.71900517505586 * (1 - 1e-3)), ('1/2', 11.71900517505586 * (1 + 1e-3)), ('2', 6.0), ('2', 0.0)]


@pytest.mark.parametrize('e,b', AR)
def test_argon_agrees_with_sealed_v1_where_v1_works(e, b):
    from c1b1_o1 import continuous, model
    with mm.workdps(100):
        V = model.Potential(params=model.parse(_lang_path()))
    with mm.workdps(60):
        mu = mm.mpf(Fraction(model.MASS).numerator) / Fraction(model.MASS).denominator / 2
        E = mm.mpf(Fraction(e).numerator) / Fraction(e).denominator * mm.mpf(model.DE)
        L = mm.mpf(b) * mm.sqrt(2 * mu * E)
        pt = L / 20
        q, p = [mm.mpf(20), mm.mpf(0)], [-mm.sqrt(2 * mu * (E - V(mm.mpf(20))) - pt * pt), pt]
    old = continuous.scatter(V, mu, q, p, mm.mpf(20), 40)
    new = c2.scatter(V, mu, q, p, 20, dps=40)
    with mm.workdps(60):
        assert abs(mm.mpf(old['sweep']) - mm.mpf(new['sweep'])) < mm.mpf('1e-18')
        assert abs(mm.mpf(old['time']) - mm.mpf(new['time'])) / mm.mpf(new['time']) < mm.mpf('1e-18')
