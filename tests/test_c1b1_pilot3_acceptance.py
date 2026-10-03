import pytest
from experiments.verified_superoptimizer_c1b1 import pilot3_acceptance as A,pilot3_campaign as P

def test_actual_four_production_modes_trace_same_endpoints(tmp_path):
    row=A.paired(dict(id='four_modes',e='2',b_frac='1/2',cap=2),tmp_path/'actual.gz')
    assert row['steps']==2 and row['impulses']==3

def test_actual_production_nested_binding_fault_is_detected(tmp_path,monkeypatch):
    actual=P.R.bind
    def bind(run,*,mode='fast'):
        ex=actual(run,mode=mode)
        if mode=='fast_pilot3':
            selected=ex.function.__globals__['impulse']
            raw=P.clone(selected.__globals__['impulse_raw'],_mul=lambda a,b,M:(0,0))
            ex.function=P.clone(ex.function,impulse=P.clone(selected,impulse_raw=raw))
        return ex
    monkeypatch.setattr(P.R,'bind',bind)
    with pytest.raises(AssertionError,match='production modes differ'):
        A.paired(dict(id='wrong_actual',e='2',b_frac='1/2',cap=1),tmp_path/'wrong.gz')


def stage_fixture(out):
    inputs=dict(cases=[dict(id='one')],diagnostics=[])
    P.write(out/'inputs.json',inputs)
    source={'a.py':'sealed'}
    m=dict(run_id='this-run',source=source,source_hash=P.E.digest(source),
           input_hash=P.E.sha(out/'inputs.json'),outputs={})
    files={'integration':['integration.json','one.jsonl.gz'],
           'profile':['profile.json','fast_combined.pstats','fast_pilot3.pstats'],
           'producer':['producer.json'],
           'full':['full.json','full.xml','full.log','full_execution.json']}
    for stage,names in files.items():
        for name in names:
            if name==stage+'.json':
                P.write(out/name,{k:m[k] for k in ('run_id','source_hash','input_hash')})
            else:(out/name).write_bytes(b'preserved artifact')
        m['outputs'][stage]={name:P.E.sha(out/name) for name in names}
    P.write(out/'manifest.json',m)
    return m


@pytest.mark.parametrize('fault',['empty_stages','missing_producer','missing_pstats',
                                 'stale_run','stale_source','stale_input'])
def test_stage_closure_rejects_missing_or_stale_evidence(tmp_path,fault):
    m=stage_fixture(tmp_path)
    if fault=='empty_stages':m['outputs']={}
    elif fault=='missing_producer':del m['outputs']['producer']
    elif fault=='missing_pstats':del m['outputs']['profile']['fast_pilot3.pstats']
    else:
        payload=P.read(tmp_path/'profile.json')
        payload[dict(stale_run='run_id',stale_source='source_hash',stale_input='input_hash')[fault]]='stale'
        P.write(tmp_path/'profile.json',payload)
        m['outputs']['profile']['profile.json']=P.E.sha(tmp_path/'profile.json')
    P.write(tmp_path/'manifest.json',m)
    with pytest.raises(AssertionError):A.verify_stage(tmp_path)


def test_stage_closure_accepts_complete_bound_inventory(tmp_path):
    m=stage_fixture(tmp_path)
    assert A.verify_stage(tmp_path)==m


@pytest.mark.parametrize('profiles',[{}, {'fast_combined':{}}, {'unexpected':{}}])
def test_profile_closure_rejects_missing_modes(tmp_path,profiles):
    with pytest.raises(AssertionError,match='profile mode inventory'):
        A.validate_profiles(tmp_path,profiles,[])


def test_allocation_closure_rejects_stale_mathematical_source(tmp_path):
    cpp='experiments/verified_superoptimizer_c1b1/pilot3_alloc_probe.cpp'
    source={p:'current' for p in A.ALLOCATION_SOURCES}
    stale=dict(source);stale['a_reference/c1b1_pilot3_impulse.py']='different arithmetic'
    P.write(tmp_path/'source.json',stale)
    P.write(tmp_path/'allocations.json',dict(source_hash=P.E.digest(stale)))
    with pytest.raises(AssertionError,match='allocation mathematical source changed'):
        A.validate_allocations(tmp_path,source)


@pytest.mark.parametrize('labels',[[],list(A.ALLOCATION_CASES[:-1]),list(reversed(A.ALLOCATION_CASES))])
def test_allocation_closure_rejects_incomplete_or_wrong_case_inventory(tmp_path,labels):
    cpp='experiments/verified_superoptimizer_c1b1/pilot3_alloc_probe.cpp'
    source={p:'current' for p in A.ALLOCATION_SOURCES}
    P.write(tmp_path/'source.json',source)
    P.write(tmp_path/'allocations.json',dict(source_hash=P.E.digest(source),rows=[dict(label=x) for x in labels]))
    with pytest.raises(AssertionError,match='allocation case inventory'):
        A.validate_allocations(tmp_path,source)


def allocation_fixture(out):
    import sysconfig
    source={}
    for name in A.ALLOCATION_SOURCES:
        path=out/'source_snapshot'/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(('sealed '+name).encode());source[name]=P.E.sha(path)
    native='native/pilot3_alloc_probe'+sysconfig.get_config_var('EXT_SUFFIX')
    (out/'native').mkdir()
    (out/native).write_bytes(b'native observer')
    (out/'native/build.log').write_bytes(b'build evidence')
    cpp='experiments/verified_superoptimizer_c1b1/pilot3_alloc_probe.cpp'
    (out/'native/pilot3_alloc_probe.cpp').write_bytes((out/'source_snapshot'/cpp).read_bytes())
    P.write(out/'source.json',source)
    rows=[]
    for label in A.ALLOCATION_CASES:
        measurements={}
        for kind,value in [('old_R2_radius',[1,1]),('raw_R2_radius',[1,1]),
                           ('old_component',['1','2']),('raw_component',[1,2,1])]:
            measurements[kind]=dict(calls=5000,heap_integer_objects=5000,object_allocator_allocations=10000,
                object_allocator_peak_live_bytes=40,bigint_allocated_bytes=25000 if kind=='raw_component' else 50000,
                bigint_max_bits=31,bigint_max_object_bytes=32,bigint_objects=5000,bigint_peak_live_bytes=32,
                value=value,operations_per_call={'integer *':4})
        rows.append(dict(label=label,shift=48,dt='1',raw=[1,0,0],M=128,measurements=measurements))
    a=dict(source_hash=P.E.digest(source),rows=rows,native_hash=P.E.sha(out/native),
           input_fingerprint=P.E.digest([{k:r[k] for k in ('label','shift','dt','raw','M')} for r in rows]))
    P.write(out/'allocations.json',a)
    names=['source.json','allocations.json',native,'native/build.log','native/pilot3_alloc_probe.cpp',
           *('source_snapshot/'+name for name in A.ALLOCATION_SOURCES)]
    manifest=dict(run_id='fixture',source_hash=a['source_hash'],input_fingerprint=a['input_fingerprint'],
                  outputs={name:P.E.sha(out/name) for name in names})
    P.write(out/'manifest.json',manifest)
    return source,a,manifest


def test_allocation_closure_accepts_complete_bound_observation(tmp_path):
    source,a,_=allocation_fixture(tmp_path)
    assert A.validate_allocations(tmp_path,source)==a


@pytest.mark.parametrize('fault',['stale_observer','tampered_data','missing_metric',
                                 'negative_metric','bool_metric','wrong_calls','missing_file'])
def test_allocation_closure_rejects_stale_tampered_or_incomplete_cost_data(tmp_path,fault):
    source,a,m=allocation_fixture(tmp_path)
    if fault=='stale_observer':
        current=dict(source);current['experiments/verified_superoptimizer_c1b1/pilot3_allocations.py']='changed observer'
        with pytest.raises(AssertionError,match='allocation mathematical source changed'):
            A.validate_allocations(tmp_path,current)
        return
    metric=a['rows'][0]['measurements']['raw_component']
    if fault=='missing_metric':del metric['heap_integer_objects']
    elif fault in ('negative_metric','tampered_data'):metric['object_allocator_peak_live_bytes']=-1
    elif fault=='bool_metric':metric['heap_integer_objects']=True
    elif fault=='wrong_calls':metric['calls']=1
    elif fault=='missing_file':del m['outputs']['native/build.log']
    P.write(tmp_path/'allocations.json',a)
    if fault!='tampered_data':m['outputs']['allocations.json']=P.E.sha(tmp_path/'allocations.json')
    P.write(tmp_path/'manifest.json',m)
    with pytest.raises(AssertionError):A.validate_allocations(tmp_path,source)
