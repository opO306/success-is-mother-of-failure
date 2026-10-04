"""Post-acquisition evidence checks; never runs electronic calculations."""
from pathlib import Path
import json
from decimal import Decimal as D,localcontext
from electronic_pilot.h2_multistep_v0.kit import quick,diagnostic_check,verify,sha,decide

DOC=Path('docs/active/h2_multistep_layered_v0')
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def data():return read(DOC/'protocol.json'),read(DOC/'results.json')
def snapshot_root(result):return result['controller_runtime_module_origins']['electronic_pilot.h2_multistep_v0.campaign'].split('/electronic_pilot/')[0]

def test_actual_five_added_steps_twelve_calls_and_no_C0_force_reexecution():
    q,r=data();s=r['segment']
    assert r['classification']=='H2_MULTISTEP_LAYERED_VALIDATION_PILOT_SUPPORTED'
    assert len(s['steps'])==5 and s['quick_ok'] and all(x['completed'] for x in s['timings'])
    expected=[[i,label] for i in range(1,6) for label in (('left','right','center') if i in (3,5) else ('left','right'))]
    assert r['actual_call_sequence']==expected and r['actual_electronic_calls']==r['electronic_results_completed']==12
    assert len(r['process_launches'])==12 and all(x['process']['launched'] and x['process']['exit']==0 for x in r['process_launches'])
    assert not r['C0_force_recalculated'] and [x['step_index'] for x in s['diagnostics']]==[3,5]
    previous=read('docs/active/h2_nuclear_1step_v0/results.json')
    assert q['C0']['R']==previous['R1_requested'] and q['C0']['P']==previous['P1'] and q['C0']['F']==previous['F1']

def test_actual_independent_chain_and_diagnostic_replay():
    q,r=data();previous=q['C0'];root=snapshot_root(r)
    for state in r['segment']['steps']:
        assert quick(previous,state,q['mass']['literal_value'],root)['status']=='QUICK_KIT_PASS'
        assert state['state_status']=='SPECULATIVE' and state['energy_conservation_tolerance'] is None
        assert D('1.2')<=D(state['R'])<=D('1.6')
        assert state['center_geometry_status']=='SERIALIZATION_ONLY_NOT_ELECTRONICALLY_EVALUATED'
        with localcontext() as ctx:
            ctx.prec=100
            half=D(previous['P'])+D(previous['F'])/2
            expected_R=D(previous['R'])+half/(D(q['mass']['literal_value'])/2)
            left,right=state['points']
            force=(D.from_float(left['total_energy_hartree'])-D.from_float(right['total_energy_hartree']))*5
            assert abs(D(state['P_half'])-half)<D('1e-75') and abs(D(state['R'])-expected_R)<D('1e-75')
            assert D(state['F'])==force and abs(D(state['P'])-(half+force/2))<D('1e-75')
        previous=state
    for checkpoint in r['segment']['diagnostics']:
        state=r['segment']['steps'][checkpoint['step_index']-1]
        assert diagnostic_check(state,checkpoint['point'],q['mass']['literal_value'],q['C0']['H_total'],checkpoint['values'],root)=='MEASURED_SCALAR_RECOMPUTATION_PASS'

def test_final_audit_and_explicit_authority_or_rollback():
    q,r=data()
    assert r['start_full_audit']['passed'] and r['end_full_audit']['passed'] and r['end_full_audit']['scalar_chain_replayed']==5
    d=read(DOC/'authority_decision.json')
    assert d['promoted'] and d['state_statuses']==['CONFIRMED']*5 and d['authoritative_state']==r['segment']['steps'][-1]
    failure=decide(q['C0'],r['segment']['steps'],False,True)
    assert not failure['promoted'] and failure['authoritative_state']==q['C0'] and failure['state_statuses']==['DISCARDED']*5
    assert failure['event']=='CAMPAIGN_POST_AUDIT_FAILED' and not failure['retry_performed']
    assert r['NOT_CERTIFIED'] and r['NOT_PRODUCTION_APPROVED'] and r['energy_conservation_tolerance'] is None

def test_preserved_history_snapshot_raw_state_and_published_point_hashes():
    q,r=data();snap=read(DOC/'snapshot_seal.json');end=read(DOC/'execution_seal.json')
    assert sha(DOC/'protocol.json')==snap['protocol_sha256']
    assert verify({**q['protected_sha256'],**q['implementation_sha256'],**snap['bound_sha256'],**end['bound_sha256']})>2500
    for item in r['segment']['receipts']:assert sha(item['path'])==item['sha256']
    assert (DOC/'C0.json').read_bytes()==Path(q['snapshot_root'],'config/c0.json').read_bytes()
    for row in r['new_calls']:
        assert read(DOC/f"point_{row['step_index']}_{row['label']}.json")==row
        assert row['numerical_guard_status']=='ACCEPTED'

def test_actual_cost_rss_scope_and_hypothetical_cadence_only():
    q,r=data();c=r['cost'];t=r['segment']['timings']
    pairs=[x['process']['outer_wall_seconds'] for x in r['process_launches'] if x['label'] in ('left','right')]
    assert abs(sum(pairs)-c['electronic_pair_seconds'])<1e-9
    assert c['raw_dynamics_seconds']>=c['electronic_pair_seconds']>0 and c['quick_kit_seconds']>0
    assert c['medium_check_seconds']>0 and c['final_checkpoint_seconds']>0
    assert c['full_audit_start_seconds']>0 and c['full_audit_end_seconds']>0 and c['other_seconds']>=0
    assert r['memory']['samples']>0 and r['memory']['workflow_sampled_aggregate_peak_rss_bytes']>0
    assert all(x['electronic_pair_peak_rss_kib']>0 for x in t)
    assert [x['K'] for x in r['cadence_model']]==[1,5,10,50,100] and r['final_K_selected'] is None
    assert all(x['maximum_discarded_steps']==x['K'] and not x['chosen'] for x in r['cadence_model'])
    for x in r['cadence_model']:assert x['amortized_audit_seconds_per_step']==c['full_audit_end_seconds']/x['K']
