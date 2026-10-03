"""Portable readback of the actual run, provenance, and historical regression."""
import hashlib
import json
from pathlib import Path
from decimal import Decimal
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/active/h2_ground_state_audit_v0/evidence'


def read(name):
    return json.loads((DATA/name).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_sources_and_existing_guard_identity():
    seal=read('execution_seal.json')
    assert seal['Git']['HEAD']==seal['spec']['base_commit']=='fad6df112a6b9351c577831a3980f38332053858'
    for name in ['operator.py','run.py','replay.py','io.py','protocol.json','DERIVATION.md','seal.py']:
        path='electronic_pilot/ground_state_audit_v0/'+name
        assert digest(ROOT/path)==seal['bound_sha256']['worktree:'+path]
    old=json.loads((ROOT/'electronic_pilot/ao_micro_v0/protocol.json').read_text(encoding='utf-8'))
    assert seal['guards']==old['guards']
    assert seal['energy_agreement']==1e-9
    assert digest(ROOT/'electronic_pilot/solver.py')==seal['builder_sha256']


def test_replay_bitwise_energy_and_vector_provenance():
    replay=read('replay.json');seal=read('execution_seal.json')
    assert replay['status']=='REPLAY_INPUT_ACCEPTED' and replay['energy_bitwise_equal']
    assert float(replay['E_direct']).hex()==float(replay['E_replayed']).hex()==replay['archived_energy_hex']
    assert replay['residual_l2']<=seal['guards']['eigen_l2_max']
    assert replay['vector_norm_error']<=seal['guards']['norm_max']
    assert replay['archived_next_singlet_gap'] is None and 'UNAVAILABLE' in replay['gap_comparison']
    assert replay['next_singlet_gap']>seal['energy_agreement']
    assert 'REPRODUCED_FROM_SEALED_REPLAY' in replay['provenance']
    p=DATA/'v_direct_reproduced.npy';v=np.load(p,allow_pickle=False)
    assert v.shape==(1830,) and v.dtype.str=='<f8' and replay['vector']['byte_order']=='little'
    assert digest(p)==replay['vector']['file_sha256']
    assert hashlib.sha256(v.tobytes()).hexdigest()==replay['vector']['array_sha256']
    assert p.read_bytes()==(DATA/'v_direct_canonical.npy').read_bytes()


def test_complete_canonical_mapping_has_no_missing_or_duplicate_state():
    mapping=read('basis_mapping.json');pairs=[tuple(x['pair']) for x in mapping['rows']]
    assert mapping['status']=='MATCH' and mapping['dimensions']==1830 and mapping['duplicate_missing_extra']==0
    assert pairs==sorted(set(pairs)) and set(pairs)=={(i,j) for i in range(60) for j in range(i,60)}
    for i,row in enumerate(mapping['rows']):
        assert row['canonical_index']==row['direct_index']==i and row['S']==row['Ms']==0
        assert sum(x[1] for x in row['occupation'])==2
        assert row['normalization']==('closed_unit' if row['pair'][0]==row['pair'][1] else 'open_1_over_sqrt2')


def test_stage_a_full_action_artifacts_and_maximum_component():
    a=read('stage_A.json');seal=read('execution_seal.json')
    v=np.load(DATA/'v_direct_canonical.npy',allow_pickle=False)
    action=np.load(DATA/'H_SC_v_direct.npy',allow_pickle=False)
    delta=np.load(DATA/'stage_A_residual.npy',allow_pickle=False)
    energy=read('replay.json')['E_direct']
    assert np.array_equal(delta,action-energy*v)
    index=int(abs(delta).argmax())
    assert index==a['maximum_index']==2 and a['maximum_state']['pair']==[0,2]
    assert delta[index]==a['difference'] and max(abs(delta))==a['linf']
    assert np.linalg.norm(delta)<=seal['guards']['eigen_l2_max']
    assert a['hamiltonian_asymmetry']<=seal['guards']['H_asym_max']
    assert a['classification']=='GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED'
    rayleigh=float(v@action/(v@v))
    assert abs(rayleigh-a['rayleigh_quotient'])<1e-14


def test_independent_full_spectrum_residual_and_overlap():
    b=read('stage_B.json');seal=read('execution_seal.json')
    energies=np.load(DATA/'E_independent_all.npy',allow_pickle=False)
    assert len(energies)==1830 and np.all(energies[1:]>=energies[:-1])
    assert energies[0]==b['E_independent']
    assert b['absolute_difference']==abs(b['E_independent']-b['E_direct'])<=seal['energy_agreement']
    assert b['classification']=='INDEPENDENT_GROUND_STATE_ENERGY_SUPPORTED'
    assert not b['hint_vector_used'] and not b['shift_or_energy_target_used']
    assert b['lowest_cluster_dimension_at_existing_band']==1
    v=np.load(DATA/'v_direct_reproduced.npy',allow_pickle=False)
    w=np.load(DATA/'v_independent.npy',allow_pickle=False)
    assert abs(float(abs(v@w))-b['overlap_absolute'])<1e-14
    assert abs(w@w-1)<=seal['guards']['norm_max']
    delta=np.load(DATA/'stage_B_residual.npy',allow_pickle=False)
    assert np.linalg.norm(delta)<=seal['guards']['eigen_l2_max']
    assert b['canonical_input_unchanged_after_solve']
    assert 'numpy.linalg.eigh' in b['driver'] and '_syevd' in b['driver']


def test_regression_values_and_old_counterexample_bytes_remain():
    regression=read('regression_preservation.json')
    old=ROOT/'docs/active/h2_ci_layer_audit_v0/evidence/counterexample.json'
    assert digest(old)==regression['source_sha256']
    record=json.loads(old.read_text(encoding='utf-8'))
    for key,value in regression['immutable_prior_values'].items():
        assert record[key]==value
    assert record['existing_direct_pair']==-4.231303534059128
    assert record['independent_SC']==-4.231303534059129
    assert record['prior_action']==-4.231297967351358
    assert abs(regression['new_minus_frozen_SC'])<=read('execution_seal.json')['guards']['H_asym_max']
    assert regression['old_invalid_action_not_repaired'] and regression['prior_counterexample_not_overwritten']


def test_physical_comparison_is_separate_and_old_fail_criterion_remains():
    result=read('physical_comparison.json');seal=read('postcomparison_seal.json')
    assert seal['after_stage_A_and_B'] and seal['reference_not_used_in_CI']
    assert digest(DATA/'stage_A.json')==seal['input_sha256']['Stage_A']
    assert digest(DATA/'stage_B.json')==seal['input_sha256']['Stage_B']
    assert Decimal(result['original_criterion'])==Decimal('.001')
    assert Decimal(result['direct_signed_difference'])>Decimal('.001')
    assert Decimal(result['independent_signed_difference'])>Decimal('.001')
    assert not result['direct_within_criterion'] and not result['independent_within_criterion']
    assert result['no_basis_cause_inference']


def test_raw_manifest_readback_and_stop_boundary():
    manifest=read('raw_manifest.json')
    for name,record in manifest['files'].items():
        if record['committed_as_compact_evidence']:
            path=DATA/name
            assert digest(path)==record['sha256'] and path.stat().st_size==record['bytes']
    summary=read('summary.json');preservation=read('preservation.json')
    assert preservation['protected_bindings_checked']==972 and preservation['preceding_inherited_bindings']==910
    assert summary['not_certified'] and summary['designer_decision_required'] and summary['stop']
    assert summary['QZ44_gate']=='NUMERICAL FAIL unchanged' and len(summary['unresolved'])==4
