"""The promotion gate must reject incomplete/contradictory raw CPU evidence."""
import copy
import pytest
from experiments.verified_superoptimizer_c1b1 import generation1 as G


def campaign():
    inputs=dict(cases=[dict(id='one')],case_steps=[1],repetitions=3)
    cpu=dict(reference=4.0,fast=3.0,fast_combined=2.5,fast_pilot3=2.0,
             pilot3_without_new_binding_guard_control=1.9)
    rows=[dict(rep=rep,mode=mode,workload=kind,calls=1,result='same',cpu_seconds=seconds,wall_seconds=seconds+1,
               **(dict(id='one',final_sha256='same') if kind=='trajectory' else {}))
          for rep in range(3) for mode,seconds in cpu.items() for kind in ('drift','kick','step','trajectory')]
    body=dict(samples=rows,medians={kind:dict(cpu) for kind in ('drift','kick','step','trajectory')})
    return inputs,body


@pytest.mark.parametrize('fault',['missing','duplicate','median','result','final','zero_cpu','old_default_regression'])
def test_raw_evidence_fault_cannot_promote(fault):
    inputs,body=campaign();G.validate_benchmark(body,inputs)
    bad=copy.deepcopy(body)
    if fault=='missing':bad['samples'].pop()
    elif fault=='duplicate':bad['samples'].append(dict(bad['samples'][0]))
    elif fault=='median':bad['medians']['trajectory']['fast_pilot3']=1.0
    elif fault=='result':bad['samples'][0]['result']='different'
    elif fault=='final':next(r for r in bad['samples'] if r['workload']=='trajectory')['final_sha256']='different'
    elif fault=='zero_cpu':bad['samples'][0]['cpu_seconds']=0
    else:
        for r in bad['samples']:
            if r['mode']=='fast' and r['workload']=='trajectory':r['cpu_seconds']=1.0
        bad['medians']['trajectory']['fast']=1.0
    with pytest.raises(AssertionError):G.validate_benchmark(bad,inputs)


def test_saved_JSON_arrays_match_exact_tuple_endpoints():
    stored=dict(radius=[1,2],dV=[-3,4],inverse=[5,6])
    fresh=dict(radius=(1,2),dV=(-3,4),inverse=(5,6))
    G.validate_fixed(stored,fresh)


@pytest.mark.parametrize('field',['radius','dV','inverse'])
def test_saved_JSON_endpoint_corruption_refuses(field):
    stored=dict(radius=[1,2],dV=[-3,4],inverse=[5,6])
    fresh=dict(radius=(1,2),dV=(-3,4),inverse=(5,6))
    stored[field][1]+=1
    with pytest.raises(AssertionError):G.validate_fixed(stored,fresh)


@pytest.mark.parametrize('fault',[None,'default_mode','missing_mode','input_hash','steps','equality'])
def test_actual_producer_evidence_requires_all_modes_and_the_omitted_default(fault):
    inputs={'unit':dict(sha256='sealed',steps=3)}
    values=[dict(runtime_mode=m,steps=3,all_states_equal_old_raw_inputs=True) for m in G.MODES]
    row=dict(label='unit',source_sha256='sealed',values=values,default=dict(values[-1]))
    if fault=='default_mode':row['default']['runtime_mode']='fast'
    elif fault=='missing_mode':row['values'].pop()
    elif fault=='input_hash':row['source_sha256']='changed'
    elif fault=='steps':row['default']['steps']=2
    elif fault=='equality':row['values'][0]['all_states_equal_old_raw_inputs']=False
    if fault:
        with pytest.raises(AssertionError):G.validate_producer([row],inputs)
    else:G.validate_producer([row],inputs)


@pytest.mark.parametrize('fault',['missing','empty','missing_case'])
def test_live_manifest_cannot_omit_default_producer_gate(fault):
    from tools import c1b1_replay_benchmark as driver
    manifest=dict(producer_inputs={label:dict(sha256='sealed',steps=3) for label in driver.LABELS})
    assert G.require_producer_inputs(manifest,dict(kind='live'))==manifest['producer_inputs']
    if fault=='missing':del manifest['producer_inputs']
    elif fault=='empty':manifest['producer_inputs']={}
    else:manifest['producer_inputs'].pop(driver.LABELS[0])
    with pytest.raises(AssertionError):G.require_producer_inputs(manifest,dict(kind='live'))


def test_only_explicit_historical_checker_epoch_can_lack_new_default_schema():
    assert G.require_producer_inputs({},dict(kind='historical_checker_repair')) is None
    with pytest.raises(AssertionError):G.require_producer_inputs({},dict(kind='unknown'))
