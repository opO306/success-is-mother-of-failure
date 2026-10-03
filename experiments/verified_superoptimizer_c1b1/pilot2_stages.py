"""Measured Pilot2 stages. Artifact directories are append-only, source-bound."""
from __future__ import annotations
import argparse, copy, cProfile, gzip, hashlib, json, platform, pstats, statistics, sys, time, subprocess, uuid, tracemalloc, math
from pathlib import Path
from fractions import Fraction as Q
from . import integration_stages as I
from . import pilot2_arithmetic as P, evidence as E
from types import FunctionType
from a_numeric.profiles import FixedPoint, _div_round
from a_reference import c1b1_two_atom as C, c1b1_fast_impulse as F

ROOT=Path(__file__).resolve().parents[2]
CASES=[dict(id=i,e=e,b_frac=b,cap=100000) for i,e,b in (
    ('head_on','9','0'),('oblique','1/2','1'),('weak','1/100','2'),
    ('extra_head_on','1/2','0'),('extra_high_oblique','5','3/2'),('extra_low_oblique','1/10','3/2'))]
MODES=('BASE','A','B','C','Combined')
BIGINT_BENCHMARK_CALLS=1000000  # Shorter CPU batches can be zero on Windows process_time.


def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()


def digest(x): return hashlib.sha256(canonical(x)).hexdigest()


def write(path,x):
    path=Path(path)
    if path.exists(): raise FileExistsError(path)
    path.write_bytes(canonical(x)+b'\n')


def sources():
    files=['a_reference/c1b1_two_atom.py','a_reference/c1b1_runtime.py',
           'a_reference/c1b1_fast_impulse.py','a_numeric/profiles.py',
           'experiments/verified_superoptimizer_c1b1/pilot2_arithmetic.py',
           'experiments/verified_superoptimizer_c1b1/pilot2_stages.py']
    return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}


def timed(fn):
    cpu=time.process_time_ns(); wall=time.perf_counter_ns(); result=fn()
    return result,dict(cpu_seconds=(time.process_time_ns()-cpu)/1e9,wall_seconds=(time.perf_counter_ns()-wall)/1e9)


def paired(spec,modes,out):
    from .runtime_activation import make_run
    base=make_run(spec); runs={m:copy.copy(base) for m in modes}
    calls={m:[] for m in ['BASE','REF',*modes]};guards={m:[] for m in calls}
    def instrument(ns,mode):
        ns=dict(ns);actual=F.impulse if mode!='REF' else C.impulse
        def impulse(dr,dt,profile):
            try: raw=actual(dr,dt,profile)
            except (C.ExecutorLimitExceeded,C.PhysicsDomainExceeded,C.ContractViolation,C.IntegratorDomainExceeded,C.VMHalt) as exc:
                result=dict(kind='halt' if isinstance(exc,C.VMHalt) else 'refusal',type=type(exc).__name__,reason=exc.reason,message=str(exc))
                calls[mode].append(dict(dr=list(map(str,dr)),dt=str(dt),result=result));raise
            result=dict(kind='value',raw=raw)
            calls[mode].append(dict(dr=list(map(str,dr)),dt=str(dt),result=result))
            return raw
        def guard(a,d):
            v=C.segment_min_R2(a,d)
            guards[mode].append(dict(a=list(map(str,a)),d=list(map(str,d)),minimum=str(v)))
            return v
        ns.update(impulse=impulse,segment_min_R2=guard)
        return ns
    executors={m:P.PreparedRuntime(r,m) for m,r in runs.items()}
    for m,ex in executors.items(): ex.function=FunctionType(C.step.__code__,instrument(ex.function.__globals__,m))
    functions={m:ex.step for m,ex in executors.items()}
    bs=FunctionType(C.step.__code__,instrument(F.step_fast.__globals__,'BASE'))
    rs=FunctionType(C.step.__code__,instrument(C.step.__globals__,'REF'))
    h=hashlib.sha256(); ref=copy.copy(base)
    with gzip.open(out,'wb') as stream:
        stream.write(canonical(dict(spec=spec,initial=I.raw(base),source=sources()))+b'\n')
        for attempt in range(1,spec['cap']+1):
            for xs in (*calls.values(),*guards.values()): xs.clear()
            before=I.raw(base)
            before_vars={m:dict(vars(r)) for m,r in dict(BASE=base,REF=ref,**runs).items()}
            expected=I.capture(bs,base)
            values={m:I.capture(fn) for m,fn in functions.items()}
            rr=I.capture(rs,ref)
            observations={m:dict(state=I.raw(r),result=(expected if m=='BASE' else rr if m=='REF' else values[m]),
                impulses=list(calls[m]),guards=list(guards[m])) for m,r in dict(BASE=base,REF=ref,**runs).items()}
            row=canonical(dict(attempt=attempt,result=expected,state=I.raw(base),equal_modes=['REF','BASE',*modes],
                impulses=calls['BASE'],guards=guards['BASE'],per_mode=observations))+b'\n'
            # Preserve actual failing observations before asserting; no erased counterexample.
            stream.write(row);h.update(row)
            assert all(v==expected and I.raw(runs[m])==I.raw(base) for m,v in values.items()),'state/result equivalence'
            assert rr==expected and I.raw(ref)==I.raw(base),'REF equivalence'
            assert all(v==calls['BASE'] for v in calls.values()),'impulse equivalence'
            assert all(v==guards['BASE'] for v in guards.values()),'guard equivalence'
            if expected['kind']!='value':
                assert I.raw(base)==before,'refusal mutated state'
                assert all(vars(r)==before_vars[m] for m,r in dict(BASE=base,REF=ref,**runs).items()),'refusal mutated metadata'
            if expected['kind']!='value' or I.outgoing(base): break
        else: raise AssertionError('trajectory step cap')
    return dict(id=spec['id'],steps=base.t_steps,attempts=attempt,result=expected,final_sha256=digest(I.raw(base)),witness_sha256=h.hexdigest())


def seal(out):
    out=Path(out);out.mkdir(exist_ok=False)
    original=json.loads((E.HERE/'promotion_inputs.json').read_bytes())
    precision=next(r for r in original['impulses'] if 'precision_target_16384' in r['tags'])
    inputs=dict(cases=CASES,refusals=original['refusals'],precision=dict(precision,id='real_cap_precision_STOP',cap=1),
                modes=list(MODES),benchmark=dict(repetitions=3,warmup=1,component_calls=30000,atom_calls=10000,step_calls=1000))
    write(out/'inputs.json',inputs)
    inventory=E.inventory()
    write(out/'manifest.json',dict(schema='c1b1-pilot2-v1',run_id=str(uuid.uuid4()),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source=inventory,source_hash=digest(inventory),input_hash=E.sha(out/'inputs.json'),stages=[]))


def component():
    count=0;ratio_bits=[];rows=[];tie_rows=[]
    for w,fp,fm in [(8,0,0),(16,4,7),(96,48,80),(192,110,150)]:
        pos,mom=FixedPoint(w,fp),FixedPoint(w,fm)
        for mass in [C.AR40_MASS_ME,Q(13,17),Q(1,2**127-1)]:
            for dt in [Q(0),Q(40),Q(7,11),Q(-9,13)]:
                k=P.DriftConversionContract.build(pos,mom,dt,mass)
                for raw in [0,1,-1,17,-17,mom.hi//32,mom.lo//32]:
                    n,d=k.ratio(raw); exact=mom.to_exact(raw)*dt/mass
                    assert n*exact.denominator==exact.numerator*d
                    a=I.capture(pos.from_exact,exact);b=I.capture(k.rounded,n,d)
                    if a['kind']=='value': assert b==a
                    else: assert a['reason']=='overflow' and b['reason']=='executor_limit_exceeded'
                    rows.append(dict(width=w,fpos=fp,fmom=fm,dt=str(dt),mass=str(mass),raw=raw,
                        candidate_ratio=[n,d],reference_exact=str(exact),reference_rounded=a,candidate_rounded=b))
                    ratio_bits.append((abs(n).bit_length(),d.bit_length(),exact.numerator.bit_length(),exact.denominator.bit_length()))
                    count+=1
    ties=0
    pos=mom=FixedPoint(16,0)
    for q in range(-64,65):
        for eps in [Q(-1,2**20),Q(0),Q(1,2**20)]:
            dt=Q(q)+Q(1,2)+eps;k=P.DriftConversionContract.build(pos,mom,dt,Q(1))
            nr=k.rounded(*k.ratio(1));ref=pos.from_exact(dt)
            assert nr==ref;ties+=1;tie_rows.append(dict(dt=str(dt),reference_raw=ref,candidate_raw=nr))
    return dict(component_inputs=count,half_even_and_neighbors=ties,max_bits=[max(v[i] for v in ratio_bits) for i in range(4)],
                rows=rows,ties=tie_rows,scope='exact algebraic displacement conversion; canonical FX grid, not whole FixedPoint/world coverage')


def differential(inputs,out):
    rows=[]
    for spec in [*inputs['cases'],*inputs['refusals'],inputs['precision']]:
        r=paired(spec,[m for m in MODES if m!='BASE'],out/(spec['id']+'.jsonl.gz'));rows.append(r)
        print('differential',r['id'],r['steps'],r['result']['kind'],flush=True)
    assert C.MAX_PRECISION_BITS==16384
    stop=next(r for r in rows if r['id']=='real_cap_precision_STOP')
    assert stop['steps']==0 and stop['result']['type']=='ReferenceUndecided'
    return dict(rows=rows,real_cap=16384,precision_scope='synthetic huge dt stress diagnostic, not world trajectory')


def component_fn(mode,run):
    raw=run.atoms[0].p[0];k=P.DriftConversionContract.build(run.pos,run.mom,run.dt,C.AR40_MASS_ME)
    if mode in ('BASE','C'):
        def f():
            exact=run.mom.to_exact(raw)*run.dt/C.AR40_MASS_ME
            stored=run.pos.from_exact(run.mom.to_exact(raw)*run.dt/C.AR40_MASS_ME)
            return exact,stored
    elif mode=='A':
        def f():
            exact=run.mom.to_exact(raw)*run.dt/C.AR40_MASS_ME
            return exact,run.pos.from_exact(exact)
    else:
        def f():
            n,d=k.ratio(raw)
            return Q(n,d),k.rounded(n,d)
    return f


def atom_fn(mode,run):
    a=run.atoms[0]
    if mode in ('BASE','C'): return lambda:C._drift(run.pos,run.mom,a,run.dt)
    if mode=='A': return lambda:P.drift_A(run.pos,run.mom,a,run.dt)
    k=P.DriftConversionContract.build(run.pos,run.mom,run.dt,C.AR40_MASS_ME)
    return lambda:P.drift_B(k,run.pos,run.mom,a,run.dt)


def loop(fn,n):
    for _ in range(n): last=fn()
    return last


def trajectory(spec,mode,stored=None,run=None,executor=None):
    if run is None: run=I.make_run(spec)
    if executor is None: executor=P.PreparedRuntime(run,mode)
    final=I.complete_trajectory(run,lambda r:executor.step(),spec['cap'],stored=stored)
    return dict(steps=run.t_steps,final=final)


def benchmark(inputs):
    import psutil
    proc=psutil.Process();previous=proc.cpu_affinity();cpu=previous[-1];proc.cpu_affinity([cpu])
    b=inputs['benchmark'];base=I.make_run(inputs['cases'][0]);samples=[]
    try:
        for mode in MODES:
            loop(component_fn(mode,base),1000);loop(atom_fn(mode,base),1000)
            for spec in inputs['cases']:
                r=I.make_run(spec);ex=P.PreparedRuntime(r,mode)
                loop(ex.step,1000)
        for rep in range(b['repetitions']):
            order=MODES[rep%len(MODES):]+MODES[:rep%len(MODES)]
            if rep%2:order=tuple(reversed(order))
            for mode in order:
                for workload,n,fn in [('drift_component',b['component_calls'],component_fn(mode,base)),('drift_atom',b['atom_calls'],atom_fn(mode,base))]:
                    result,clock=timed(lambda:loop(fn,n))
                    samples.append(dict(rep=rep,mode=mode,workload=workload,calls=n,result=str(result),**clock))
                r=copy.copy(base);ex=P.PreparedRuntime(r,mode)
                _,clock=timed(lambda:loop(ex.step,b['step_calls']))
                samples.append(dict(rep=rep,mode=mode,workload='step',calls=b['step_calls'],result_sha256=digest(I.raw(r)),**clock))
                for spec in inputs['cases']:
                    states=[]
                    run=I.make_run(spec);executor=P.PreparedRuntime(run,mode)
                    result,clock=timed(lambda:trajectory(spec,mode,states,run,executor))
                    samples.append(dict(rep=rep,mode=mode,workload='trajectory',id=spec['id'],calls=result['steps'],
                        result_sha256=digest(states),final_sha256=digest(result['final']),**clock))
                    print('benchmark',rep,mode,spec['id'],clock['cpu_seconds'],flush=True)
        medians=median_rows(samples,b['repetitions'])
        return dict(environment=dict(python=sys.version,cpu=platform.processor(),physical_cores=psutil.cpu_count(logical=False),
            logical_threads=psutil.cpu_count(),worker_threads=1,affinity=[cpu]),warmup='1000 component+atom, 1000 steps per each of six inputs per mode',
            repetitions=b['repetitions'],samples=samples,medians=medians,setup_admission_and_hashing='outside timer; same state retention inside trajectory timer')
    finally:proc.cpu_affinity(previous)


def median_rows(samples,reps):
    out={}
    for work in ('drift_component','drift_atom','step','trajectory'):
        out[work]={}
        for mode in MODES:
            rows=[r for r in samples if r['workload']==work and r['mode']==mode]
            out[work][mode]={kind:statistics.median(sum(r[kind+'_seconds'] for r in rows if r['rep']==rep) for rep in range(reps)) for kind in ('cpu','wall')}
        base=out[work]['BASE']['cpu']
        for row in out[work].values():row['cpu_speedup']=base/row['cpu']
    return out


def profile(inputs,out):
    import psutil
    proc=psutil.Process();old=proc.cpu_affinity();proc.cpu_affinity([old[-1]])
    rows={}
    try:
        for mode in MODES:
            prof=cProfile.Profile(timer=time.process_time);finals=[]
            elapsed=0
            for spec in inputs['cases']:
                run=I.make_run(spec);executor=P.PreparedRuntime(run,mode)
                start=time.process_time();prof.enable()
                value=trajectory(spec,mode,run=run,executor=executor)
                prof.disable();elapsed+=time.process_time()-start
                finals.append(dict(id=spec['id'],**value))
                print('profile',mode,spec['id'],flush=True)
            path=out/(mode+'.pstats');prof.dump_stats(path)
            stats=pstats.Stats(prof)
            rows[mode]=dict(measured_cpu=elapsed,**profile_summary(stats),
                final=[dict(id=r['id'],steps=r['steps'],final_sha256=digest(r['final'])) for r in finals])
    finally:proc.cpu_affinity(old)
    return dict(timer='process_time; instrumentation overhead, not benchmark cost',rows=rows)


def profile_summary(stats):
    selected=[]
    for key,v in stats.stats.items():
        if (Path(key[0]).name=='fractions.py' and key[2] in ('__new__','forward','_mul')) or key[2]=='<built-in method math.gcd>':
            selected.append(dict(file=key[0],line=key[1],function=key[2],calls=v[1],self_cpu=v[2],cumulative_cpu=v[3]))
    top=sorted(stats.stats.items(),key=lambda kv:kv[1][2],reverse=True)[:5]
    return dict(profile_self_cpu=stats.total_tt,fraction_gcd=sorted(selected,key=lambda r:(r['file'],r['line'],r['function'])),
                top5=[dict(function=k[2],file=k[0],calls=v[1],self_cpu=v[2]) for k,v in top])


def bigint(inputs):
    rows=[];cases=[('production',FixedPoint(96,48),FixedPoint(96,80),Q(40),C.AR40_MASS_ME),
                    ('large_denominator_stress',FixedPoint(192,110),FixedPoint(192,150),Q(7,11),Q(1,2**127-1))]
    for label,pos,mom,dt,mass in cases:
        k=P.DriftConversionContract.build(pos,mom,dt,mass);raw=mom.hi//32;n,d=k.ratio(raw);reduced=Q(n,d)
        fns=dict(integer_multiplication=lambda:raw*k.multiplier,integer_round_division=lambda:_div_round(n<<pos.frac_bits,d),
                 gcd=lambda:math.gcd(n,d),Fraction_ratio=lambda:Q(n,d),
                 original_exact=lambda:mom.to_exact(raw)*dt/mass)
        costs={}
        for name,fn in fns.items():
            loop(fn,1000);samples=[]
            for _ in range(3): _,clock=timed(lambda:loop(fn,BIGINT_BENCHMARK_CALLS));samples.append(clock)
            tracemalloc.start();loop(fn,1000);current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            costs[name]=dict(calls=BIGINT_BENCHMARK_CALLS,warmup_calls=1000,samples=samples,median_cpu_per_operation=statistics.median(s['cpu_seconds'] for s in samples)/BIGINT_BENCHMARK_CALLS,
                             traced_current_bytes=current,traced_peak_bytes=peak)
        rows.append(dict(label=label,raw_bits=abs(raw).bit_length(),numerator_bits=abs(n).bit_length(),denominator_bits=d.bit_length(),
            width=pos.width,fpos=pos.frac_bits,fmom=mom.frac_bits,dt=str(dt),mass=str(mass),raw=raw,
            scaled_numerator_bits=abs(n<<pos.frac_bits).bit_length(),reduced_numerator_bits=abs(reduced.numerator).bit_length(),
            reduced_denominator_bits=reduced.denominator.bit_length(),unreduced_integer_storage_bytes=sys.getsizeof(n)+sys.getsizeof(d),
            reduced_integer_storage_bytes=sys.getsizeof(reduced.numerator)+sys.getsizeof(reduced.denominator),costs=costs))
    return dict(rows=rows,allocation_scope='traced peak live memory for 1000 repeated calls; not cumulative allocation count',
                bigint_scope='fixed run-local denominator each packet; no cross-step rational chain')


def execute(stage,out):
    out=Path(out);manifest=json.loads((out/'manifest.json').read_bytes());inputs=json.loads((out/'inputs.json').read_bytes())
    assert digest(E.inventory())==manifest['source_hash'],'source changed'
    assert E.sha(out/'inputs.json')==manifest['input_hash']
    assert stage not in manifest['stages'],'stage already executed'
    result={'component':lambda:component(),'differential':lambda:differential(inputs,out),
            'benchmark':lambda:benchmark(inputs),'profile':lambda:profile(inputs,out),'bigint':lambda:bigint(inputs)}[stage]()
    write(out/(stage+'.json'),dict(run_id=manifest['run_id'],source_hash=manifest['source_hash'],input_hash=manifest['input_hash'],payload=result))
    manifest['stages'].append(stage)
    manifest.setdefault('outputs',{})[stage]={p.name:E.sha(p) for p in out.iterdir() if p.is_file() and (p.name==stage+'.json' or (stage=='differential' and p.suffix=='.gz') or (stage=='profile' and p.suffix=='.pstats'))}
    (out/'manifest.json').write_bytes(canonical(manifest)+b'\n')


def validate_component(payload):
    # Judge retained candidate values using original Fraction/FixedPoint arithmetic.
    expected=[]
    for w,fp,fm in [(8,0,0),(16,4,7),(96,48,80),(192,110,150)]:
        for mass in [C.AR40_MASS_ME,Q(13,17),Q(1,2**127-1)]:
            for dt in [Q(0),Q(40),Q(7,11),Q(-9,13)]:
                mom=FixedPoint(w,fm)
                for raw in [0,1,-1,17,-17,mom.hi//32,mom.lo//32]:expected.append((w,fp,fm,str(dt),str(mass),raw))
    rows=payload['rows'];assert len(rows)==payload['component_inputs']==len(expected)==336
    bits=[]
    for row,keys in zip(rows,expected):
        assert tuple(row[k] for k in ('width','fpos','fmom','dt','mass','raw'))==keys
        w,fp,fm,dt,mass,raw=keys;dt,mass=Q(dt),Q(mass)
        pos=FixedPoint(w,fp);want=Q(raw,1<<fm)*dt/mass;n,d=row['candidate_ratio']
        assert type(n) is int and type(d) is int and d>0 and n*want.denominator==d*want.numerator
        assert row['reference_exact']==str(want)
        reference=I.capture(pos.from_exact,want);assert row['reference_rounded']==reference
        if reference['kind']=='value':assert row['candidate_rounded']==reference
        else:assert row['candidate_rounded']==dict(kind='refusal',type='ExecutorLimitExceeded',reason='executor_limit_exceeded',message='overflow in from_exact')
        bits.append([abs(n).bit_length(),d.bit_length(),abs(want.numerator).bit_length(),want.denominator.bit_length()])
    assert payload['max_bits']==[max(b[j] for b in bits) for j in range(4)]
    ties=payload['ties'];assert len(ties)==payload['half_even_and_neighbors']==387
    expected_ties=[Q(q)+Q(1,2)+eps for q in range(-64,65) for eps in [Q(-1,2**20),Q(0),Q(1,2**20)]]
    pos=FixedPoint(16,0)
    for row,dt in zip(ties,expected_ties):assert row['dt']==str(dt) and row['reference_raw']==row['candidate_raw']==pos.from_exact(dt)


def from_state(run,state):
    run.atoms=tuple(C.Atom(a['species'],tuple(a['r']),tuple(a['p'])) for a in state['atoms'])
    run.t_steps=state['step'];run.J_cache=None if state['J_cache'] is None else tuple(state['J_cache'])
    return run


def validate_differential(inputs,payload,out,source):
    from .runtime_activation import make_run
    specs=[*inputs['cases'],*inputs['refusals'],*([inputs['precision']] if inputs.get('precision') else [])]
    rows=payload['rows'];assert len(rows)==len(specs) and payload['real_cap']==C.MAX_PRECISION_BITS==16384
    assert [r['id'] for r in rows]==[s['id'] for s in specs]
    snapshots={};normal={s['id'] for s in inputs['cases']}
    for summary,spec in zip(rows,specs):
        run=make_run(spec);initial=I.raw(run);before=initial;n=0;h=hashlib.sha256();last=None
        path=Path(out)/(spec['id']+'.jsonl.gz')
        with gzip.open(path,'rb') as f:
            header=json.loads(f.readline())
            assert header['spec']==spec and canonical(header['initial'])==canonical(initial) and header['source']==source
            for line in f:
                x=json.loads(line);n+=1
                assert x['attempt']==n and x['equal_modes']==['REF','BASE','A','B','C','Combined']
                modes=x['per_mode'];assert set(modes)=={'REF',*MODES}
                base=modes['BASE'];assert all(v==base for v in modes.values())
                assert x['state']==base['state'] and x['result']==base['result'] and x['impulses']==base['impulses'] and x['guards']==base['guards']
                state,result=base['state'],base['result'];success=result['kind']=='value'
                assert state['step']==n if success else state['step']==n-1
                if not success:assert canonical(state)==canonical(before)
                calls=base['impulses'];guards=base['guards'];assert isinstance(calls,list) and isinstance(guards,list)
                # Initial J must be evaluated unless already cached. Its stored raw then feeds the kick.
                first_needed=before['J_cache'] is None
                if first_needed:
                    assert calls and calls[0]['dt']==str(run.dt/2)
                    old_run=from_state(copy.copy(run),before)
                    assert tuple(map(Q,calls[0]['dr']))==C.relative(run.pos,*old_run.atoms)
                if success:
                    assert len(calls)==1+int(first_needed) and len(guards)==1
                    assert all(c['result']['kind']=='value' for c in calls)
                    assert tuple(calls[-1]['result']['raw'])==tuple(state['J_cache'])
                    end=from_state(copy.copy(run),state)
                    assert tuple(map(Q,calls[-1]['dr']))==C.relative(run.pos,*end.atoms)
                    assert calls[-1]['dt']==str(run.dt/2)
                else:
                    assert calls and len(calls)<=1+int(first_needed) and len(guards)<=1
                for g in guards:
                    assert Q(g['minimum'])==C.segment_min_R2(tuple(map(Q,g['a'])),tuple(map(Q,g['d'])))
                    # Independently rederive drift from original REF helpers and the retained half-kick.
                    old_run=from_state(copy.copy(run),before)
                    old_rel=C.relative(run.pos,*old_run.atoms)
                    J=before['J_cache'] if not first_needed else calls[0]['result']['raw']
                    halves=C._kick(run.mom,old_run.atoms,J)
                    ref_drifts=[C._drift(run.pos,run.mom,a,run.dt,rule=run.drift) for a in halves]
                    d=tuple(y-x-a for x,y,a in zip(ref_drifts[0][1],ref_drifts[1][1],old_rel))
                    assert tuple(map(Q,g['a']))==old_rel and tuple(map(Q,g['d']))==d
                    if success:
                        drift_atoms=tuple(v[0] for v in ref_drifts)
                        ref_final=C._kick(run.mom,drift_atoms,calls[-1]['result']['raw'])
                        assert [dict(species=a.species,r=list(a.r),p=list(a.p)) for a in ref_final]==state['atoms']
                        assert sum(x*x for x in C.relative(run.pos,*drift_atoms))>=C.R_MIN2
                if n==inputs.get('benchmark',{}).get('step_calls',1000):snapshots[spec['id']]=digest(state)
                h.update(line);before=state;last=x
                if not success:assert f.read()==b'';break
        assert last and n==summary['attempts']<=spec['cap']
        assert summary['steps']==last['state']['step'] and summary['result']==last['result']
        assert h.hexdigest()==summary['witness_sha256'] and digest(last['state'])==summary['final_sha256']
        if spec['id'] in normal:
            assert last['result']['kind']=='value' and I.outgoing(from_state(run,last['state']))
        else:assert last['result']['kind']!='value' and summary['steps']==0
        if spec['id']=='real_cap_precision_STOP':assert summary['result']['type']=='ReferenceUndecided' and summary['attempts']==1
    return {r['id']:r for r in rows},snapshots


def validate_benchmark(inputs,payload,finals,snapshots):
    b=inputs['benchmark'];samples=payload['samples'];reps=b['repetitions'];expected=set();seen=set()
    workloads={'drift_component':b['component_calls'],'drift_atom':b['atom_calls'],'step':b['step_calls']}
    for rep in range(reps):
        for mode in MODES:
            expected.update((rep,mode,w,None) for w in workloads)
            expected.update((rep,mode,'trajectory',s['id']) for s in inputs['cases'])
    for row in samples:
        key=(row['rep'],row['mode'],row['workload'],row.get('id'));assert key in expected and key not in seen;seen.add(key)
        assert all(type(row[k+'_seconds']) in (int,float) and math.isfinite(row[k+'_seconds']) and row[k+'_seconds']>0 for k in ('cpu','wall'))
        if row['workload']=='trajectory':
            assert row['calls']==finals[row['id']]['steps'] and row['final_sha256']==finals[row['id']]['final_sha256']
        else:assert row['calls']==workloads[row['workload']]
    assert seen==expected
    for work in ('drift_component','drift_atom','step','trajectory'):
        ids=[s['id'] for s in inputs['cases']] if work=='trajectory' else [None]
        for id_ in ids:
            rows=[r for r in samples if r['workload']==work and r.get('id')==id_]
            field='result' if work.startswith('drift') else 'result_sha256'
            assert len({r[field] for r in rows})==1
            if work=='step' and snapshots:assert rows[0][field]==snapshots[inputs['cases'][0]['id']]
    assert payload['medians']==median_rows(samples,reps)


def validate_profile(inputs,payload,out,finals):
    assert set(payload['rows'])==set(MODES)
    for mode in MODES:
        row=payload['rows'][mode];stats=pstats.Stats(str(Path(out)/(mode+'.pstats')))
        expected=profile_summary(stats)
        assert all(row[k]==v for k,v in expected.items())
        assert math.isfinite(row['measured_cpu']) and row['measured_cpu']>0
        fs=row['final'];assert [r['id'] for r in fs]==[s['id'] for s in inputs['cases']]
        assert all(r['steps']==finals[r['id']]['steps'] and r['final_sha256']==finals[r['id']]['final_sha256'] for r in fs)


def validate_bigint(payload):
    rows=payload['rows'];assert [r['label'] for r in rows]==['production','large_denominator_stress']
    expected=[(96,48,80,Q(40),C.AR40_MASS_ME),(192,110,150,Q(7,11),Q(1,2**127-1))]
    for r,(w,fp,fm,dt,mass) in zip(rows,expected):
        assert (r['width'],r['fpos'],r['fmom'],r['dt'],r['mass'])==(w,fp,fm,str(dt),str(mass))
        raw=((1<<(w-1))-1)//32;assert r['raw']==raw
        n=raw*dt.numerator*mass.denominator;d=(1<<fm)*dt.denominator*mass.numerator;q=Q(n,d)
        values=dict(raw_bits=abs(raw).bit_length(),numerator_bits=abs(n).bit_length(),denominator_bits=d.bit_length(),scaled_numerator_bits=abs(n<<fp).bit_length(),
            reduced_numerator_bits=abs(q.numerator).bit_length(),reduced_denominator_bits=q.denominator.bit_length(),unreduced_integer_storage_bytes=sys.getsizeof(n)+sys.getsizeof(d),
            reduced_integer_storage_bytes=sys.getsizeof(q.numerator)+sys.getsizeof(q.denominator))
        assert all(r[k]==v for k,v in values.items())
        assert set(r['costs'])=={'integer_multiplication','integer_round_division','gcd','Fraction_ratio','original_exact'}
        for c in r['costs'].values():
            assert c['calls']==BIGINT_BENCHMARK_CALLS and c['warmup_calls']==1000
            assert len(c['samples'])==3 and all(math.isfinite(v[k+'_seconds']) and v[k+'_seconds']>0 for v in c['samples'] for k in ('cpu','wall'))
            assert c['median_cpu_per_operation']==statistics.median(v['cpu_seconds'] for v in c['samples'])/BIGINT_BENCHMARK_CALLS
            assert 0<=c['traced_current_bytes']<=c['traced_peak_bytes']


def check(out):
    try:
        out=Path(out);m=json.loads((out/'manifest.json').read_bytes());i=json.loads((out/'inputs.json').read_bytes())
        assert m['schema']=='c1b1-pilot2-v1' and digest(m['source'])==m['source_hash']==digest(E.inventory())
        assert E.sha(out/'inputs.json')==m['input_hash']
        original=json.loads((E.HERE/'promotion_inputs.json').read_bytes())
        precision=next(r for r in original['impulses'] if 'precision_target_16384' in r['tags'])
        assert i['cases']==CASES and i['modes']==list(MODES) and i['refusals']==original['refusals']
        assert i['precision']==dict(precision,id='real_cap_precision_STOP',cap=1)
        assert sorted(m['stages'])==sorted(['component','differential','benchmark','profile','bigint'])
        payloads={}
        for stage in m['stages']:
            assert stage+'.json' in m['outputs'][stage]
            for name,sha in m['outputs'][stage].items():
                p=(out/name).resolve();assert p.parent==out.resolve() and E.sha(p)==sha
            r=json.loads((out/(stage+'.json')).read_bytes())
            assert all(r[k]==m[k] for k in ('run_id','source_hash','input_hash'));payloads[stage]=r['payload']
        validate_component(payloads['component'])
        finals,snapshots=validate_differential(i,payloads['differential'],out,{k:m['source'][k] for k in sources()})
        validate_benchmark(i,payloads['benchmark'],finals,snapshots)
        validate_profile(i,payloads['profile'],out,finals)
        validate_bigint(payloads['bigint'])
        return dict(status='PASS',source_hash=m['source_hash'],input_hash=m['input_hash'])
    except (OSError,KeyError,ValueError,AssertionError,TypeError,EOFError) as exc:
        return dict(status='INCOMPLETE',error=type(exc).__name__+': '+str(exc))


def candidate_gate(out,mode):
    out=Path(out);out.mkdir(exist_ok=False)
    write(out/'binding.json',dict(source=sources(),cases=CASES))
    rows=[]
    for s in CASES:
        row=paired(s,[mode],out/(s['id']+'.jsonl.gz'));rows.append(row)
        print(mode,'trajectory',row['id'],row['steps'],flush=True)
    run=I.make_run(CASES[0]);atom=run.atoms[0]
    samples=[]
    for rep in range(4):
        for method in ('BASE',mode) if rep%2==0 else (mode,'BASE'):
            if method=='BASE': fn=lambda:C._drift(run.pos,run.mom,atom,run.dt)
            elif method=='A': fn=lambda:P.drift_A(run.pos,run.mom,atom,run.dt)
            else:
                k=P.DriftConversionContract.build(run.pos,run.mom,run.dt,C.AR40_MASS_ME)
                fn=lambda:P.drift_B(k,run.pos,run.mom,atom,run.dt)
            result,clock=timed(lambda:[fn() for _ in range(10000)])
            if rep: samples.append(dict(mode=method,rep=rep,result=repr(result[0]),**clock))
    write(out/'result.json',dict(status='PASS',trajectories=rows,samples=samples))


def main():
    # Synthetic cap stress has exact rational integers larger than Python's text limit.
    sys.set_int_max_str_digits(0)
    parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--out',required=True)
    args=parser.parse_args()
    if args.stage in ('A_gate','B_gate'): candidate_gate(args.out,args.stage[0])
    elif args.stage=='seal':seal(args.out)
    elif args.stage=='check':
        result=check(args.out);print(result);sys.exit(0 if result['status']=='PASS' else 1)
    elif args.stage in ('component','differential','benchmark','profile','bigint'):execute(args.stage,args.out)
    else: raise ValueError(args.stage)


if __name__=='__main__': main()
