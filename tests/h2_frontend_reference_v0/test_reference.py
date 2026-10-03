"""Fault injection at the controlling definition/uncertainty gates."""
import copy
from decimal import Decimal
from pathlib import Path
import pytest
from electronic_pilot.frontend_reference_v0.audit import (
    contract, crosscheck, downstream, parenthetical, read, sha, transcription, verify)

ROOT=Path(__file__).resolve().parents[2]
MANUAL=read(ROOT/'electronic_pilot/frontend_reference_v0/primary_transcriptions.json')


def sources():
    return copy.deepcopy(MANUAL['Pachucki']), copy.deepcopy(MANUAL['Sims_Hagstrom'])


def stored():
    return dict(R_bohr='0.4',total_energy_hartree='-0.120230341178823',
                published_uncertainty_hartree='0.000000000000015')


def test_last_digit_uncertainty_is_not_printing_precision():
    value,uncertainty=parenthetical('-0.120230341178823(15)')
    assert value==Decimal('-0.120230341178823')
    assert uncertainty==Decimal('1.5e-14')


@pytest.mark.parametrize('text',['-0.12','-0.12(unknown)','0.12(1) extra'])
def test_unreported_uncertainty_cannot_be_parsed_as_zero(text):
    with pytest.raises(ValueError): parenthetical(text)


@pytest.mark.parametrize('field,value',[
    ('total_energy_hartree','-0.120230341178824'),
    ('published_uncertainty_hartree','0.0000000000000015'),
    ('R_bohr','3.3')])
def test_faulty_energy_uncertainty_or_wrong_table_pair_is_refused(field,value):
    row=stored();row[field]=value
    assert transcription(sources()[0],row)['status']=='REFERENCE_TRANSCRIPTION_ERROR_CONFIRMED'


def test_disconnected_manual_expansion_does_not_pass():
    first,_=sources();first['energy_hartree']='-0.120230341178824'
    with pytest.raises(ValueError,match='manual'): transcription(first,stored())


@pytest.mark.parametrize('field,value',[
    ('nuclear_repulsion','none'),('quantity','E_electronic'),('R_unit','angstrom'),
    ('finite_mass',True),('QED',True),('spin_S',1)])
def test_definition_fault_is_detected_before_numerical_crosscheck(field,value):
    first,_=sources();ours=copy.deepcopy(MANUAL['ours_contract']);ours[field]=value
    result=contract(ours,first['contract'])
    assert result['status']=='COMPARISON_CONTRACT_MISMATCH_CONFIRMED'
    assert field in result['differences']


def test_missing_definition_has_no_default_pass():
    first,_=sources();ours=copy.deepcopy(MANUAL['ours_contract']);del ours['fixed_nuclei']
    assert contract(ours,first['contract'])['status']=='COMPARISON_CONTRACT_UNRESOLVED'


def test_larger_singlet_space_is_disclosed_without_false_mismatch():
    first,_=sources();result=contract(MANUAL['ours_contract'],first['contract'])
    assert result['status']=='PHYSICAL_QUANTITY_MATCH_SUPPORTED'
    assert result['identical_trial_spaces'] is False
    assert result['observed_state_spatial_irrep']=='NOT_INDEPENDENTLY_CHECKED'


def test_numerically_close_does_not_pass_unknown_uncertainty():
    result=crosscheck(*sources())
    assert Decimal(result['second_minus_first_hartree'])==Decimal('9.586e-13')
    assert result['status']=='REFERENCE_SIDE_UNRESOLVED'
    assert result['within_reported_uncertainty'] is None
    assert result['meaningful_reference_disagreement'] is False


@pytest.mark.parametrize('manufactured',['1e-12','285.9e-12','5e-17'])
def test_another_R_contribution_or_printing_digits_are_not_a_reported_uncertainty(manufactured):
    first,second=sources();second['uncertainty_hartree']=manufactured
    assert crosscheck(first,second)['within_reported_uncertainty'] is None


def test_another_R_reported_bound_cannot_close_R04():
    first,second=sources();second.update(uncertainty_hartree='1e-12',
                                      reported_pointwise_uncertainty=True,uncertainty_R_bohr='1.4')
    assert crosscheck(first,second)['status']=='REFERENCE_SIDE_UNRESOLVED'


def test_same_lineage_preprint_is_not_independent():
    first,second=sources();second['calculation_lineage']=first['calculation_lineage']
    assert crosscheck(first,second)['reason']=='same calculation lineage'


def test_reported_bounds_gate_behavior_on_synthetic_independent_data():
    first,second=sources();second.update(uncertainty_hartree='1e-12',
                                      reported_pointwise_uncertainty=True,uncertainty_R_bohr='0.4')
    assert crosscheck(first,second)['status']=='REFERENCE_CROSSCHECK_SUPPORTED'
    second['uncertainty_hartree']='1e-14'
    result=crosscheck(first,second)
    assert result['status']=='REFERENCE_SIDE_UNRESOLVED'
    assert result['meaningful_reference_disagreement'] is True


def test_open_reference_gate_blocks_every_downstream_stage():
    first,second=sources()
    result=downstream(transcription(first,stored()),contract(MANUAL['ours_contract'],first['contract']),
                      crosscheck(first,second))
    assert all(value['status']=='NOT_EXECUTED' for value in result.values())


def test_byte_fault_is_detected(tmp_path):
    path=tmp_path/'historic';path.write_bytes(b'preserve')
    bindings={'worktree:historic':sha(path)}
    assert verify(bindings,tmp_path,tmp_path)==1
    path.write_bytes(b'edited')
    with pytest.raises(ValueError,match='BYTE DRIFT'): verify(bindings,tmp_path,tmp_path)


def test_audit_imports_no_electronic_evaluator():
    import ast
    tree=ast.parse((ROOT/'electronic_pilot/frontend_reference_v0/audit.py').read_text(encoding='utf-8'))
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    imports += [alias.name for n in ast.walk(tree) if isinstance(n,ast.Import) for alias in n.names]
    assert not any(name and name.startswith(('pyscf','numpy','scipy','electronic_pilot.solver',
                                            'electronic_pilot.numerical_cause')) for name in imports)
