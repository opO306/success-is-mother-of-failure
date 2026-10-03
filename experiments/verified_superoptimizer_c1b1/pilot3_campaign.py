"""CPU-only Pilot3 evidence; isolated candidates, actual calls, sealed inputs."""
from __future__ import annotations
import argparse,copy,cProfile,gzip,hashlib,json,math,pstats,statistics,subprocess,sys,time,tracemalloc,uuid
from pathlib import Path
from fractions import Fraction as Q
from types import FunctionType,SimpleNamespace
from a_numeric.profiles import FixedPoint,_div_round
from a_reference import c1b1_two_atom as C,c1b1_fast_impulse as F,c1b1_runtime as R,c1b1_pilot3_impulse as X
from . import combined_promotion as P,pilot2_stages as P2,integration_stages as I,evidence as E,checker as CK

MODES=('reference','fast','fast_combined',*X.VARIANTS)
def bind(run,mode):return X.Runtime(run,mode) if mode in X.VARIANTS else R.bind(run,mode=mode)
def write(path,value):E.write(path,value)
def read(path):return json.loads(Path(path).read_bytes())
def plain(value):return P.plain(tuple(value) if type(value) is X.RawRelative else value)

def clone(fn,**overrides):
    result=FunctionType(fn.__code__,dict(fn.__globals__,**overrides),fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=fn.__kwdefaults__
    return result

def traced_impulse(mode,trace,actual=None):
    def model(fn,raw=False,reference=False):
        def call(radius,M,ret):
            value=fn(radius,M,ret)
            dv,inv=value[1:] if reference else value
            rr=radius if raw else F._radius(radius,M)
            trace.append(dict(kind='model',M=M,radius=rr,dV=dv,inverse=inv))
            return value
        return call
    def multiply(fn):
        def call(a,b,M):
            value=fn(a,b,M);trace.append(dict(kind='G',M=M,raw=value));return value
        return call
    def decision(fn,integer=False):
        def call(profile,at):
            def observed(M):
                value=at(M)
                lo,hi=(Q(value[0],value[2]),Q(value[1],value[2])) if integer else value
                trace.append(dict(kind='component',M=M,lo=str(lo),hi=str(hi)))
                return value
            return fn(profile,observed)
        return call
    if mode in ('reference','fast','fast_combined','A','B'):
        fn=actual if actual is not None else C.impulse if mode=='reference' else X.impulse_A if mode=='A' else F.impulse
        ns=fn.__globals__
        return clone(fn,_model=model(ns['_model'],reference=mode=='reference'),
                     _mul=multiply(ns['_mul']),_decide=decision(ns['_decide']))
    rawfn=actual.__globals__.get('impulse_raw',X.impulse_raw) if actual is not None else X.impulse_raw
    ns=rawfn.__globals__
    raw=clone(rawfn,F=SimpleNamespace(**dict(vars(ns['F']),_impulse_model_R_fast=model(ns['F']._impulse_model_R_fast,raw=True))),
              model_prepared=model(ns['model_prepared'],raw=True),_mul=multiply(ns['_mul']),
              decide_raw=decision(ns['decide_raw'],integer=True),
              C=SimpleNamespace(**dict(vars(ns['C']),_decide=decision(ns['C']._decide))))
    if actual is not None:return clone(actual,impulse_raw=raw)
    return lambda dr,dt,profile:raw(dr,dt,profile,prepared=mode=='ABCD',final_integer=mode!='BC')

def instrument(ex,mode,events):
    ns=dict(ex.function.__globals__);trace=[]
    actual_impulse=traced_impulse(mode if getattr(ex,'pilot3_enabled',True) else 'fast',trace,actual=ns['impulse'])
    for name in ('impulse','_kick','_drift','segment_min_R2'):
        fn=actual_impulse if name=='impulse' else ns[name]
        def observed(*args,_name=name,_fn=fn,**kwargs):
            if _name=='impulse':trace.clear()
            try:value=_fn(*args,**kwargs)
            except (C.ExecutorLimitExceeded,C.PhysicsDomainExceeded,C.ContractViolation,C.IntegratorDomainExceeded,C.VMHalt) as exc:
                result=dict(kind='halt' if isinstance(exc,C.VMHalt) else 'refusal',type=type(exc).__name__,reason=exc.reason,message=str(exc))
                row=P.event(_name,tuple(tuple(a) if type(a) is X.RawRelative else a for a in args),kwargs,result)
                if _name=='impulse':row['endpoint_trace']=plain(trace)
                events.append(row);raise
            row=P.event(_name,tuple(tuple(a) if type(a) is X.RawRelative else a for a in args),kwargs,dict(kind='value',raw=value))
            if _name=='impulse':row['endpoint_trace']=plain(trace)
            events.append(row);return value
        ns[name]=observed
    ex.function=clone(ex.function,**ns)

def make_run(spec):
    if spec.get('adversarial')!='three_axis':return P.make_run(spec)
    run=I.make_run(dict(e='2',b_frac='1/2'))
    matrix=((Q(9,25),Q(-12,25),Q(4,5)),(Q(4,5),Q(3,5),Q(0)),(Q(-12,25),Q(16,25),Q(3,5)))
    def rotate(v):return tuple(sum(a*b for a,b in zip(row,v)) for row in matrix)
    rs=[rotate(C.exact(run.pos,a.r)) for a in run.atoms];ps=[rotate(C.exact(run.mom,a.p)) for a in run.atoms]
    return C.new_run(run.pos,run.dt,rs[0],ps[0],rs[1],ps[1],momentum_profile=run.mom,validated_only=False)

def validate(obs,spec,run,previous):
    assert set(obs)==set(MODES),'missing candidate mode'
    assert all(v==obs['reference'] for v in obs.values()),'actual endpoint/event/state disagreement'
    P.validate_observations(spec,{m:obs[m] for m in P.MODES},run,verify_impulse=False)
    P.validate_transition(run,previous,obs['reference'])

def paired(spec,out):
    original=make_run(spec);runs={m:copy.copy(original) for m in MODES};events={m:[] for m in MODES}
    executors={m:bind(r, m) for m,r in runs.items()}
    for m,ex in executors.items():instrument(ex,m,events[m])
    h=hashlib.sha256();counts=dict(impulse=0,drift=0,kick=0,guard=0,models=0,components=0)
    with gzip.open(out,'wb') as stream:
        stream.write(E.canonical(dict(spec=spec,initial=plain(I.raw(original))))+b'\n')
        for attempt in range(1,spec['cap']+1):
            before={m:dict(vars(r)) for m,r in runs.items()}
            for ev in events.values():ev.clear()
            obs={m:dict(result=I.capture(ex.step),state=plain(I.raw(runs[m])),events=events[m]) for m,ex in executors.items()}
            encoded=E.canonical(dict(attempt=attempt,per_mode=obs))+b'\n';stream.write(encoded);h.update(encoded)
            previous=plain(dict(step=before['reference']['t_steps'],atoms=before['reference']['atoms'],J_cache=before['reference']['J_cache']))
            validate(obs,spec,original,previous)
            value=obs['reference']
            for ev in value['events']:
                counts[{'impulse':'impulse','_drift':'drift','_kick':'kick','segment_min_R2':'guard'}[ev['function']]]+=1
                for t in ev.get('endpoint_trace',[]):
                    if t['kind']=='model':counts['models']+=1
                    if t['kind']=='component':counts['components']+=1
            if value['result']['kind']!='value':
                assert all(vars(r)==before[m] for m,r in runs.items()),'failure changed run'
                end=value['result']['type'];break
            if I.outgoing(runs['reference']):end='outgoing_R20';break
        else:end='step_cap'
        if spec in P2.CASES:assert end=='outgoing_R20'
    return dict(id=spec['id'],attempts=attempt,steps=runs['reference'].t_steps,end=end,result=value['result'],
                final_sha256=E.digest(value['state']),witness_sha256=h.hexdigest(),counts=counts)

def fixed(inputs):
    rows=[];outcomes=[]
    for row in inputs['impulses']:
        dr=tuple(Q(v) for v in row['dr']);r2=sum(v*v for v in dr)
        if r2<C.R_MIN2:continue
        dt=Q(row['dt']);dyadic=all(v.denominator&(v.denominator-1)==0 for v in dr)
        shift=max(48,*(v.denominator.bit_length()-1 for v in dr)) if dyadic else None
        packet=X.RawRelative(tuple(int(v*(1<<shift)) for v in dr),shift,dr) if dyadic else None
        tiers=(128,256,512,1024,16384) if 'precision_target_16384' in row['tags'] else (128,256,512,1024)
        for M in tiers:
            radius=F._radius(r2,M);ref=C._model(r2,M,C.L.WORLD_RETARDATION)[1:];old=F._model(r2,M,C.L.WORLD_RETARDATION)
            prepared=X.model_prepared(radius,M,C.L.WORLD_RETARDATION);independent=CK.model(r2,M,C.L.WORLD_RETARDATION)
            assert ref==old==prepared==independent
            if packet:assert X.radius_raw(sum(v*v for v in packet.raw),shift,M)==radius
            G=F._mul(F._neg(ref[0]),ref[1],M)
            components=[]
            for axis,v in enumerate(dr):
                lo,hi=sorted((Q(G[0],1<<M)*v*dt,Q(G[1],1<<M)*v*dt))
                if packet:
                    n,h,d=X.component_interval(G,packet.raw[axis],shift,dt,M)
                    assert Q(n,d)==lo and Q(h,d)==hi
                components.append([str(lo),str(hi)])
            rows.append(dict(id=row['id'],M=M,dyadic=dyadic,radius=radius,dV=ref[0],inverse=ref[1],G=G,components=components))
        # Every canonical FX corpus outcome, including real precision/overflow boundaries.
        for spec in row.get('profiles',[dict(kind='FX',width=96,frac=80)]):
            if spec['kind']!='FX':continue
            profile=FixedPoint(spec['width'],spec['frac'])
            values={m:plain(I.capture(fn,dr,dt,profile)) for m,fn in (('REF',C.impulse),('B',F.impulse),('A',X.impulse_A))}
            if packet:
                for m in ('BC','BCD','ABCD'):
                    values[m]=plain(I.capture(lambda:X.impulse_raw(packet,dt,profile,prepared=m=='ABCD',final_integer=m!='BC')))
            assert all(v==values['REF'] for v in values.values())
            outcomes.append(dict(id=row['id'],profile=spec,dyadic=dyadic,values=values))
    return dict(endpoints=rows,outcomes=outcomes,scope='same-M endpoints; raw paths only exactly dyadic coordinates; no input rounding')

def complete(run,executor,cap,states):
    return I.complete_trajectory(run,lambda ignored_run:executor.step(),cap,stored=states)

def benchmark(inputs,out):
    import psutil
    proc=psutil.Process();old=proc.cpu_affinity();proc.cpu_affinity([old[-1]])
    samples=[];microcalls=inputs['micro_calls'];warm=inputs['warmup_calls']
    stream=(out/'benchmark_samples.jsonl').open('xb')
    def retain(row):
        samples.append(row);stream.write(E.canonical(row)+b'\n');stream.flush()
    try:
        base=make_run(inputs['cases'][0]);dr=C.relative(base.pos,*base.atoms);packet=X.relative_raw(base.pos,*base.atoms)
        r2=sum(v*v for v in dr);n=sum(v*v for v in packet.raw);M=128;dt=base.dt/2
        dv,inv=F._model(r2,M,C.L.WORLD_RETARDATION);g=F._mul(F._neg(dv),inv,M)
        axis=next(i for i,v in enumerate(packet.raw) if v!=0);v=packet.raw[axis]
        def component_ref():
            c=dr[axis]*dt;end=sorted((Q(g[0],1<<M)*c,Q(g[1],1<<M)*c))
            return tuple(base.mom.from_exact(x) for x in end)
        def component_raw():
            a,b,d=X.component_interval(g,v,packet.shift,dt,M)
            return tuple(base.mom._check(_div_round(*X.round_operands(base.mom,x,d))) for x in (a,b))
        def micros(mode):
            raw=mode in ('B','BC','BCD','ABCD')
            imp=C.impulse if mode=='reference' else X.impulse_A if mode=='A' else F.impulse
            if mode in ('BC','BCD','ABCD'):
                impulse=lambda:X.impulse_raw(packet,dt,base.mom,prepared=mode=='ABCD',final_integer=mode!='BC')
            else:impulse=lambda:imp(packet if raw else dr,dt,base.mom)
            return dict(relative=lambda:tuple(X.relative_raw(base.pos,*base.atoms)) if raw else C.relative(base.pos,*base.atoms),
                        radius=lambda:X.radius_raw(n,packet.shift,M) if mode in ('BC','BCD','ABCD') else F._radius(r2,M),
                        component=component_raw if mode in ('BCD','ABCD') else component_ref,impulse=impulse)
        for mode in MODES:
            for fn in micros(mode).values():P2.loop(fn,warm)
            for spec in inputs['cases']:
                run=make_run(spec);ex=bind(run,mode);P2.loop(ex.step,warm)
        for rep in range(inputs['repetitions']):
            order=list(MODES[rep:]+MODES[:rep])
            if rep%2:order.reverse()
            for mode in order:
                for name,fn in micros(mode).items():
                    calls=microcalls[name];value=fn();_,clock=P2.timed(lambda:P2.loop(fn,calls))
                    retain(dict(rep=rep,mode=mode,workload=name,calls=calls,result=plain(value),**clock))
                    assert clock['cpu_seconds']>=0.125,'CPU sample below eight Windows clock ticks; preserved raw sample requires a longer sealed batch'
                run=make_run(inputs['cases'][0]);ex=bind(run,mode)
                _,clock=P2.timed(lambda:P2.loop(ex.step,inputs['step_calls']))
                retain(dict(rep=rep,mode=mode,workload='step',calls=inputs['step_calls'],result=E.digest(plain(I.raw(run))),**clock))
                for spec in inputs['cases']:
                    run=make_run(spec);ex=bind(run,mode);states=[]
                    _,clock=P2.timed(lambda:complete(run,ex,spec['cap'],states))
                    retain(dict(rep=rep,mode=mode,workload='trajectory',id=spec['id'],calls=run.t_steps,
                                        final_sha256=E.digest(plain(I.raw(run))),result=E.digest(states),**clock))
                print('benchmark',rep,mode,flush=True)
        medians={}
        for workload in ('relative','radius','component','impulse','step','trajectory'):
            medians[workload]={}
            for mode in MODES:
                rows=[s for s in samples if s['mode']==mode and s['workload']==workload]
                medians[workload][mode]={k:statistics.median(sum(s[k+'_seconds'] for s in rows if s['rep']==rep)
                                                           for rep in range(inputs['repetitions'])) for k in ('cpu','wall')}
                medians[workload][mode]['speedup_vs_combined']=medians[workload]['fast_combined']['cpu']/medians[workload][mode]['cpu'] if 'fast_combined' in medians[workload] else None
            for mode in MODES:medians[workload][mode]['speedup_vs_combined']=medians[workload]['fast_combined']['cpu']/medians[workload][mode]['cpu']
        for work in ('relative','radius','component','impulse','step','trajectory'):
            for ident in ([s['id'] for s in inputs['cases']] if work=='trajectory' else [None]):
                rows=[s for s in samples if s['workload']==work and s.get('id')==ident]
                assert all(s['result']==rows[0]['result'] for s in rows),'benchmark output differs'
        return dict(samples=samples,medians=medians,environment=dict(python=sys.version,physical_cores=psutil.cpu_count(logical=False),
            logical_threads=psutil.cpu_count(),worker_threads=1,affinity=[old[-1]],cpu_model=subprocess.check_output(
                ['powershell','-NoProfile','-Command','(Get-CimInstance Win32_Processor).Name'],text=True).strip()),
            warmup_calls=warm,repetitions=inputs['repetitions'],micro_calls=microcalls,
            timing='CPU only; setup/bind/hash outside timer; relative includes packet Fraction guard view; radius precomputed R2/N; component precomputed G; trajectory includes R20 stop and state retention')
    finally:stream.close();proc.cpu_affinity(old)

def profile(inputs,out):
    import psutil
    proc=psutil.Process();old=proc.cpu_affinity();proc.cpu_affinity([old[-1]]);result={}
    try:
        for mode in ('fast_combined','fast_pilot3'):
            prof=cProfile.Profile(timer=time.process_time);finals=[]
            for spec,steps in zip(inputs['cases'],inputs['case_steps']):
                run=make_run(spec);ex=bind(run,mode)
                prof.enable();P2.loop(ex.step,steps);prof.disable()
                finals.append(dict(id=spec['id'],steps=steps,final_sha256=E.digest(plain(I.raw(run)))))
                print('profile',mode,spec['id'],flush=True)
            prof.dump_stats(out/(mode+'.pstats'))
            result[mode]=dict(finals=finals,**P.profile_summary(pstats.Stats(prof)))
        assert result['fast_combined']['finals']==result['fast_pilot3']['finals']
        return dict(rows=result,scope='production only, fixed independently verified step counts, no stop observer/hash/admission/bind/storage in profile')
    finally:proc.cpu_affinity(old)

def bigint():
    rows=[]
    for label,width,shift,frac,dt,raw in (
        ('production',96,48,80,Q(20),(3<<48,1<<48,-(1<<48))),
        ('stress',192,150,150,Q(7,11),(3<<150,1,-(5<<150))),
        ('large_dt',192,48,150,Q(1<<120,13),(3<<48,-1,1)),
        ('near_raw_limit',192,48,150,Q(7,11),((1<<191)-1,-(1<<191),1))):
        n=sum(v*v for v in raw);M=256;radius=X.radius_raw(n,shift,M);dv,inv=X.model_prepared(radius,M,C.L.WORLD_RETARDATION);g=F._mul(F._neg(dv),inv,M)
        profile=FixedPoint(width,frac);a,b,d=X.component_interval(g,raw[0],shift,dt,M);rn,rd=X.round_operands(profile,a,d)
        exact=Q(a,d);old_scaled=exact.numerator<<frac
        fns=dict(raw_multiply=lambda:g[0]*raw[0]*dt.numerator,raw_divide=lambda:_div_round(rn,rd),
                 old_Fraction=lambda:Q(g[0],1<<M)*Q(raw[0],1<<shift)*dt,
                 old_divide=lambda:_div_round(old_scaled,exact.denominator))
        costs={}
        for name,fn in fns.items():
            P2.loop(fn,1000);times=[]
            for _ in range(3):_,clock=P2.timed(lambda:P2.loop(fn,200000));times.append(clock)
            tracemalloc.start();P2.loop(fn,1000);current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            costs[name]=dict(calls=200000,median_cpu_per_call=statistics.median(t['cpu_seconds'] for t in times)/200000,
                             samples=times,traced_live_peak_bytes=peak,traced_live_current_bytes=current)
        vals=dict(raw_R2=n,radius_scaled_quotient=n<<(2*(M-shift)) if M>=shift else n>>(2*(shift-M)),
                  component_n=a,component_d=d,round_n=rn,round_d=rd,old_scaled_n=old_scaled,old_d=exact.denominator)
        rows.append(dict(label=label,width=width,shift=shift,momentum_frac=frac,dt=str(dt),
                         bits={k:abs(v).bit_length() for k,v in vals.items()},bytes={k:sys.getsizeof(v) for k,v in vals.items()},costs=costs,
                         raw_operations_per_R2=dict(multiply=3,add=3),raw_operations_per_nonzero_component=dict(multiply=4,divide=2,endpoint_int_products=4),
                         no_cross_step_rational_chain=True))
    return dict(rows=rows,allocation_scope='integer object sizes and tracemalloc peak live bytes; no claim of cumulative allocation count')

def seal(out):
    out.mkdir(parents=True,exist_ok=False);old=read(E.HERE/'promotion_inputs.json')
    precision=next(x for x in old['impulses'] if 'precision_target_16384' in x['tags'])
    inputs=dict(impulses=old['impulses'],cases=P2.CASES,case_steps=[1564,6456,26285,5597,2454,13489],
                diagnostics=[*old['refusals'],dict(precision,id='real_cap_precision_STOP',cap=1),*P.EXTRA,
                             dict(id='three_axis',adversarial='three_axis',cap=20000)],modes=MODES,
                warmup_calls=1000,micro_calls=dict(relative=100000,radius=1000000,component=100000,impulse=5000),step_calls=1000,repetitions=3,
                trace_scope='actual selected impulse and its actual callees preserved; Fraction-path radius reconstructed post-model; raw radius is actual model argument; fixed-M radius checked separately')
    write(out/'inputs.json',inputs);source=E.inventory()
    write(out/'manifest.json',dict(run_id=str(uuid.uuid4()),source=source,source_hash=E.digest(source),
          input_hash=E.sha(out/'inputs.json'),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),outputs={}))

def execute(stage,out):
    manifest=read(out/'manifest.json');inputs=read(out/'inputs.json')
    assert E.inventory()==manifest['source'],'source changed after seal'
    assert E.sha(out/'inputs.json')==manifest['input_hash'];assert stage not in manifest['outputs']
    if stage=='differential':
        payload=[]
        for spec in (*inputs['cases'],*inputs['diagnostics']):
            row=paired(spec,out/(spec['id']+'.jsonl.gz'));payload.append(row);print('differential',row['id'],row['steps'],row['end'],flush=True)
    else:payload={'fixed':lambda:fixed(inputs),'benchmark':lambda:benchmark(inputs,out),'profile':lambda:profile(inputs,out),'bigint':bigint}[stage]()
    write(out/(stage+'.json'),dict(run_id=manifest['run_id'],source_hash=manifest['source_hash'],input_hash=manifest['input_hash'],payload=payload))
    paths=[out/(stage+'.json')]
    if stage=='differential':paths+=list(out.glob('*.jsonl.gz'))
    if stage=='profile':paths+=list(out.glob('*.pstats'))
    if stage=='benchmark':paths.append(out/'benchmark_samples.jsonl')
    latest=read(out/'manifest.json')
    assert all(latest[k]==manifest[k] for k in ('run_id','source_hash','input_hash'))
    assert stage not in latest['outputs']
    latest['outputs'][stage]={p.name:E.sha(p) for p in paths};write(out/'manifest.json',latest)

def main():
    sys.set_int_max_str_digits(0) # trusted cap input serialization only
    parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    if a.stage=='seal':seal(a.out)
    else:execute(a.stage,a.out)
if __name__=='__main__':main()
