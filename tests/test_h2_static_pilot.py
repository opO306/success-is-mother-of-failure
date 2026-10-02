"""Dependency-light structural/fault tests; no PySCF installation needed."""
import ast
import copy
import csv
import json
from pathlib import Path

import numpy as np
import pytest

from electronic_pilot.solver import singlet_matrix, validate
from electronic_pilot.check_reference import compare

ROOT = Path(__file__).resolve().parents[1]


def test_singlet_projection_against_fermionic_operator_spectrum():
    # Different construction: explicit creation/annihilation signs in four
    # spin orbitals, compared with singlet plus the spatial triplet spectrum.
    h = np.array([[-.8, .13], [.13, -.3]])
    pair = {(0,0):0,(0,1):1,(1,0):1,(1,1):2}
    g = np.array([[.6,.2,.1],[.2,.5,.1],[.1,.1,.4]])
    eri = np.empty((2,)*4)
    for p,q,r,s in np.ndindex((2,)*4):
        eri[p,q,r,s]=g[pair[p,q],pair[r,s]]
    dets=[(1<<(2*a))|(1<<(2*b+1)) for a in range(2) for b in range(2)]
    matrix=np.zeros((4,4))
    def act(mask, operators):
        sign=1
        for orb, create in operators:
            occupied=bool(mask & (1<<orb))
            if occupied==create:
                return None,0
            if (mask & ((1<<orb)-1)).bit_count()%2:
                sign=-sign
            mask ^= 1<<orb
        return mask,sign
    for j,det in enumerate(dets):
        for p,q in np.ndindex((2,2)):
            for spin in range(2):
                end,sign=act(det,[(2*q+spin,False),(2*p+spin,True)])
                if end in dets:
                    matrix[dets.index(end),j]+=h[p,q]*sign
        for p,q,r,s in np.ndindex((2,)*4):
            for alpha,beta in np.ndindex((2,2)):
                end,sign=act(det,[(2*q+alpha,False),(2*s+beta,False),
                                   (2*r+beta,True),(2*p+alpha,True)])
                if end in dets:
                    matrix[dets.index(end),j]+=.5*eri[p,q,r,s]*sign
    singlet,*_=singlet_matrix(h,eri)
    triplet=h[0,0]+h[1,1]+eri[0,0,1,1]-eri[0,1,1,0]
    np.testing.assert_allclose(np.linalg.eigvalsh(matrix),
                               np.sort(np.r_[np.linalg.eigvalsh(singlet),triplet]),atol=1e-14)


def test_noninteracting_electrons_fill_lowest_orbital():
    h=np.array([[-.7,.2],[.2,.1]])
    mat,*_=singlet_matrix(h,np.zeros((2,)*4))
    e=np.linalg.eigvalsh(h)
    np.testing.assert_allclose(np.linalg.eigvalsh(mat),[2*e[0],e.sum(),2*e[1]],atol=1e-14)


@pytest.mark.parametrize("positions,basis,electrons,sector",[
    ([[0,0,0],[0,0,0]],"cc-pVDZ",2,"singlet"),
    ([[0,0,0],[0,0,float('nan')]],"cc-pVDZ",2,"singlet"),
    ([[0,0,0]],"cc-pVDZ",2,"singlet"),
    ([[0,0,0],[0,0,1]],"other",2,"singlet"),
    ([[0,0,0],[0,0,1]],"cc-pVDZ",3,"singlet"),
    ([[0,0,0],[0,0,1]],"cc-pVDZ",2,"triplet"),
])
def test_unsupported_inputs_refused(positions,basis,electrons,sector):
    with pytest.raises(ValueError):
        validate(positions,basis,electrons,sector)


def sample():
    spec=json.loads((ROOT/"electronic_pilot/protocol_v2.json").read_text())
    spec["bases"]=["cc-pVQZ"]
    spec["R_grid_bohr"]=[1,2,3,10,12,16,20]
    energies=[-1.1,-1.15,-1.05,-1.0000004,-1.0000003,-1.0000002,-1.0000001]
    rows=[dict(kind="atom",basis="cc-pVQZ",ghost_distance=None,energy_hartree=-.5)]
    ref=[]
    for r,e in zip(spec["R_grid_bohr"],energies):
        rows.append(dict(kind="curve",basis="cc-pVQZ",R_bohr=r,sector="singlet",electrons=2,
                         electronic_energy_hartree=e-1/r,nuclear_repulsion_hartree=1/r,
                         total_energy_hartree=e,eigen_residual_l2=1e-14,wall_seconds=1,
                         process_peak_rss_bytes=1000,basis_size=2,singlet_dimension=3))
        ref.append(dict(R_bohr=str(r),total_energy_hartree=str(e)))
    return dict(rows=rows),spec,ref


def test_checker_minimum_and_fragment_use_total_energy():
    result=compare(*sample())
    q=result["summaries"]["cc-pVQZ"]
    assert q["P1_sampled_minimum"]
    assert q["sampled_min_R_bohr"]==2
    assert q["P2_tail_decreases"]
    assert q["P2_fragment_tolerance_pass"]


@pytest.mark.parametrize("mutation",["omit_nn","double_nn","wrong_count","wrong_sector","nan","residual","missing","duplicate"])
def test_checker_fault_injection(mutation):
    results,spec,ref=sample()
    row=results["rows"][1]
    if mutation=="omit_nn": row["total_energy_hartree"]=row["electronic_energy_hartree"]
    if mutation=="double_nn": row["total_energy_hartree"]+=row["nuclear_repulsion_hartree"]
    if mutation=="wrong_count": row["electrons"]=1
    if mutation=="wrong_sector": row["sector"]="triplet"
    if mutation=="nan": row["total_energy_hartree"]=float("nan")
    if mutation=="residual": row["eigen_residual_l2"]=.1
    if mutation=="missing": results["rows"].pop(1)
    if mutation=="duplicate": results["rows"].append(copy.deepcopy(row))
    with pytest.raises(ValueError):
        compare(results,spec,ref)


def test_preserved_refusal_cannot_pass_full_curve():
    results,spec,ref=sample()
    results["rows"][1]=dict(status="FAILED_PRESERVED",error="diagnostic refusal",
                            job=dict(kind="curve",basis="cc-pVQZ",R=1))
    out=compare(results,spec,ref)
    assert len(out["refused_points"])==1
    assert not out["summaries"]["cc-pVQZ"]["P3_curve_tolerance_pass"]
    assert out["summaries"]["cc-pVQZ"]["P3_computed_subset_tolerance_pass"]


def test_energy_mismatch_reports_false_without_changing_threshold():
    results,spec,ref=sample()
    ref[0]["total_energy_hartree"]="-1.11"
    out=compare(results,spec,ref)
    assert not out["summaries"]["cc-pVQZ"]["P3_curve_tolerance_pass"]
    assert spec["criteria"]["P3_curve_max_abs_error_hartree"]==.001


def test_comparator_has_no_executor_or_engine_import():
    tree=ast.parse((ROOT/"electronic_pilot/check_reference.py").read_text())
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): imports.extend(x.name for x in node.names)
        if isinstance(node,ast.ImportFrom): imports.append(node.module or "")
    assert all(x.split('.')[0] in {"__future__","argparse","csv","hashlib","json","math","decimal","pathlib"} for x in imports)
    executor=(ROOT/"electronic_pilot/solver.py").read_text()
    assert "pachucki" not in executor.lower()
    assert "1.4011" not in executor


def test_frozen_protocol_changes_only_failure_collection():
    v1=json.loads((ROOT/"electronic_pilot/protocol_v1.json").read_text())
    v2=json.loads((ROOT/"electronic_pilot/protocol_v2.json").read_text())
    for key in ("version","failure_policy"):
        del v1[key]; del v2[key]
    del v2["amendment"]; del v2["continue_independent_points_after_refusal"]
    assert v1==v2


def test_reference_coverage_and_tail_uncertainty_missing_explicitly():
    with (ROOT/"electronic_pilot/reference_pachucki_v2.csv").open() as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==44
    assert [float(x["R_bohr"]) for x in rows if not x["published_uncertainty_hartree"]]==[16,20]
