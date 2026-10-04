"""NON_CANONICAL small algebra controls; no physical pilot tuning."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import eigh

from electronic_pilot.state_history.core import canonicalize, coefficients, density_kernel, evolve, experiment, same_pure_state, validate_input
from electronic_pilot.state_history.checker import check

SPEC=json.loads((Path(__file__).parents[1]/"electronic_pilot/state_history/protocol.json").read_text(encoding="utf-8"))


def synthetic():
    spec=copy.deepcopy(SPEC);spec["basis_size"]=3
    s=np.array([[1.,.1,0],[.1,1.3,.04],[0,.04,.8]])
    h=np.array([[-1.,.12,.01],[.12,-.4,.02],[.01,.02,.4]])
    mu=np.zeros((3,3,3));mu[2]=[[.1,.6,.03],[.6,-.2,.04],[.03,.04,.1]]
    e,u=eigh(h,s)
    arrays,summary=experiment(s,h,mu,e,u,spec);summary["input"]=spec["case"]
    return dict(s=s,h=h,dipoles=mu,energies=e,eigenvectors=u,**arrays),summary,spec


def test_closed_nonorthogonal_full_space_control():
    d,summary,spec=synthetic();verdict=check(d,summary,spec)
    assert verdict["status"]=="PASS",verdict
    assert verdict["metrics"]["expm_vs_eigen_evolution_max"]<1e-13
    assert summary["initial_plus_minus_overlap_abs"]<1e-13
    assert summary["initial_plus_minus_density_kernel_max"]==0
    assert all(abs(x)>1e-4 for x in summary["dipole_z_differences"][1:])


@pytest.mark.parametrize("mutation",["duplicate_eigenvector","break_orthogonality","same_i_sign","remove_normalization","wrong_energies","reverse_time_sign","omit_imaginary_density","global_phase_wrong_state","electron_mismatch","sector_mismatch"])
def test_required_faults_are_detected(mutation):
    d,summary,spec=synthetic()
    if mutation=="duplicate_eigenvector": d["eigenvectors"][:,1]=d["eigenvectors"][:,0]
    elif mutation=="break_orthogonality": d["eigenvectors"][:,1]+=.02*d["eigenvectors"][:,0]
    elif mutation=="same_i_sign":
        d["initials"][1]=d["initials"][0];d["waves"][1]=d["waves"][0];d["density_kernels"][1]=d["density_kernels"][0]
    elif mutation=="remove_normalization":
        d["initials"]*=np.sqrt(2.);d["waves"]*=np.sqrt(2.);d["density_kernels"]*=2.
    elif mutation=="wrong_energies": d["energies"][1]+=.1
    elif mutation=="reverse_time_sign":
        d["waves"]=np.array([evolve(v,d["s"],d["energies"],d["eigenvectors"],[-t for t in spec["times_atomic"]]) for v in d["initials"]])
        d["density_kernels"]=np.array([[density_kernel(v) for v in group] for group in d["waves"]])
    elif mutation=="omit_imaginary_density": d["density_kernels"]=np.array([[np.outer(v.real,v.real) for v in group] for group in d["waves"]])
    elif mutation=="global_phase_wrong_state": summary["phase_same_physical_state"]=False
    elif mutation=="electron_mismatch": summary["input"]=dict(spec["case"],electrons=2)
    elif mutation=="sector_mismatch": summary["input"]=dict(spec["case"],sector="singlet")
    verdict=check(d,summary,spec)
    assert verdict["status"]=="FAIL",mutation
    assert verdict["errors"],mutation


def test_global_phase_and_preparation_preserve_projector_not_raw_bits():
    d,summary,spec=synthetic();a=d["initials"][0];b=d["initials"][4]
    assert not np.array_equal(a,b)
    assert same_pure_state(a,b,d["s"],1e-10)
    assert not same_pure_state(a,d["initials"][1],d["s"],1e-10)
    assert np.max(np.abs(canonicalize(a)-canonicalize(b)))<1e-14
    assert np.max(np.abs(density_kernel(a)-density_kernel(b)))<1e-14


@pytest.mark.parametrize("key",["history","bond","molecule","reaction","H2+","charge"])
def test_no_extra_authority_or_chemistry_labels(key):
    case=dict(SPEC["case"]);case[key]="selector"
    with pytest.raises(ValueError,match="authority/chemical label"):validate_input(case)


@pytest.mark.parametrize("change",[{"electrons":2},{"electrons":True},{"sector":"singlet"},{"basis":"cc-pVQZ"},{"law":"ground_re_solve"}])
def test_ne_sector_basis_law_validation(change):
    case=dict(SPEC["case"]);case.update(change)
    with pytest.raises(ValueError):validate_input(case)


def test_sealed_geometry_times_and_full_count():
    assert validate_input(SPEC["case"])==1
    assert SPEC["times_atomic"]==[0.,.5,1.]
    assert SPEC["basis_size"]==28
    bad=copy.deepcopy(SPEC["case"]);bad["nuclei"][0]["position_bohr"][2]=-.8
    with pytest.raises(ValueError):validate_input(bad)


def test_initial_density_kernel_does_not_equal_full_density_operator():
    d,_,_=synthetic();a,b=d["initials"][:2]
    assert np.max(np.abs(density_kernel(a)-density_kernel(b)))==0
    assert np.max(np.abs(np.outer(a,a.conj())-np.outer(b,b.conj())))>1e-3


def test_nonfinite_and_truncated_full_space_refused():
    d,summary,spec=synthetic();d["eigenvectors"]=d["eigenvectors"][:,:2]
    assert check(d,summary,spec)["status"]=="FAIL"
    d,summary,spec=synthetic();d["energies"][0]=np.nan
    assert check(d,summary,spec)["status"]=="FAIL"
