"""Breaks guarded: changed exact meaning, misplaced rounding, overflow and stale bindings."""
import copy
import importlib
from pathlib import Path
from fractions import Fraction as Q
import pytest
from a_numeric.profiles import FixedPoint, VMHalt
from a_reference import c1b1_two_atom as C, c1b1_fast_impulse as F
from experiments.verified_superoptimizer_c1b1 import integration_stages as I


def pilot():
    assert Path('experiments/verified_superoptimizer_c1b1/pilot2_arithmetic.py').is_file(), 'Pilot2 missing'
    return importlib.import_module('experiments.verified_superoptimizer_c1b1.pilot2_arithmetic')


@pytest.mark.parametrize('raw', [0, 1, -1, 17, -17, 2**40, -(2**40)])
@pytest.mark.parametrize('dt', [Q(40), Q(7,11), Q(-9,13)])
def test_A_exact_endpoint_and_stored_displacement_match_REF(raw, dt):
    p=pilot(); pos=FixedPoint(96,48); mom=FixedPoint(96,80)
    atom=C.Atom('Ar40',(19,-31,47),(raw,-raw,0))
    packet=p.prepare_A(pos,mom,atom,dt)
    want=tuple(x*dt/C.SPECIES_MASS['Ar40'] for x in C.drift_momentum(mom,atom.p))
    assert packet.exact_displacement==want
    assert packet.stored_displacement==C.displacement(pos,mom,atom,dt)
    for rule in ('v1','v2'):
        assert p.drift_A(pos,mom,atom,dt,rule)==C._drift(pos,mom,atom,dt,rule)


def test_A_half_even_uses_displacement_not_endpoint_rounding():
    p=pilot(); pos=FixedPoint(8,0); mom=FixedPoint(16,0)
    # r=1 and d=1/2: displacement ties to 0; endpoint ties to 2.
    a=C.Atom('Ar40',(1,0,0),(1,0,0)); dt=C.SPECIES_MASS['Ar40']/2
    assert p.drift_A(pos,mom,a,dt,'v2')[0].r==(1,0,0)
    assert p.drift_A(pos,mom,a,dt,'v1')[0].r==(2,0,0)


@pytest.mark.parametrize('raw_r,raw_p',[(0,127),(127,1),(-128,-1)])
def test_A_range_overflow_is_REF_exception(raw_r,raw_p):
    p=pilot(); pos=FixedPoint(8,0); mom=FixedPoint(16,0)
    a=C.Atom('Ar40',(raw_r,0,0),(raw_p,0,0)); dt=2*C.SPECIES_MASS['Ar40']
    assert I.capture(p.drift_A,pos,mom,a,dt)==I.capture(C._drift,pos,mom,a,dt)


def test_A_steps_are_current_FAST_and_do_not_patch_REF():
    p=pilot(); base=I.make_run(dict(e='9',b_frac='0')); new=copy.copy(base)
    old=(C.step,C._drift,C._kick,C.impulse,F.step_fast)
    ex=p.PreparedRuntime(new,'A')
    for _ in range(30):
        F.step_fast(base); ex.step()
        assert I.raw(base)==I.raw(new)
    assert (C.step,C._drift,C._kick,C.impulse,F.step_fast)==old


@pytest.mark.parametrize('width,fpos,fmom',[(8,0,0),(16,4,7),(96,48,80),(192,110,150)])
@pytest.mark.parametrize('dt,mass',[(Q(40),C.AR40_MASS_ME),(Q(7,11),Q(13,17)),(Q(-9,13),Q(1,2**127-1))])
def test_B_unreduced_ratio_exact_cross_product_and_RAW(width,fpos,fmom,dt,mass):
    p=pilot(); assert hasattr(p,'DriftConversionContract'),'raw drift missing'
    pos=FixedPoint(width,fpos); mom=FixedPoint(width,fmom)
    contract=p.DriftConversionContract.build(pos,mom,dt,mass)
    for raw in (0,1,-1,17,-17,mom.hi//32,mom.lo//32):
        num,den=contract.ratio(raw)
        want=mom.to_exact(raw)*dt/mass
        assert num*want.denominator==want.numerator*den
        assert den>0
        try: expected=pos.from_exact(want)
        except VMHalt:
            with pytest.raises(C.ExecutorLimitExceeded): contract.rounded(num,den)
        else: assert contract.rounded(num,den)==expected


@pytest.mark.parametrize('num,den,want',[(5,2,2),(7,2,4),(-5,2,-2),(-7,2,-4),
    (499,200,2),(501,200,3),(-499,200,-2),(-501,200,-3),(1,2,0),(-1,2,0)])
def test_B_rounding_half_even_and_neighbors(num,den,want):
    p=pilot(); assert hasattr(p,'DriftConversionContract'),'raw drift missing'
    pos=mom=FixedPoint(8,0)
    k=p.DriftConversionContract.build(pos,mom,Q(num,den),Q(1))
    assert k.rounded(*k.ratio(1))==want


@pytest.mark.parametrize('change',['dt','pos','mom','species','mass','profile_mutation'])
def test_B_stale_run_contract_is_refused_without_state_change(change,monkeypatch):
    p=pilot(); run=I.make_run(dict(e='9',b_frac='0'))
    # I.make_run uses shared survey profiles; mutate a local clone only.
    run.pos=copy.copy(run.pos);run.mom=copy.copy(run.mom)
    ex=p.PreparedRuntime(run,'B')
    if change=='dt': run.dt=Q(20)
    elif change=='pos': run.pos=FixedPoint(96,47)
    elif change=='mom': run.mom=FixedPoint(96,79)
    elif change=='species': run.atoms=(C.Atom('other',run.atoms[0].r,run.atoms[0].p),run.atoms[1])
    elif change=='mass': monkeypatch.setitem(C.SPECIES_MASS,'Ar40',Q(1))
    else: run.pos.frac_bits=47
    before=dict(vars(run))
    with pytest.raises(C.ContractViolation,match='stale'): ex.step()
    assert vars(run)==before


@pytest.mark.parametrize('raw_r,raw_p',[(0,127),(127,1),(-128,-1)])
def test_B_atom_overflow_message_cause_matches_REF(raw_r,raw_p):
    p=pilot(); pos=FixedPoint(8,0); mom=FixedPoint(16,0)
    a=C.Atom('Ar40',(raw_r,0,0),(raw_p,0,0));dt=2*C.AR40_MASS_ME
    k=p.DriftConversionContract.build(pos,mom,dt,C.AR40_MASS_ME)
    assert I.capture(p.drift_B,k,pos,mom,a,dt)==I.capture(C._drift,pos,mom,a,dt)


def test_B_preserves_exact_segment_near_domain_boundary():
    p=pilot(); pos=FixedPoint(96,48);mom=FixedPoint(96,80)
    # Exact endpoint intentionally differs from rounded endpoint.
    a=C.Atom('Ar40',(0,0,0),(1,0,0));b=C.Atom('Ar40',(pos.from_exact(Q(23,10)),0,0),(-1,0,0))
    dt=Q(40);k=p.DriftConversionContract.build(pos,mom,dt,C.AR40_MASS_ME)
    before=C.relative(pos,a,b)
    old=[C._drift(pos,mom,x,dt) for x in (a,b)]
    new=[p.drift_B(k,pos,mom,x,dt) for x in (a,b)]
    assert new==old
    def guard(xs):
        dr=tuple(y-x-r for x,y,r in zip(xs[0][1],xs[1][1],before))
        stored=C.relative(pos,xs[0][0],xs[1][0])
        return C.segment_min_R2(before,dr),sum(x*x for x in stored)
    assert guard(old)==guard(new)


def test_B_fake_profile_is_not_treated_as_canonical_raw():
    p=pilot()
    class Fake(FixedPoint):
        def to_exact(self,v): return 2*super().to_exact(v)
    run=I.make_run(dict(e='9',b_frac='0'));run.mom=Fake(96,80)
    base=copy.copy(run);ex=p.PreparedRuntime(run,'B')
    assert not ex.raw_drift_enabled
    assert I.capture(ex.step)==I.capture(F.step_fast,base)
    assert I.raw(run)==I.raw(base)


@pytest.mark.parametrize('entry',['ratio','rounded','drift'])
def test_B_component_contract_cannot_bypass_profile_mutation(entry):
    p=pilot();pos=FixedPoint(96,48);mom=FixedPoint(96,80)
    k=p.DriftConversionContract.build(pos,mom,Q(40),C.AR40_MASS_ME)
    mom.frac_bits=79
    with pytest.raises(C.ContractViolation,match='stale'):
        if entry=='ratio': k.ratio(1)
        elif entry=='rounded': k.rounded(1,2)
        else: p.drift_B(k,pos,mom,C.Atom('Ar40',(0,0,0),(1,0,0)),Q(40))


@pytest.mark.parametrize('J',[(0,0,0),(1,-1,7),(-127,127,0),(127,-127,1)])
@pytest.mark.parametrize('ps',[(0,0,0),(126,-127,0),(-128,127,0)])
def test_C_kick_RAW_and_overflow_are_REF(J,ps):
    p=pilot();assert hasattr(p,'kick_C'),'raw kick missing'
    mom=FixedPoint(8,4)
    atoms=(C.Atom('Ar40',(0,0,0),ps),C.Atom('Ar40',(48,0,0),tuple(-v if v!=-128 else 127 for v in ps)))
    assert I.capture(p.kick_C,mom,atoms,J)==I.capture(C._kick,mom,atoms,J)


@pytest.mark.parametrize('mode',['C','Combined'])
@pytest.mark.parametrize('kind',['domain','impulse_overflow','momentum_overflow','position_overflow'])
def test_C_actual_step_refusal_keeps_Run_unchanged(mode,kind):
    p=pilot();run=I.make_run(dict(refusal=kind));base=copy.copy(run);before=dict(vars(run))
    ex=p.PreparedRuntime(run,mode)
    expected=I.capture(F.step_fast,base)
    assert I.capture(ex.step)==expected and expected['kind']!='value'
    assert vars(run)==before and I.raw(run)==I.raw(base)


@pytest.mark.parametrize('bad',[True,Q(1),0.0])
def test_C_step_rejects_invalid_stored_RAW_before_commit(bad):
    p=pilot();run=I.make_run(dict(e='9',b_frac='0'))
    run.atoms=(C.Atom('Ar40',run.atoms[0].r,(bad,0,0)),run.atoms[1]);before=dict(vars(run))
    ex=p.PreparedRuntime(run,'C')
    with pytest.raises(C.ContractViolation): ex.step()
    assert vars(run)==before


def test_C_fake_same_metadata_profile_keeps_original_semantics():
    p=pilot();assert hasattr(p,'kick_C'),'raw kick missing'
    class Fake(FixedPoint):
        def to_exact(self,v): return 2*super().to_exact(v)
    mom=Fake(16,4);atoms=(C.Atom('Ar40',(0,0,0),(1,2,3)),C.Atom('Ar40',(48,0,0),(-1,-2,-3)))
    assert p.kick_C(mom,atoms,(1,1,1))==C._kick(mom,atoms,(1,1,1))


def test_whole_runtime_gate_detects_changed_raw_and_keeps_failed_witness(tmp_path,monkeypatch):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    real=pilot().PreparedRuntime.step
    def faulty(self):
        real(self)
        if self.mode=='Combined':self.run.J_cache=(self.run.J_cache[0]+1,*self.run.J_cache[1:])
    monkeypatch.setattr(pilot().PreparedRuntime,'step',faulty)
    with pytest.raises(AssertionError,match='equivalence'): S.paired(dict(id='fault',e='9',b_frac='0',cap=2),['Combined'],tmp_path/'bad.gz')
    assert (tmp_path/'bad.gz').is_file()


def test_whole_runtime_gate_detects_changed_impulse_before_overflow(tmp_path,monkeypatch):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    actual=F.impulse
    def faulty(dr,dt,profile):
        value=actual(dr,dt,profile)
        return (value[0]+1,*value[1:])
    # Current FAST's first impulse must be recorded even if final states were forged equal.
    monkeypatch.setattr(F,'impulse',faulty)
    with pytest.raises(AssertionError,match='equivalence'): S.paired(dict(id='fault',e='9',b_frac='0',cap=1),['C'],tmp_path/'bad.gz')


def test_evidence_validator_refuses_missing_artifacts(tmp_path):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    assert hasattr(S,'check'),'Pilot2 evidence validator missing'
    assert S.check(tmp_path)['status']!='PASS'


@pytest.mark.parametrize('fault',['missing_rows','numerator','rounded','tie','bits','count'])
def test_component_evidence_validator_catches_arithmetic_payload_faults(fault):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    assert hasattr(S,'validate_component'),'component payload validation missing'
    payload=S.component()
    if fault=='missing_rows':payload['rows']=[]
    elif fault=='numerator':payload['rows'][0]['candidate_ratio'][0]+=1
    elif fault=='rounded':payload['rows'][0]['candidate_rounded']={'kind':'value','raw':999}
    elif fault=='tie':payload['ties'][0]['candidate_raw']+=1
    elif fault=='bits':payload['max_bits'][0]+=1
    else:payload['component_inputs']+=1
    with pytest.raises(AssertionError):S.validate_component(payload)


@pytest.mark.parametrize('fault',['spec','initial','source','steps','result','impulses','guards','state','equal_mode'])
def test_differential_evidence_validator_catches_saved_history_faults(fault,tmp_path):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    import gzip,json,hashlib
    assert hasattr(S,'validate_differential'),'differential validation missing'
    spec=dict(id='overflow',refusal='impulse_overflow',cap=1)
    row=S.paired(spec,['A','B','C','Combined'],tmp_path/'overflow.jsonl.gz')
    inputs=dict(cases=[],refusals=[spec],precision=None)
    with gzip.open(tmp_path/'overflow.jsonl.gz','rb') as f: lines=[json.loads(v) for v in f]
    if fault=='spec':lines[0]['spec']={'id':'overflow'}
    elif fault=='initial':lines[0]['initial']=None
    elif fault=='source':lines[0]['source']={}
    elif fault=='steps':row['steps']=8
    elif fault=='result':row['result']={'kind':'value'}
    elif fault=='impulses':lines[1]['per_mode']['A']['impulses']=[]
    elif fault=='guards':lines[1]['per_mode']['A']['guards']=[{'invented':True}]
    elif fault=='state':lines[1]['per_mode']['A']['state']['step']=999
    else:lines[1]['equal_modes']=['BASE']
    with gzip.open(tmp_path/'overflow.jsonl.gz','wb') as f:
        for v in lines:f.write(S.canonical(v)+b'\n')
    row['witness_sha256']=hashlib.sha256(b''.join(S.canonical(v)+b'\n' for v in lines[1:])).hexdigest()
    with pytest.raises(AssertionError):S.validate_differential(inputs,dict(rows=[row],real_cap=16384),tmp_path,S.sources())


@pytest.mark.parametrize('fault',['step_missing','component_unequal','atom_missing','calls','negative_clock','fake_median'])
def test_benchmark_validator_catches_incomplete_or_unequal_workloads(fault):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    assert hasattr(S,'validate_benchmark'),'benchmark grid validation missing'
    specs=[dict(id='x')]; b=dict(repetitions=3,component_calls=30000,atom_calls=10000,step_calls=1000)
    inputs=dict(cases=specs,benchmark=b)
    samples=[]
    for rep in range(3):
        for mode in S.MODES:
            for work,n in [('drift_component',30000),('drift_atom',10000),('step',1000),('trajectory',1)]:
                r=dict(rep=rep,mode=mode,workload=work,calls=n,cpu_seconds=2.0,wall_seconds=3.0)
                if work in ('drift_component','drift_atom'):r['result']='same'
                else:r['result_sha256']='same'
                if work=='trajectory':r.update(id='x',final_sha256='final')
                samples.append(r)
    payload=dict(samples=samples,medians=S.median_rows(samples,3))
    if fault=='step_missing':samples[:]=[s for s in samples if not(s['mode']=='A' and s['workload']=='step' and s['rep']==0)]
    elif fault=='component_unequal':samples[0]['result']='wrong'
    elif fault=='atom_missing':samples[:]=[s for s in samples if not(s['mode']=='A' and s['workload']=='drift_atom' and s['rep']==0)]
    elif fault=='calls':samples[0]['calls']=0
    elif fault=='negative_clock':samples[0]['cpu_seconds']=-2.0
    else:payload['medians']['step']['A']['cpu_speedup']=999
    if fault!='fake_median':payload['medians']=S.median_rows(samples,3)
    with pytest.raises(AssertionError):S.validate_benchmark(inputs,payload,{'x':dict(steps=1,final_sha256='final')},{})


def test_failed_witness_preserves_real_counterexample(tmp_path,monkeypatch):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    import gzip,json
    real=pilot().PreparedRuntime.step
    def faulty(self):
        real(self)
        if self.mode=='Combined':self.run.J_cache=(self.run.J_cache[0]+1,*self.run.J_cache[1:])
    monkeypatch.setattr(pilot().PreparedRuntime,'step',faulty)
    with pytest.raises(AssertionError,match='equivalence'):S.paired(dict(id='fault',e='9',b_frac='0',cap=2),['Combined'],tmp_path/'bad.gz')
    with gzip.open(tmp_path/'bad.gz','rb') as f:rows=[json.loads(x) for x in f]
    assert len(rows)==2 and rows[1]['per_mode']['Combined']['state']!=rows[1]['per_mode']['BASE']['state']


@pytest.mark.parametrize('fault',['empty_final','count','cpu','top5'])
def test_profile_summary_cannot_replace_actual_pstats(fault,tmp_path):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    import cProfile,pstats
    payload={'rows':{}}
    for mode in S.MODES:
        prof=cProfile.Profile();prof.enable()
        for n in range(100):Q(n,17)*Q(7,19)
        prof.disable();prof.dump_stats(str(tmp_path/(mode+'.pstats')))
        payload['rows'][mode]=dict(measured_cpu=1.0,**S.profile_summary(pstats.Stats(prof)),final=[dict(id='x',steps=1,final_sha256='final')])
    if fault=='empty_final':payload['rows']['A']['final']=[]
    elif fault=='count':payload['rows']['A']['fraction_gcd'][0]['calls']+=1
    elif fault=='cpu':payload['rows']['A']['fraction_gcd'][0]['self_cpu']+=1
    else:payload['rows']['A']['top5']=[]
    with pytest.raises(AssertionError):S.validate_profile({'cases':[{'id':'x'}]},payload,tmp_path,{'x':dict(steps=1,final_sha256='final')})


def test_valid_component_evidence_is_accepted():
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    S.validate_component(S.component())


def test_valid_refusal_witness_is_accepted(tmp_path):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    spec=dict(id='overflow',refusal='impulse_overflow',cap=1)
    row=S.paired(spec,['A','B','C','Combined'],tmp_path/'overflow.jsonl.gz')
    S.validate_differential(dict(cases=[],refusals=[spec],precision=None),dict(rows=[row],real_cap=16384),tmp_path,S.sources())


def _bounded_bigint_fixture(monkeypatch):
    from experiments.verified_superoptimizer_c1b1 import pilot2_stages as S
    batches=[]
    def loop(fn,n):
        batches.append(n)
        return fn()
    monkeypatch.setattr(S,'loop',loop)
    monkeypatch.setattr(S,'timed',lambda fn:(fn(),dict(cpu_seconds=2.0,wall_seconds=3.0)))
    return S,S.bigint({}),batches


def test_bigint_measurement_records_long_batches_and_accepts_valid_data(monkeypatch):
    S,payload,batches=_bounded_bigint_fixture(monkeypatch)
    assert {n for n in batches if n!=1000}=={1000000}
    assert all(c['calls']==1000000 and c['warmup_calls']==1000 for r in payload['rows'] for c in r['costs'].values())
    S.validate_bigint(payload)


@pytest.mark.parametrize('fault',['calls','zero_cpu','median'])
def test_bigint_measurement_rejects_forged_batch_or_unresolved_cpu(fault,monkeypatch):
    S,payload,_=_bounded_bigint_fixture(monkeypatch)
    row=payload['rows'][0]['costs']['integer_multiplication']
    if fault=='calls':row['calls']=100000
    elif fault=='zero_cpu':row['samples'][0]['cpu_seconds']=0.0
    else:row['median_cpu_per_operation']*=10
    with pytest.raises(AssertionError):S.validate_bigint(payload)
