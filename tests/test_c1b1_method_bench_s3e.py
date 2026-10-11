"""Method bench S3e: M9 two-axis ladder (step + grid) on fixed-point Chin 4A, round-back, estimator audit (+ faults)."""
import importlib.util
import json
import sys
from pathlib import Path

import mpmath as mm

from c1b1_method_bench import ladder2, quadref
from c1b1_method_bench.potentials import DE, MU, ExpWall

TOOLS = Path(__file__).resolve().parents[1] / 'tools'


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _verified(pot, E, b, tol):
    res = ladder2.ladder2(pot, E, b, tol)
    _tool('c1b1_method_bench_s3e').verify(pot, E, b, res)
    return res


def test_base_start_is_on_the_base_grid_at_r0():
    q0, p0 = ladder2.base_start(ExpWall(), 45 * DE, 6)
    with mm.workdps(60):
        assert q0 == [20, 0]
        assert all(mm.ldexp(x, 80) == mm.nint(mm.ldexp(x, 80)) for x in p0)


def test_ordinary_accepts_on_first_rung_and_round_back_is_harmless():
    pot, E, b = ExpWall(), 45 * DE, 6
    res = _verified(pot, E, b, '1e-9')
    assert res['status'] == 'accepted' and (res['j_out'], res['g_out']) == (1, 1)
    rg = res['rungs'][0]
    assert rg['C_state']['err_sweep'] <= float(rg['est_sweep']) and rg['C_state']['err_time'] <= float(rg['est_time'])
    o, ob = res['out'], res['out_base']
    assert abs(float(ob['sweep_shift'])) < 1e-14 and abs(ob['err_sweep'] - o['err_sweep']) < 1e-13
    assert all(int(x) % 2 == 0 for x in ob['q_raw'])


def _base_rounding(pot, E, b):
    """Grid term of the first rung at tol 1e-9 = base-grid (48-bit) rounding of this collision."""
    rg = ladder2.ladder2(pot, E, b, '1e-9')['rungs'][0]
    return max(float(rg['dgrid_sweep']), float(rg['dgrid_time']))


def test_tight_tolerance_needs_both_axes_and_estimates_cover_truth():
    """tol = (base-grid rounding of this collision) / 20 on T4 45 De b = 6: the grid must be refined (its term at the
    base grid exceeds tol; the rounding term fluctuates between levels, S3d, hence the factor 20) and the step too
    (Chin 40 error ~1e-12, S2); every rung's estimate must cover its C run."""
    pot, E, b = ExpWall(), 45 * DE, 6
    dg0 = _base_rounding(pot, E, b)
    assert 1e-17 < dg0 < 1e-12                       # rounding is measurable here and below the Chin 40 step error
    tol = repr(dg0 / 20)
    res = _verified(pot, E, b, tol)
    assert res['status'] == 'accepted' and res['j_out'] >= 3 and any(rg['g'] >= 1 for rg in res['rungs'])
    for rg in res['rungs']:
        st = rg['C_state']
        assert st['err_sweep'] <= float(rg['est_sweep']) and st['err_time'] <= float(rg['est_time'])
    assert res['out']['err_sweep'] <= float(tol) and res['out']['err_time'] <= float(tol)


def test_planted_step_only_ladder_cannot_converge():
    """Fault: never refine the grid. The grid term stays at the base-grid rounding (> tol), so the ladder must stop
    (cap), not accept."""
    pot, E, b = ExpWall(), 45 * DE, 6
    tol = repr(_base_rounding(pot, E, b) / 20)
    res = ladder2.ladder2(pot, E, b, tol, choose=lambda dg, ds: 'step')
    assert res['status'] == 'cap_stop' and res['j_out'] is None


def test_deterministic_repeat():
    a = ladder2.ladder2(ExpWall(), 45 * DE, 6, '1e-9')
    b = ladder2.ladder2(ExpWall(), 45 * DE, 6, '1e-9')
    assert a == b


def test_study_jobs_and_one_row():
    s3e = _tool('c1b1_method_bench_s3e')
    js = s3e.jobs()
    assert len(js) == 130 and sum(j[0] == 'killer' and j[4] == 'main' for j in js) == 84 and len(set(js)) == len(js)
    row = s3e.one(('ordinary', 'T4_exp_wall', '45', '6', 'main'))
    assert row['status'] == 'accepted' and row['out']['err_sweep'] <= 1e-9 and 'err_sweep' in row['out_base']


def test_planted_summary_faults_are_reported(tmp_path):
    st = dict(sweep='1', r='20', time='40', err_sweep=5e-9, err_time=1e-12)
    row = dict(status='accepted', j_out=1, g_out=1, substeps=2, wall_s=1.0, level0=dict(st), out=dict(st),
               out_base=dict(st),
               rungs=[dict(j=0, g=0, est_sweep='1e-10', est_time='1e-10', accepted=True, C_state=dict(st))],
               job=dict(kind='ordinary', pot='T4_exp_wall', e='45', x='6', variant='main'))
    p = tmp_path / 'rows.jsonl'
    p.write_text(json.dumps(row) + '\n', encoding='utf-8')
    summ = _tool('c1b1_method_bench_s3e_summary')
    old = sys.argv
    try:
        sys.argv = ['x', str(p), str(tmp_path / 'sum')]
        summ.main()
    finally:
        sys.argv = old
    out = json.loads((tmp_path / 'sum.json').read_text(encoding='utf-8'))
    assert len(out['V_violations']) == 2 and len(out['U_underestimates']) == 1
