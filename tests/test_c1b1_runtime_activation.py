"""The production producer must exercise the selected runtime, with REF reachable."""
import copy
import importlib
import io
import json
import gzip
import hashlib
from pathlib import Path
from fractions import Fraction as Q
import pytest


def runtime():
    assert Path('a_reference/c1b1_runtime.py').is_file(), 'production runtime selector missing'
    return importlib.import_module('a_reference.c1b1_runtime')


def driver():
    assert Path('experiments/verified_superoptimizer_c1b1/runtime_activation.py').is_file(), 'runtime differential gate missing'
    return importlib.import_module('experiments.verified_superoptimizer_c1b1.runtime_activation')


def test_default_fast_and_explicit_reference_are_real_functions():
    r = runtime()
    from a_reference import c1b1_two_atom as c, c1b1_fast_impulse as f
    assert r.select() == (f.impulse, f.step_fast)
    assert r.select('reference') == (c.impulse, c.step)
    assert r.new_run is c.new_run


@pytest.mark.parametrize('mode', ['REF', '', None, 'automatic'])
def test_unknown_mode_fails_before_any_state_change(mode):
    r = runtime()
    with pytest.raises(ValueError, match='mode'):
        r.step(object(), mode=mode)


@pytest.mark.parametrize('mode', ['fast', 'reference', 'fast_combined'])
def test_real_production_producer_dispatches_selected_runtime(mode, tmp_path, monkeypatch):
    r = runtime()
    from a_reference import c1b1_two_atom as c
    from experiments.verified_superoptimizer_c1b1 import integration_stages as i
    from tools import c1b1_replay_benchmark as producer
    run = i.make_run(dict(e='9', b_frac='0'))
    states = [[list(v) for a in run.atoms for v in (a.r, a.p)]]
    js = [list(c.impulse(c.relative(run.pos, *run.atoms), Q(20), run.mom))]
    for _ in range(3):
        c.step(run)
        states.append([list(v) for a in run.atoms for v in (a.r, a.p)])
        js.append(list(run.J_cache))
    (tmp_path/'witness_unit.json').write_text(json.dumps(dict(states=states, J=js, steps=3)))
    monkeypatch.setattr(producer, 'OLD', tmp_path)
    calls = []
    actual = r.bind
    bindings = []
    def observed(run, *, mode='fast'):
        ex = actual(run, mode=mode)
        bindings.append(mode)
        step = ex.step
        def traced():
            calls.append(mode)
            return step()
        ex.step = traced
        return ex
    monkeypatch.setattr(r, 'bind', observed)
    result = producer.execute('unit') if mode == 'fast' else producer.execute('unit', mode=mode)
    assert bindings == [mode]
    assert calls == [mode]*3
    assert result['runtime_mode'] == mode
    assert result['all_states_equal_old_raw_inputs']


@pytest.mark.parametrize('mode', ['fast', 'reference'])
@pytest.mark.parametrize('kind', ['domain', 'impulse_overflow', 'momentum_overflow', 'position_overflow'])
def test_selected_runtime_preserves_actual_refusal_state(mode, kind):
    r = runtime()
    from experiments.verified_superoptimizer_c1b1 import integration_stages as i
    run = i.make_run(dict(refusal=kind))
    original = dict(vars(run))
    reference = copy.copy(run)
    from a_reference import c1b1_two_atom as c
    expected = i.capture(c.step, reference)
    assert expected['kind'] != 'value'
    try:
        r.step(run, mode=mode)
    except Exception as exc:
        assert (type(exc).__name__, exc.reason, str(exc)) == (expected['type'], expected['reason'], expected['message'])
    else:
        pytest.fail('selected runtime swallowed an actual refusal')
    assert vars(run) == original


@pytest.mark.parametrize('mode', ['fast', 'reference'])
def test_precision_rehearsal_stops_selected_runtime_at_same_step(mode, monkeypatch):
    r = runtime()
    from a_reference import c1b1_two_atom as c, c1b1_stress_survey as x
    st = x.canonical(Q(1,2), Q(0))
    rj = (st['r_j'][0]+Q(46, 1<<48), Q(0), Q(0))
    run = c.new_run(x.POS, 40, st['r_i'], st['p_i'], rj, st['p_j'], momentum_profile=x.MOM)
    before = dict(vars(run))
    monkeypatch.setattr(c, 'MAX_PRECISION_BITS', 128)
    with pytest.raises(c.ReferenceUndecided):
        r.step(run, mode=mode)
    assert vars(run) == before and run.t_steps == 0


def test_runtime_never_patches_reference_globals():
    r = runtime()
    from a_reference import c1b1_two_atom as c
    from experiments.verified_superoptimizer_c1b1 import integration_stages as i
    originals = (c.step, c.impulse, c._model_R, c._decide)
    ref = i.make_run(dict(e='9', b_frac='0'))
    fast = copy.copy(ref)
    for _ in range(10):
        r.step(ref, mode='reference')
        r.step(fast)
        assert i.raw(ref) == i.raw(fast)
    assert originals == (c.step, c.impulse, c._model_R, c._decide)


def test_differential_gate_detects_wrong_actual_default_step(monkeypatch):
    d = driver()
    r = runtime()
    actual = r.step
    def bad(run, *, mode='fast'):
        actual(run, mode=mode)
        if mode == 'fast':
            run.J_cache = (run.J_cache[0]+1, *run.J_cache[1:])
    monkeypatch.setattr(r, 'step', bad)
    with pytest.raises(AssertionError):
        d.paired(dict(id='fault', e='9', b_frac='0', cap=1), io.BytesIO())


def test_differential_keeps_initial_state_and_every_actual_impulse():
    d = driver()
    stream = io.BytesIO()
    row = d.paired(dict(id='two', e='9', b_frac='0', cap=2), stream)
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert len(records) == 3 and records[0]['initial']
    assert row['records'] == 2 and row['impulses'] == 3
    assert all(x['REF_state'] == x['FAST_state'] and x['REF_impulses'] == x['FAST_impulses'] for x in records[1:])


def test_profile_uses_exclusive_cost_for_amdahl_bound():
    d = driver()
    row = d.cost_row(('f.py', 12, 'f'), (10, 10, 2.0, 7.0, {}), 10.0)
    assert row['exclusive_cpu_percent'] == 20.0
    assert row['self_cpu_per_call_seconds'] == 0.2
    assert row['ideal_elimination_whole_speedup_upper_bound'] == 1.25


def test_missing_activation_artifacts_cannot_be_passed_by_summary(tmp_path):
    d = driver()
    assert d.check_activation(tmp_path)['status'] != 'PASS'


def test_benchmark_rejects_fabricated_median():
    d = driver()
    inputs = dict(benchmark=dict(repetitions=3),runtime_trajectories=[dict(id='x')],trajectories=[dict(id='x')])
    samples = [dict(rep=rep,method=method,workload=workload,calls=1,result_sha256='same',
                    cpu_seconds=1.0,wall_seconds=1.0,**({'id':'x'} if workload=='trajectory' else {}))
               for rep in range(3) for method in ('REF','FAST') for workload in ('impulse','step','trajectory')]
    with pytest.raises(AssertionError):
        d.benchmark_valid(dict(samples=samples,medians=dict(impulse=dict(cpu_speedup=99.0))),inputs)


@pytest.mark.parametrize('fault', [None, 'initial', 'spec', 'duplicate_initial', 'attempt', 'step', 'missing_impulse', 'refusal_state'])
def test_differential_validator_rejects_broken_origin_or_history(tmp_path, fault):
    d = driver()
    from experiments.verified_superoptimizer_c1b1 import evidence as e, integration_stages as i
    spec = dict(id='real_cap_precision_STOP',dr=['10','0','0'],dt='20',cap=1)
    inputs = dict(runtime_trajectories=[],refusals=[],runtime_precision=dict(dr=spec['dr'],dt=spec['dt']))
    state = i.raw(d.make_run(spec))
    result = dict(kind='refusal',type='ReferenceUndecided',reason='executor_limit',message='diagnostic fixture')
    header = dict(id=spec['id'],initial=state,spec=spec)
    row = dict(id=spec['id'],attempt=1,REF_state=copy.deepcopy(state),FAST_state=copy.deepcopy(state),
               REF_result=result,FAST_result=result,REF_impulses=[dict(dr=spec['dr'],dt='20',result=result)],
               FAST_impulses=[dict(dr=spec['dr'],dt='20',result=result)])
    if fault=='initial':header['initial']=None
    elif fault=='spec':header['spec']={'unrelated':True}
    elif fault=='attempt':row['attempt']=999
    elif fault=='step':row['REF_state']['step']=row['FAST_state']['step']=999
    elif fault=='refusal_state':
        row['REF_state']['atoms'][0]['r']=(1,0,0)
        row['FAST_state']['atoms'][0]['r']=(1,0,0)
    elif fault=='missing_impulse':row['REF_impulses']=row['FAST_impulses']=[]
    encoded=e.canonical(row)+b'\n'
    summary=dict(id=spec['id'],steps=0,records=1,impulses=len(row['REF_impulses']),attempt=1,end='refusal',
                 result=result,final_sha256=e.digest(row['FAST_state']),witness_sha256=hashlib.sha256(encoded).hexdigest())
    with gzip.open(tmp_path/'runtime.witnesses.jsonl.gz','wb') as stream:
        stream.write(e.canonical(header)+b'\n')
        if fault=='duplicate_initial':stream.write(e.canonical(header)+b'\n')
        stream.write(encoded)
    if fault is None:
        assert d.differential_valid(tmp_path,dict(rows=[summary],real_cap=16384),inputs)
    else:
        with pytest.raises(AssertionError):
            d.differential_valid(tmp_path,dict(rows=[summary],real_cap=16384),inputs)
