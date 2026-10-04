"""Actual one-step evidence, independently replayed after acquisition."""
from decimal import Decimal as D,localcontext
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
from electronic_pilot.h2_nuclear_v0.check import check

DOC=Path('docs/active/h2_nuclear_1step_v0')


def read(path):return json.loads(Path(path).read_text(encoding='utf8'))


def test_actual_three_new_points_and_one_step():
    q=read(DOC/'protocol.json');r=read(DOC/'results.json')
    old=[read(p) for p in q['reuse_paths']]
    assert r['classification']=='H2_BO_NUCLEAR_1STEP_SUPPORTED'
    assert r['new_electronic_calls_completed']==3 and r['new_initial_electronic_calls']==0
    assert [x['label'] for x in r['new_points']]==['left','center','right']
    assert r['executed_steps']==1 and r['stop_after_one_step']
    assert check(r,old,r['new_points'],q['mass']['literal_value'])['status']=='SCALAR_AND_GEOMETRY_REPLAY_PASS'
    assert all(x['numerical_guard_status']=='ACCEPTED' for x in r['new_points'])


def test_actual_decimal_force_recomputation_and_measured_energy():
    q=read(DOC/'protocol.json');r=read(DOC/'results.json')
    left,center,right=r['new_points']
    with localcontext() as ctx:
        ctx.prec=100
        f1=(D.from_float(left['total_energy_hartree'])-D.from_float(right['total_energy_hartree']))*D(5)
        assert D(r['F1'])==f1
        p=(D(r['initial']['F0'])+f1)/2
        k=p*p/D(q['mass']['literal_value'])
        h=D.from_float(center['total_energy_hartree'])+k
        assert abs(D(r['H1'])-h)<D('1e-75')  # only arithmetic, no deltaH acceptance
        assert D(r['initial']['F0'])<0 and D(r['initial']['P_half'])<0 and D(r['F1'])<0 and D(r['P1'])<0
        assert D(r['R1_requested'])<D('1.5')
    assert r['energy_diagnostic_status']=='MEASURED' and r['energy_conservation_tolerance'] is None
    assert r['NOT_CERTIFIED'] and r['NOT_PRODUCTION_APPROVED']


def test_historical_source_and_current_capture_hashes_unchanged():
    q=read(DOC/'protocol.json');original=read(DOC/'execution_seal.json')
    seal=read(DOC/'execution_seal_rebound_v1.json');receipt=read(DOC/'seal_race_receipt.json')
    original_hash=hashlib.sha256((DOC/'execution_seal.json').read_bytes()).hexdigest()
    assert original_hash==seal['original_seal_sha256']==receipt['original_execution_seal_sha256']
    changed=[name for name,h in original['bound_sha256'].items() if seal['bound_sha256'][name]!=h]
    assert changed==[receipt['changed_binding']]
    assert receipt['numerical_and_source_bindings_changed']==[]
    partial=Path(receipt['partial_snapshot']).read_bytes()
    assert len(partial)==receipt['partial_snapshot_bytes']==0
    assert hashlib.sha256(partial).hexdigest()==receipt['partial_original_sha256']==original['bound_sha256'][changed[0]]
    assert hashlib.sha256(Path(changed[0]).read_bytes()).hexdigest()==receipt['full_completed_log_sha256']==seal['bound_sha256'][changed[0]]
    bindings={**q['protected_sha256'],**q['implementation_sha256'],**q['preflight_sha256'],**seal['bound_sha256']}
    for name,h in bindings.items():
        with Path(name).open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==h,name
    assert hashlib.sha256((DOC/'protocol.json').read_bytes()).hexdigest()==read(DOC/'protocol_seal.json')['sha256']


def test_literal_mass_and_nonhidden_geometry_rounding():
    q=read(DOC/'protocol.json');r=read(DOC/'results.json')
    mass=q['mass']
    assert mass['literal_value']=='1836.152673426' and mass['local_pilot_only']
    assert mass['literal_fingerprint_sha256']==hashlib.sha256(mass['literal_value'].encode('ascii')).hexdigest()
    assert D(r['initial']['mu'])==D('918.076336713')
    for x in r['new_points']:
        g=x['geometry']
        assert D(g['actual_R_exact_decimal'])==D.from_float(g['actual_serialized_R'])
        assert g['R_rounding_delta']!='0'
        assert x['actual_stored_positions_bohr']==g['positions_bohr']
        assert sum(Q.from_float(z[2]) for z in x['actual_stored_positions_bohr'])==0


def test_measured_memory_and_incremental_vs_estimated_cold_start():
    r=read(DOC/'results.json')
    assert r['memory_samples']>0 and r['workflow_sampled_aggregate_peak_rss_bytes']>r['controller_sampled_peak_rss_bytes']>0
    assert all(x['process']['measurement']['peak_rss_kib']>0 for x in r['new_points'])
    assert r['incremental_one_step_wall_seconds']>=r['new_electronic_process_wall_sum_seconds']
    assert r['validation_wall_seconds']>0 and r['scalar_integration_wall_seconds']>0
    c=r['cold_start_equivalent']
    assert c['status'].startswith('ESTIMATED_FROM_PREVIOUS_MEASURED')
    assert c['initial_three_process_wall_seconds']==86.48
    assert c['equivalent_wall_seconds']==c['initial_three_process_wall_seconds']+r['incremental_one_step_wall_seconds']
