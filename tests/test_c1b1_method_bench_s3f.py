"""Method bench S3f: M10 one-dial ladder (step + grid by one rule), rounding check, round-back (+ planted faults)."""
import importlib.util
import json
import sys
from pathlib import Path

import mpmath as mm

from c1b1_method_bench import pen
from c1b1_method_bench.potentials import DE, ExpWall

TOOLS = Path(__file__).resolve().parents[1] / 'tools'


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dial_rule():
    assert [pen.grid(j) for j in range(4)] == [(64, 96), (68, 100), (72, 104), (76, 108)]


def test_ordinary_accepts_with_rounding_check_and_harmless_round_back():
    pot, E, b = ExpWall(), 45 * DE, 6
    res = pen.pen(pot, E, b, '1e-9')
    _tool('c1b1_method_bench_s3f').verify(pot, E, b, res)
    assert res['status'] == 'accepted' and res['j_out'] == 1 and res['bits_out'] == [68, 100]
    last = res['pairs'][-1]
    assert last['checked'] and float(last['d_round_sweep']) < float(last['est_step_sweep']) / 100
    o, ob = res['out'], res['out_base']
    assert o['err_sweep'] <= float(last['est_sweep']) and o['err_time'] <= float(last['est_time'])
    assert abs(ob['err_sweep'] - o['err_sweep']) < 1e-13 and abs(float(ob['sweep_shift'])) < 1e-14
    assert [c['extra'] for c in res['track_cost']].count(pen.CHECK_BITS) == 1


def test_tight_tolerance_descends_the_dial_and_estimates_cover_truth():
    """T4 10 De b = 2 (Chin 40 error ~4e-11, S2) with tol 1e-12: the dial must go below level 1."""
    pot, E, b = ExpWall(), 10 * DE, 2
    res = pen.pen(pot, E, b, '1e-12')
    _tool('c1b1_method_bench_s3f').verify(pot, E, b, res)
    assert res['status'] == 'accepted' and res['j_out'] >= 2
    for pr in res['pairs']:
        es = pr['est_sweep'] if pr.get('checked') else pr['est_step_sweep']
        assert pr['C_state']['err_sweep'] <= float(es)
    assert res['out']['err_sweep'] <= 1e-12 and res['out']['err_time'] <= 1e-12


def test_planted_coarse_dial_is_caught_by_the_rounding_check():
    """Fault: a dial that stays on the base grid (fp0 = 48, dbits = 0). With tol below the base-grid rounding the
    collision must not be accepted (cap): the base-grid rounding either keeps the step estimate above tol or is
    caught by the rounding check."""
    pot, E, b = ExpWall(), 45 * DE, 6
    ok = pen.pen(pot, E, b, '1e-9', fp0=48, dbits=0)
    d0 = float(ok['pairs'][-1]['d_round_sweep'])                  # base-grid rounding of this collision (check vs +16)
    assert d0 > 1e-17
    res = pen.pen(pot, E, b, repr(d0 / 50), fp0=48, dbits=0, j_max=4)
    assert res['status'] == 'cap_stop' and res['j_out'] is None


def test_deterministic_repeat():
    a = pen.pen(ExpWall(), 45 * DE, 6, '1e-9')
    b = pen.pen(ExpWall(), 45 * DE, 6, '1e-9')
    strip = lambda d: {k: v for k, v in d.items() if k != 'track_cost'}
    assert strip(a) == strip(b)
    assert [c['substeps'] for c in a['track_cost']] == [c['substeps'] for c in b['track_cost']]


def test_study_jobs_and_one_row():
    s3f = _tool('c1b1_method_bench_s3f')
    js = s3f.jobs()
    assert len(js) == 130 and len(set(js)) == len(js)
    row = s3f.one(('ordinary', 'T4_exp_wall', '45', '6', 'main'))
    assert row['status'] == 'accepted' and row['out']['err_sweep'] <= 1e-9 and 'err_sweep' in row['out_base']


def test_planted_summary_faults_are_reported(tmp_path):
    st = dict(sweep='1', r='20', time='40', err_sweep=5e-9, err_time=1e-12)
    pair = dict(j=0, est_step_sweep='1e-10', est_step_time='1e-10', checked=True, d_round_sweep='5e-11',
                d_round_time='1e-13', est_sweep='1.5e-10', est_time='1e-10', C_state=dict(st))
    row = dict(status='accepted', j_out=1, bits_out=[68, 100], substeps=2, wall_s=1.0, level0=dict(st), out=dict(st),
               out_base=dict(st), pairs=[pair], track_cost=[],
               job=dict(kind='ordinary', pot='T4_exp_wall', e='45', x='6', variant='main'))
    p = tmp_path / 'rows.jsonl'
    p.write_text(json.dumps(row) + '\n', encoding='utf-8')
    summ = _tool('c1b1_method_bench_s3f_summary')
    old = sys.argv
    try:
        sys.argv = ['x', str(p), str(tmp_path / 'sum')]
        summ.main()
    finally:
        sys.argv = old
    out = json.loads((tmp_path / 'sum.json').read_text(encoding='utf-8'))
    assert len(out['V_violations']) == 2 and len(out['U_underestimates']) == 1 and len(out['R_rounding_not_small']) == 1
