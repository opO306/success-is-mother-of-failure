import copy
import pytest
from experiments.verified_superoptimizer_c1b1 import pilot3_campaign as P,integration_stages as I

def test_actual_all_path_endpoint_and_def_use_comparison(tmp_path):
    row=P.paired(dict(id='small',e='2',b_frac='1/2',cap=3),tmp_path/'steps.gz')
    assert row['steps']==3 and row['counts']['models']==4
    # Initial transverse coordinate is exactly zero; no refinement for that axis.
    assert row['counts']['components']==7

def test_trace_gate_rejects_missing_mode_and_wrong_endpoint():
    spec=dict(id='small',e='2',b_frac='1/2',cap=1);original=P.make_run(spec)
    obs={}
    for mode in P.MODES:
        run=copy.copy(original);ex=P.bind(run,mode);events=[];P.instrument(ex,mode,events)
        obs[mode]=dict(result=I.capture(ex.step),state=P.plain(I.raw(run)),events=events)
    P.validate(obs,spec,original,P.plain(I.raw(original)))
    bad=copy.deepcopy(obs);bad['ABCD']['events'][0]['endpoint_trace'][0]['dV'][0]+=1
    with pytest.raises(AssertionError,match='disagreement'):P.validate(bad,spec,original,P.plain(I.raw(original)))
    del obs['B']
    with pytest.raises(AssertionError,match='missing'):P.validate(obs,spec,original,P.plain(I.raw(original)))

def test_three_axis_input_is_actual_canonical_stored_state():
    run=P.make_run(dict(adversarial='three_axis'))
    assert all(v!=0 for v in I.C.relative(run.pos,*run.atoms))

def test_wrong_actual_binding_cannot_be_replaced_by_observer(tmp_path,monkeypatch):
    actual=P.bind
    def bind(run,mode):
        ex=actual(run,mode)
        if mode=='ABCD':ex.function=P.clone(ex.function,impulse=lambda dr,dt,profile:(0,0,0))
        return ex
    monkeypatch.setattr(P,'bind',bind)
    with pytest.raises(AssertionError,match='disagreement'):
        P.paired(dict(id='bad_binding',e='2',b_frac='1/2',cap=1),tmp_path/'bad.gz')

def test_benchmark_uses_actual_zero_argument_bound_step(monkeypatch):
    run=P.make_run(dict(e='9',b_frac='0'));ex=P.bind(run,'fast_combined');states=[]
    monkeypatch.setattr(I,'outgoing',lambda run:run.t_steps==2)
    P.complete(run,ex,3,states)
    assert run.t_steps==2 and len(states)==2

def test_wrong_actual_nested_callee_is_preserved_and_rejected(tmp_path,monkeypatch):
    actual=P.bind
    def bind(run,mode):
        ex=actual(run,mode)
        if mode=='ABCD':
            selected=ex.function.__globals__['impulse']
            raw=P.clone(selected.__globals__['impulse_raw'],_mul=lambda a,b,M:(0,0))
            ex.function=P.clone(ex.function,impulse=P.clone(selected,impulse_raw=raw))
        return ex
    monkeypatch.setattr(P,'bind',bind)
    with pytest.raises(AssertionError,match='disagreement'):
        P.paired(dict(id='bad_callee',e='2',b_frac='1/2',cap=1),tmp_path/'bad.gz')
