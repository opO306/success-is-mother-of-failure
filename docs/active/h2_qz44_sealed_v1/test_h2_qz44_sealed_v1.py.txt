"""Fault injection in independent full-grid comparison and source binding."""
import ast
import copy
import csv
import json
from pathlib import Path
import pytest
from electronic_pilot.qz44_sealed_v1.compare import assess
from electronic_pilot.qz44_sealed_v1.seal import sha,verify


def panel():
    parent=json.loads(Path('electronic_pilot/protocol_v2.json').read_text());numeric=json.loads(Path('electronic_pilot/ao_micro_v0/protocol.json').read_text())
    with Path('electronic_pilot/reference_pachucki_v2.csv').open() as f: ref=list(csv.DictReader(f))
    rows=[]
    for entry in ref:
        r=float(entry['R_bohr']);e=float(entry['total_energy_hartree'])
        row=dict(basis='cc-pVQZ',basis_size=60,singlet_dimension=1830,electrons=2,sector='singlet',accepted=True,failure_stage=None,
            total_energy_hartree=e,electronic_energy_hartree=e-1/r,nuclear_repulsion_hartree=1/r,Smin=1e-5,
            orthogonality_l2=1e-12,singlet_asymmetry=1e-15,eigen_residual_l2=1e-14,vector_norm_error=1e-15)
        rows.append(dict(R_bohr=r,paths=[row],source_seal_valid=True,AO=dict(lower_representatives_match_raw=True)))
    control=dict(source='synthetic comparison input',R_bohr=1.4,total_energy_hartree=rows[10]['paths'][0]['total_energy_hartree'])
    return rows,ref,[control],parent['R_grid_bohr'],numeric['guards'],parent['criteria'],numeric['control_energy_max_difference'],control['total_energy_hartree']


def test_all_44_required_and_pointwise_reference():
    args=panel();out=assess(*args)
    assert out['numerical_pass'] and out['accepted']==44 and not out['failed_points']
    args[0][0]['paths'][0]['total_energy_hartree']+=.0011
    out=assess(*args)
    assert not out['numerical_pass'] and out['reference_exceeding_R_bohr']==[.4]


@pytest.mark.parametrize('fault',['refusal','control','dimension','sector','nan','orth','H','eigen','norm','floor','source','representative','missing','duplicate'])
def test_gate_faults(fault):
    args=panel();rows=args[0];row=rows[10]['paths'][0]
    if fault=='refusal': row.update(accepted=False,failure_stage='orthonormalization',total_energy_hartree=None)
    elif fault=='control': row['total_energy_hartree']+=1e-6
    elif fault=='dimension': row['basis_size']=59
    elif fault=='sector': row['sector']='triplet'
    elif fault=='nan': row['total_energy_hartree']=float('nan')
    elif fault=='orth': row['orthogonality_l2']=2e-10
    elif fault=='H': row['singlet_asymmetry']=2e-10
    elif fault=='eigen': row['eigen_residual_l2']=2e-9
    elif fault=='norm': row['vector_norm_error']=2e-10
    elif fault=='floor': row['Smin']=1e-11
    elif fault=='source': rows[10]['source_seal_valid']=False
    elif fault=='representative': rows[10]['AO']['lower_representatives_match_raw']=False
    elif fault=='missing': rows.pop()
    elif fault=='duplicate': rows[-1]=copy.deepcopy(rows[0])
    if fault in ('refusal','control'): assert not assess(*args)['numerical_pass']
    else:
        with pytest.raises(ValueError): assess(*args)


def test_inclusive_original_reference_boundary():
    args=panel();rows=args[0]
    from decimal import Decimal
    e=Decimal(args[1][0]['total_energy_hartree'])+Decimal('.001')
    rows[0]['paths'][0]['total_energy_hartree']=float(e)
    # Use a decimal-exact boundary at a zero-valued synthetic reference entry.
    args[1][0]['total_energy_hartree']='0';rows[0]['paths'][0]['total_energy_hartree']=.001
    assert assess(*args)['numerical_pass']


def test_source_drift_is_refused(tmp_path):
    p=tmp_path/'source';p.write_bytes(b'original');bound={str(p):sha(p)}
    verify(bound);p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='SEAL DRIFT'): verify(bound)


def test_comparison_imports_no_calculation_path():
    tree=ast.parse(Path('electronic_pilot/qz44_sealed_v1/compare.py').read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):
            assert not any(x in (node.module or '') for x in ('ao_micro','solver','numpy','pyscf','numerical_cause'))
