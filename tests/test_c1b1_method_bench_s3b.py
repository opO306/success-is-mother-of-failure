"""Method bench S3b: narrow-band turning point fix, fail-closed runner, Gauss-Kronrod rule, Q2_fin node (+ planted faults)."""
import json
import os

import mpmath as mm
import pytest

from c1b1_method_bench import orbit, q2, quadref
from c1b1_method_bench.potentials import MU, Free, LennardJones, Morse
from c1b1_method_bench.runner import run_jobs

S3_FAILED = [(Morse, '0.9'), (LennardJones, '0.3'), (LennardJones, '0.6')]     # S3: rho = +1e-6 fail-closed inputs


def _pr2(pot, frac, rho):
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf(frac)
        o = orbit.orbit(pot, MU, E)
        b = o['b_orb'] * (1 + mm.mpf(rho))
    with mm.workdps(quadref.DPS):
        L = b * mm.sqrt(2 * MU * E)
        return E, L, o['r_star'], (lambda r: 2 * MU * (E - pot.V(r)) - L * L / (r * r))


@pytest.mark.parametrize('cls,frac', S3_FAILED)
def test_s3_failed_inputs_now_take_outer_root(cls, frac):
    pot = cls()
    E, L, rs, pr2 = _pr2(pot, frac, '1e-6')
    with mm.workdps(quadref.DPS):
        rt = quadref.turning(pr2, mm.mpf(quadref.R0))
        assert rs < rt < rs + mm.mpf('0.1')                      # just outside the barrier top, not the inner wall
        assert pr2(rt) > 0 and pr2(rt - mm.mpf('1e-20')) < 0     # a simple root: forbidden just inside
    ref = quadref.reference(pot, MU, E, L, mm.mpf(20), time=False)
    assert not isinstance(ref['sweep'], mm.mpc) and ref['sweep'] > 0


def test_fixed_reference_matches_independent_implementation():
    """S3 failed input (LJ 0.3 E_max, rho = +1e-6) against c1b1_o1.continuous (linear scan, step 0.0043 < band 0.017)."""
    from c1b1_o1 import continuous
    from c1b1_method_bench.run import initial
    pot = LennardJones()
    E, L, rs, pr2 = _pr2(pot, '0.3', '1e-6')
    ref = quadref.reference(pot, MU, E, L, mm.mpf(20), time=False)
    with mm.workdps(40):
        q, p, _ = initial(pot, MU, E, L / mm.sqrt(2 * MU * E))
        got = continuous.scatter(pot.V, MU, q, p, mm.mpf(20), 40)
        assert abs(mm.mpf(got['sweep']) - ref['sweep']) < mm.mpf('1e-18')


def test_band_far_narrower_than_scan_step():
    """rho = +1e-10: band ~1e-4 bohr, about 1/200 of a scan step."""
    E, L, rs, pr2 = _pr2(LennardJones(), '0.6', '1e-10')
    with mm.workdps(quadref.DPS):
        rt = quadref.turning(pr2, mm.mpf(quadref.R0))
        assert rs < rt < rs + mm.mpf('1e-3') and pr2(rt - mm.mpf('1e-20')) < 0


def test_planted_band_check_removed_is_detected(monkeypatch):
    """Without the minimum check the scan returns the inner wall again (the S3 failure)."""
    E, L, rs, pr2 = _pr2(LennardJones(), '0.3', '1e-6')
    monkeypatch.setattr(quadref, 'minima', lambda f, a, b, **k: [])
    with mm.workdps(quadref.DPS):
        assert quadref.turning(pr2, mm.mpf(quadref.R0)) < rs - mm.mpf(1)


def test_inside_orbit_unchanged_and_precision_stable():
    """rho < 0 (passes over the barrier): no band, same turning point as before; 80 vs 100 digits."""
    E, L, rs, pr2 = _pr2(LennardJones(), '0.6', '-1e-6')
    a = quadref.reference(LennardJones(), MU, E, L, mm.mpf(20), time=False)
    old = quadref.DPS
    try:
        quadref.DPS = 100
        c = quadref.reference(LennardJones(), MU, E, L, mm.mpf(20), time=False)
    finally:
        quadref.DPS = old
    assert a['r_turn'] < rs - 1 and abs(a['sweep'] - c['sweep']) < mm.mpf('1e-30')


def test_gk15_exactness():
    with mm.workdps(40):
        nodes = q2.gk15(-1, 1)
        assert len(nodes) == 15 and sum(1 for _, _, wg in nodes if wg != 0) == 7
        for k in range(23):
            exact = mm.mpf(2) / (k + 1) if k % 2 == 0 else 0
            assert abs(sum(wk * x ** k for x, wk, _ in nodes) - exact) < mm.mpf('1e-35')
            if k <= 13:                       # Gauss weights come from the closed formula, not from the moments
                assert abs(sum(wg * x ** k for x, _, wg in nodes) - exact) < mm.mpf('1e-35')
        assert abs(sum(wg * x ** 14 for x, _, wg in nodes) - mm.mpf(2) / 15) > mm.mpf('1e-6')   # G7 not exact
        assert abs(sum(wk * x ** 24 for x, wk, _ in nodes) - mm.mpf(2) / 25) > mm.mpf('1e-12')  # K15 not exact


def test_gk15_matches_published_quadpack_values():
    """Outside cross-check of the computed rule (the typed constants are good to ~1e-26 only)."""
    with mm.workdps(40):
        rule = q2._rule(40)
        xs = sorted([x for x, _, _ in rule], reverse=True)
        assert all(abs(x - mm.mpf(c)) < mm.mpf('1e-20') for x, c in zip(xs, q2.XGK))
        byx = {mm.nstr(x, 15): (wk, wg) for x, wk, wg in rule}
        for c, wk in zip(q2.XGK, q2.WGK):
            assert abs(byx[mm.nstr(mm.mpf(c), 15)][0] - mm.mpf(wk)) < mm.mpf('1e-20')


def test_b_of_maps_sides():
    with mm.workdps(40):
        b, j = q2.b_of('in', mm.mpf(2), mm.mpf(10))
        assert abs(b - 10 * (1 - mm.exp(-2))) < mm.mpf('1e-35') and abs(j - 10 * mm.exp(-2)) < mm.mpf('1e-35')
        b, _ = q2.b_of('out', mm.mpf(2), mm.mpf(10))
        assert b > 10


def test_free_particle_has_zero_deflection():
    """chi_fin = sweep + 2 alpha - pi = 0 on a straight line (checks the alpha convention); H3 = 0 for V = 0."""
    n = q2.node(Free(), mm.mpf('0.001'), mm.mpf(7))
    assert n['sin2_true'] < mm.mpf('1e-30') and all(v < mm.mpf('1e-30') for v in n['sin2'].values())


def test_panels_cover_orbit_and_control():
    with mm.workdps(60):
        E, b_orb, pans = q2.panels('0.6', LennardJones(), mm.mpf(18), mm.mpf('1e-8'), mm.mpf('0.5'))
        ins = [p for p in pans if p[0] == 'in']; outs = [p for p in pans if p[0] == 'out']
        assert ins[0][1] == 0 and abs(ins[-1][2] - mm.log(10 ** 8)) < mm.mpf('1e-40')
        assert abs(q2.b_of('out', outs[0][1], b_orb)[0] - 18) < mm.mpf('1e-40')
        _, none, plain = q2.panels('1.5', LennardJones(), mm.mpf(18), mm.mpf('1e-8'), mm.mpf('0.5'))
        assert none is None and plain[0][1] == 0 and plain[-1][2] == 18


def _job_ok(j):
    return dict(job=j, status='ok')


def _job_dies(j):
    if j == 3:
        os._exit(1)                                          # simulates the OOM killer
    return dict(job=j, status='ok')


def test_runner_writes_all_rows(tmp_path):
    out = tmp_path / 'rows.jsonl'
    run_jobs(_job_ok, list(range(10)), str(out), workers=2)
    assert sorted(json.loads(x)['job'] for x in open(out)) == list(range(10))


def test_planted_worker_death_fails_closed(tmp_path, capsys):
    out = tmp_path / 'rows.jsonl'
    with pytest.raises(SystemExit) as e:
        run_jobs(_job_dies, list(range(6)), str(out), workers=2)
    assert e.value.code == 3
    text = capsys.readouterr().out
    assert 'WORKER_DIED' in text and 'LOST 3' in text
    assert 3 not in [json.loads(x)['job'] for x in open(out)]
