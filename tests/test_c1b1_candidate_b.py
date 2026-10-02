"""Promotion tests: evidence cannot manufacture a successful execution."""
import importlib
import json
from pathlib import Path
import pytest
from fractions import Fraction as Q


def test_evidence_closure_exists_and_missing_run_is_incomplete(tmp_path):
    path = Path('experiments/verified_superoptimizer_c1b1/evidence.py')
    assert path.exists(), 'run-bound evidence closure is missing'
    e = importlib.import_module('experiments.verified_superoptimizer_c1b1.evidence')
    assert e.check_run(tmp_path)['status'] == 'INCOMPLETE'


@pytest.fixture
def executed(tmp_path):
    from experiments.verified_superoptimizer_c1b1 import evidence as e
    run = tmp_path / 'fresh'
    e.create_run(run, e.HERE / 'pilot_inputs.json', required=('structure',))
    assert e.run_stage(run, 'structure') == 0
    assert e.check_run(run, required=('structure',))['status'] == 'PASS'
    return e, run


@pytest.mark.parametrize('fault', ['run_id','source_hash','input_hash','candidate_hash','checker_hash',
                                  'profile_version','returncode','executed','command','output','input',
                                  'missing','duplicate','source_inventory','result_binding','false_check'])
def test_fresh_execution_cannot_be_replaced_by_stale_or_missing_evidence(executed, fault):
    e, run = executed
    m = json.loads((run / 'manifest.json').read_bytes())
    r = m['stages'][0]
    if fault in e.binding(m):
        r[fault] = 'stale'
    elif fault == 'returncode':
        r[fault] = 7
    elif fault == 'executed':
        r[fault] = False
    elif fault == 'command':
        r[fault] = []
    elif fault == 'output':
        (run / 'structure.log').write_text('replaced old log')
    elif fault == 'input':
        (run / 'inputs.json').write_text('[]')
    elif fault == 'missing':
        m['stages'] = []
    elif fault == 'duplicate':
        m['stages'].append(dict(r))
    elif fault == 'source_inventory':
        m['source_hash'] = 'changed'
    else:
        result = json.loads((run / 'structure.json').read_bytes())
        if fault == 'result_binding':
            result['run_id'] = 'another run'
        else:
            result['checks']['a_live_ast_equal'] = False
        e.write(run / 'structure.json', result)
        r['outputs']['structure.json'] = e.sha(run / 'structure.json')
    e.write(run / 'manifest.json', m)
    assert e.check_run(run, required=('structure',))['status'] in ('INCOMPLETE', 'FAIL')


def test_summary_cannot_downgrade_required_gate_set(executed):
    e, run = executed
    m = json.loads((run / 'manifest.json').read_bytes())
    m['required'] = ['structure']
    e.write(run / 'manifest.json', m)
    assert e.check_run(run)['status'] == 'INCOMPLETE'


def test_execution_log_is_required_even_when_deleted_from_manifest(executed):
    e, run = executed
    m = json.loads((run / 'manifest.json').read_bytes())
    del m['stages'][0]['outputs']['structure.log']
    e.write(run / 'manifest.json', m)
    assert e.check_run(run, required=('structure',))['status'] == 'INCOMPLETE'


def test_arbitrary_true_check_cannot_replace_stage_semantics(executed):
    e, run = executed
    m = json.loads((run / 'manifest.json').read_bytes())
    result = json.loads((run / 'structure.json').read_bytes())
    result['checks'] = {'anything': True}
    e.write(run / 'structure.json',result)
    m['stages'][0]['outputs']['structure.json'] = e.sha(run / 'structure.json')
    e.write(run / 'manifest.json',m)
    assert e.check_run(run,required=('structure',))['status'] == 'INCOMPLETE'


def test_run_directory_cannot_be_reused(executed):
    e, run = executed
    with pytest.raises(FileExistsError):
        e.create_run(run, e.HERE / 'pilot_inputs.json')
    with pytest.raises(ValueError, match='only once'):
        e.run_stage(run, 'structure')


@pytest.mark.parametrize('fault',['wrong_command','empty_payload'])
def test_arbitrary_command_or_empty_payload_cannot_pass(executed,fault):
    e,run=executed
    m=json.loads((run/'manifest.json').read_bytes())
    if fault=='wrong_command':
        m['stages'][0]['command']=['python','-c','print(True)']
    else:
        result=json.loads((run/'structure.json').read_bytes())
        result['payload']={}
        e.write(run/'structure.json',result)
        m['stages'][0]['outputs']['structure.json']=e.sha(run/'structure.json')
    e.write(run/'manifest.json',m)
    assert e.check_run(run,required=('structure',))['status']=='INCOMPLETE'


@pytest.mark.parametrize('stage', ['fixed','high','dataset','mutations','trajectory','benchmark'])
def test_empty_witnesses_cannot_pass(stage,tmp_path):
    from experiments.verified_superoptimizer_c1b1 import evidence as e
    assert not e.valid_payload(tmp_path,stage,[])


def test_separate_repository_fast_path_exists():
    assert Path('a_reference/c1b1_fast_impulse.py').exists(), 'separate opt-in repo integration missing'


@pytest.mark.parametrize('denominator', [(0,1),(-1,2),(2,1)])
def test_positive_division_guard_is_executable(denominator):
    from experiments.verified_superoptimizer_c1b1 import fast_primitives as fp
    with pytest.raises(ValueError, match='positive ordered'):
        fp._div_pos((-5,7),denominator,128)


@pytest.mark.parametrize('dr,dt', [((Q(3),Q(0),Q(0)),Q(20)),
                                  ((Q(6),Q(-8),Q(0)),Q(20)),
                                  ((Q(10),Q(1,2**120),Q(-1,2**160)),Q(20)),
                                  ((Q(3),Q(0),Q(0)),Q(0)),
                                  ((Q(0),Q(0),Q(0)),Q(0))])
def test_repo_raw_endpoints_and_decision_sequence_match(dr,dt):
    from experiments.verified_superoptimizer_c1b1 import stage as s, verify as v
    from a_reference import c1b1_fast_impulse as fast
    spec = dict(kind='FX',width=96,frac=80)
    assert s.trace(fast,dr,dt,spec) == s.trace(v.REF,dr,dt,spec) == s.independent_trace(dr,dt,spec)


def test_production_step_is_exact_reference_code_with_only_impulse_rebound():
    from a_reference import c1b1_fast_impulse as fast, c1b1_two_atom as ref
    assert fast.step_fast.__code__ is ref.step.__code__
    assert fast.step_fast.__globals__['impulse'] is fast.impulse
    assert ref.step.__globals__['impulse'] is ref.impulse
    for name in ref.step.__code__.co_names:
        if name != 'impulse':
            assert fast.step_fast.__globals__.get(name) is ref.step.__globals__.get(name)


@pytest.mark.parametrize('kind', ['precision','domain','impulse_overflow','momentum_overflow','position_overflow'])
def test_fast_step_has_same_refusal_and_no_partial_write(kind,monkeypatch):
    import copy
    from a_reference import c1b1_fast_impulse as fast, c1b1_two_atom as c
    from a_reference import c1b1_stress_survey as x
    from a_numeric.profiles import FixedPoint
    z = (Q(0),)*3
    if kind == 'precision':
        st = x.canonical(Q(1,2),Q(0))
        rj = (st['r_j'][0]+Q(46,1<<48),Q(0),Q(0))
        run = c.new_run(x.POS,40,st['r_i'],st['p_i'],rj,st['p_j'],momentum_profile=x.MOM)
        monkeypatch.setattr(c,'MAX_PRECISION_BITS',128)
    elif kind == 'domain':
        p = (Q(6000),Q(0),Q(0))
        run = c.new_run(x.POS,40,(Q(0),Q(-1),Q(0)),tuple(-q for q in p),
                        (Q(-3),Q(1),Q(0)),p,momentum_profile=x.MOM,validated_only=False)
    elif kind == 'impulse_overflow':
        run = c.new_run(x.POS,40,z,z,(Q(3),Q(0),Q(0)),z,momentum_profile=FixedPoint(8,4),validated_only=False)
    elif kind == 'momentum_overflow':
        p = (Q(12799,100),Q(0),Q(0))
        run = c.new_run(x.POS,40,z,tuple(-q for q in p),(Q(5),Q(0),Q(0)),p,
                        momentum_profile=FixedPoint(24,16),validated_only=False)
    else:
        p = (Q(10),Q(0),Q(0))
        run = c.new_run(FixedPoint(40,32),40,(Q(108),Q(0),Q(0)),tuple(-q for q in p),
                        (Q(127999,1000),Q(0),Q(0)),p,momentum_profile=x.MOM)
    outcomes = []
    for step in (c.step,fast.step_fast):
        fresh = copy.deepcopy(run)
        before = dict(vars(fresh))
        try:
            step(fresh)
        except Exception as exc:
            outcomes.append((type(exc),getattr(exc,'reason',None),str(exc)))
        else:
            pytest.fail('expected actual refusal')
        assert vars(fresh) == before
    assert outcomes[0] == outcomes[1]


def test_executable_fault_injection_and_original_counterexample():
    from experiments.verified_superoptimizer_c1b1.stage import mutants
    rows = mutants()
    assert len(rows) == 8 and all(r['detected'] for r in rows)
    assert all('mutant_source_hash' in r for r in rows[:6])
    old = rows[-1]
    assert old['historical_reproduced']
    assert int(old['mutant'][0][0])-int(old['expected'][0][0]) == -490
    assert int(old['mutant'][0][1])-int(old['expected'][0][1]) == 64


def test_repository_ast_equivalence():
    from experiments.verified_superoptimizer_c1b1.integration_stages import repo_equivalence
    assert repo_equivalence()


def test_trajectory_checker_rejects_wrong_fast_impulse(monkeypatch):
    import io
    from experiments.verified_superoptimizer_c1b1 import integration_stages as s
    original=s.FAST.impulse
    def wrong(*args):
        value=original(*args)
        return (value[0]+1,*value[1:])
    monkeypatch.setattr(s.FAST,'impulse',wrong)
    with pytest.raises(AssertionError):
        s.paired(dict(id='injected',e='9',b_frac='0',cap=1),io.BytesIO())
