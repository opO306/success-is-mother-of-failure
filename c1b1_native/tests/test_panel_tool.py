"""Pure tests of the C3a-4 panel tool's comparison and bookkeeping (tools/c1b1_native_panel.py; no physics run).

Kept outside tests/ with the other C3a tests (designer decision (c)).
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location('native_panel', ROOT / 'tools/c1b1_native_panel.py')
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


def res(sweep='0.5', q='7', cpu=1.0):
    st = dict(tick=10, q_raw=[q, '3'], p_raw=['1', '2'], r='20.1', time='400', sweep=sweep, substeps=40)
    return dict(status='accepted', j_out=1, bits_out=[48, 80], out=dict(st), out_base=dict(st, sweep_shift='0'),
                pairs=[dict(j=0, tick=10, est_step_sweep='1e-12', est_step_time='2e-12', C_state=dict(st),
                            cpu_s=cpu)],
                level0=dict(st), substeps=120, world_kdk=dict(st, cpu_s=cpu),
                track_cost=[dict(j=0, extra=0, substeps=40, cpu_s=cpu), dict(j=1, extra=0, substeps=80, cpu_s=cpu)])


def row(pid, engine, kind='ok', kicks=100, **kw):
    r = dict(id=pid, engine=engine, kind=kind)
    if kind == 'ok':
        r.update(world=P.world(res(**kw)), kicks=kicks, pen_cpu_s=2.0, kdk_cpu_s=0.5)
    return r


def test_world_drops_verification_and_cpu_fields():
    w = P.world(res(cpu=1.0))
    assert w == P.world(res(cpu=9.0))
    assert 'cpu_s' not in w['world_kdk'] and 'cpu_s' not in w['pairs'][0]
    assert w['track_substeps'] == [[0, 0, 40], [1, 0, 80]]


def test_identical():
    v = P.classify(row('G1', 'py'), row('G1', 'native'))
    assert v['verdict'] == 'IDENTICAL' and v['n_diffs'] == 0 and v['kicks_equal']


def test_last_digit_of_sweep_is_a_difference():
    v = P.classify(row('G1', 'py', sweep='0.5000000001'), row('G1', 'native', sweep='0.5000000002'))
    assert v['verdict'] == 'DIFFERENT'
    assert '.out.sweep' in v['diffs'] and '.level0.sweep' in v['diffs']


def test_integer_difference():
    v = P.classify(row('G1', 'py', q='7'), row('G1', 'native', q='8'))
    assert v['verdict'] == 'DIFFERENT' and '.out.q_raw[0]' in v['diffs']


def test_kick_count_difference():
    v = P.classify(row('G1', 'py', kicks=100), row('G1', 'native', kicks=101))
    assert v['verdict'] == 'DIFFERENT' and v['n_diffs'] == 0 and not v['kicks_equal']


@pytest.mark.parametrize('a,b', [('refused', 'ok'), ('ok', 'refused'), ('refused', 'refused')])
def test_refusal_is_unresolved(a, b):
    assert P.classify(row('B4', 'py', a), row('B4', 'native', b))['verdict'] == 'UNRESOLVED'


def test_error_and_missing():
    assert P.classify(row('B4', 'py', 'error'), row('B4', 'native', 'refused'))['verdict'] == 'ERROR'
    assert P.classify(None, row('B4', 'native'))['verdict'] == 'ERROR'
    assert P.classify(row('B4', 'py'), None)['verdict'] == 'ERROR'


def test_summary_counts_every_panel_input(tmp_path):
    rows = [row(i, e) for i in P.PANEL_IDS for e in P.ENGINES if i != 'H2']
    rows[0] = row(rows[0]['id'], rows[0]['engine'], sweep='0.6')
    f = tmp_path / 'rows.jsonl'
    f.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    s = P.summary(f, tmp_path / 's.json')
    assert s['counts'] == {'DIFFERENT': 1, 'IDENTICAL': 12, 'ERROR': 1}
    assert s['per_input']['H2']['verdict'] == 'ERROR'
    assert s['per_input']['G2']['pen_ratio'] == 1.0


def test_summary_refuses_duplicate_rows(tmp_path):
    f = tmp_path / 'rows.jsonl'
    f.write_text(json.dumps(row('G1', 'py')) + '\n' + json.dumps(row('G1', 'py')) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        P.summary(f, tmp_path / 's.json')


def test_order_python_first_then_smallest_rho():
    panel = {k: dict(rho=None) for k in P.PANEL_IDS}
    panel.update(B4=dict(rho='1e-9'), B1=dict(rho='1e-3'))
    jobs = [(k, e) for k in ('G1', 'B1', 'B4') for e in P.ENGINES]
    got = sorted(jobs, key=lambda j: P.order_key(j, panel))
    assert got == [('B4', 'py'), ('B1', 'py'), ('G1', 'py'), ('B4', 'native'), ('B1', 'native'), ('G1', 'native')]


def _raise(exc):
    def f(*a, **k):
        raise exc
    return f


def test_one_maps_exceptions_to_row_kinds(monkeypatch):
    from c1b1_method_bench.fixedpoint import Undecided
    from c1b1_native.track import NativeError, NativeRefused
    cases = [(Undecided('tie'), 'refused'), (NativeRefused('refuse: exit band'), 'refused'),
             (RuntimeError('level 2: no exit within 300000 ticks'), 'no_exit'),
             (NativeError('no exit'), 'error'), (RuntimeError('something else'), 'error'), (ValueError('x'), 'error')]
    for exc, kind in cases:
        monkeypatch.setattr(P, 'run_world', _raise(exc))
        assert P.one(('G1', 'py', ['1'], None))['kind'] == kind, exc


def test_no_exit_pairs():
    ne = lambda e, m='level 2: no exit within 300000 ticks': dict(id='B6', engine=e, kind='no_exit', message=m)
    assert P.classify(ne('py'), ne('native'))['verdict'] == 'IDENTICAL'
    assert P.classify(ne('py'), ne('native', 'level 3: no exit within 300000 ticks'))['verdict'] == 'DIFFERENT'
    assert P.classify(ne('py'), row('B6', 'native'))['verdict'] == 'DIFFERENT'
    assert P.classify(ne('py'), row('B6', 'native', 'refused'))['verdict'] == 'UNRESOLVED'


def test_type_difference_and_unexpected_rows(tmp_path):
    a, b = row('G1', 'py'), row('G1', 'native')
    b['world']['substeps'] = str(b['world']['substeps'])
    assert P.classify(a, b)['verdict'] == 'DIFFERENT'
    rows = [row(i, e) for i in P.PANEL_IDS for e in P.ENGINES] + [row('T7X', 'py')]
    f = tmp_path / 'rows.jsonl'
    f.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    s = P.summary(f, tmp_path / 's.json')
    assert s['counts'] == {'IDENTICAL': 14} and s['unexpected_rows'] == [['T7X', 'py']] and s['manifest'] is None
