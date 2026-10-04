"""Real controller semantics with deterministic synthetic electronic inputs."""
from pathlib import Path
import importlib.util
from .test_kit import point
from electronic_pilot.h2_multistep_v0.kit import persist,sha

def campaign():
    assert importlib.util.find_spec('electronic_pilot.h2_multistep_v0.campaign'),'campaign missing'
    return __import__('electronic_pilot.h2_multistep_v0.campaign',fromlist=['*'])

def test_five_steps_reuse_force_and_exactly_two_diagnostic_centers(tmp_path):
    calls=[];receipts=[]
    def call(index,label,requested):
        calls.append((index,label));row=point(requested)
        row['process']=dict(outer_wall_seconds=0.,measurement=dict(peak_rss_kib=1,wall_seconds=0.))
        return row
    def record(index,value):
        item=persist(tmp_path/f'step_{index}.json',value);receipts.append(item);return item
    result=campaign().run_segment(dict(R='1.5',P='0',F='-.2'),'2000','.01',call,record,'/snapshot')
    assert result['quick_ok'] and len(result['steps'])==5 and len(receipts)==5
    assert calls==[(i,label) for i in range(1,6) for label in (('left','right','center') if i in (3,5) else ('left','right'))]
    assert len(result['diagnostics'])==2 and [x['step_index'] for x in result['diagnostics']]==[3,5]
    assert all(x['state_status']=='SPECULATIVE' for x in result['steps'])
    for item in receipts:assert sha(item['path'])==item['sha256']

def test_hard_failure_stops_without_later_calls_or_retries(tmp_path):
    calls=[]
    def call(index,label,requested):
        calls.append((index,label));row=point(requested)
        row['process']=dict(outer_wall_seconds=0.,measurement=dict(peak_rss_kib=1,wall_seconds=0.))
        if index==2 and label=='left':row['accepted']=False
        return row
    result=campaign().run_segment(dict(R='1.5',P='0',F='-.2'),'2000','.01',call,
        lambda i,v:persist(tmp_path/f'step_{i}.json',v),'/snapshot')
    assert not result['quick_ok'] and len(result['steps'])==1
    assert calls==[(1,'left'),(1,'right'),(2,'left')]
    assert result['event']=='QUICK_KIT_TRIGGERED_STOP' and result['failed_step_index']==2

def test_final_audit_mismatch_cannot_publish(tmp_path):
    p=tmp_path/'source.py';p.write_bytes(b'first');bindings={str(p):sha(p)}
    assert campaign().full_audit(bindings,[])['passed']
    p.write_bytes(b'changed')
    result=campaign().full_audit(bindings,[])
    assert not result['passed'] and 'BYTE DRIFT' in result['failure']

def test_saved_step_byte_change_is_audit_failure(tmp_path):
    item=persist(tmp_path/'state.json',dict(R='1.5',P='0',F='-.2'))
    assert campaign().full_audit({},[item])['passed']
    Path(item['path']).write_text('{}',encoding='utf8')
    assert not campaign().full_audit({},[item])['passed']

def test_failed_step_keeps_incurred_call_cost_and_receipts(tmp_path):
    def call(index,label,requested):
        row=point(requested);row['process']=dict(outer_wall_seconds=2.,measurement=dict(peak_rss_kib=1,wall_seconds=2.))
        if index==2:row['accepted']=False
        return row
    result=campaign().run_segment(dict(R='1.5',P='0',F='-.2'),'2000','.01',call,
        lambda i,v:persist(tmp_path/f'step_{i}.json',v),'/snapshot')
    assert [x['electronic_pair_wall_seconds'] for x in result['timings']]==[4.,2.]
    assert result['timings'][-1]['completed'] is False

def test_per_step_center_encoding_without_center_electronic_call():
    from .test_kit import sample
    prev,state=sample()
    assert state['center_geometry']['actual_serialized_R']==1.4999
    assert state['center_geometry_status']=='SERIALIZATION_ONLY_NOT_ELECTRONICALLY_EVALUATED'

def test_nonzero_process_still_has_launch_cost_and_exit_receipt(tmp_path):
    import sys
    code="from pathlib import Path;Path('native.time').write_text('wall_seconds=0.01\\npeak_rss_kib=1\\n');raise SystemExit(7)"
    result=campaign().run_process([sys.executable,'-c',code],tmp_path)
    assert result['launched'] and result['exit']==7 and result['outer_wall_seconds']>0
    assert (tmp_path/'process.json').exists()
