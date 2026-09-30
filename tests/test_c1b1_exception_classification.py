"""Missing classification boundaries; existing physics/refusal tests remain authoritative."""
import io
import json
from pathlib import Path
from fractions import Fraction as Q
import pytest
from a_numeric import FixedPoint
from a_numeric.profiles import VMHalt
from a_reference import c1b1_two_atom as C, c1b1_stress_survey as X
from c1b1_replay import Limits, Verdict, verify
from c1b1_replay.history import Approval, History
from c1b1_replay.provenance import fingerprints
from c1b1_replay import spec
from c1b1_replay.witness import Header, write

def run_at(radius=Q(20),momentum=Q(1)):
    z=Q(0)
    return C.new_run(FixedPoint(96,48),Q(40),(-radius/2,z,z),(-momentum,z,z),
        (radius/2,z,z),(momentum,z,z),momentum_profile=FixedPoint(96,80),validated_only=False)

def test_reversed_enclosure_is_a_contract_violation_even_inside_one_rounding_cell():
    with pytest.raises(C.ContractViolation,match='reversed') as caught:
        C._decide(FixedPoint(96,80),lambda _: (Q(1,2**84),Q(0)))
    assert not isinstance(caught.value,C.ExecutorLimitExceeded)
    assert X.classify(caught.value)=='contract_violation'

@pytest.mark.parametrize('bad',[True,1<<95,-(1<<95)-1])
def test_malformed_stored_raw_stops_before_any_step_commit(bad):
    run=run_at();a,b=run.atoms
    run.atoms=(C.Atom(a.species,(bad,)+a.r[1:],a.p),b)
    before=dict(vars(run))
    with pytest.raises(C.ContractViolation,match='invalid stored raw'):C.step(run)
    assert vars(run)==before

@pytest.mark.parametrize('reason',['division_by_zero','sqrt_of_negative','non_finite_value'])
def test_limit_does_not_relabel_non_overflow_vm_halts(reason):
    original=VMHalt(reason)
    def fail():raise original
    with pytest.raises(VMHalt) as caught:C._limit(fail)
    assert caught.value is original and not isinstance(caught.value,C.ExecutorLimitExceeded)
    assert X.classify(original)=='vm_halt:'+reason
    class BrokenProfile:
        def from_exact(self,value):raise original
    # A non-range VM halt must not become precision exhaustion when the
    # evaluator interval crosses zero, or get hidden by refining an endpoint.
    with pytest.raises(VMHalt) as caught:
        C._decide(BrokenProfile(),lambda _: (Q(-1),Q(1)))
    assert caught.value is original

def test_profile_overflow_translation_keeps_the_original_cause():
    with pytest.raises(C.ExecutorLimitExceeded) as caught:
        C._limit(FixedPoint(8,4).from_exact,Q(8))
    assert type(caught.value) is C.ExecutorLimitExceeded
    assert isinstance(caught.value.__cause__,VMHalt) and caught.value.__cause__.reason=='overflow'
    assert X.classify(caught.value)=='executor_limit_exceeded'

def test_vm_halt_from_evaluator_is_not_an_endpoint_or_precision_claim():
    original=VMHalt('division_by_zero')
    def broken(_):raise original
    with pytest.raises(VMHalt) as caught:C._decide(FixedPoint(96,80),broken)
    assert caught.value is original

def test_known_direct_overflow_and_memory_are_not_unexpected_bug_records():
    assert X.classify(VMHalt('overflow'))=='vm_overflow'
    assert X.classify(MemoryError('budget'))=='resource_refused'
    assert X.classify(ValueError('unknown'))=='unexpected_exception'

def test_step_memory_refusal_stops_and_is_recorded_without_a_physics_failure(monkeypatch):
    run=run_at();before=dict(vars(run))
    sp=X.spec('test','memory',X.canonical(Q(1,2),Q(0)),2)
    def no_memory(*args):raise MemoryError('injected allocation refusal')
    monkeypatch.setattr(C,'_model',no_memory)
    with pytest.raises(MemoryError):C.step(run)
    assert vars(run)==before
    rec=X.run_trajectory(sp,telemetry=False)
    assert rec['end']=='resource_refused' and rec['exception'].startswith('MemoryError:')

@pytest.mark.parametrize('kind',['bootstrap','chain','inbound','outgoing_energy'])
@pytest.mark.parametrize('precision',[True,False])
def test_formal_catch_keeps_precision_apart_from_generic_executor_limits(monkeypatch,kind,precision):
    from a_reference import c1b1_outer_bootstrap as O,c1b1_outer_chain as OC
    from a_reference import c1b1_inbound_outer as IB,c1b1_outgoing_energy as OE
    run=run_at(Q(28),Q(-12)) if kind=='inbound' else run_at()
    original=C.ReferenceUndecided('injected precision cap') if precision else C.ExecutorLimitExceeded('injected capability limit')
    def fail(*args):raise original
    monkeypatch.setattr(C,'_kick' if kind=='chain' else 'impulse',fail)
    calls={'bootstrap':lambda:O.certify_shell(run,Q(20),Q(21),Q(2),32),
        'chain':lambda:OC.certify_outgoing_outer(run,Q(2)),
        'inbound':lambda:IB.certify_inbound_outer(run,Q(13)),
        'outgoing_energy':lambda:OE.certify_outgoing_outer_energy(run,Q(2))}
    with pytest.raises(O.NotCertified) as caught:calls[kind]()
    assert caught.value.__cause__ is original
    assert ('precision refused' if precision else 'executor limit exceeded') in str(caught.value)
    assert 'overflow' not in str(caught.value)

def replay_window():
    fixture=json.loads((Path(__file__).parent/'fixtures/c1b1_replay_v1_windows.json').read_bytes())
    row=fixture['windows']['initial']
    states=[tuple(v for group in s for v in group) for s in row['states']]
    js=[tuple(j) for j in row['J']]
    return states,js

@pytest.mark.parametrize('invalid',[False,True])
def test_replay_gate_keeps_resource_refusal_and_actual_invalidity_separate(tmp_path,invalid):
    states,js=replay_window();claimed=list(states)
    if invalid:
        changed=list(claimed[1]);changed[0]+=1;claimed[1]=tuple(changed)
    stream=io.BytesIO();write(stream,Header(states[0],js[0],claimed[-1],len(states)-1),zip(js[1:],claimed[1:]))
    limits=Limits() if invalid else Limits(max_steps=1)
    implementation,dependency=fingerprints()
    history=History(tmp_path,states[0],approval=Approval('test-only approval',spec.SPEC_FINGERPRINT,implementation,dependency))
    history.enqueue(stream.getvalue());history.limits=limits
    result=history.verify_next()
    assert result.verdict==(Verdict.INVALID if invalid else Verdict.REFUSED)
    assert history.entries[0].status==('DISCARDED' if invalid else 'SPECULATIVE')
    assert history.confirmed==states[0] and history.confirmed_step==0 and history.halted
