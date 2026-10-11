"""Method bench S3c: M8 per-collision refinement ladder (world tick fixed), estimator audit, cap (+ planted faults)."""
import importlib.util
import json
from pathlib import Path

import mpmath as mm

from c1b1_method_bench import quadref, refine
from c1b1_method_bench.methods import chin4a
from c1b1_method_bench.potentials import DE, MU, ExpWall, LennardJones
from c1b1_method_bench.run import initial, run

TOOLS = Path(__file__).resolve().parents[1] / 'tools'


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _true_errors(pot, E, b, st, dps=40):
    """Independent check of one recorded state against quadref (not the tool's verify)."""
    with mm.workdps(dps):
        E, b = mm.mpf(E), mm.mpf(b)
        _, _, L = initial(pot, MU, E, b)
    ref = quadref.reference(pot, MU, E, L, mm.mpf(st['r']))
    with mm.workdps(quadref.DPS):
        return (abs(mm.mpf(st['sweep']) - ref['sweep']), abs(mm.mpf(st['time']) - ref['time']) / ref['time'])


def test_level0_track_matches_fixed_step_run():
    """Level 0 is Chin 4A with h = 40: same exit step and sweep as the S1-S3 fixed-step runner."""
    pot, E, b = LennardJones(), 10 * DE, 3
    row = run(pot, 'chin4a', E, b, 40)
    with mm.workdps(40):
        q, p, _ = initial(pot, MU, mm.mpf(E), mm.mpf(b))
        t = refine.Track(pot, q, p, 0)
        t.run_to_exit(100_000)
        assert t.exit_tick == row['steps'] and mm.nstr(t.sweep, 25) == row['sweep']


def test_finer_level_keeps_world_ticks():
    """Level 1 = two Chin 4A substeps of 20 per world tick; tick count and time stay on the H0 = 40 clock."""
    pot = ExpWall()
    with mm.workdps(40):
        q, p, _ = initial(pot, MU, 10 * DE, mm.mpf(2))
        t = refine.Track(pot, q, p, 1)
        for _ in range(3):
            t.advance_tick()
        qq, pp = q, p
        for _ in range(6):
            qq, pp = chin4a(pot, qq, pp, mm.mpf(20), MU)
        assert t.tick == 3 and t.substeps == 6 and t.q == qq and t.p == pp
        assert t.state()['time'] == mm.nstr(mm.mpf(120), 45)


def test_ladder_descends_and_estimates_cover_true_error():
    """T4 10 De b = 2 (Chin 40 error ~4e-11, S2) with tol 1e-12 must go below level 1; every finer run's true error
    is within its estimate and the accepted output meets tol."""
    pot, E, b, tol = ExpWall(), 10 * DE, 2, '1e-12'
    res = refine.refine(pot, E, b, tol)
    assert res['status'] == 'accepted' and res['j_out'] >= 2
    for pr in res['pairs']:
        es, et = _true_errors(pot, E, b, pr['fine_state'])
        assert es <= mm.mpf(pr['est_sweep']) and et <= mm.mpf(pr['est_time'])
    es, et = _true_errors(pot, E, b, res['out'])
    assert es <= mm.mpf(tol) and et <= mm.mpf(tol)


def test_planted_blind_estimator_is_caught_by_audit():
    """Fault: the 'finer' run is the same level, so the estimate is 0 and level 0 is accepted. The verification
    layer must see true error > estimate (underestimate) and > tol (violation)."""
    pot, E, b, tol = ExpWall(), 10 * DE, 2, '1e-12'
    res = refine.refine(pot, E, b, tol, next_level=lambda j: j)
    assert res['status'] == 'accepted' and res['j_out'] == 0
    pr = res['pairs'][0]
    es, _ = _true_errors(pot, E, b, pr['fine_state'])
    assert mm.mpf(pr['est_sweep']) == 0 and es > mm.mpf(tol)


def test_cap_stops_without_output():
    res = refine.refine(ExpWall(), 10 * DE, 2, '1e-40', j_max=2)
    assert res['status'] == 'cap_stop' and res['j_out'] is None and 'out' not in res and len(res['pairs']) == 2


def test_deterministic_repeat():
    a = refine.refine(ExpWall(), 45 * DE, 6, '1e-9')
    b = refine.refine(ExpWall(), 45 * DE, 6, '1e-9')
    assert a == b


def test_study_jobs_predictions_and_one_row():
    s3c = _tool('c1b1_method_bench_s3c')
    js = s3c.jobs()
    kinds = [(j[0], j[4]) for j in js]
    assert len(js) == 152 and kinds.count(('killer', 'main')) == 84 and kinds.count(('ordinary', 'main')) == 44
    assert kinds.count(('killer', 'cross')) == 18 and len(set(js)) == len(js)
    summ = _tool('c1b1_method_bench_s3c_summary')
    assert [summ.pred_j(x) for x in (1e-2, 1e-4, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10)] == [1, 1, 2, 3, 3, 4, 5]
    row = s3c.one(('ordinary', 'T4_exp_wall', '45', '6', 'main'))
    assert row['status'] == 'accepted' and row['out']['err_sweep'] <= 1e-9 and 'err_time' in row['level0']


def test_planted_summary_faults_are_reported(tmp_path):
    """The summary must report an accepted output above tol (V) and a pair whose true error exceeds its estimate (U)."""
    st = dict(sweep='1', r='20', time='40', err_sweep=5e-9, err_time=1e-12)
    row = dict(status='accepted', j_out=1, substeps=2, wall_s=1.0, out=dict(st), level0=dict(st),
               pairs=[dict(coarse=0, fine=1, est_sweep='1e-10', est_time='1e-10', accepted=True, fine_state=dict(st))],
               job=dict(kind='ordinary', pot='T4_exp_wall', e='45', x='6', variant='main'))
    p = tmp_path / 'rows.jsonl'
    p.write_text(json.dumps(row) + '\n', encoding='utf-8')
    summ = _tool('c1b1_method_bench_s3c_summary')
    import sys
    old = sys.argv
    try:
        sys.argv = ['x', str(p), str(tmp_path / 'sum')]
        summ.main()
    finally:
        sys.argv = old
    out = json.loads((tmp_path / 'sum.json').read_text(encoding='utf-8'))
    assert len(out['V_violations']) == 1 and len(out['U_underestimates']) == 1
