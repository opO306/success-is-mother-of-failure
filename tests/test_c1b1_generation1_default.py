"""Generation 1 default must reach the bound ABCD executor through real production."""
import copy,json
from fractions import Fraction as Q
from a_reference import c1b1_runtime as R,c1b1_two_atom as C,c1b1_pilot3_impulse as X
from experiments.verified_superoptimizer_c1b1 import pilot3_campaign as P,integration_stages as I


def test_default_selector_and_bound_execution_are_guarded_pilot3():
    assert R.select()==(X.impulse,X.step)
    run=P.make_run(dict(e='9',b_frac='0'));reference=copy.copy(run);ex=R.bind(run)
    assert ex.variant=='ABCD' and ex._prepared_binding is not None
    assert ex.function.__code__ is C.step.__code__
    for _ in range(20):
        ex.step();C.step(reference)
        assert I.raw(run)==I.raw(reference)


def test_omitted_producer_mode_reaches_guarded_pilot3(tmp_path,monkeypatch):
    from tools import c1b1_replay_benchmark as producer
    run=P.make_run(dict(e='9',b_frac='0'))
    states=[[list(v) for a in run.atoms for v in (a.r,a.p)]]
    js=[list(C.impulse(C.relative(run.pos,*run.atoms),Q(20),run.mom))]
    for _ in range(3):
        C.step(run)
        states.append([list(v) for a in run.atoms for v in (a.r,a.p)])
        js.append(list(run.J_cache))
    (tmp_path/'witness_unit.json').write_text(json.dumps(dict(states=states,J=js,steps=3)),encoding='utf8')
    monkeypatch.setattr(producer,'OLD',tmp_path)
    actual=R.bind;calls=[]
    def observed(run,*,mode=R.bind.__kwdefaults__['mode']):
        ex=actual(run,mode=mode)
        assert ex.variant=='ABCD' and ex._prepared_binding is not None
        calls.append(mode)
        return ex
    monkeypatch.setattr(R,'bind',observed)
    row=producer.execute('unit')
    assert calls==['fast_pilot3'] and row['runtime_mode']=='fast_pilot3'
    assert row['all_states_equal_old_raw_inputs']
