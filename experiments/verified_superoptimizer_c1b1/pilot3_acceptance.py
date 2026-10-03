"""Fail-closed final integration/FULL/evidence checks; no new physical oracle."""
import argparse,copy,gzip,hashlib,json,math,pstats,subprocess,sys,statistics
from pathlib import Path
from . import pilot3_campaign as P,combined_promotion as K,evidence as E

ACTUAL_MODES=('reference','fast','fast_combined','fast_pilot3')
PROFILE_MODES=('fast_combined','fast_pilot3')
ALLOCATION_CASES=('production','stress_F150','large_dt','near_raw_limit','actual_cap16384')
MATH_SOURCES=('a_reference/c1b1_two_atom.py','a_reference/c1b1_fast_impulse.py',
    'a_reference/c1b1_impulse_primitives.py','a_reference/c1b1_combined_arithmetic.py',
    'a_reference/c1b1_pilot3_impulse.py','a_reference/ar2_lang2024.py','a_numeric/profiles.py',
    'experiments/verified_superoptimizer_c1b1/checker.py','experiments/verified_superoptimizer_c1b1/pilot3_checker.py')
ALLOCATION_SOURCES=(*MATH_SOURCES,'experiments/verified_superoptimizer_c1b1/pilot3_allocations.py',
                    'experiments/verified_superoptimizer_c1b1/pilot3_alloc_probe.cpp')

def collected():
    output=subprocess.check_output([sys.executable,'-m','pytest','tests','--collect-only','-q'],text=True)
    result=[]
    for line in output.splitlines():
        if line.startswith(('tests/','tests\\')) and '::' in line:
            parts=line.split('::');module=parts[0].replace('\\','/').removesuffix('.py').replace('/','.')
            result.append([module+''.join('.'+x for x in parts[1:-1]),parts[-1]])
    assert len(result)==len(set(map(tuple,result))) and len(result)>3904
    return result

def seal(out):
    P.seal(out);m=P.read(out/'manifest.json');m['full_identities']=collected()
    m['math_sources']={p:m['source'][p] for p in MATH_SOURCES};P.write(out/'manifest.json',m)

def observed(ex,mode,events):P.instrument(ex,'ABCD' if mode=='fast_pilot3' else mode,events)

def validate_observation(spec,run,previous,observations):
    assert set(observations)==set(ACTUAL_MODES),'missing actual runtime'
    assert all(v==observations['reference'] for v in observations.values()),'actual production modes differ'
    K.validate_observations(spec,{m:observations[m] for m in K.MODES},run,verify_impulse=False)
    K.validate_transition(run,previous,observations['reference'])

def paired(spec,out):
    original=P.make_run(spec);runs={m:copy.copy(original) for m in ACTUAL_MODES}
    events={m:[] for m in ACTUAL_MODES};executors={m:P.R.bind(r,mode=m) for m,r in runs.items()}
    assert executors['fast_pilot3'].variant=='ABCD'
    for m,ex in executors.items():observed(ex,m,events[m])
    h=hashlib.sha256();impulses=0
    with gzip.open(out,'wb') as stream:
        stream.write(E.canonical(dict(spec=spec,initial=P.plain(P.I.raw(original))))+b'\n')
        for attempt in range(1,spec['cap']+1):
            previous=P.plain(P.I.raw(runs['reference']));before={m:dict(vars(r)) for m,r in runs.items()}
            for ev in events.values():ev.clear()
            observations={m:dict(result=P.I.capture(ex.step),events=events[m],state=P.plain(P.I.raw(runs[m]))) for m,ex in executors.items()}
            encoded=E.canonical(dict(attempt=attempt,per_mode=observations))+b'\n';h.update(encoded);stream.write(encoded)
            validate_observation(spec,original,previous,observations)
            value=observations['reference'];impulses+=sum(e['function']=='impulse' for e in value['events'])
            if value['result']['kind']!='value':
                assert all(vars(r)==before[m] for m,r in runs.items());end=value['result']['type'];break
            if P.I.outgoing(runs['reference']):end='outgoing_R20';break
        else:end='step_cap'
    return dict(id=spec['id'],attempts=attempt,steps=runs['reference'].t_steps,impulses=impulses,end=end,
                result=value['result'],final_sha256=E.digest(value['state']),witness_sha256=h.hexdigest())

def integration(out):
    m=P.read(out/'manifest.json');assert E.inventory()==m['source'];inputs=P.read(out/'inputs.json');rows=[]
    for spec in (*inputs['cases'],*inputs['diagnostics']):
        row=paired(spec,out/(spec['id']+'.jsonl.gz'));rows.append(row);print('production',row['id'],row['steps'],row['end'],flush=True)
    P.write(out/'integration.json',dict(source_hash=m['source_hash'],input_hash=m['input_hash'],run_id=m['run_id'],rows=rows))
    latest=P.read(out/'manifest.json');assert latest['source_hash']==m['source_hash']
    latest['outputs']['integration']={p.name:E.sha(p) for p in (out/'integration.json',*out.glob('*.jsonl.gz'))};P.write(out/'manifest.json',latest)

def producer(out):
    from tools import c1b1_replay_benchmark as driver
    m=P.read(out/'manifest.json');assert E.inventory()==m['source']
    rows=[]
    for label in driver.LABELS:
        values=[driver.execute(label,mode=m) for m in ACTUAL_MODES]
        assert all(v['all_states_equal_old_raw_inputs'] for v in values)
        assert len({v['steps'] for v in values})==1
        rows.append(dict(label=label,source_sha256=E.sha(driver.OLD/f'witness_{label}.json'),values=values))
    assert E.inventory()==m['source']
    P.write(out/'producer.json',dict(rows=rows,**{k:m[k] for k in ('run_id','source_hash','input_hash')}))
    register(out,'producer',('producer.json',))

def register(out,stage,names):
    m=P.read(out/'manifest.json');assert stage not in m['outputs']
    m['outputs'][stage]={name:E.sha(out/name) for name in names};P.write(out/'manifest.json',m)

def attach_full(out):
    m=P.read(out/'manifest.json');assert E.inventory()==m['source']
    full=K.validate_full(out,m)
    assert full['source_hash']==m['source_hash'] and full['source_unchanged'] is True
    assert full['workers']==6 and full['existing_CUDA_GPU_regressions_included'] is True
    P.write(out/'full.json',dict(payload=full,**{k:m[k] for k in ('run_id','source_hash','input_hash')}))
    register(out,'full',('full.json','full.xml','full.log','full_execution.json'))

def verify_stage(out,required=('integration','profile','producer','full')):
    m=P.read(out/'manifest.json');assert E.sha(out/'inputs.json')==m['input_hash'];assert E.digest(m['source'])==m['source_hash']
    inputs=P.read(out/'inputs.json');specs=[*inputs['cases'],*inputs['diagnostics']]
    assert len({s['id'] for s in specs})==len(specs)
    names={s:{s+'.json'} for s in required}
    for s in ('integration','differential'):
        if s in names:names[s].update(x['id']+'.jsonl.gz' for x in specs)
    if 'profile' in names:names['profile'].update(mode+'.pstats' for mode in PROFILE_MODES)
    if 'full' in names:names['full'].update(('full.xml','full.log','full_execution.json'))
    if 'benchmark' in names:names['benchmark'].add('benchmark_samples.jsonl')
    if 'r2_radius' in names:names['r2_radius']={'r2_radius_supplement.json'}
    assert set(m['outputs'])==set(required),'missing required evidence stage'
    for stage,files in m['outputs'].items():
        assert set(files)==names[stage],'incomplete artifact inventory'
        for name,sha in files.items():assert E.sha(E._safe_file(out,name))==sha,(stage,name)
        body=P.read(out/('r2_radius_supplement.json' if stage=='r2_radius' else stage+'.json'))
        for key in ('run_id','source_hash','input_hash'):
            field='main_input_hash' if stage=='r2_radius' and key=='input_hash' else key
            assert body[field]==m[key],('stale stage envelope',stage,key)
    return m

def validate_profiles(out,profiles,integration_rows):
    assert set(profiles)==set(PROFILE_MODES),'profile mode inventory'
    for mode,value in profiles.items():
        stats=pstats.Stats(str(out/(mode+'.pstats')));summary=K.profile_summary(stats)
        assert all(value[k]==v for k,v in summary.items())
        assert [(x['id'],x['steps'],x['final_sha256']) for x in value['finals']]==[(r['id'],r['steps'],r['final_sha256']) for r in integration_rows[:6]]

def validate_allocations(out,source):
    a=P.read(out/'allocations.json');earlier=P.read(out/'source.json')
    assert E.digest(earlier)==a['source_hash']
    cpp='experiments/verified_superoptimizer_c1b1/pilot3_alloc_probe.cpp'
    assert all(earlier[p]==source[p] for p in ALLOCATION_SOURCES),'allocation mathematical source changed'
    assert [r['label'] for r in a['rows']]==list(ALLOCATION_CASES),'allocation case inventory'
    manifest=P.read(out/'manifest.json');assert manifest['source_hash']==a['source_hash']
    assert manifest['input_fingerprint']==a['input_fingerprint']
    native='native/pilot3_alloc_probe'+__import__('sysconfig').get_config_var('EXT_SUFFIX')
    required={'allocations.json','source.json','native/pilot3_alloc_probe.cpp',native,'native/build.log',
              *('source_snapshot/'+p for p in ALLOCATION_SOURCES)}
    assert set(manifest['outputs'])==required,'allocation artifact inventory'
    for name,sha in manifest['outputs'].items():assert E.sha(E._safe_file(out,name))==sha,'allocation artifact hash'
    for p in ALLOCATION_SOURCES:assert E.sha(out/'source_snapshot'/p)==earlier[p],'allocation source snapshot'
    assert E.digest([{k:r[k] for k in ('label','shift','dt','raw','M')} for r in a['rows']])==a['input_fingerprint']
    assert E.sha(out/'native'/Path(cpp).name)==earlier[cpp]
    assert a['native_hash']==E.sha(out/'native'/('pilot3_alloc_probe'+__import__('sysconfig').get_config_var('EXT_SUFFIX')))
    for row in a['rows']:
        v=row['measurements'];assert set(v)=={'old_R2_radius','raw_R2_radius','old_component','raw_component'}
        for metric in v.values():
            keys=('calls','heap_integer_objects','object_allocator_allocations','object_allocator_peak_live_bytes',
                  'bigint_allocated_bytes','bigint_max_bits','bigint_max_object_bytes','bigint_objects','bigint_peak_live_bytes')
            assert all(k in metric and type(metric[k]) is int and metric[k]>=0 for k in keys),'allocation metric schema'
            assert metric['calls']==5000 and metric['object_allocator_peak_live_bytes']>0,'allocation measurement scope'
            assert metric['object_allocator_allocations']>=metric['heap_integer_objects']>=metric['bigint_objects']
        lo,hi,d=v['raw_component']['value']
        assert [str(P.Q(n,d)) for n in (lo,hi)]==v['old_component']['value']
        assert v['raw_R2_radius']['value']==v['old_R2_radius']['value']
        assert v['raw_component']['bigint_allocated_bytes']<v['old_component']['bigint_allocated_bytes']
        assert v['raw_component']['operations_per_call']['integer *']==4
    return a

def check(out,old,fixed,alloc):
    m=verify_stage(out);assert E.inventory()==m['source']
    old_m=verify_stage(old,('differential','benchmark','bigint','r2_radius'));fixed_m=verify_stage(fixed,('fixed',))
    for earlier in (old_m,fixed_m):
        assert all(earlier['source'][p]==m['source'][p] for p in MATH_SOURCES),'mathematical source changed'
    identities=m['full_identities'];full=K.validate_full(out,m);assert full['counts']['PASS']>=3903
    assert P.read(out/'full.json')['payload']==full
    assert full['source_hash']==m['source_hash'] and full['source_unchanged'] is True
    assert full['workers']==6 and full['existing_CUDA_GPU_regressions_included'] is True
    assert sorted(collected())==sorted(identities)
    assert P.read(out/'inputs.json')==P.read(old/'inputs.json')
    assert P.read(out/'inputs.json')['impulses']==P.read(fixed/'inputs.json')['impulses']
    f=P.read(fixed/'fixed.json')['payload'];assert len(f['endpoints'])==889 and len(f['outcomes'])==222
    for row in f['outcomes']:assert all(v==row['values']['REF'] for v in row['values'].values())
    b=P.read(old/'benchmark.json')['payload'];samples=b['samples'];assert len(samples)==264
    assert [json.loads(x) for x in (old/'benchmark_samples.jsonl').read_bytes().splitlines()]==samples
    keys={(s['rep'],s['mode'],s['workload'],s.get('id')) for s in samples}
    expected={(rep,mode,work,None) for rep in range(3) for mode in P.MODES for work in ('relative','radius','component','impulse','step')}
    expected.update((rep,mode,'trajectory',spec['id']) for rep in range(3) for mode in P.MODES for spec in P.read(old/'inputs.json')['cases'])
    assert keys==expected and len(keys)==264
    for s in samples:
        assert all(math.isfinite(s[k]) and s[k]>0 for k in ('cpu_seconds','wall_seconds'))
        if s['workload'] in ('relative','radius','component','impulse'):assert s['cpu_seconds']>=0.125
    med=b['medians'];assert med['trajectory']['ABCD']['cpu']<med['trajectory']['fast_combined']['cpu']
    for work,by_mode in med.items():
        for mode,row in by_mode.items():
            for clock in ('cpu','wall'):
                assert row[clock]==statistics.median(sum(s[clock+'_seconds'] for s in samples if s['workload']==work and s['mode']==mode and s['rep']==rep) for rep in range(3))
            assert row['speedup_vs_combined']==by_mode['fast_combined']['cpu']/row['cpu']
    assert med['trajectory']['ABCD']['cpu']<=min(med['trajectory'][v]['cpu'] for v in P.X.VARIANTS)
    integration_rows=P.read(out/'integration.json')['rows'];old_rows=P.read(old/'differential.json')['payload']
    assert [(r['id'],r['steps'],r['end'],r['final_sha256']) for r in integration_rows]==[(r['id'],r['steps'],r['end'],r['final_sha256']) for r in old_rows]
    specs=[*P.read(out/'inputs.json')['cases'],*P.read(out/'inputs.json')['diagnostics']]
    assert [r['id'] for r in integration_rows]==[s['id'] for s in specs]
    for spec,row in zip(specs,integration_rows):
        h=hashlib.sha256();run=P.make_run(spec);previous=P.plain(P.I.raw(run));n=0
        with gzip.open(out/(spec['id']+'.jsonl.gz'),'rb') as stream:
            assert json.loads(next(stream))==dict(spec=spec,initial=previous)
            for line in stream:
                h.update(line);record=json.loads(line);n+=1;assert record['attempt']==n
                validate_observation(spec,run,previous,record['per_mode']);previous=record['per_mode']['reference']['state']
        assert n==row['attempts'] and h.hexdigest()==row['witness_sha256'] and E.digest(previous)==row['final_sha256']
    profiles=P.read(out/'profile.json')['payload']['rows']
    validate_profiles(out,profiles,integration_rows);validate_allocations(alloc,m['source'])
    from tools import c1b1_replay_benchmark as driver
    producer_rows=P.read(out/'producer.json')['rows'];assert [r['label'] for r in producer_rows]==list(driver.LABELS)
    for r in producer_rows:
        witness=driver.OLD/f"witness_{r['label']}.json";assert E.sha(witness)==r['source_sha256']
        assert [v['runtime_mode'] for v in r['values']]==list(ACTUAL_MODES)
        assert all(v['label']==r['label'] and v['steps']==P.read(witness)['steps'] and v['all_states_equal_old_raw_inputs'] is True for v in r['values'])
    return dict(status='PASS',source_hash=m['source_hash'],input_hash=m['input_hash'],run_id=m['run_id'],
                counts=full['counts'],trajectory_steps=sum(r['steps'] for r in integration_rows),
                producer_steps=sum(r['values'][0]['steps'] for r in producer_rows),
                speedup_vs_combined=med['trajectory']['fast_combined']['cpu']/med['trajectory']['ABCD']['cpu'])

def main():
    sys.set_int_max_str_digits(0)
    parser=argparse.ArgumentParser();parser.add_argument('stage');parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--old',type=Path);parser.add_argument('--fixed',type=Path);parser.add_argument('--alloc',type=Path);a=parser.parse_args()
    if a.stage=='seal':seal(a.out)
    elif a.stage=='integration':integration(a.out)
    elif a.stage=='producer':producer(a.out)
    elif a.stage=='attach-full':attach_full(a.out)
    elif a.stage=='check':P.write(a.out/'closure.json',check(a.out,a.old,a.fixed,a.alloc))
if __name__=='__main__':main()
