"""PySCF-dependent local WSL checks, outside the production LOCAL FULL suite."""
import numpy as np
import pytest
from electronic_pilot.solver import solve, atom_energy


def test_rotation_translation_and_proton_exchange():
    q=np.array([[0,0,-1],[0,0,1.]])
    original=solve(q,"cc-pVDZ",crosscheck=True)
    transformed=q[:,[2,0,1]]+np.array([2.0,-1.0,.5])
    for positions in (transformed,q[::-1]):
        other=solve(positions,"cc-pVDZ")
        assert abs(other["total_energy_hartree"]-original["total_energy_hartree"])<1e-10
    assert original["shared_integral_crosscheck"]["converged"]
    assert abs(original["shared_integral_crosscheck"]["difference_hartree"])<1e-10


def test_alternative_lapack_driver_same_finite_problem():
    q=[[0,0,-1],[0,0,1]]
    a=solve(q,"cc-pVDZ",driver="evr")
    b=solve(q,"cc-pVDZ",driver="evd")
    assert abs(a["electronic_energy_hartree"]-b["electronic_energy_hartree"])<1e-11


def test_dissociation_and_one_electron_exact_reference():
    a=atom_energy("cc-pVTZ")
    assert 0 <= a+.5 < .001
    row=solve([[0,0,-10],[0,0,10]],"cc-pVTZ")
    assert abs(row["total_energy_hartree"]-2*a)<1e-6
    assert abs(row["electronic_energy_hartree"]+.05-row["total_energy_hartree"])<1e-14


def test_nonhermitian_fault_refused(monkeypatch):
    from electronic_pilot import solver
    real=solver.singlet_matrix
    def broken(*args):
        mat,i,j,norms=real(*args)
        mat[0,1]+=.01
        return mat,i,j,norms
    monkeypatch.setattr(solver,"singlet_matrix",broken)
    with pytest.raises(ValueError,match="REFUSED: non-Hermitian"):
        solve([[0,0,-1],[0,0,1]],"cc-pVDZ")


def test_overlap_failure_has_diagnostic_not_name_error(monkeypatch):
    # Inject loss of orthonormality rather than freeze a real numerical defect.
    from electronic_pilot import solver
    real=solver.eigh
    def broken(*args,**kwargs):
        w,u=real(*args,**kwargs)
        u[:,0]*=1.0001
        return w,u
    monkeypatch.setattr(solver,"eigh",broken)
    with pytest.raises(ValueError,match="REFUSED: orthonormalization error="):
        solver.integrals([("H",(0,0,-1)),("H",(0,0,1))],"cc-pVDZ")
