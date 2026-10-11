"""Method bench S3d: production-style fixed-point arithmetic (FX) on the bench, rounding near the boundary (+ faults)."""
import importlib.util
import json
import sys
from pathlib import Path

import mpmath as mm

from c1b1_method_bench import fixedpoint as fx, refine
from c1b1_method_bench.methods import kdk
from c1b1_method_bench.potentials import DE, MU, ExpWall
from c1b1_method_bench.run import initial

TOOLS = Path(__file__).resolve().parents[1] / 'tools'


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fx_vs_hp(pot, E, b, fp, fm, dps=40):
    with mm.workdps(dps):
        q, p, _ = initial(pot, MU, mm.mpf(E), mm.mpf(b))
        f = fx.FxTrack(pot, q, p, 0, 'kdk', fp, fm)
        with mm.workdps(max(dps, fx.FORCE_DPS)):
            q0, p0 = f.q_mpf(), f.p_mpf()
        h = refine.Track(pot, q0, p0, 0, MU, 40, kdk)
        f.run_to_exit(100_000)
        h.run_to_exit(100_000)
        n = max(f.tick, h.tick)
        f.run_to(n)
        h.run_to(n)
        return abs(f.sweep - h.sweep), f


def test_half_even_is_odd_symmetric_with_ties_to_even():
    for den in (1, 2, 3, 7, 1 << 20):
        for num in range(-60, 61):
            assert fx._half_even(-num, den) == -fx._half_even(num, den)
    assert [fx._half_even(n, 2) for n in (1, 3, 5, -1, -3)] == [0, 2, 2, 0, -2]


def test_very_fine_grid_reproduces_hp_kdk():
    """With 2^-120 grids the FX run must equal the mpmath KDK run to rounding level (no other difference)."""
    d, _ = _fx_vs_hp(ExpWall(), 10 * DE, 2, 120, 120)
    assert d < mm.mpf('1e-30')


def test_production_grid_rounds_but_small_away_from_boundary():
    d, f = _fx_vs_hp(ExpWall(), 10 * DE, 2, 48, 80)
    assert mm.mpf('1e-18') < d < mm.mpf('1e-12')       # rounding is active (planted 'no rounding' would give < 1e-30)
    assert all(isinstance(x, int) for x in f.qr + f.pr_)


def test_initial_state_on_the_grid_and_start_radius_exact():
    with mm.workdps(40):
        q, p, _ = initial(ExpWall(), MU, 10 * DE, mm.mpf(2))
    f = fx.FxTrack(ExpWall(), q, p, 0)
    assert f.qr == [20 << 48, 0] and all(x % 2 == 0 for x in f.qr)       # q = 2 round(q/2): two opposite atoms


def test_fx_ladder_on_fine_grid_matches_s3c_ladder():
    pot, E, b = ExpWall(), 45 * DE, 6
    a = refine.refine(pot, E, b, '1e-9')
    c = fx.fx_refine(pot, E, b, '1e-9', 'chin', 120, 120)
    assert a['j_out'] == c['j_out'] and a['out']['tick'] == c['out']['tick']
    with mm.workdps(60):
        assert abs(mm.mpf(a['out']['sweep']) - mm.mpf(c['out']['sweep'])) < mm.mpf('1e-30')


def test_deterministic_repeat():
    a = fx.fx_refine(ExpWall(), 45 * DE, 6, '1e-9')
    b = fx.fx_refine(ExpWall(), 45 * DE, 6, '1e-9')
    assert a == b


def test_study_jobs_and_one_row():
    s3d = _tool('c1b1_method_bench_s3d')
    js = s3d.jobs()
    kinds = [j[0] for j in js]
    assert len(js) == 139 and kinds.count('kdk_fx') == 84 and kinds.count('m8_fx') == 6 and len(set(js)) == len(js)
    row = s3d.one(('ordinary', 'T4_exp_wall', '45', '2', 48, 80))
    assert row['status'] == 'ok' and row['d_sweep'] < 1e-12 and 'err_sweep' in row['fx'] and 'err_sweep' in row['hp']


def test_planted_summary_faults_are_reported(tmp_path):
    """An accepted FX ladder output above tol must appear in V; a wrong P5 status must be flagged False."""
    st = dict(sweep='1', r='20', time='40', err_sweep=5e-9, err_time=1e-12)
    row = dict(status='accepted', j_out=1, substeps=2, out=dict(st), level0=dict(st),
               pairs=[dict(coarse=0, fine=1, est_sweep='1e-10', est_time='1e-10', accepted=True, fine_state=dict(st))],
               job=dict(kind='m8_fx', pot='T5_morse', e='0.9', x='-1e-8', fp=48, fm=80, j=None))
    p = tmp_path / 'rows.jsonl'
    p.write_text(json.dumps(row) + '\n', encoding='utf-8')
    summ = _tool('c1b1_method_bench_s3d_summary')
    old = sys.argv
    try:
        sys.argv = ['x', str(p), str(tmp_path / 'sum')]
        summ.main()
    finally:
        sys.argv = old
    out = json.loads((tmp_path / 'sum.json').read_text(encoding='utf-8'))
    assert len(out['V_m8_violations']) == 1 and out['P5_m8_fx'][0][-1] is False
