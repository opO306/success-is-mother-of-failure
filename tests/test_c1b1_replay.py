"""Permanent witness/model mutants. Only the independent verifier makes verdicts."""
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import subprocess
import sys
import pytest
from c1b1_replay import Limits, Verdict, verify
from c1b1_replay import exact, spec
from c1b1_replay.history import Approval, History
from c1b1_replay.model import Dual, Model, endpoints
from c1b1_replay.provenance import fingerprints, independence
from c1b1_replay.types import Invalid, Refused
from c1b1_replay.witness import Header, Reader, canonical, write, MAGIC

FIXTURE=json.loads((Path(__file__).parent/'fixtures/c1b1_replay_v1_windows.json').read_text())

def window(name='initial'):
    row=copy.deepcopy(FIXTURE['windows'][name])
    return [tuple(x for group in s for x in group) for s in row['states']], [tuple(j) for j in row['J']],row['start']

def encode(states,js,start,end='SEGMENT'):
    stream=io.BytesIO()
    write(stream,Header(states[0],js[0],states[-1],len(states)-1,start,end),zip(js[1:],states[1:]))
    return stream.getvalue()

@pytest.mark.parametrize('name',list(FIXTURE['windows']))
def test_true_windows_stream_and_full(name):
    payload=encode(*window(name))
    a,b=verify(payload),verify(payload,materialize=True)
    assert a.verdict==b.verdict==Verdict.VALID
    assert a.verified_steps==b.verified_steps==6
    assert a.last_state==b.last_state
    assert a.witness_sha256==b.witness_sha256

@pytest.mark.parametrize('kind',range(6))
def test_six_original_witness_faults(kind):
    states,js,start=window('recross' if kind==2 else 'turning')
    at=3
    if kind in (0,1,2,3):
        component=1 if kind==2 else 2 if kind==3 else 0
        delta=-1 if kind==2 else 1
        changed=list(js[at]);changed[component]+=delta;js[at]=tuple(changed)
        if kind in (1,2):
            # Forge every subsequent state consistently with the forged J.
            for k in range(at-1,len(states)-1):
                states[k+1]=exact.transition(states[k],js[k],js[k+1])
    else:
        changed=list(states[at]);changed[6 if kind==4 else 3]+=1;states[at]=tuple(changed)
    result=verify(encode(states,js,start))
    assert result.verdict==Verdict.INVALID
    assert result.verified_steps<at

def test_original_truncated_exit_is_refused():
    result=verify(encode(*window('truncated'),end='R20_OUTBOUND'))
    assert result.verdict==Verdict.REFUSED
    assert result.verified_steps==6

@pytest.mark.parametrize('kind',['qed','c6','half','sign','derivative'])
def test_original_model_faults_and_added_derivative_fault(monkeypatch,kind):
    if kind=='qed':
        changed=copy.deepcopy(spec.SHORT)
        for j,(alpha,coefficients) in changed['QED'].items():
            changed['QED'][j]=(alpha,{i:'0' for i in coefficients})
        monkeypatch.setattr(spec,'SHORT',changed)
    elif kind=='c6':
        changed=copy.deepcopy(spec.LONG);changed['BO'][1][3]='64.2295223'
        monkeypatch.setattr(spec,'LONG',changed)
    elif kind=='half':
        monkeypatch.setattr(spec,'HALF',spec.DT/4)
    else:
        original=Model.evaluate
        def mutant(self,r2,bits):
            v,d,r=original(self,r2,bits)
            return v,(-d if kind=='sign' else d*0),r
        monkeypatch.setattr(Model,'evaluate',mutant)
    assert verify(encode(*window())).verdict==Verdict.INVALID

@pytest.mark.parametrize('limits',[Limits(max_steps=1),Limits(max_bytes=15),
    Limits(max_evaluations=1),Limits(start_bits=16,max_bits=16),Limits(seconds=1e-12)])
def test_resource_refused_not_invalid(limits):
    assert verify(encode(*window()),limits).verdict==Verdict.REFUSED

def test_stream_can_read_partial_chunks():
    class Slow(io.BytesIO):
        def read(self,n=-1):return super().read(min(n,3))
    assert verify(Slow(encode(*window()))).verdict==Verdict.VALID
    assert verify(Slow(encode(*window())),materialize=True).verdict==Verdict.VALID

def test_exact_byte_limit_and_noncanonical_varint():
    import struct
    payload=encode(*window())
    assert verify(payload,Limits(max_bytes=len(payload))).verdict==Verdict.VALID
    size=struct.unpack('<I',payload[8:12])[0]
    at=12+size
    # First varint encoded redundantly, without changing its numerical value.
    end=at
    while payload[end]&128:end+=1
    mutant=payload[:end]+bytes([payload[end]|128,0])+payload[end+1:]
    assert verify(mutant).verdict==Verdict.INVALID

def test_dependency_version_refused(monkeypatch):
    import mpmath
    monkeypatch.setattr(mpmath,'__version__','unapproved')
    assert verify(encode(*window())).verdict==Verdict.REFUSED

def test_unapproved_backend_refused(monkeypatch):
    import mpmath
    monkeypatch.setattr(mpmath.libmp,'BACKEND','unapproved')
    assert verify(encode(*window())).verdict==Verdict.REFUSED

def test_truncated_wire_refused_and_trailing_invalid():
    payload=encode(*window())
    assert verify(payload[:-2]).verdict==Verdict.REFUSED
    assert verify(payload+b'x').verdict==Verdict.INVALID

def rewrite_header(payload,mutate):
    import struct
    size=struct.unpack('<I',payload[8:12])[0]
    data=json.loads(payload[12:12+size]);mutate(data)
    header=canonical(data)
    return MAGIC+struct.pack('<I',len(header))+header+payload[12+size:]

@pytest.mark.parametrize('mutate',[
    lambda d:d['initial'].__setitem__(0,'01'),
    lambda d:d.__setitem__('n_steps',True),
    lambda d:d['initial'].__setitem__(0,str(1<<95)),
    lambda d:d['final'].__setitem__(0,str(int(d['final'][0])+1)),
    lambda d:d.__setitem__('extra',0)])
def test_malformed_and_false_claims_invalid(mutate):
    assert verify(rewrite_header(encode(*window()),mutate)).verdict==Verdict.INVALID

def test_foreign_spec_refused():
    assert verify(rewrite_header(encode(*window()),lambda d:d.__setitem__('spec','0'*64))).verdict==Verdict.REFUSED

def test_initial_energy_admission_independent_of_J():
    def mutant(d):
        for at in (3,4,9,10):d['initial'][at]=str(100*int(d['initial'][at]))
    result=verify(rewrite_header(encode(*window()),mutant))
    assert result.verdict==Verdict.INVALID
    assert '10 De' in result.reason
    assert result.verified_steps==0

def test_nonfinite_backend_refuses(monkeypatch):
    original=Model.evaluate
    def mutant(self,r2,bits):
        v,d,r=original(self,r2,bits)
        return v,self.context(bits)[0].mpf('inf'),r
    monkeypatch.setattr(Model,'evaluate',mutant)
    assert verify(encode(*window())).verdict==Verdict.REFUSED

def test_streaming_model_cache_contains_only_spec_constants():
    from fractions import Fraction as Q
    model=Model()
    model.evaluate(Q(400),128)
    constant_keys=set(model.contexts[128][1])
    for i in range(1,25):model.evaluate(Q(400+i,1),128)
    assert set(model.contexts[128][1])==constant_keys

def test_exact_rounding_even_ties_and_odd_symmetry():
    for n,want in [(1,0),(3,2),(5,2),(7,4)]:
        assert exact.nearest(n,2)==want
        assert exact.nearest(-n,2)==-want

def test_unrounded_segment_guard_endpoints_not_enough():
    from fractions import Fraction as Q
    assert Q(3)**2>spec.R_MIN2
    with pytest.raises(Invalid,match='segment'):
        exact.guard((Q(3),Q(0),Q(0)),(Q(-6),Q(0),Q(0)))
    exact.guard((Q(3),Q(0),Q(0)),(Q(0),Q(0),Q(0)))

def test_overflow_is_explicit_and_profile_bools_rejected():
    s,j,_=window()
    bad=list(s[0]);bad[3]=spec.LOW
    with pytest.raises(Invalid):exact.drift(tuple(bad),(1,0,0))
    with pytest.raises(Invalid):exact.raw(True)

def test_isolated_import_independence():
    assert independence()==()
    code='import c1b1_replay,sys; assert not any(n.split(".")[0] in {"a_reference","a_numeric","engine","audit"} for n in sys.modules)'
    subprocess.run([sys.executable,'-c',code],check=True,capture_output=True)

def test_frozen_spec_matches_executor_spec_only():
    from a_reference import c1b1_two_atom as c
    from a_reference import ar2_lang2024 as l
    assert spec.MASS==c.AR40_MASS_ME
    assert spec.R_MIN2==c.R_MIN2
    assert spec.DE==c.DE_CONTRACT
    assert spec.FROZEN_FINGERPRINT==l.parameter_fingerprint()

def approval():
    impl,dep=fingerprints()
    return Approval('TEST ONLY explicit synthetic approval',spec.SPEC_FINGERPRINT,impl,dep)

def test_history_confirms_only_approved_valid_and_binds_origin(tmp_path):
    s,j,start=window()
    payload=encode(s,j,start)
    history=History(tmp_path,s[0],approval=approval())
    history.enqueue(payload)
    assert history.verify_next().verdict==Verdict.VALID
    assert history.entries[0].status=='CONFIRMED'
    assert history.entries[0].evidence=='REPLAY_VERIFIED'
    assert history.confirmed==s[-1]
    assert history.entries[0].witness_path.read_bytes()==payload

@pytest.mark.parametrize('kind',['no_approval','stale_approval','refused'])
def test_history_keeps_unconfirmed_and_halts(tmp_path,kind):
    s,j,start=window();policy=approval()
    if kind=='no_approval':policy=None
    if kind=='stale_approval':policy=replace(policy,implementation_fingerprint='0'*64)
    history=History(tmp_path,s[0],approval=policy,limits=Limits(max_evaluations=1) if kind=='refused' else None)
    history.enqueue(encode(s,j,start));result=history.verify_next()
    assert result.verdict==(Verdict.REFUSED if kind=='refused' else Verdict.VALID)
    assert history.entries[0].status=='SPECULATIVE'
    assert history.confirmed==s[0]
    with pytest.raises(Refused):history.verify_next()

def test_history_bad_interval_discards_descendants_no_retry(tmp_path):
    s,j,start=window()
    h=History(tmp_path,s[0],approval=approval())
    bad=list(s[3]);bad[6]+=1;s[3]=tuple(bad)
    h.enqueue(encode(s,j,start));h.enqueue(encode(*window('turning')))
    assert h.verify_next().verdict==Verdict.INVALID
    assert [e.status for e in h.entries]==['DISCARDED','DISCARDED']
    assert h.confirmed==s[0]
    with pytest.raises(Refused):h.verify_next()

def test_valid_wrong_history_root_discards(tmp_path):
    s,j,start=window();bad=list(s[0]);bad[0]+=1
    h=History(tmp_path,tuple(bad),approval=approval())
    h.enqueue(encode(s,j,start))
    assert h.verify_next().verdict==Verdict.INVALID
    assert h.entries[0].status=='DISCARDED'

def test_history_last_confirmed_survives_bad_descendants(tmp_path):
    s,j,start=window();h=History(tmp_path,s[0],approval=approval())
    h.enqueue(encode(s,j,start));h.verify_next()
    saved=h.confirmed
    # Valid standalone interval, wrong causal root; both descendants must be discarded.
    h.enqueue(encode(*window('turning')));h.enqueue(encode(*window('recross')))
    assert h.verify_next().verdict==Verdict.INVALID
    assert [e.status for e in h.entries]==['CONFIRMED','DISCARDED','DISCARDED']
    assert h.confirmed==saved

def test_speculative_distance_cap_and_retained_file_binding(tmp_path):
    s,j,start=window();payload=encode(s,j,start)
    h=History(tmp_path,s[0],limits=Limits(max_steps=6),approval=approval())
    h.enqueue(payload)
    with pytest.raises(Refused,match='distance'):h.enqueue(payload)
    # A different VALID witness cannot replace the retained evidence under its original name.
    h.entries[0].witness_path.write_bytes(encode(*window('turning')))
    assert h.verify_next().verdict==Verdict.INVALID

def test_cli_refused_is_exit_two(tmp_path):
    path=tmp_path/'sample.c1br';path.write_bytes(encode(*window()))
    run=subprocess.run([sys.executable,'-m','c1b1_replay',str(path),'--max-steps','1'],capture_output=True,text=True)
    assert run.returncode==2
    assert json.loads(run.stdout)['verdict']=='REFUSED'
