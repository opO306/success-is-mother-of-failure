"""Post-run evidence checks, independently accumulating saved term records."""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest

ROOT=Path('docs/active/h2_ci_layer_audit_v0/evidence')


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def terms_value(detail):
    terms=detail['terms']
    exact=sum((Fraction(row['input'])*Fraction(row['coefficient']) for row in terms),Fraction())
    power=terms[0]['sqrt2_denominator_power'] if terms else 0
    with localcontext() as ctx:
        ctx.prec=110
        return float(Decimal(exact.numerator)/Decimal(exact.denominator)/(Decimal(2).sqrt()**power))


def validate_counter(counter):
    expected=terms_value(counter['independent_breakdown'])
    assert abs(expected-counter['independent_SC'])<1e-14
    assert abs(expected-counter['existing_direct_pair'])<1e-14
    assert abs(counter['spin_free_unpacked_value']-expected)<1e-14
    assert abs(counter['spin_free_packed_value']-counter['prior_action'])<1e-14
    assert abs(counter['prior_action']-expected)>1e-10


def test_physical_basis_mapping_and_original_order_difference():
    mapping=read('basis_mapping.json')
    assert mapping['status']=='MATCH'
    assert set(mapping['dimensions'].values())=={1830}
    assert set(mapping['unique'].values())=={1830}
    assert not any(mapping['duplicates'].values())
    assert not any(mapping['missing'].values()) and not mapping['unmappable']
    rows=mapping['rows'];assert len({tuple(x['pair']) for x in rows})==1830
    assert any(x['A_index']!=x['prior_lower_index'] for x in rows)


def test_selected_classes_and_exact_stored_terms():
    audit=read('matrix_elements.json');assert audit['status']=='AGREE'
    assert len(audit['rows'])==8 and audit['max_absolute_difference']<1e-10
    for row in audit['rows']:
        expected=terms_value(row['breakdown'])
        assert abs(expected-row['independent'])<1e-14
        assert abs(row['existing']-expected)<1e-10
        assert abs(row['prior_direct_pair']-expected)<1e-10
    zero=[x for x in audit['rows'] if 'expected zero' in x['class']]
    assert len(zero)==2 and all(x['existing']==x['independent']==0 for x in zero)


def test_submatrix_and_single_column_disagreement():
    sub=read('submatrix.json');assert sub['size']==12 and sub['mismatch_count']==0
    assert sub['canonical_states']==sorted(sub['canonical_states'])
    assert sub['max_absolute_difference']<1e-10
    with np.load(ROOT/'matvec_single.npz') as arrays:
        a=arrays['existing_direct_pair'];b=arrays['independent_SC'];prior=arrays['prior_determinant_action']
    assert len(a)==len(b)==len(prior)==1830
    assert max(abs(a-b))<1e-10 and sum(abs(prior-b)>1e-10)==19
    record=read('matvec.json')['vectors'][0]
    assert float(max(abs(prior-b)))==record['prior_action_vs_independent_max']


def test_counterexample_terms_and_localized_packing_layer():
    counter=read('counterexample.json');validate_counter(counter)
    assert counter['bra']==[39,50] and counter['ket']==[50,50]
    assert not counter['no_repair_applied'] is False
    reduced=read('counterexample_reduction.json')
    assert len(reduced['dominant_changed_K_entries'])==3
    assert abs(reduced['prediction_minus_observed'])<1e-14
    exact=sum((Fraction(x['forward'])-Fraction(x['reverse']) for x in reduced['trace_terms']),Fraction())
    assert exact==Fraction(reduced['trace_difference_exact'])


@pytest.mark.parametrize('fault',['sign','normalization','one_electron','old_action'])
def test_counterexample_fault_injections(fault):
    counter=deepcopy(read('counterexample.json'))
    if fault=='sign': counter['independent_breakdown']['terms'][0]['coefficient']='-1'
    elif fault=='normalization':
        for term in counter['independent_breakdown']['terms']:term['sqrt2_denominator_power']=0
    elif fault=='one_electron':counter['independent_breakdown']['terms'][0]['input']+=.001
    else:counter['prior_action']=counter['independent_SC']
    with pytest.raises(AssertionError):validate_counter(counter)


def test_stop_preserves_gate_and_does_not_eigensolve():
    summary=read('summary.json');action=read('matvec.json')
    assert summary['classification']=='CI_CONSTRUCTION_MISMATCH_CONFIRMED'
    assert summary['failure_stage']=='prior_determinant_action' and summary['valid_approaches']==1
    assert len(action['vectors'])==1 and action['not_executed']==['few_sparse','mixed_sign']
    assert read('eigensolver.json')['status']=='NOT_EXECUTED'
    assert read('preservation.json')['all_bound_bytes_unchanged']
    gate=Path('docs/active/h2_qz44_sealed_v1/gate.json')
    results=Path('docs/active/h2_qz44_sealed_v1/results.json')
    assert hashlib.sha256(gate.read_bytes()).hexdigest()=='02c5b4625f835f46aa247b7bd53d2909d1c92c212d74199cdd98507ee4b27ed0'
    assert hashlib.sha256(results.read_bytes()).hexdigest()=='9564be2e8e23c2dbbb39bd0a9f5eb854ce888a2337ce398c5927a003a5dc0baf'


def test_physical_sealed_source_and_compact_record_bytes_unchanged():
    seal=read('preparation_seal.json')
    for name,digest in seal['source_sha256'].items():
        # The physical worker recorded Linux absolute paths. Bind the same
        # repository-relative files on both platforms, retaining sealed bytes.
        if name.startswith('/mnt/c/'):
            name='electronic_pilot/ci_layer_audit_v0/'+name.split('/electronic_pilot/ci_layer_audit_v0/',1)[1]
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    manifest=read('artifact_manifest.json')
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((ROOT/name.replace('\\','/')).read_bytes()).hexdigest()==digest
