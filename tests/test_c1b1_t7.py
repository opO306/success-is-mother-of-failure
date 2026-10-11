"""T7 parts: Lang PES derivatives, canonical start states (bit reproduction of the O-1 raws), M10 from a stored
state (= pen.pen), multi-exit reference (= cont2.scatter), job list, one Ar job end to end, summary faults."""
import ast
import importlib.util
import json
import os
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mm
import pytest

ROOT = Path(__file__).resolve().parents[1]
O1 = ROOT / 'docs/active/C1B1_O1_INPUTS_V1.json'
FIXTURE = Path(os.environ.get('C1B1_ORBIT_FIXTURE', ROOT / 'a_reference/fixtures/c1b1_orbit_boundary_v3.json'))


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pes():
    from c1b1_t7.lang import pes_path
    if not pes_path().exists():
        pytest.fail(f'Lang PES file not found at {pes_path()} (set C1B1_LANG_PES); this test must not be skipped')


def _o1():
    return json.loads(O1.read_bytes())['payload']


def test_package_imports_no_production_module():
    banned = {'a_reference', 'a_numeric', 'a_numeric_native', 'a_physics_native', 'engine', 'audit'}
    for path in list((ROOT / 'c1b1_t7').glob('*.py')) + [ROOT / 'tools/c1b1_t7_argon.py']:
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                    [node.module or ''] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            assert not any(n.split('.')[0] in banned for n in names), (path.name, names)


RS = ['3.2', '4', '5.5', '6.6', '7.1', '8.5', '11', '15', '20', '20.4']


def test_lang_value_matches_reference_potential():
    _pes()
    from c1b1_t7.lang import LangForce, reference_potential
    F, V = LangForce(), reference_potential()
    with mm.workdps(90):
        for r in RS:
            a, b = F.V(mm.mpf(r)), V(mm.mpf(r))
            assert abs(a - b) <= abs(b) * mm.mpf('1e-70'), r


def test_lang_derivatives_match_numerical_derivatives():
    _pes()
    from c1b1_t7.lang import LangForce, reference_potential
    F, V = LangForce(), reference_potential()
    with mm.workdps(70):
        for r in RS:
            r = mm.mpf(r)
            d1, d2 = mm.diff(V, r, 1), mm.diff(V, r, 2)
            assert abs(F.dV(r) - d1) <= abs(d1) * mm.mpf('1e-40'), r
            assert abs(F.d2V(r) - d2) <= abs(d2) * mm.mpf('1e-40'), r


def test_lang_cache_respects_precision():
    _pes()
    from c1b1_t7.lang import LangForce
    F = LangForce()
    with mm.workdps(20):
        a = F.dV(mm.mpf(7))
    with mm.workdps(60):
        b = F.dV(mm.mpf(7))
    assert F.evaluations == 2 and a != b


def test_round_sqrt_exact_and_ties_to_even():
    from c1b1_t7.state import round_sqrt
    assert [round_sqrt(x) for x in (0, 1, 2, 3, Q(9, 4), Q(25, 4), Q(49, 4), 10 ** 40)] == [0, 1, 1, 2, 2, 2, 4, 10 ** 20]
    assert round_sqrt(Q(1, 4) + Q(1, 10 ** 30)) == 1 and round_sqrt(Q(1, 4) - Q(1, 10 ** 30)) == 0


def test_canonical_state_reproduces_every_o1_raw_bit_for_bit():
    _pes()
    from c1b1_t7.lang import reference_potential
    from c1b1_t7.state import canonical_raw
    V = reference_potential()
    rows = _o1()['inputs']
    assert len(rows) == 10
    for row in rows:
        assert canonical_raw(row['E_De'], Q(row['b_bohr']) ** 2, V) == row['raw'], row['id']


def test_relative_state_is_exact():
    from c1b1_t7.state import relative
    raw = _o1()['inputs'][0]['raw']
    q, p = relative(raw)
    assert q == [20, 0] and mm.ldexp(p[0], 80) == raw[9] and mm.ldexp(p[1], 80) == raw[10]
    bad = list(raw)
    bad[3] += 1
    with pytest.raises(ValueError):
        relative(bad)


def test_pen_state_equals_pen_on_the_bench():
    from c1b1_method_bench import ladder2, pen
    from c1b1_method_bench.potentials import DE, ExpWall
    from c1b1_t7.ladder import pen_state
    pot, E, b = ExpWall(), 45 * DE, 6
    a = pen.pen(pot, E, b, '1e-9')
    q0, p0 = ladder2.base_start(pot, E, b)
    c = pen_state(pot, q0, p0, '1e-9')
    for k in ('q_raw', 'p_raw'):
        c['out_base'].pop(k)
    strip = lambda d: {k: v for k, v in d.items() if k != 'track_cost'}
    assert strip(a) == strip(c)
    assert [t['substeps'] for t in a['track_cost']] == [t['substeps'] for t in c['track_cost']]


def test_exact_mass_track_differs_only_in_the_drift_divisor():
    from c1b1_method_bench import ladder2
    from c1b1_method_bench.potentials import DE, MU, ExpWall
    from c1b1_t7.ladder import FxTrackX
    from c1b1_method_bench.fixedpoint import _exact
    pot = ExpWall()
    q0, p0 = ladder2.base_start(pot, 45 * DE, 6)
    with mm.workdps(ladder2.DPS):
        same = FxTrackX(pot, q0, p0, 0, 'chin', 64, 96, MU, 40, _exact(MU))
        ref = ladder2.FxTrackP(pot, q0, p0, 0, 'chin', 64, 96, MU, 40)
        for t in (same, ref):
            t.run_to(50)
        assert same.qr == ref.qr and same.pr_ == ref.pr_


def test_scatter_many_matches_cont2_on_a_narrow_band_bench_input():
    from c1b1_cont2 import scatter as c2
    from c1b1_method_bench import orbit
    from c1b1_method_bench.potentials import MU, Morse
    from c1b1_method_bench.run import initial
    from c1b1_t7.reference import scatter_many
    pot = Morse()
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf('0.6')
        b = orbit.orbit(pot, MU, E)['b_orb'] * (1 + mm.mpf('1e-8'))
    with mm.workdps(80):
        q, p, _ = initial(pot, MU, E, b)
    exits = ['20', '20.0731', '20.4']
    many = scatter_many(pot.V, MU, q, p, exits, dps=40)
    for r, x in zip(exits, many['exits']):
        # pass the string: mm.mpf(r) here would round r to 53 bits outside the working precision (test run 1)
        one = c2.scatter(pot.V, MU, q, p, r, dps=40)
        with mm.workdps(60):
            assert abs(mm.mpf(x['sweep']) - mm.mpf(one['sweep'])) < mm.mpf('1e-18')
            assert abs(mm.mpf(x['time']) - mm.mpf(one['time'])) / mm.mpf(one['time']) < mm.mpf('1e-18')


def test_scatter_many_matches_cont2_on_argon():
    _pes()
    from c1b1_cont2 import scatter as c2
    from c1b1_t7.lang import reference_potential
    from c1b1_t7.reference import scatter_many
    from c1b1_t7.state import MU, relative
    V = reference_potential()
    row = next(r for r in _o1()['inputs'] if r['id'] == 'ordinary')
    q, p = relative(row['raw'])
    with mm.workdps(60):
        mu = mm.mpf(MU.numerator) / MU.denominator
    many = scatter_many(V, mu, q, p, ['20.0123'], dps=40)
    one = c2.scatter(V, mu, q, p, '20.0123', dps=40)              # string, as above (test run 1)
    with mm.workdps(60):
        assert abs(mm.mpf(many['exits'][0]['sweep']) - mm.mpf(one['sweep'])) < mm.mpf('1e-18')
        assert abs(mm.mpf(many['exits'][0]['time']) - mm.mpf(one['time'])) / mm.mpf(one['time']) < mm.mpf('1e-18')


def test_job_list():
    _pes()
    if not FIXTURE.exists():
        pytest.fail(f'orbit fixture not found at {FIXTURE} (set C1B1_ORBIT_FIXTURE)')
    t7 = _tool('c1b1_t7_argon')
    from c1b1_t7.lang import reference_potential
    jobs = sorted(t7.build_jobs(_o1(), json.loads(FIXTURE.read_bytes()), reference_potential()), key=t7.order_key)
    assert len(jobs) == 51 and len({j['id'] for j in jobs}) == 51
    assert [sum(j['bundle'] == x and j['variant'] == 'main' for j in jobs) for x in 'OSH'] == [10, 30, 9]
    by = {j['id']: j for j in jobs}
    for j in jobs:
        if j['variant'] == 'repeat':
            assert j['raw'] == by[j['repeat_of']]['raw']
    assert sum(j['cross'] for j in jobs) == 10 + 15 + 1          # O, S rho > 0, and the repeat of boundary_pass
    assert jobs[0]['rho'] in ('1e-10', '-1e-10')


def test_one_argon_job_end_to_end():
    """O-1 'high_energy' (9.9 De, b = 0): the fastest O input. Every verified state has a true error, the output is
    within tol, and the cross-check agrees."""
    _pes()
    t7 = _tool('c1b1_t7_argon')
    row = next(r for r in _o1()['inputs'] if r['id'] == 'high_energy')
    job = dict(id='O:high_energy', bundle='O', variant='main', e=row['E_De'], b=row['b_bohr'], rho=None,
               raw=row['raw'], cross=True)
    res = t7.one(job)
    assert res['status'] == 'accepted' and res['reference']['status'] == 'ok', res.get('error')
    assert res['out']['err_sweep'] <= 1e-9 and res['out']['err_time'] <= 1e-9
    assert res['cross']['agree']
    for pr in res['pairs']:
        assert 'err_sweep' in pr['C_state']
    assert 'err_sweep' in res['world_kdk'] and 'err_sweep' in res['out_base']


def _row(jid='S:1/2:1e-8', bundle='S', variant='main', err=1e-12, est='1e-10', rho='1e-8', status='accepted'):
    st = lambda e: dict(sweep='1', r='20', time='40', err_sweep=e, err_time=1e-13)
    pair = dict(j=0, tick=1, est_step_sweep=est, est_step_time='1e-12', checked=True, d_round_sweep='1e-15',
                d_round_time='1e-15', est_sweep=est, est_time='1e-12', C_state=st(err))
    return dict(job=dict(id=jid, bundle=bundle, variant=variant, rho=rho, repeat_of='S:1/2:1e-8'), status=status,
                j_out=1, pairs=[pair], level0=st(1e-6), world_kdk=st(1e-5), out=st(err), out_base=st(err),
                reference=dict(status='ok'), substeps=10, wall_s=1, cpu_s=1)


def test_summary_reports_planted_faults():
    sm = _tool('c1b1_t7_summary')
    clean, _ = sm.summarize([_row(), _row(jid='R:S:1/2:1e-8', variant='repeat')])
    assert not any(clean.get(k) for k in ('V_violations', 'U_underestimates', 'C_cap_stops', 'X_unresolved',
                                          'E_errors', 'R_rounding_not_small'))
    assert clean['D_repeat'] == [('R:S:1/2:1e-8', True)]
    bad, _ = sm.summarize([_row(err=2e-9, est='1e-9'), _row(jid='O:x', bundle='O', rho=None, status='cap_stop'),
                           dict(_row(jid='O:y', bundle='O', rho=None), reference=dict(status='UNRESOLVED', reason='t')),
                           _row(jid='H:20:0', bundle='H', rho=None, err=5e-9, est='1e-8'),
                           dict(job=dict(id='O:z', bundle='O', variant='main'), status='error', error='boom'),
                           _row(jid='R:S:1/2:1e-8', variant='repeat', err=3e-12)])
    assert [v[0] for v in bad['V_violations']] == ['S:1/2:1e-8', 'S:1/2:1e-8']
    assert [u[0] for u in bad['U_underestimates']] == ['S:1/2:1e-8']
    assert bad['C_cap_stops'] == ['O:x'] and bad['X_unresolved'][0][0] == 'O:y' and bad['E_errors'][0][0] == 'O:z'
    assert [v[0] for v in bad['H_V_violations']] == ['H:20:0', 'H:20:0']
    assert bad['D_repeat'] == [('R:S:1/2:1e-8', False)]
