import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'docs/active/electronic_compressibility_hotline_v1'


def read(name):return json.loads((E/name).read_text(encoding='utf-8'))


def test_primary_capture_byte_closure():
    for name,value in read('closure.json')['files'].items():
        assert hashlib.sha256((E/name).read_bytes()).hexdigest()==value
    assert read('closure.json')['sources_unchanged']
    for name,value in read('execution_seal.json')['source'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value


@pytest.mark.parametrize('key',['A','B'])
def test_original_corpus_unchanged(key):
    base=ROOT/'docs/active/electronic_representation_survey_v1'
    old=read('execution_seal.json')['corpus_sources'][key]
    assert hashlib.sha256((base/(key+'_corpus.npz')).read_bytes()).hexdigest()==old['corpus']
    assert hashlib.sha256((base/(key+'_contract.json')).read_bytes()).hexdigest()==old['contract']


@pytest.mark.parametrize('key',['A','B'])
@pytest.mark.parametrize('state',['ground','excited','plus','minus','global_phase'])
@pytest.mark.parametrize('gauge',['original_MO','energy_MO','position_z_eigenbasis'])
def test_rank_error_ledger(key,state,gauge):
    rows=[r for r in read('tensor_rows.json')[key] if r['state']==state and r['gauge']==gauge]
    for t in [0.,.5,1.]:
        for cut in [7,14,21]:
            group=sorted([r for r in rows if r['time']==t and r['cut']==cut],key=lambda r:r['chi'])
            assert len(group)==7
            assert all(r['chi_used']<=r['chi'] for r in group)
            assert all(r['discarded_weight']==pytest.approx(r['discarded_norm']**2,abs=1e-12) for r in group)
            assert all(r['discarded_weight']>=r['unconstrained_discarded_weight']-1e-12 for r in group)
            assert all(r['metrics']['state_error_S']==pytest.approx(r['discarded_norm'],abs=1e-10) for r in group)
            assert all(r['future_metrics']['state_error_S']<=r['future_state_error_bound']+1e-10 for r in group)
            assert all(r['metrics']['energy_error']<=r['energy_error_bound']+1e-9 for r in group)
            assert all(r['metrics']['dipole_error']<=r['dipole_error_bound']+1e-9 for r in group)
            assert all(a['discarded_weight']>=b['discarded_weight']-1e-12 for a,b in zip(group,group[1:]))
            assert group[-1]['meets_inherited_tolerances']


def test_separate_occupation_checker():
    r=read('tensor_independent_schmidt_checks.json')
    assert len(r)==90
    assert max(max(x['error'],x['tail']) for x in r)<1e-10


@pytest.mark.parametrize('key',['A','B'])
def test_dense_restored_phase_remains_distinct(key):
    rows=[r for r in read('tensor_phase_distinction.json') if r['corpus']==key and r['chi']==32]
    assert len(rows)==9
    assert all(r['future_dipole_difference']>.1 for r in rows)


def test_complete_baseline_paths():
    rows=read('results.json')['baseline']
    assert len(rows)==90 and all(r['canonical_bits_equal_REF'] for r in rows)
    assert all(r['cost']['checks']==(12 if r['corpus']=='A' else 21) for r in rows)
    assert all(r['cost']['monitor_full_component_reads']==(84 if r['corpus']=='A' else 1218) for r in rows)


@pytest.mark.parametrize('key',['A','B'])
@pytest.mark.parametrize('path',['REF','BASELINE','HOTLINE'])
def test_actual_next_round_corridor(key,path):
    r=next(r for r in read('live_cost_results.json') if r['corpus']==key and r['path']==path)
    assert len(r['independent_live_corridor'])==45
    assert all(x['canonical_bits_equal_dense'] and max(x['independent_metrics'].values())<1e-9 for x in r['independent_live_corridor'])
    assert len(r['cpu_samples'])==5 and r['cost_medians']['engine_cpu']>0
    assert r['observed_peak_RSS_bytes']>=r['initial_RSS_bytes']


def test_all_required_mutations_detected():
    rows=read('controls_and_mutations.json')['mutations']
    assert len(rows)==9 and all(x['caught'] for x in rows)


def test_scope_and_classification_are_not_promotion():
    r=read('results.json')
    assert r['tensor']['A']['classification']=='CONDITIONAL'
    assert r['tensor']['B']['classification']=='POOR'
    assert 'NOT_PRODUCTION' in r['scope'] and 'NOT_CERTIFIED' in r['scope']


def test_postrun_policy_binding_rejects_unapproved_threshold():
    from electronic_pilot.compressibility_hotline import policy_check
    p=json.loads((ROOT/'electronic_pilot/compressibility_hotline/protocol.json').read_text())
    special=read('controls_and_mutations.json')['controls'][6]
    with pytest.raises(ValueError,match='policy binding'):policy_check.control(special,p)
    assert policy_check.control(special,p,expected={'enter':.02,'exit':.002,'safety':.008})


def test_live_and_policy_source_seals():
    live=ROOT/'electronic_pilot/compressibility_hotline/live_cost.py'
    policy=ROOT/'electronic_pilot/compressibility_hotline/policy_check.py'
    assert hashlib.sha256(live.read_bytes()).hexdigest()==read('live_cost_seal.json')['source_sha256']
    assert hashlib.sha256(policy.read_bytes()).hexdigest()==read('policy_binding_seal.json')['source_sha256']


def test_primary_and_extra_policy_results_remain_separate():
    value=read('policy_binding_results.json')
    assert value['primary_control_checker_trusted_receipt_thresholds']
    assert value['normal_policy_mutation_rejected']=='threshold policy binding'
    assert value['normal_controls_pass']==6 and value['explicitly_sealed_safety_probe_pass']
