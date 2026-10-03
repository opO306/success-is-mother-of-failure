"""Accepted/refused scientific records must survive packaging unchanged."""
import json,hashlib
from pathlib import Path
import numpy as np
import pytest
from electronic_pilot.frontend_reference_v0.audit import read,sha,verify

BASE=Path('docs/active/h2_adversarial_v0/evidence')

def main_root():
    return Path('/mnt/c/Users/zun24/성공은 실패의 어머니') if Path('/mnt/c').is_dir() else Path('C:/Users/zun24/성공은 실패의 어머니')

def test_all_previous_and_executed_phase_source_bytes_unchanged():
    seal=read(BASE/'conditioning_and_symmetry_diagnostic_v0_seal.json')
    assert verify(seal['bound_sha256'],Path.cwd(),main_root())==1178

def test_original_vector_and_failed_column_check_not_replaced():
    result=read(BASE/'symmetry.json')
    vector=Path('docs/active/h2_ground_state_audit_v0/evidence/v_direct_reproduced.npy')
    assert result['vector_sha256']==sha(vector)=='cfb1113166b72f050f3d2d8c24de6d9aa2b00a72f64f10d83c65470f2f8d35b6'
    assert (BASE/'initial_definition_failure.log').is_file()
    assert read(BASE/'initial_column_refusal.json')['ours']!=read(BASE/'initial_column_refusal.json')['external']

def test_strict_parity_failure_not_reclassified_pass():
    row=read(BASE/'symmetry.json')
    assert row['claimed_irrep'] is None and row['status'].startswith('UNRESOLVED')
    assert float(row['high_precision_residuals']['inversion_plus'])>row['existing_norm_guard']==1e-10
    assert not row['high_precision_AO_integrals']

def test_symmetry_convention_and_tail_evidence_separated():
    row=read(BASE/'symmetry_diagnostic.json')
    assert row['conventions']['inversion_function_values_max']==0
    assert float(row['inversion_tail']['odd_S_metric_norm_squared'])<1e-18
    assert row['inversion_tail']['diagnostic_only_not_recomputed_ground_state']

def test_cardinal_trend_actual_all_guards_and_replay():
    row=read(BASE/'summary.json');assert row['QZ_replay_energy_bitwise_equal']
    rows=[row['cardinal'][k] for k in ('DZ','TZ','QZ','V5Z')]
    assert all(x['accepted'] and x['failure_stage'] is None for x in rows)
    assert [x['total_energy_hartree'] for x in rows]==sorted([x['total_energy_hartree'] for x in rows],reverse=True)
    assert rows[2]['signed_reference_difference_hartree']>.001 and rows[3]['signed_reference_difference_hartree']<.001
    assert row['QZ44_status']=='FAIL unchanged' and row['certification']=='NOT CERTIFIED'

def test_uncontracted_first_guard_refusal_has_no_energy():
    row=read(BASE/'summary.json')['cardinal']['uncontracted_QZ']
    assert row['failure_stage']=='orthonormalization' and not row['accepted']
    assert row['total_energy_hartree'] is None and row['electronic_energy_hartree'] is None
    assert row['orthogonality_l2']>1e-10 and row['basis_size']==64

def test_independent_native_engine_disclosed_and_analytical_coverage():
    row=read(BASE/'native_execution_seal.json');assert 'Libint2' in row['engine']
    assert 'libcint' not in row['linkage'] and 'libcgto' not in row['linkage']
    assert row['screening_precision']==0 and not row['normalization_embedding']
    comp=read(BASE/'AO_comparison.json');assert comp['distinct_integral_implementations']
    assert comp['native']['ncart']==70 and comp['native']['null_ERI_blocks']==0
    assert comp['libint_vs_raw_libcint']['g']['max_absolute']<1e-12

def test_connected_factorial_refused_energy_not_reported():
    data=read(BASE/'factorial.json');rows=data['rows'];assert len(rows)==4
    assert [x['accepted'] for x in rows]==[True,False,False,False]
    assert all(row['electronic_energy_hartree'] is None for row in rows[1:])
    assert data['accepted_ground_energy_interaction_hartree'] is None
    E00,E01,E10,E11=[x['same_v_rayleigh_hartree'] for x in rows]
    assert E11-E10-E01+E00==data['same_v_rayleigh_interaction_hartree']

def test_measured_amplification_not_all_MO_accurate():
    row=read(BASE/'conditioning.json')['conditioning']
    assert row['AO_delta_S_max']<1e-14 and row['transformed_overlap_delta_l2']>1e-10
    assert read(BASE/'factorial.json')['rows'][0]['ERI_symmetry']['pair']['max_absolute']>1e-5

def test_reference_primary_inventory_and_lineage_not_counted_as_independent():
    ledger=read(BASE/'reference_ledger.json');assert ledger['status']=='REFERENCE_SIDE_UNRESOLVED'
    ndeke=ledger['sources'][2];path='runs/h2_adversarial_v0/reference_acquisition_v1/Ndeke_primary.pdf'
    assert ndeke['primary_pdf_sha256']==sha(path)
    assert ndeke['R04_BO_hartree']=='-0.1202303300' and 'shared numerical lineage' in ndeke['independence']
    assert ledger['sources'][1]['reported_R04_uncertainty'] is None

def test_hypothesis_ledger_all_causal_fields_and_falsifiable_statuses():
    row=read(BASE/'hypothesis_ledger.json')
    for h in row['hypotheses']:
        assert all(h[k] for k in ('candidate','mechanism','counterevidence','direct_test','connections'))
        assert h['status'] in row['allowed_statuses']

def test_packaged_summary_reconciles_with_actual_workers():
    row=read(BASE/'summary.json')
    for key in ('DZ','TZ','QZ','V5Z','uncontracted_QZ'):
        assert row['cardinal'][key]==read('runs/h2_adversarial_v0/cardinal_v0/'+key+'/result.json')
        assert (row['cardinal'][key]['runtime_seconds']>0) and row['cardinal'][key]['peak_rss_kib']>0
