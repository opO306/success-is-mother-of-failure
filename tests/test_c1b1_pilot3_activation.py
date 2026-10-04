import copy,json
from fractions import Fraction as Q
import pytest
from a_reference import c1b1_runtime as R,c1b1_two_atom as C,c1b1_fast_impulse as F,c1b1_pilot3_impulse as X
from experiments.verified_superoptimizer_c1b1 import pilot3_campaign as P,integration_stages as I

def test_chosen_ABCD_is_default_and_preserves_explicit_fast_and_REF():
    run=P.make_run(dict(e='2',b_frac='1/2'));ex=R.bind(run,mode='fast_pilot3')
    assert ex.variant=='ABCD' and ex.function.__code__ is C.step.__code__
    assert R.select()==(X.impulse,X.step)
    assert R.select('fast')==(F.impulse,F.step_fast) and R.select('reference')==(C.impulse,C.step)
    assert R.select('fast_pilot3')==(X.impulse,X.step)
    assert C.step.__globals__['impulse'] is C.impulse
    original=copy.copy(run)
    for _ in range(20):
        ex.step();C.step(original);assert I.raw(run)==I.raw(original)

@pytest.mark.parametrize('kind',['domain','impulse_overflow','momentum_overflow','position_overflow'])
def test_actual_selected_refusal_is_same_and_atomic(kind):
    run=P.make_run(dict(refusal=kind));ref=copy.copy(run);before=dict(vars(run))
    assert I.capture(R.bind(run,mode='fast_pilot3').step)==I.capture(C.step,ref)
    assert vars(run)==before

def test_actual_producer_dispatches_new_mode(tmp_path,monkeypatch):
    from tools import c1b1_replay_benchmark as producer
    run=P.make_run(dict(e='9',b_frac='0'));states=[[list(v) for a in run.atoms for v in (a.r,a.p)]]
    js=[list(C.impulse(C.relative(run.pos,*run.atoms),Q(20),run.mom))]
    for _ in range(3):
        C.step(run);states.append([list(v) for a in run.atoms for v in (a.r,a.p)]);js.append(list(run.J_cache))
    (tmp_path/'witness_unit.json').write_text(json.dumps(dict(states=states,J=js,steps=3)),encoding='utf8')
    monkeypatch.setattr(producer,'OLD',tmp_path)
    actual=R.bind;calls=[]
    def bind(run,*,mode='fast'):
        ex=actual(run,mode=mode);assert ex.variant=='ABCD';calls.append(mode);return ex
    monkeypatch.setattr(R,'bind',bind)
    result=producer.execute('unit',mode='fast_pilot3')
    assert calls==['fast_pilot3'] and result['all_states_equal_old_raw_inputs']

def test_selected_closure_is_equivalent_to_measured_isolated_candidate():
    run=P.make_run(dict(e='2',b_frac='1/2'));a=R.bind(run,mode='fast_pilot3');b=X.Runtime(copy.copy(run),'ABCD')
    af,bf=a.function.__globals__['impulse'],b.function.__globals__['impulse']
    assert af.__code__ is bf.__code__ and af.__globals__ is bf.__globals__
    assert [c.cell_contents for c in af.__closure__]==[c.cell_contents for c in bf.__closure__]
