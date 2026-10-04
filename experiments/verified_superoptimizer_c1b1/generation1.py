"""Generation 1 integration/performance closure. CPU only; no candidate search."""
import argparse,copy,json,os,statistics,subprocess,sys,time
from pathlib import Path
from . import evidence as E,pilot3_campaign as P,pilot3_acceptance as A,combined_promotion as K
from a_reference import c1b1_runtime as R,c1b1_prepared_binding as B

MODES=A.ACTUAL_MODES
CONTROL='pilot3_without_new_binding_guard_control'


def seal(out):
    A.seal(out)
    from tools import c1b1_replay_benchmark as driver
    m=P.read(out/'manifest.json');m['generation']=1
    m['binding_source']=m['source']['a_reference/c1b1_prepared_binding.py']
    m['producer_inputs']={label:dict(sha256=E.sha(driver.OLD/f'witness_{label}.json'),
        steps=P.read(driver.OLD/f'witness_{label}.json')['steps']) for label in driver.LABELS}
    P.write(out/'manifest.json',m)


def validate_producer(rows,inputs):
    assert [r['label'] for r in rows]==list(inputs),'producer case inventory'
    for row in rows:
        expected=inputs[row['label']]
        assert row['source_sha256']==expected['sha256'],'producer input changed'
        assert [v['runtime_mode'] for v in row['values']]==list(MODES),'producer mode inventory'
        assert row['default']['runtime_mode']=='fast_pilot3','omitted producer mode differs'
        for value in (*row['values'],row['default']):
            assert value['steps']==expected['steps'] and value['all_states_equal_old_raw_inputs'] is True


def require_producer_inputs(manifest,source_epoch):
    # Historical analysis repair is explicitly identified by the source bridge.
    # A live final-default epoch must never borrow that compatibility exception.
    assert source_epoch['kind'] in ('live','historical_checker_repair')
    if source_epoch['kind']=='historical_checker_repair' and 'producer_inputs' not in manifest:
        return None
    from tools import c1b1_replay_benchmark as driver
    assert 'producer_inputs' in manifest,'missing default producer input seal'
    inputs=manifest['producer_inputs']
    assert type(inputs) is dict and set(inputs)==set(driver.LABELS),'incomplete producer input seal'
    return inputs


def producer(out):
    from tools import c1b1_replay_benchmark as driver
    m=P.read(out/'manifest.json');assert E.inventory()==m['source'];rows=[]
    assert R.DEFAULT_MODE==driver.DEFAULT_RUNTIME_MODE=='fast_pilot3'
    for label,expected in m['producer_inputs'].items():
        witness=driver.OLD/f'witness_{label}.json'
        assert E.sha(witness)==expected['sha256']
        # execute checks every actually emitted J and state against the input.
        values=[driver.execute(label,mode=mode) for mode in MODES]
        default=driver.execute(label)  # the real production call with mode omitted
        rows.append(dict(label=label,source_sha256=E.sha(witness),values=values,default=default))
        print('actual producer',label,default['steps'],default['runtime_mode'],flush=True)
    validate_producer(rows,m['producer_inputs']);assert E.inventory()==m['source']
    P.write(out/'producer.json',dict(rows=rows,**{k:m[k] for k in ('run_id','source_hash','input_hash')}))
    A.register(out,'producer',('producer.json',))


def executor(run,mode):
    ex=R.bind(run,mode='fast_pilot3' if mode==CONTROL else mode)
    if mode==CONTROL:
        # Isolated measurement of the NEW guard cost. Existing Pilot3/Combined
        # Run/profile/mass guard remains active; never exposed by production selector.
        ex._prepared_binding=None
    return ex


def benchmark(out):
    import psutil
    m=P.read(out/'manifest.json');inputs=P.read(out/'inputs.json')
    assert E.inventory()==m['source']
    proc=psutil.Process();old=proc.cpu_affinity();proc.cpu_affinity([old[-1]])
    samples=[];overhead=[];stream=(out/'benchmark_samples.jsonl').open('xb')
    def retain(row):
        samples.append(row);stream.write(E.canonical(row)+b'\n');stream.flush()
    def timed(fn):
        c,w=time.process_time(),time.perf_counter();v=fn()
        return v,dict(cpu_seconds=time.process_time()-c,wall_seconds=time.perf_counter()-w)
    try:
        base=P.make_run(inputs['cases'][0]);world=B.world_binding()
        for rep in range(inputs['repetitions']):
            for kind,count,fn in (
                ('world_prepare_once',2000,B.WorldBinding.build),
                ('run_bind_once',20000,lambda:R.bind(base,mode='fast_pilot3')),
                ('step_binding_check',50000,lambda:ex._prepared_binding.assert_current(base,ex._binding_mode()))):
                ex=R.bind(base,mode='fast_pilot3')
                _,clock=timed(lambda:P.P2.loop(fn,count))
                assert clock['cpu_seconds']>=0.125
                overhead.append(dict(rep=rep,kind=kind,calls=count,**clock))
        modes=(*MODES,CONTROL)
        for mode in modes:
            for spec in inputs['cases']:
                run=P.make_run(spec);P.P2.loop(executor(run,mode).step,inputs['warmup_calls'])
        for rep in range(inputs['repetitions']):
            order=list(modes[rep:]+modes[:rep])
            if rep%2:order.reverse()
            for mode in order:
                base=P.make_run(inputs['cases'][0]);ex=executor(base,mode)
                for kind in ('drift','kick'):
                    ns=ex.function.__globals__;a=base.atoms[0]
                    fn=(lambda:ns['_drift'](base.pos,base.mom,a,base.dt,rule=base.drift)) if kind=='drift' else (lambda:ns['_kick'](base.mom,base.atoms,(1,-1,0)))
                    P.P2.loop(fn,inputs['warmup_calls']);n=100000
                    value,clock=timed(lambda:P.P2.loop(fn,n))
                    retain(dict(rep=rep,mode=mode,workload=kind,calls=n,result=E.digest(P.plain(value)),**clock))
                run=P.make_run(inputs['cases'][0]);ex=executor(run,mode)
                _,clock=timed(lambda:P.P2.loop(ex.step,1000))
                retain(dict(rep=rep,mode=mode,workload='step',calls=1000,result=E.digest(P.plain(P.I.raw(run))),**clock))
                for spec in inputs['cases']:
                    states=[]
                    # Run admission/preparation/binding ARE inside the trajectory timer.
                    def trajectory():
                        run=P.make_run(spec);ex=executor(run,mode)
                        P.complete(run,ex,spec['cap'],states)
                        return run
                    run,clock=timed(trajectory)
                    retain(dict(rep=rep,mode=mode,workload='trajectory',id=spec['id'],calls=run.t_steps,
                                final_sha256=E.digest(P.plain(P.I.raw(run))),result=E.digest(states),**clock))
                print('benchmark',rep,mode,flush=True)
        medians={}
        for kind in ('drift','kick','step','trajectory'):
            medians[kind]={mode:statistics.median(sum(r['cpu_seconds'] for r in samples if
                r['mode']==mode and r['workload']==kind and r['rep']==rep) for rep in range(inputs['repetitions'])) for mode in modes}
        costs={kind:statistics.median(r['cpu_seconds']/r['calls'] for r in overhead if r['kind']==kind) for kind in {r['kind'] for r in overhead}}
        env=dict(python=sys.version,physical_cores=psutil.cpu_count(logical=False),logical_threads=psutil.cpu_count(),
                 worker_threads=1,affinity=[old[-1]],cpu_model=subprocess.check_output(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_Processor).Name'],text=True).strip())
        result=dict(run_id=m['run_id'],source_hash=m['source_hash'],input_hash=m['input_hash'],samples=samples,
                    overhead_samples=overhead,overhead_median_seconds_per_call=costs,medians=medians,environment=env,
                    repetitions=inputs['repetitions'],warmup_steps_per_case=inputs['warmup_calls'],
                    timing='CPU process time; drift/kick/step isolate calls; trajectory includes new Run admission, binding, all hot guards, R20 stop and state retention; same campaign direct comparisons',
                    control_scope='New binding guard disabled only in isolated benchmark control; old guard and numerical Pilot3 path remain; control unavailable in production')
        validate_benchmark(result,inputs)
        assert E.inventory()==m['source']
        P.write(out/'benchmark.json',result);A.register(out,'benchmark',('benchmark.json','benchmark_samples.jsonl'))
    finally:
        stream.close();proc.cpu_affinity(old)


def validate_benchmark(body,inputs):
    modes=(*MODES,CONTROL);rows=body['samples'];cases=inputs['cases'];reps=inputs['repetitions']
    expected={(rep,mode,kind,spec['id'] if kind=='trajectory' else None) for rep in range(reps)
              for mode in modes for kind in ('drift','kick','step','trajectory')
              for spec in (cases if kind=='trajectory' else [{}])}
    actual=[(r['rep'],r['mode'],r['workload'],r.get('id')) for r in rows]
    assert len(actual)==len(set(actual)) and set(actual)==expected
    for kind in ('drift','kick','step','trajectory'):
        for ident in ([s['id'] for s in cases] if kind=='trajectory' else [None]):
            selected=[r for r in rows if r['workload']==kind and r.get('id')==ident]
            assert len({r['result'] for r in selected})==1,'measured paths differ'
            assert all(r['cpu_seconds']>=0.125 and r['wall_seconds']>0 for r in selected)
            if kind=='trajectory':
                expected_steps=inputs['case_steps'][[s['id'] for s in cases].index(ident)]
                assert all(r['calls']==expected_steps for r in selected)
                assert len({r['final_sha256'] for r in selected})==1
        for mode in modes:
            median=statistics.median(sum(r['cpu_seconds'] for r in rows if r['mode']==mode and r['workload']==kind and r['rep']==rep) for rep in range(reps))
            assert median==body['medians'][kind][mode]
    t=body['medians']['trajectory']
    assert all(t['fast_pilot3']<t[mode] for mode in ('reference','fast','fast_combined')),'trajectory CPU gate'


def full(out):
    m=P.read(out/'manifest.json');assert E.inventory()==m['source']
    env=dict(os.environ);env['PATH']=r'C:\Program Files\Git\usr\bin'+';'+env['PATH']
    command=[sys.executable,'-m','pytest','tests','-q','-n','6','--junitxml='+str(out/'full.xml')]
    start=time.perf_counter()
    with (out/'full.log').open('wb') as stream:
        p=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=env)
    execution=dict(exit_code=p.returncode,wall_seconds=time.perf_counter()-start,source_hash=m['source_hash'],
                   source_unchanged=E.inventory()==m['source'],command=' '.join(command),workers=6,existing_CUDA_GPU_regressions_included=True)
    P.write(out/'full_execution.json',execution)
    assert p.returncode==0,execution
    A.attach_full(out)
    print(P.read(out/'full.json'),flush=True)


def validate_fixed(stored,fresh):
    # JSON's array representation is shared by Python lists and tuples. Values,
    # signs, integer types, dictionary keys and array order remain exact.
    assert E.canonical(stored)==E.canonical(fresh),'saved exact endpoints differ'


def checked_source_epoch(out,manifest):
    current=E.inventory()
    if current==manifest['source']:
        return dict(kind='live',checker_source_hash=E.digest(current))
    # A narrowly checked historical validation, not rebinding old evidence to a
    # new runtime. All runtime/math/measurement sources must remain byte-identical.
    allowed={'experiments/verified_superoptimizer_c1b1/generation1.py','tests/test_c1b1_generation1_evidence.py'}
    changed={p for p in set(current)|set(manifest['source']) if current.get(p)!=manifest['source'].get(p)}
    assert changed and changed<=allowed,'historical runtime/measurement source changed'
    import ast
    snapshots=out.parent/'checker_repair_v3/source_before'
    for name in allowed:assert E.sha(snapshots/name)==manifest['source'][name]
    old=ast.parse((snapshots/'experiments/verified_superoptimizer_c1b1/generation1.py').read_text('utf8'))
    new=ast.parse((E.HERE/'generation1.py').read_text('utf8'))
    old_functions={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,ast.FunctionDef)}
    new_functions={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,ast.FunctionDef)}
    assert set(new_functions)==set(old_functions)|{'validate_fixed','checked_source_epoch'}
    assert all(new_functions[name]==body for name,body in old_functions.items() if name!='check')
    assert ast.dump(ast.Module(body=[n for n in old.body if not isinstance(n,ast.FunctionDef)],type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=[n for n in new.body if not isinstance(n,ast.FunctionDef)],type_ignores=[]),include_attributes=False)
    return dict(kind='historical_checker_repair',checker_source_hash=E.digest(current),parent_source_hash=manifest['source_hash'],
                changed_analysis_only=sorted(changed),all_runtime_math_measurement_sources_byte_identical=True,
                all_measurement_function_ASTs_unchanged=True)


def check(out):
    m=A.verify_stage(out,required=('integration','producer','benchmark','full','fixed','bigint','profile'))
    source_epoch=checked_source_epoch(out,m)
    producer_inputs=require_producer_inputs(m,source_epoch)
    inputs=P.read(out/'inputs.json');integration=P.read(out/'integration.json')
    assert [r['id'] for r in integration['rows']]==[s['id'] for s in (*inputs['cases'],*inputs['diagnostics'])]
    # Existing acceptance closure replays every retained observation/transition.
    import gzip,hashlib
    for spec,row in zip((*inputs['cases'],*inputs['diagnostics']),integration['rows']):
        run=P.make_run(spec);previous=P.plain(P.I.raw(run));h=hashlib.sha256();count=0
        with gzip.open(out/(spec['id']+'.jsonl.gz'),'rb') as f:
            header=json.loads(next(f));assert header['spec']==spec and header['initial']==previous
            for line in f:
                item=json.loads(line);h.update(line);count+=1;assert item['attempt']==count
                A.validate_observation(spec,run,previous,item['per_mode']);previous=item['per_mode']['reference']['state']
        assert count==row['attempts'] and h.hexdigest()==row['witness_sha256'] and E.digest(previous)==row['final_sha256']
    b=P.read(out/'benchmark.json');validate_benchmark(b,inputs)
    raw=[json.loads(x) for x in (out/'benchmark_samples.jsonl').read_bytes().splitlines()]
    assert raw==b['samples']
    if producer_inputs is not None:
        from tools import c1b1_replay_benchmark as driver
        for label,value in producer_inputs.items():
            path=driver.OLD/f'witness_{label}.json'
            assert E.sha(path)==value['sha256'] and P.read(path)['steps']==value['steps']
        validate_producer(P.read(out/'producer.json')['rows'],producer_inputs)
    validate_fixed(P.read(out/'fixed.json')['payload'],P.fixed(inputs))
    actual_big=P.read(out/'bigint.json')['payload'];fresh_big=P.bigint()
    assert actual_big['allocation_scope']==fresh_big['allocation_scope']
    assert [{k:v for k,v in r.items() if k!='costs'} for r in actual_big['rows']]==[{k:v for k,v in r.items() if k!='costs'} for r in fresh_big['rows']]
    for row in actual_big['rows']:
        assert set(row['costs'])=={'raw_multiply','raw_divide','old_Fraction','old_divide'}
        for cost in row['costs'].values():
            assert cost['calls']==200000 and len(cost['samples'])==3
            assert cost['median_cpu_per_call']==statistics.median(s['cpu_seconds'] for s in cost['samples'])/cost['calls']
    A.validate_profiles(out,P.read(out/'profile.json')['payload']['rows'],integration['rows'])
    full_result=K.validate_full(out,m);assert full_result==P.read(out/'full.json')['payload']
    result=dict(status='PASS',source_hash=m['source_hash'],input_hash=m['input_hash'],run_id=m['run_id'],
                validation_source=source_epoch,
                default_producer_verified=producer_inputs is not None,
                integration_cases=len(integration['rows']),integration_steps=sum(r['steps'] for r in integration['rows']),
                trajectory_speedup_vs_REF=b['medians']['trajectory']['reference']/b['medians']['trajectory']['fast_pilot3'],
                trajectory_speedup_vs_Combined=b['medians']['trajectory']['fast_combined']/b['medians']['trajectory']['fast_pilot3'])
    name='closure_rebound_v1.json' if source_epoch['kind']!='live' else 'closure.json'
    P.write(out/name,result);print(result,flush=True)


def main():
    # Trusted sealed exact integers may exceed Python's decimal JSON safety cap.
    # This changes serialization only, never precision/rounding/arithmetic caps.
    sys.set_int_max_str_digits(0)
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=('seal','integration','producer','benchmark','fixed','bigint','profile','full','check'));ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.stage=='seal':seal(a.out)
    elif a.stage=='integration':A.integration(a.out)
    elif a.stage in ('fixed','bigint','profile'):P.execute(a.stage,a.out)
    else:globals()[a.stage](a.out)


if __name__=='__main__':main()
