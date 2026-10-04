"""Actual 28-orbital sealed evidence and required semantic mutations."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from electronic_pilot.state_history.checker import check
from electronic_pilot.state_history.core import evolve, density_kernel

ROOT=Path(__file__).parents[1]/"docs/active/electronic_state_history_v1"
SEAL=json.loads((ROOT/"desktop_seal.json").read_text(encoding="utf-8"))
RESULT=json.loads((ROOT/"desktop_results.json").read_text(encoding="utf-8"))
SPEC=SEAL["protocol"]


def actual():
    with np.load(ROOT/"desktop_experiment.npz") as z:d={k:z[k].copy() for k in z.files}
    return d,copy.deepcopy(RESULT)


def test_saved_actual_state_history_experiment():
    d,result=actual();verdict=check(d,result,SPEC)
    assert verdict["status"]=="PASS",verdict
    assert all(verdict[k]=="PASS" for k in ["P1","P2","P3","P4"])
    assert result["protected_bytes_unchanged"] and result["source_bytes_unchanged"]
    assert result["retained_eigenvectors"]==result["spatial_orbitals"]==28
    assert result["original_TZ_exact_basis_match"]
    assert result["raw_AO_matches_prior_S_h"]=={"s":True,"h":True}
    assert hashlib.sha256((ROOT/"desktop_experiment.npz").read_bytes()).hexdigest()==result["artifact_sha256"]["experiment.npz"]
    assert result["initial_plus_minus_density_kernel_max"]==0
    assert result["initial_plus_minus_overlap_abs"]<1e-10
    assert result["gap_hartree"]>1e-7


@pytest.mark.parametrize("mutation",["duplicate_eigenvector","break_orthogonality","same_i_sign","remove_normalization","wrong_energies","reverse_time_sign","omit_imaginary_density","global_phase_wrong_state","electron_mismatch","sector_mismatch"])
def test_actual_required_mutations_detected(mutation):
    d,result=actual()
    if mutation=="duplicate_eigenvector":d["eigenvectors"][:,1]=d["eigenvectors"][:,0]
    elif mutation=="break_orthogonality":d["eigenvectors"][:,1]+=.01*d["eigenvectors"][:,0]
    elif mutation=="same_i_sign":
        d["initials"][1]=d["initials"][0];d["waves"][1]=d["waves"][0];d["density_kernels"][1]=d["density_kernels"][0]
    elif mutation=="remove_normalization":
        d["initials"]*=np.sqrt(2.);d["waves"]*=np.sqrt(2.);d["density_kernels"]*=2.
    elif mutation=="wrong_energies":d["energies"][:2]+=[.01,-.01]
    elif mutation=="reverse_time_sign":
        d["waves"]=np.array([evolve(v,d["s"],d["energies"],d["eigenvectors"],[-t for t in SPEC["times_atomic"]]) for v in d["initials"]])
        d["density_kernels"]=np.array([[density_kernel(v) for v in group] for group in d["waves"]])
    elif mutation=="omit_imaginary_density":d["density_kernels"]=np.array([[np.outer(v.real,v.real) for v in group] for group in d["waves"]])
    elif mutation=="global_phase_wrong_state":result["phase_same_physical_state"]=False
    elif mutation=="electron_mismatch":result["input"]["electrons"]=2
    elif mutation=="sector_mismatch":result["input"]["sector"]="singlet"
    verdict=check(d,result,SPEC)
    assert verdict["status"]=="FAIL",mutation
    assert verdict["errors"],mutation


def test_laptop_stored_H_eigenvector_environment_reproduction():
    laptop=json.loads((ROOT/"laptop_results_v1.json").read_text(encoding="utf-8"))
    assert laptop["status"]==laptop["checker"]["status"]=="PASS"
    assert laptop["host"]=="DESKTOP-0EASI0F"
    assert laptop["source_sha256"]==SEAL["source_sha256"]
    assert laptop["desktop_dipole_difference_max"]<=SPEC["dual_machine_tolerance"]
    assert laptop["desktop_density_metric_difference_max"]<=SPEC["dual_machine_tolerance"]
    assert laptop["scope"].endswith("NOT_PHYSICS_AUDIT")


def test_combinatorial_scaling_ledger_exact_counts():
    from math import comb
    scaling=json.loads((ROOT/"scaling_v1.json").read_text(encoding="utf-8"))
    assert scaling["pilot_dimension"]==28 and scaling["pilot_wavefunction_bytes"]==448
    assert scaling["pilot_dense_quantum_density_operator_bytes"]==12544
    for row in scaling["examples"]:
        d=comb(row["M_spatial"],row["N_alpha"])*comb(row["M_spatial"],row["N_beta"])
        assert row["dimension"]==row["wavefunction_complex_coefficients"]==d
        assert row["dense_density_operator_entries"]==d*d
        assert row["N_alpha"]+row["N_beta"]==row["N"]
