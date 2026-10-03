"""Source-bound production integration campaign; old Pilot 2 evidence is immutable."""
from __future__ import annotations
import argparse, copy, gzip, hashlib, json, math, statistics, subprocess, sys, time, uuid, cProfile, pstats, tracemalloc
from pathlib import Path
from types import FunctionType
from fractions import Fraction as Q
from a_reference import c1b1_runtime as R, c1b1_two_atom as C, c1b1_combined_arithmetic as A
from a_numeric.profiles import FixedPoint, _div_round
from . import evidence as E, integration_stages as I, pilot2_stages as P
from .runtime_activation import make_run as original_run

MODES=('reference','fast','fast_combined')
EXTRA=[dict(id=k,adversarial=k,cap=n) for k,n in (
    ('reverse_momentum',80),('zero_momentum',16),('cached_min_raw',1),
    ('cached_max_raw',1),('invalid_bool',1),('invalid_fraction',1),
    ('exact_segment_boundary',1),('retired_v1',16),('mirror',80))]
STAGES=('component','differential','full','benchmark','profile','bigint')
STRICT_XFAIL=('tests.test_c1b1_two_atom','test_representation_preserving_translation_b64')


def read(path): return json.loads(Path(path).read_bytes())
def write(path,x): P.write(path,x)
def digest(x): return P.digest(x)


def seal(out):
    out.mkdir(parents=True,exist_ok=False)
    old=read(E.HERE/'promotion_inputs.json')
    precision=next(x for x in old['impulses'] if 'precision_target_16384' in x['tags'])
    inputs=dict(cases=P.CASES,diagnostics=[*old['refusals'],dict(precision,id='real_cap_precision_STOP',cap=1),*EXTRA],
                modes=MODES,repetitions=3,warmup_calls=1000,drift_calls=30000,kick_calls=30000,step_calls=1000)
    write(out/'inputs.json',inputs)
    collected=subprocess.check_output([sys.executable,'-m','pytest','tests','--collect-only','-q'],text=True)
    identities=[]
    for line in collected.splitlines():
        if line.startswith('tests/') or line.startswith('tests\\'):
            parts=line.split('::')
            if len(parts)>1:
                module=parts[0].replace('\\','/').removesuffix('.py').replace('/','.')
                identities.append([module+(''.join('.'+x for x in parts[1:-1])),parts[-1]])
    assert len(identities)>=3866 and len({tuple(x) for x in identities})==len(identities)
    source=E.inventory()
    write(out/'manifest.json',dict(schema='c1b1-combined-promotion-v1',run_id=str(uuid.uuid4()),
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source=source,source_hash=digest(source),input_hash=E.sha(out/'inputs.json'),full_identities=identities,outputs={}))


def make_run(spec):
    if 'adversarial' not in spec:return original_run(spec)
    r=I.make_run(dict(e='9',b_frac='0'))
    kind=spec['adversarial']
    if kind=='reverse_momentum':r.atoms=tuple(C.Atom(a.species,a.r,tuple(-v for v in a.p)) for a in r.atoms)
    elif kind=='zero_momentum':r.atoms=tuple(C.Atom(a.species,a.r,(0,0,0)) for a in r.atoms)
    elif kind in ('cached_min_raw','cached_max_raw'):r.J_cache=(r.mom.lo if kind=='cached_min_raw' else r.mom.hi,0,0)
    elif kind in ('invalid_bool','invalid_fraction'):
        a=r.atoms[0];r.atoms=(C.Atom(a.species,a.r,(True if kind=='invalid_bool' else Q(1,2),0,0)),r.atoms[1])
    elif kind=='retired_v1':r.drift='v1'
    elif kind=='mirror':r.atoms=tuple(C.Atom(a.species,tuple(-v for v in a.r),tuple(-v for v in a.p)) for a in r.atoms)
    elif kind=='exact_segment_boundary':
        # R=3: exact relative endpoint 2.1 enters r_min; rounded displacement is zero.
        pos=FixedPoint(96,0);mom=FixedPoint(96,80);z=(Q(0),)*3
        r=C.new_run(pos,C.AR40_MASS_ME*Q(9,20),z,(Q(1),Q(0),Q(0)),
                    (Q(3),Q(0),Q(0)),(Q(-1),Q(0),Q(0)),momentum_profile=mom,validated_only=False)
        r.J_cache=(0,0,0)
    else:raise ValueError(kind)
    return r


def plain(x):
    if isinstance(x,C.Atom):return plain(dict(species=x.species,r=x.r,p=x.p))
    if isinstance(x,Q):return str(x)
    if isinstance(x,(tuple,list)):return [plain(v) for v in x]
    if isinstance(x,dict):return {k:plain(v) for k,v in x.items()}
    return x


def instrument(ex,events):
    """Wrap the real bound production namespace; no module/global/profile edits."""
    ns=dict(ex.function.__globals__)
    for name in ('impulse','_kick','_drift','segment_min_R2'):
        actual=ns[name]
        def wrapper(*args,_fn=actual,_name=name,**kwargs):
            try:value=_fn(*args,**kwargs)
            except (C.ExecutorLimitExceeded,C.PhysicsDomainExceeded,C.ContractViolation,C.IntegratorDomainExceeded,C.VMHalt) as exc:
                result=dict(kind='halt' if isinstance(exc,C.VMHalt) else 'refusal',type=type(exc).__name__,reason=exc.reason,message=str(exc))
                record=event(_name,args,kwargs,result);events.append(record);raise
            events.append(event(_name,args,kwargs,dict(kind='value',raw=value)))
            return value
        ns[name]=wrapper
    ex.function=FunctionType(C.step.__code__,ns,'observed_production_step')


def event(name,args,kwargs,result):
    row=dict(function=name,result=plain(result))
    if name=='impulse':row.update(dr=plain(args[0]),dt=str(args[1]))
    elif name=='_kick':row.update(atoms=plain(args[1]),J=plain(args[2]))
    elif name=='_drift':
        atom=args[2];row.update(atom=plain(atom),dt=str(args[3]),rule=kwargs.get('rule','v2'))
        if result['kind']=='value':
            moved,endpoint=result['raw']
            row['displacement_raw']=[y-x for x,y in zip(atom.r,moved.r)]
            row['exact_endpoint']=plain(endpoint)
    else:row.update(start=plain(args[0]),delta=plain(args[1]))
    return row


def paired(spec,out):
    original=make_run(spec);runs={m:copy.copy(original) for m in MODES}
    executors={m:R.bind(r,mode=m) for m,r in runs.items()}
    events={m:[] for m in MODES}
    for m,ex in executors.items():instrument(ex,events[m])
    h=hashlib.sha256();counts=dict(impulse=0,drift=0,kick=0,guard=0)
    with gzip.open(out,'wb') as stream:
        stream.write(P.canonical(dict(spec=spec,initial=plain(I.raw(original))))+b'\n')
        for attempt in range(1,spec['cap']+1):
            before={m:dict(vars(r)) for m,r in runs.items()}
            for xs in events.values():xs.clear()
            observations={m:dict(state=None,result=I.capture(ex.step),events=events[m]) for m,ex in executors.items()}
            for m in MODES:observations[m]['state']=plain(I.raw(runs[m]))
            encoded=P.canonical(dict(attempt=attempt,per_mode=observations))+b'\n'
            stream.write(encoded);h.update(encoded)  # failure evidence precedes assertion
            validate_observations(spec,observations,original,verify_impulse=False)
            v=before['reference']
            validate_transition(original,plain(dict(step=v['t_steps'],atoms=v['atoms'],J_cache=v['J_cache'])),observations['reference'])
            expected=observations['reference']
            for ev in expected['events']:counts[{'impulse':'impulse','_drift':'drift','_kick':'kick','segment_min_R2':'guard'}[ev['function']]]+=1
            if expected['result']['kind']!='value':
                assert all(vars(r)==before[m] for m,r in runs.items()),'refusal mutated Run'
                end=expected['result']['type'];break
            if I.outgoing(runs['reference']):end='outgoing_R20';break
        else:end='step_cap'
        if spec in P.CASES:assert end=='outgoing_R20'
    return dict(id=spec['id'],steps=runs['reference'].t_steps,attempts=attempt,end=end,
                result=expected['result'],final_sha256=digest(expected['state']),witness_sha256=h.hexdigest(),counts=counts)


def validate_observations(spec,obs,run=None,verify_impulse=True):
    assert set(obs)==set(MODES),'missing production mode'
    assert all(x==obs['reference'] for x in obs.values()),'production modes differ'
    if run is None:run=make_run(spec)  # original profiles/coefficient oracle
    for ev in obs['reference']['events']:
        if ev['function']=='impulse' and verify_impulse:
            assert plain(I.capture(C.impulse,tuple(map(Q,ev['dr'])),Q(ev['dt']),run.mom))==ev['result'],'original REF impulse mismatch'
        elif ev['function']=='_drift':
            x=ev['atom'];a=C.Atom(x['species'],tuple(x['r']),tuple(x['p']))
            expected=I.capture(C._drift,run.pos,run.mom,a,Q(ev['dt']),ev['rule'])
            assert plain(expected)==ev['result'],'original Fraction drift mismatch'
            if expected['kind']=='value':
                moved,endpoint=expected['raw']
                assert ev['displacement_raw']==[y-x for x,y in zip(a.r,moved.r)]
                assert ev['exact_endpoint']==plain(endpoint)
                if ev['rule']=='v2':assert ev['displacement_raw']==list(C.displacement(run.pos,run.mom,a,Q(ev['dt'])))
        elif ev['function']=='_kick':
            atoms=tuple(C.Atom(x['species'],tuple(x['r']),tuple(x['p'])) for x in ev['atoms'])
            assert plain(I.capture(C._kick,run.mom,atoms,tuple(ev['J'])))==ev['result']
        elif ev['function']=='segment_min_R2':
            assert plain(C.segment_min_R2(tuple(map(Q,ev['start'])),tuple(map(Q,ev['delta']))))==ev['result']['raw']


def validate_transition(run,previous,observation):
    """Check event ordering and def-use continuity separately from per-mode equality."""
    events=iter(observation['events']);used=0
    def take(name):
        nonlocal used
        ev=next(events);used+=1
        assert ev['function']==name,'event order'
        return ev
    def terminal(result):
        assert observation['result']==result
        assert observation['state']==previous and used==len(observation['events'])
    def atoms(raws):return tuple(C.Atom(x['species'],tuple(x['r']),tuple(x['p'])) for x in raws)
    def impulse(at):
        ev=take('impulse')
        assert ev['dr']==plain(C.relative(run.pos,*atoms(at))) and Q(ev['dt'])==run.dt/2
        return ev['result']
    current=previous['atoms'];j=previous['J_cache']
    stored=[(run.pos,x['r']) for x in current]+[(run.mom,x['p']) for x in current]
    if j is not None:stored.append((run.mom,j))
    if any(not all(profile.valid_raw(v) for v in raws) for profile,raws in stored):
        assert not observation['events'] and observation['state']==previous
        assert observation['result']['type']=='ContractViolation';return
    if j is None:
        value=impulse(current)
        if value['kind']!='value':terminal(value);return
        j=value['raw']
    ev=take('_kick');assert ev['atoms']==current and ev['J']==j
    if ev['result']['kind']!='value':terminal(ev['result']);return
    current=ev['result']['raw'];start=C.relative(run.pos,*atoms(current));moved=[];endpoints=[]
    for atom in current:
        ev=take('_drift');assert ev['atom']==atom and Q(ev['dt'])==run.dt and ev['rule']==run.drift
        if ev['result']['kind']!='value':terminal(ev['result']);return
        moved.append(ev['result']['raw'][0]);endpoints.append(tuple(map(Q,ev['exact_endpoint'])))
    delta=tuple(y-x-a for x,y,a in zip(endpoints[0],endpoints[1],start))
    ev=take('segment_min_R2');assert ev['start']==plain(start) and ev['delta']==plain(delta)
    if Q(ev['result']['raw'])<C.R_MIN2 or sum(x*x for x in C.relative(run.pos,*atoms(moved)))<C.R_MIN2:
        assert observation['result']['type']=='PhysicsDomainExceeded' and observation['state']==previous
        assert used==len(observation['events']);return
    value=impulse(moved)
    if value['kind']!='value':terminal(value);return
    ev=take('_kick');assert ev['atoms']==moved and ev['J']==value['raw']
    if ev['result']['kind']!='value':terminal(ev['result']);return
    assert used==len(observation['events']) and observation['result']==dict(kind='value',raw=None)
    assert observation['state']==dict(step=previous['step']+1,atoms=ev['result']['raw'],J_cache=value['raw'])


def differential(inputs,out):
    rows=[]
    for spec in [*inputs['cases'],*inputs['diagnostics']]:
        row=paired(spec,out/(spec['id']+'.jsonl.gz'));rows.append(row)
        print('differential',row['id'],row['steps'],row['end'],flush=True)
    return dict(rows=rows,scope='integration evidence; original endpoint argument retained; cap=16384')


def component():
    checks=0
    for width,fp,fm in ((8,0,0),(16,4,7),(96,48,80),(192,110,150)):
        pos=FixedPoint(width,fp);mom=FixedPoint(width,fm)
        for dt,mass in ((Q(40),C.AR40_MASS_ME),(Q(7,11),Q(13,17)),(Q(-9,13),Q(1,2**127-1))):
            k=A.DriftConversionContract.build(pos,mom,dt,mass)
            for raw in (0,1,-1,mom.lo,mom.lo+1,mom.hi-1,mom.hi):
                n,d=k.ratio(raw);want=mom.to_exact(raw)*dt/mass
                assert n*want.denominator==d*want.numerator
                assert I.capture(k.rounded,n,d)==I.capture(C._limit,pos.from_exact,want)
                checks+=1
        for raw in (0,1,-1,mom.lo,mom.lo+1,mom.hi-1,mom.hi):
            for j in (0,1,-1,mom.lo,mom.hi):
                atoms=tuple(C.Atom('Ar40',(0,0,0),(raw,0,0)) for _ in range(2))
                assert I.capture(A.kick,mom,atoms,(j,0,0))==I.capture(C._kick,mom,atoms,(j,0,0))
                checks+=1
    return dict(checks=checks,status='PASS',oracle='original Fraction path',protected_step_code=A.CombinedRuntime(I.make_run(P.CASES[0])).function.__code__ is C.step.__code__)


def trajectory(run,ex,cap,stored=None):
    final=I.complete_trajectory(run,lambda r:ex.step(),cap,stored=stored)
    return dict(steps=run.t_steps,final=plain(final))


def work_fn(mode,kind,run):
    ns=R.bind(run,mode=mode).function.__globals__
    a=run.atoms[0]
    if kind=='drift':return lambda:ns['_drift'](run.pos,run.mom,a,run.dt,rule=run.drift)
    if kind=='kick':return lambda:ns['_kick'](run.mom,run.atoms,(1,-1,0))
    raise ValueError(kind)


def benchmark(inputs):
    import psutil
    process=psutil.Process();old=process.cpu_affinity();process.cpu_affinity([old[-1]])
    samples=[]
    try:
        for mode in MODES:
            run=make_run(inputs['cases'][0])
            for kind in ('drift','kick'):P.loop(work_fn(mode,kind,run),inputs['warmup_calls'])
            for spec in inputs['cases']:
                run=make_run(spec);P.loop(R.bind(run,mode=mode).step,inputs['warmup_calls'])
        for rep in range(inputs['repetitions']):
            order=MODES[rep%3:]+MODES[:rep%3]
            if rep%2:order=tuple(reversed(order))
            for mode in order:
                base=make_run(inputs['cases'][0])
                for kind in ('drift','kick'):
                    fn=work_fn(mode,kind,base);n=inputs[kind+'_calls']
                    value,clock=P.timed(lambda:P.loop(fn,n))
                    samples.append(dict(rep=rep,mode=mode,workload=kind,calls=n,result=plain(value),**clock))
                run=copy.copy(base);ex=R.bind(run,mode=mode)
                _,clock=P.timed(lambda:P.loop(ex.step,inputs['step_calls']))
                samples.append(dict(rep=rep,mode=mode,workload='step',calls=inputs['step_calls'],result_sha256=digest(plain(I.raw(run))),**clock))
                for spec in inputs['cases']:
                    run=make_run(spec);ex=R.bind(run,mode=mode);states=[]
                    value,clock=P.timed(lambda:trajectory(run,ex,spec['cap'],states))
                    samples.append(dict(rep=rep,mode=mode,workload='trajectory',id=spec['id'],calls=value['steps'],
                        result_sha256=digest(states),final_sha256=digest(value['final']),**clock))
                    print('benchmark',rep,mode,spec['id'],clock['cpu_seconds'],flush=True)
        medians=benchmark_medians(samples,inputs['repetitions'])
        return dict(samples=samples,medians=medians,environment=dict(python=sys.version,physical_cores=psutil.cpu_count(logical=False),
            logical_threads=psutil.cpu_count(),worker_threads=1,affinity=[old[-1]],cpu_model=subprocess.check_output(
                ['powershell','-NoProfile','-Command','(Get-CimInstance Win32_Processor).Name'],text=True).strip()),
            warmup_calls=inputs['warmup_calls'],warmup='drift+kick; 1000 steps each of six inputs per mode',
            repetitions=inputs['repetitions'],timing='setup/admission/binding/hashing outside timer; state retention inside six trajectory timer')
    finally:process.cpu_affinity(old)


def benchmark_medians(samples,reps):
    result={}
    for workload in ('drift','kick','step','trajectory'):
        result[workload]={}
        for mode in MODES:
            rows=[x for x in samples if x['workload']==workload and x['mode']==mode]
            result[workload][mode]={kind:statistics.median(sum(x[kind+'_seconds'] for x in rows if x['rep']==rep) for rep in range(reps)) for kind in ('cpu','wall')}
        for v in result[workload].values():
            v['speedup_vs_REF']=result[workload]['reference']['cpu']/v['cpu']
            v['speedup_vs_B']=result[workload]['fast']['cpu']/v['cpu']
    return result


def profile_summary(stats):
    rows=[]
    for (file,line,fn),v in stats.stats.items():
        rows.append(dict(file=file,line=line,function=fn,calls=v[1],self_cpu=v[2],cumulative_cpu=v[3],
                         cpu_fraction=v[2]/stats.total_tt,per_call_cpu=v[2]/v[1],maximum_total_speedup=1/(1-v[2]/stats.total_tt)))
    selected=[x for x in rows if Path(x['file']).name in ('fractions.py','c1b1_combined_arithmetic.py','c1b1_impulse_primitives.py') or x['function']=='<built-in method math.gcd>']
    return dict(profile_self_cpu=stats.total_tt,top10=sorted(rows,key=lambda x:x['self_cpu'],reverse=True)[:10],selected=selected)


def profile(inputs,out):
    import psutil
    proc=psutil.Process();old=proc.cpu_affinity();proc.cpu_affinity([old[-1]])
    result={}
    try:
        for mode in MODES:
            prof=cProfile.Profile(timer=time.process_time);finals=[]
            for spec in inputs['cases']:
                run=make_run(spec);ex=R.bind(run,mode=mode)
                prof.enable();value=trajectory(run,ex,spec['cap']);prof.disable()
                finals.append(dict(id=spec['id'],steps=value['steps'],final_sha256=digest(value['final'])))
                print('profile',mode,spec['id'],flush=True)
            prof.dump_stats(out/(mode+'.pstats'))
            result[mode]=dict(final=finals,**profile_summary(pstats.Stats(prof)))
    finally:proc.cpu_affinity(old)
    return dict(rows=result,timer='process_time; profiler overhead; self CPU excludes descendants')


def bigint(inputs):
    rows=[];cases=[('production',FixedPoint(96,48),FixedPoint(96,80),Q(40),C.AR40_MASS_ME),
                    ('large_denominator_stress',FixedPoint(192,110),FixedPoint(192,150),Q(7,11),Q(1,2**127-1))]
    for label,pos,mom,dt,mass in cases:
        k=A.DriftConversionContract.build(pos,mom,dt,mass);raw=mom.hi//32;n,d=k.ratio(raw);reduced=Q(n,d)
        fns=dict(integer_multiplication=lambda:raw*k.multiplier,integer_round_division=lambda:_div_round(n<<pos.frac_bits,d),
                 gcd=lambda:math.gcd(n,d),Fraction_ratio=lambda:Q(n,d),
                 original_exact=lambda:mom.to_exact(raw)*dt/mass)
        costs={}
        for name,fn in fns.items():
            P.loop(fn,1000);samples=[]
            for _ in range(3): _,clock=P.timed(lambda:P.loop(fn,1000000));samples.append(clock)
            tracemalloc.start();P.loop(fn,1000);current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            costs[name]=dict(calls=1000000,warmup_calls=1000,samples=samples,median_cpu_per_operation=statistics.median(s['cpu_seconds'] for s in samples)/1000000,
                             traced_current_bytes=current,traced_peak_bytes=peak)
        rows.append(dict(label=label,raw_bits=abs(raw).bit_length(),numerator_bits=abs(n).bit_length(),denominator_bits=d.bit_length(),
            width=pos.width,fpos=pos.frac_bits,fmom=mom.frac_bits,dt=str(dt),mass=str(mass),raw=raw,
            scaled_numerator_bits=abs(n<<pos.frac_bits).bit_length(),reduced_numerator_bits=abs(reduced.numerator).bit_length(),
            reduced_denominator_bits=reduced.denominator.bit_length(),unreduced_integer_storage_bytes=sys.getsizeof(n)+sys.getsizeof(d),
            reduced_integer_storage_bytes=sys.getsizeof(reduced.numerator)+sys.getsizeof(reduced.denominator),costs=costs))
    return dict(rows=rows,allocation_scope='traced peak live memory for 1000 repeated calls; not cumulative allocation count',
                bigint_scope='fixed run-local denominator each packet; no cross-step rational chain')


def execute(stage,out):
    m=read(out/'manifest.json');inputs=read(out/'inputs.json')
    assert digest(E.inventory())==m['source_hash'],'source changed since seal'
    assert E.sha(out/'inputs.json')==m['input_hash'],'input changed since seal'
    assert stage not in m['outputs'],'stage already executed'
    if stage=='full':raise ValueError('FULL is run externally; use attach-full')
    payload={'component':component,'differential':lambda:differential(inputs,out),
             'benchmark':lambda:benchmark(inputs),'profile':lambda:profile(inputs,out),'bigint':lambda:bigint(inputs)}[stage]()
    write(out/(stage+'.json'),dict(run_id=m['run_id'],source_hash=m['source_hash'],input_hash=m['input_hash'],payload=payload))
    paths=[out/(stage+'.json')]
    if stage=='differential':paths+=list(out.glob('*.jsonl.gz'))
    if stage=='profile':paths+=list(out.glob('*.pstats'))
    m['outputs'][stage]={p.name:E.sha(p) for p in paths}
    (out/'manifest.json').write_bytes(P.canonical(m)+b'\n')


def attach_full(out):
    m=read(out/'manifest.json');assert digest(E.inventory())==m['source_hash']
    payload=validate_full(out,m)
    write(out/'full.json',dict(run_id=m['run_id'],source_hash=m['source_hash'],input_hash=m['input_hash'],payload=payload))
    m['outputs']['full']={n:E.sha(out/n) for n in ('full.json','full.xml','full.log','full_execution.json')}
    (out/'manifest.json').write_bytes(P.canonical(m)+b'\n')


def validate_full(out,m):
    import xml.etree.ElementTree as ET
    counts=dict(PASS=0,FAIL=0,ERROR=0,XFAIL=0,SKIP=0);identities=[];xfails=[]
    for case in ET.parse(out/'full.xml').iter('testcase'):
        identity=[case.get('classname'),case.get('name')];identities.append(identity)
        key='FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'XFAIL' if case.find('skipped') is not None and case.find('skipped').get('type')=='pytest.xfail' else 'SKIP' if case.find('skipped') is not None else 'PASS'
        counts[key]+=1
        if key=='XFAIL':xfails.append(tuple(identity))
    assert sorted(identities)==sorted(m['full_identities']),'FULL item inventory differs'
    assert xfails==[STRICT_XFAIL] and counts['PASS']>=3865
    clock=read(out/'full_execution.json')
    assert clock['exit_code']==0 and counts['FAIL']==counts['ERROR']==counts['SKIP']==0
    assert clock['wall_seconds']>0
    return dict(counts=counts,**clock)


def check(out):
    m=read(out/'manifest.json');inputs=read(out/'inputs.json')
    current=E.inventory()
    assert m['source']==current and digest(m['source'])==m['source_hash']
    assert E.sha(out/'inputs.json')==m['input_hash']
    assert set(m['outputs'])==set(STAGES)
    old=read(E.HERE/'promotion_inputs.json')
    precision=next(x for x in old['impulses'] if 'precision_target_16384' in x['tags'])
    assert inputs==dict(cases=P.CASES,diagnostics=[*old['refusals'],dict(precision,id='real_cap_precision_STOP',cap=1),*EXTRA],
        modes=list(MODES),repetitions=3,warmup_calls=1000,drift_calls=30000,kick_calls=30000,step_calls=1000)
    required={s:{s+'.json'} for s in STAGES}
    required['differential'].update(s['id']+'.jsonl.gz' for s in [*inputs['cases'],*inputs['diagnostics']])
    required['profile'].update(mode+'.pstats' for mode in MODES)
    required['full'].update(('full.xml','full.log','full_execution.json'))
    assert all(set(files)==required[s] for s,files in m['outputs'].items()),'incomplete artifact inventory'
    for files in m['outputs'].values():
        for name,sha in files.items():assert E.sha(out/name)==sha
    payloads={s:read(out/(s+'.json')) for s in STAGES}
    for x in payloads.values():assert all(x[k]==m[k] for k in ('run_id','source_hash','input_hash'))
    assert payloads['component']['payload']==component()
    assert payloads['full']['payload']==validate_full(out,m)
    specs=[*inputs['cases'],*inputs['diagnostics']];finals={};snapshots={};bits={}
    summaries=payloads['differential']['payload']['rows']
    assert [x['id'] for x in summaries]==[x['id'] for x in specs],'differential case inventory'
    for spec,summary in zip(specs,summaries):
        h=hashlib.sha256();run=make_run(spec);previous=plain(I.raw(run));attempt=0
        counts=dict(impulse=0,drift=0,kick=0,guard=0)
        with gzip.open(out/(spec['id']+'.jsonl.gz'),'rb') as stream:
            header=next(stream);first=json.loads(header)
            assert first==dict(spec=spec,initial=previous)
            for encoded in stream:
                h.update(encoded);row=json.loads(encoded);attempt+=1;assert row['attempt']==attempt
                validate_observations(spec,row['per_mode'],run)
                o=row['per_mode']['reference'];state=o['state']
                validate_transition(run,previous,o)
                for ev in o['events']:counts[{'impulse':'impulse','_drift':'drift','_kick':'kick','segment_min_R2':'guard'}[ev['function']]]+=1
                terminal=o['result']['kind']!='value'
                run.atoms=tuple(C.Atom(x['species'],tuple(x['r']),tuple(x['p'])) for x in state['atoms'])
                ended=I.outgoing(run) if not terminal else False
                assert not (attempt<summary['attempts'] and (terminal or ended)),'continued after terminal'
                previous=state
                if attempt==inputs['step_calls']:snapshots[spec['id']]=digest(state)
                for ev in o['events']:
                    if ev['function']=='_drift':
                        den=(1<<run.mom.frac_bits)*Q(ev['dt']).denominator*C.SPECIES_MASS[ev['atom']['species']].numerator
                        for raw in ev['atom']['p']:
                            n=raw*Q(ev['dt']).numerator*C.SPECIES_MASS[ev['atom']['species']].denominator
                            b=bits.setdefault(spec['id'],dict(max_numerator_bits=0,max_denominator_bits=0,max_scaled_bits=0,components=0))
                            b['max_numerator_bits']=max(b['max_numerator_bits'],abs(n).bit_length());b['max_denominator_bits']=max(b['max_denominator_bits'],den.bit_length())
                            b['max_scaled_bits']=max(b['max_scaled_bits'],abs(n<<run.pos.frac_bits).bit_length());b['components']+=1
        assert summary['id']==spec['id'] and attempt==summary['attempts'] and h.hexdigest()==summary['witness_sha256']
        assert digest(previous)==summary['final_sha256'] and previous['step']==summary['steps'] and summary['counts']==counts
        assert summary['result']==o['result'] and 0<attempt<=spec['cap']
        end=o['result']['type'] if terminal else 'outgoing_R20' if ended else 'step_cap'
        assert summary['end']==end
        if spec in inputs['cases']:assert end=='outgoing_R20'
        elif spec.get('refusal') or spec['id'] in ('real_cap_precision_STOP','cached_min_raw','invalid_bool','invalid_fraction','exact_segment_boundary'):
            assert terminal and attempt==1 and previous['step']==0
        if spec['id']=='real_cap_precision_STOP':assert end=='ReferenceUndecided' and C.MAX_PRECISION_BITS==16384
        if end=='step_cap':assert attempt==spec['cap']
        finals[spec['id']]=summary['final_sha256']
    b=payloads['benchmark']['payload'];samples=b['samples'];expected=inputs['repetitions']*len(MODES)*(3+len(inputs['cases']))
    assert len(samples)==expected and len({(x['rep'],x['mode'],x['workload'],x.get('id')) for x in samples})==expected
    keys={(rep,mode,work,None) for rep in range(inputs['repetitions']) for mode in MODES for work in ('drift','kick','step')}
    keys.update((rep,mode,'trajectory',s['id']) for rep in range(inputs['repetitions']) for mode in MODES for s in inputs['cases'])
    assert {(x['rep'],x['mode'],x['workload'],x.get('id')) for x in samples}==keys
    for x in samples:
        assert x['mode'] in MODES and 0<=x['rep']<inputs['repetitions']
        assert all(type(x[k]) in (int,float) and math.isfinite(x[k]) and x[k]>0 for k in ('cpu_seconds','wall_seconds'))
        calls=next(s['steps'] for s in summaries if s['id']==x['id']) if x['workload']=='trajectory' else inputs[x['workload']+'_calls']
        assert x['calls']==calls
        if x['workload']=='trajectory':assert x['final_sha256']==finals[x['id']]
        elif x['workload']=='step':assert x['result_sha256']==snapshots[inputs['cases'][0]['id']]
    for work in ('drift','kick','step','trajectory'):
        for ident in ([s['id'] for s in inputs['cases']] if work=='trajectory' else [None]):
            rows=[x for x in samples if x['workload']==work and x.get('id')==ident]
            key='result' if work in ('drift','kick') else 'result_sha256'
            assert all(x[key]==rows[0][key] for x in rows),'benchmark output mismatch'
    assert b['medians']==benchmark_medians(samples,inputs['repetitions'])
    assert b['medians']['trajectory']['fast_combined']['cpu']<b['medians']['trajectory']['fast']['cpu'],'no measured CPU reduction'
    assert set(payloads['profile']['payload']['rows'])==set(MODES)
    for mode,row in payloads['profile']['payload']['rows'].items():
        assert {x['id']:x['final_sha256'] for x in row['final']}=={s['id']:finals[s['id']] for s in inputs['cases']}
        expected=profile_summary(pstats.Stats(str(out/(mode+'.pstats'))))
        assert all(row[k]==v for k,v in expected.items())
    P.validate_bigint(payloads['bigint']['payload'])
    return dict(status='PASS',run_id=m['run_id'],source_hash=m['source_hash'],input_hash=m['input_hash'],
                trajectory_steps=sum(x['steps'] for x in payloads['differential']['payload']['rows'][:6]),actual_bigint=bits)


def configure_text_limit():
    # Trusted sealed synthetic cap stress exceeds Python's text conversion limit.
    # This affects input serialization only; the arithmetic precision cap is unchanged.
    sys.set_int_max_str_digits(0)


def main():
    configure_text_limit()
    parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.stage=='seal':seal(args.out)
    elif args.stage=='attach-full':attach_full(args.out)
    elif args.stage=='check':
        result=check(args.out);write(args.out/'check.json',result);print(json.dumps(result),flush=True)
    else:execute(args.stage,args.out)


if __name__=='__main__':main()
