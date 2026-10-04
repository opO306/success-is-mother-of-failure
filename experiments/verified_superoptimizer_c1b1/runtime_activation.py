"""Fresh master/runtime integration evidence; never rewrites historical runs.

Endpoint proofs remain in the original closure. These stages exercise the actual
production selector and retain integration evidence, not a new physical proof.
"""
from __future__ import annotations
import argparse
import copy
import cProfile
import gzip
import hashlib
import json
import platform
import pstats
import statistics
import subprocess
import sys
import time
import types
from collections import Counter
from contextlib import contextmanager
from fractions import Fraction as Q
from pathlib import Path
from . import evidence as E, integration_stages as I
from a_reference import c1b1_runtime as R, c1b1_two_atom as C, c1b1_fast_impulse as F
from a_reference import c1b1_stress_survey as X

MASTER_RUN = E.ROOT/'runs/c1b1_candidate_b_master_gate_v1'
FULL_GATES = (*E.CLOSURE, 'audit', 'local_full')
ACTIVATION_STAGES = ('differential', 'benchmark', 'profile')


def read(path):
    return json.loads(Path(path).read_bytes())


def seal(out):
    assert E.check_run(MASTER_RUN, required=FULL_GATES, live=False)['status'] == 'PASS'
    original = read(MASTER_RUN/'manifest.json')
    live = E.inventory()
    changed = [p for p,h in original['source'].items() if live.get(p) != h]
    assert changed == ['tools/c1b1_replay_benchmark.py'], changed
    assert subprocess.check_output(['git','branch','--show-current'],cwd=E.ROOT,text=True).strip() == 'master'
    inputs = read(E.HERE/'promotion_inputs.json')
    inputs['runtime_trajectories'] = [*inputs['trajectories'],
        dict(id='extra_head_on',e='1/2',b_frac='0',cap=100000),
        dict(id='extra_high_oblique',e='5',b_frac='3/2',cap=100000),
        dict(id='extra_low_oblique',e='1/10',b_frac='3/2',cap=100000)]
    inputs['runtime_precision'] = next(r for r in inputs['impulses'] if 'precision_target_16384' in r['tags'])
    seed = out.with_name(out.name+'_inputs.json')
    if seed.exists():
        raise FileExistsError(seed)
    E.write(seed, inputs)
    manifest = E.create_run(out, seed, required=FULL_GATES)
    E.write(out/'activation_manifest.json',dict(schema='c1b1-runtime-activation-v1',
        binding=E.binding(manifest),pre_activation_source_hash=original['source_hash'],
        master_run_id=original['run_id'],master_full_sha256=E.sha(MASTER_RUN/'local_full.json'),
        changed_existing_source=changed,stages=[]))
    return manifest


def make_run(spec):
    if spec.get('id') == 'real_cap_precision_STOP':
        z = (Q(0),)*3
        return R.new_run(X.POS,2*Q(spec['dt']),z,z,tuple(Q(v) for v in spec['dr']),z,
                         momentum_profile=X.MOM,validated_only=False)
    return I.make_run(spec)


def capture(fn, run):
    return I.capture(fn, run)


@contextmanager
def observed_steps():
    """Observe real selected functions in this serial evidence process only."""
    originals = C.step, F.step_fast
    refs, fasts = [], []
    def observed(impulse, calls):
        def call(dr, dt, profile):
            try:
                result = impulse(dr,dt,profile)
            except (C.ExecutorLimitExceeded,C.PhysicsDomainExceeded,C.ContractViolation,C.VMHalt) as exc:
                calls.append(dict(dr=list(map(str,dr)),dt=str(dt),result=dict(
                    kind='halt' if isinstance(exc,C.VMHalt) else 'refusal',
                    type=type(exc).__name__,reason=exc.reason,message=str(exc))))
                raise
            calls.append(dict(dr=list(map(str,dr)),dt=str(dt),result=dict(kind='value',raw=result)))
            return result
        return call
    rs = types.FunctionType(originals[0].__code__,dict(originals[0].__globals__,impulse=observed(C.impulse,refs)))
    fs = types.FunctionType(originals[1].__code__,dict(originals[1].__globals__,impulse=observed(F.impulse,fasts)))
    assert rs.__code__ is fs.__code__ is originals[0].__code__
    try:
        C.step, F.step_fast = rs, fs
        yield refs, fasts
    finally:
        C.step, F.step_fast = originals


def paired(spec, stream):
    ref = make_run(spec)
    fast = copy.copy(ref)
    assert I.raw(ref) == I.raw(fast)
    stream.write(E.canonical(dict(id=spec['id'],initial=I.raw(ref),spec=spec))+b'\n')
    digest = hashlib.sha256()
    impulses = records = 0
    with observed_steps() as (refs,fasts):
        for attempt in range(1,spec['cap']+1):
            refs.clear();fasts.clear()
            before_ref, before_fast = dict(vars(ref)),dict(vars(fast))
            ro = capture(lambda run:R.step(run,mode='reference'),ref)
            # Preserve Candidate B's historical differential path after later defaults.
            fo = capture(lambda run:R.step(run,mode='fast'),fast)
            assert ro == fo and refs == fasts and I.raw(ref) == I.raw(fast)
            if ro['kind'] != 'value':
                assert vars(ref) == before_ref and vars(fast) == before_fast
            row = dict(id=spec['id'],attempt=attempt,REF_state=I.raw(ref),FAST_state=I.raw(fast),
                       REF_impulses=list(refs),FAST_impulses=list(fasts),REF_result=ro,FAST_result=fo)
            encoded = E.canonical(row)+b'\n'
            stream.write(encoded);digest.update(encoded)
            impulses += len(refs);records += 1
            end = ro['kind'] if ro['kind'] != 'value' else 'outgoing_R20' if I.outgoing(ref) else None
            if end:
                return dict(id=spec['id'],steps=ref.t_steps,records=records,impulses=impulses,
                            end=end,attempt=attempt,result=ro,final_sha256=E.digest(I.raw(ref)),witness_sha256=digest.hexdigest())
    return dict(id=spec['id'],steps=ref.t_steps,records=records,impulses=impulses,end='step_cap',
                final_sha256=E.digest(I.raw(ref)),witness_sha256=digest.hexdigest())


def specs(inputs):
    return [*inputs['runtime_trajectories'],*inputs['refusals'],
            dict(inputs['runtime_precision'],id='real_cap_precision_STOP',cap=1)]


def differential(inputs,out):
    rows=[]
    with gzip.open(out/'runtime.witnesses.jsonl.gz','wb') as f:
        for spec in specs(inputs):
            row=paired(spec,f);rows.append(row)
            print('runtime differential',row['id'],row['steps'],row['end'],flush=True)
    success={s['id'] for s in inputs['runtime_trajectories']}
    assert all(r['end']=='outgoing_R20' if r['id'] in success else r['end'] in ('refusal','halt') for r in rows)
    precision=next(r for r in rows if r['id']=='real_cap_precision_STOP')
    assert precision['result']['type']=='ReferenceUndecided' and precision['steps']==0
    assert C.MAX_PRECISION_BITS==16384
    return dict(rows=rows,real_cap=16384,precision_diagnostic='synthetic dt, initial-state step attempt; not a world trajectory')


def measured(fn):
    return I.measured(fn)


def benchmark(inputs):
    import psutil
    proc=psutil.Process();previous=proc.cpu_affinity();cpu=previous[-1]
    proc.cpu_affinity([cpu])
    reps=inputs['benchmark']['repetitions'];warmup=inputs['benchmark']['warmup']
    cases=inputs['runtime_trajectories'];samples=[]
    base=make_run(cases[0]);dr=C.relative(base.pos,*base.atoms)
    try:
        for _ in range(warmup):
            for mode in ('reference','fast'):
                R.impulse(dr,Q(20),X.MOM,mode=mode)
                for spec in cases:
                    I.complete_trajectory(make_run(spec),lambda run:R.step(run,mode=mode),spec['cap'])
        for rep in range(reps):
            for mode in (('reference','fast') if rep%2==0 else ('fast','reference')):
                name='REF' if mode=='reference' else 'FAST'
                values,clock=measured(lambda:[R.impulse(dr,Q(20),X.MOM,mode=mode) for _ in range(1000)])
                samples.append(dict(rep=rep,method=name,workload='impulse',calls=1000,result_sha256=E.digest(values),**clock))
                run=copy.copy(base)
                _,clock=measured(lambda:[R.step(run,mode=mode) for _ in range(1000)])
                samples.append(dict(rep=rep,method=name,workload='step',calls=1000,result_sha256=E.digest(I.raw(run)),**clock))
                for spec in cases:
                    run=make_run(spec);states=[]
                    final,clock=measured(lambda:I.complete_trajectory(run,lambda run:R.step(run,mode=mode),spec['cap'],stored=states))
                    samples.append(dict(rep=rep,method=name,workload='trajectory',id=spec['id'],calls=run.t_steps,
                                        result_sha256=E.digest(states),final_sha256=E.digest(final),**clock))
                    print('runtime benchmark',rep,name,spec['id'],clock,flush=True)
        original={s['id'] for s in inputs['trajectories']}
        medians={}
        for label in ('impulse','step','trajectory_original3','trajectory_all6'):
            workload='trajectory' if label.startswith('trajectory') else label
            values={}
            for name in ('REF','FAST'):
                rows=[s for s in samples if s['method']==name and s['workload']==workload and
                      (label!='trajectory_original3' or s.get('id') in original)]
                values[name]={f'median_{kind}_seconds':statistics.median(
                    sum(s[f'{kind}_seconds'] for s in rows if s['rep']==rep) for rep in range(reps)) for kind in ('cpu','wall')}
            medians[label]=dict(**values,cpu_speedup=values['REF']['median_cpu_seconds']/values['FAST']['median_cpu_seconds'],
                               wall_speedup=values['REF']['median_wall_seconds']/values['FAST']['median_wall_seconds'])
        assert benchmark_valid(dict(samples=samples,medians=medians),inputs)
        return dict(cpu=cpu_name(),threads=1,affinity_cpu=cpu,logical_cpus=psutil.cpu_count(),
                    warmup=warmup,repetitions=reps,python=sys.version,samples=samples,medians=medians,
                    limits='background load uncontrolled; stored-state collection inside timed span, admission and hashing outside')
    finally:
        proc.cpu_affinity(previous)


def cpu_name():
    if sys.platform=='win32':
        return subprocess.check_output(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_Processor).Name'],text=True).strip()
    return platform.processor()


def cost_row(key,stats,total):
    primitive,calls,self_time,cumulative,callers=stats
    share=self_time/total
    filename,line,name=key
    try:
        filename=Path(filename).resolve().relative_to(E.ROOT).as_posix()
    except ValueError:
        filename=filename.replace('\\','/')
    return dict(file=filename,line=line,function=name,calls=calls,primitive_calls=primitive,
                exclusive_cpu_seconds=self_time,inclusive_cpu_seconds=cumulative,
                exclusive_cpu_percent=100*share,self_cpu_per_call_seconds=self_time/calls,
                ideal_elimination_whole_speedup_upper_bound=1/(1-share) if share<1 else None,
                exact_reference_scope='exact Python integer/Fraction or canonical half-even storage; fast derivative / slow drift and step code',
                duplicate_work='same-argument reuse not measured for this function; call count alone cannot prove redundant computation',
                callers=[dict(file=k[0],line=k[1],function=k[2],statistics=v) for k,v in sorted(callers.items(),key=lambda x:x[1][-1],reverse=True)[:5]])


def profile(inputs,out):
    import psutil
    proc=psutil.Process();previous=proc.cpu_affinity();cpu=previous[-1];proc.cpu_affinity([cpu])
    profiler=cProfile.Profile(timer=time.process_time)
    finals=[];cpu_total=wall_total=0.0
    try:
        for spec in inputs['runtime_trajectories']:
            run=make_run(spec)
            started,wall=time.process_time(),time.perf_counter()
            profiler.enable()
            try:
                final=I.complete_trajectory(run,lambda r:R.step(r,mode='fast'),spec['cap'])
            finally:
                profiler.disable()
            clock=time.process_time()-started
            cpu_total+=clock;wall_total+=time.perf_counter()-wall
            finals.append(dict(id=spec['id'],steps=run.t_steps,final_sha256=E.digest(final),cpu_seconds=clock))
            print('runtime profile',spec['id'],run.t_steps,clock,flush=True)
        profiler.dump_stats(str(out/'runtime.profile.pstats'))
        stats=pstats.Stats(profiler)
        top=sorted(stats.stats.items(),key=lambda item:item[1][2],reverse=True)[:5]
        rows=[cost_row(k,v,cpu_total) for k,v in top]
        return dict(cpu=cpu_name(),threads=1,affinity_cpu=cpu,timer='time.process_time',
                    measured_cpu_seconds=cpu_total,measured_wall_seconds=wall_total,attributed_self_cpu_seconds=stats.total_tt,
                    finals=finals,top5=rows,next_target_selected=False,
                    limits='complete FAST runtime trajectories; excludes admission, serialization and independent replay; instrumentation overhead included. Amdahl bounds assume impossible zero-cost elimination and are not achievable forecasts; exclusive fractions do not double count')
    finally:
        proc.cpu_affinity(previous)


def differential_valid(out,payload,inputs):
    definitions=specs(inputs)
    sealed={s['id']:s for s in definitions}
    expected={r['id']:r for r in payload['rows']}
    assert len(sealed)==len(definitions) and len(expected)==len(payload['rows'])
    initial=set();counts=Counter();impulses=Counter();hashes={k:hashlib.sha256() for k in expected}
    final={};results={};previous={};bases={};active=None
    def stored_run(base,state):
        run=copy.copy(base)
        run.atoms=tuple(C.Atom(a['species'],tuple(a['r']),tuple(a['p'])) for a in state['atoms'])
        run.J_cache=None if state['J_cache'] is None else tuple(state['J_cache'])
        run.t_steps=state['step']
        return run
    with gzip.open(out/'runtime.witnesses.jsonl.gz','rb') as f:
        for line in f:
            row=json.loads(line);key=row['id']
            assert key in sealed and key in expected
            if 'initial' in row:
                assert key not in initial and key==definitions[len(initial)]['id']
                assert E.digest(row['spec'])==E.digest(sealed[key])
                base=make_run(sealed[key])
                assert E.digest(row['initial'])==E.digest(I.raw(base))
                bases[key]=base;previous[key]=row['initial']
                initial.add(key);active=key;continue
            assert key==active and key in initial
            assert row['attempt']==counts[key]+1
            assert results.get(key,{'kind':'value'})['kind']=='value'
            assert row['REF_state']==row['FAST_state'] and row['REF_impulses']==row['FAST_impulses'] and row['REF_result']==row['FAST_result']
            state=row['FAST_state'];result=row['FAST_result'];calls=row['FAST_impulses']
            success=result['kind']=='value'
            assert state['step']==previous[key]['step']+int(success)
            if not success:
                assert state==previous[key]
            # All sealed refusals happen on their first impulse/step. Successful
            # cold steps have initial+outlet calls; cached steps have one outlet.
            assert len(calls)==(2 if previous[key]['J_cache'] is None else 1) if success else len(calls)==1
            prior_run=stored_run(bases[key],previous[key]);final_run=stored_run(bases[key],state)
            positions=([C.relative(prior_run.pos,*prior_run.atoms)] if previous[key]['J_cache'] is None else [])
            if success:positions.append(C.relative(final_run.pos,*final_run.atoms))
            assert len(positions)==len(calls)
            for call,position in zip(calls,positions):
                assert call['dr']==list(map(str,position)) and call['dt']==str(bases[key].dt/2)
            if success:
                assert all(call['result']['kind']=='value' for call in calls)
                assert list(calls[-1]['result']['raw'])==list(state['J_cache'])
            previous[key]=state
            counts[key]+=1;impulses[key]+=len(row['REF_impulses']);hashes[key].update(line)
            final[key]=E.digest(state);results[key]=result
    assert initial==set(expected)=={s['id'] for s in specs(inputs)}
    success={s['id'] for s in inputs['runtime_trajectories']}
    for k,row in expected.items():
        assert counts[k]==row['records'] and impulses[k]==row['impulses'] and hashes[k].hexdigest()==row['witness_sha256']
        assert final[k]==row['final_sha256'] and results[k]==row['result']
        assert row['steps']==previous[k]['step'] and row['attempt']==counts[k]
        assert row['end']=='outgoing_R20' if k in success else row['end'] in ('refusal','halt') and row['steps']==0
        assert results[k]['kind']=='value' and I.outgoing(stored_run(bases[k],previous[k])) if k in success else results[k]['kind']==row['end']
    assert expected['real_cap_precision_STOP']['result']['type']=='ReferenceUndecided' and payload['real_cap']==16384
    return True


def benchmark_valid(payload,inputs):
    samples=payload['samples'];reps=inputs['benchmark']['repetitions']
    observed=Counter((s['rep'],s['method'],s['workload'],s.get('id')) for s in samples)
    expected=Counter((rep,name,kind,key) for rep in range(reps) for name in ('REF','FAST')
                     for kind,key in [('impulse',None),('step',None),*[('trajectory',s['id']) for s in inputs['runtime_trajectories']]])
    assert reps>=3 and observed==expected
    for sample in samples:
        assert sample['cpu_seconds']>0 and sample['wall_seconds']>0
        assert all(s['calls']==sample['calls'] and s['result_sha256']==sample['result_sha256'] for s in samples
                   if s['workload']==sample['workload'] and s.get('id')==sample.get('id'))
    original={s['id'] for s in inputs['trajectories']}
    expected_medians={}
    for label in ('impulse','step','trajectory_original3','trajectory_all6'):
        kind='trajectory' if label.startswith('trajectory') else label
        values={}
        for name in ('REF','FAST'):
            rows=[s for s in samples if s['method']==name and s['workload']==kind and
                  (label!='trajectory_original3' or s.get('id') in original)]
            values[name]={f'median_{clock}_seconds':statistics.median(
                sum(s[f'{clock}_seconds'] for s in rows if s['rep']==rep) for rep in range(reps)) for clock in ('cpu','wall')}
        expected_medians[label]=dict(**values,cpu_speedup=values['REF']['median_cpu_seconds']/values['FAST']['median_cpu_seconds'],
                                    wall_speedup=values['REF']['median_wall_seconds']/values['FAST']['median_wall_seconds'])
    assert payload['medians']==expected_medians
    return True


def check_activation(out,required=ACTIVATION_STAGES,full=True):
    out=Path(out)
    try:
        manifest=read(out/'manifest.json');activation=read(out/'activation_manifest.json')
        assert activation['binding']==E.binding(manifest)
        assert E.check_run(out,required=FULL_GATES if full else (*E.CLOSURE,'audit'))['status']=='PASS'
        inputs=read(out/'inputs.json')
        for name in required:
            matches=[r for r in activation['stages'] if r['stage']==name]
            assert len(matches)==1
            row=matches[0]
            assert row['binding']==E.binding(manifest)
            assert row['returncode']==0 and row['executed'] is True
            assert row['command']==[manifest['environment']['executable'],'-u','-m',
                'experiments.verified_superoptimizer_c1b1.runtime_activation',
                '--run',str(out.resolve()),'--stage',name,'--worker']
            assert row['result'] in row['outputs'] and f'{name}.activation.log' in row['outputs']
            for path,hash_value in row['outputs'].items():
                safe=(out/path).resolve();assert safe.is_relative_to(out.resolve()) and E.sha(safe)==hash_value
            payload=read(out/row['result'])
            if name=='differential':
                assert {'runtime.witnesses.jsonl.gz','differential.activation.json'}<=row['outputs'].keys()
                assert differential_valid(out,payload,inputs)
            elif name=='benchmark':
                assert benchmark_valid(payload,inputs)
                prior={r['id']:r for r in read(out/'differential.activation.json')['rows']}
                assert all(s['calls']==prior[s['id']]['steps'] and s['final_sha256']==prior[s['id']]['final_sha256']
                           for s in payload['samples'] if s['workload']=='trajectory')
            elif name=='profile':
                assert 'runtime.profile.pstats' in row['outputs']
                assert len(payload['top5'])==5 and payload['next_target_selected'] is False
                stats=pstats.Stats(str(out/'runtime.profile.pstats'))
                top=sorted(stats.stats.items(),key=lambda item:item[1][2],reverse=True)[:5]
                expected=[cost_row(k,v,payload['measured_cpu_seconds']) for k,v in top]
                assert E.digest(expected)==E.digest(payload['top5']) and stats.total_tt==payload['attributed_self_cpu_seconds']
                prior={r['id']:r for r in read(out/'differential.activation.json')['rows']}
                assert {r['id'] for r in payload['finals']}=={s['id'] for s in inputs['runtime_trajectories']}
                assert all(r['steps']==prior[r['id']]['steps'] and r['final_sha256']==prior[r['id']]['final_sha256'] for r in payload['finals'])
        return dict(status='PASS',errors=[])
    except (AssertionError,OSError,KeyError,ValueError,TypeError) as exc:
        return dict(status='INCOMPLETE',errors=[f'{type(exc).__name__}: {exc}'])


def run_activation_stage(out,name):
    required=() if name=='differential' else ('differential',) if name=='benchmark' else ('differential','benchmark')
    assert check_activation(out,required=required,full=name!='differential')['status']=='PASS'
    activation=read(out/'activation_manifest.json');manifest=read(out/'manifest.json')
    if any(row['stage']==name for row in activation['stages']):
        raise ValueError('activation stage may execute only once')
    result=f'{name}.activation.json';log=f'{name}.activation.log'
    command=[sys.executable,'-u','-m','experiments.verified_superoptimizer_c1b1.runtime_activation',
             '--run',str(out.resolve()),'--stage',name,'--worker']
    with (out/log).open('xb') as stream:
        rc=subprocess.run(command,cwd=E.ROOT,stdout=stream,stderr=subprocess.STDOUT).returncode
    files=[log]
    for candidate in (result,'runtime.witnesses.jsonl.gz' if name=='differential' else 'runtime.profile.pstats' if name=='profile' else ''):
        if candidate and (out/candidate).is_file():files.append(candidate)
    activation['stages'].append(dict(stage=name,binding=E.binding(manifest),result=result,executed=True,
                                    command=command,returncode=rc,outputs={p:E.sha(out/p) for p in files}))
    E.write(out/'activation_manifest.json',activation)
    assert E.inventory()==manifest['source']
    if rc:raise RuntimeError(f'{name} worker failed with rc={rc}; retained log {log}')


def worker(out,name):
    manifest=read(out/'manifest.json')
    assert E.inventory()==manifest['source'] and E.sha(out/'inputs.json')==manifest['input_hash']
    result=out/f'{name}.activation.json'
    if result.exists():raise FileExistsError(result)
    inputs=read(out/'inputs.json')
    payload=differential(inputs,out) if name=='differential' else benchmark(inputs) if name=='benchmark' else profile(inputs,out)
    E.write(result,payload)


def main():
    sys.set_int_max_str_digits(0)  # diagnostics have huge exact rational dt only
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--stage',choices=('seal','closure','differential','full','benchmark','profile','check'),required=True)
    p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args();out=args.run.resolve()
    if args.worker:
        assert args.stage in ACTIVATION_STAGES
        worker(out,args.stage)
    elif args.stage=='seal':
        seal(out)
    elif args.stage=='closure':
        for name in (*E.CLOSURE,'audit'):
            if E.run_stage(out,name):return 1
    elif args.stage=='full':
        assert check_activation(out,required=('differential',),full=False)['status']=='PASS'
        return E.run_stage(out,'local_full')
    elif args.stage=='check':
        result=check_activation(out);print(result,flush=True)
        E.write(out/'activation_decision.json',result)
        return 0 if result['status']=='PASS' else 1
    else:
        run_activation_stage(out,args.stage)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
