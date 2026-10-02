"""Local WSL PySCF/multiprecision diagnostic tests, outside LOCAL FULL."""
import numpy as np
from .core import ao_data, inspect_path, coordinates
from .high_precision import propagated_asymmetry, mp_cholesky_coordinates
from electronic_pilot.solver import singlet_matrix


def test_multiprecision_antisymmetry_contraction_matches_independent_tensor():
    s=np.eye(3)
    h=np.array([[1,.2,.1],[.3,2,.4],[.1,.4,3.]])
    g=np.arange(81,dtype=float).reshape((3,)*4)/128
    c=np.array([[1,.1,.2],[.3,1,.4],[.2,.1,1.]])
    transformed=np.einsum("pqrs,pi,qj,rk,sl->ijkl",g,c,c,c,c,optimize=False)
    m,ii,jj,_=singlet_matrix(c.T@h@c,transformed)
    for a,b in ((0,3),(1,5),(2,4)):
        row=propagated_asymmetry(s,h,g,c,(ii[a],jj[a]),(ii[b],jj[b]),80,False)
        assert abs(float(row["total"])-(m[a,b]-m[b,a]))<1e-12


def test_high_precision_coordinates_retain_full_dimension():
    s=np.array([[1,.5],[.5,1.]])
    for digits in (60,80):
        c,orth,det=mp_cholesky_coordinates(s,digits)
        assert len(c)==2 and len(c[0])==2
        assert float(orth)<1e-50
        assert float(det)!=0


def test_asymmetric_raw_overlap_not_averaged_or_hidden():
    s=np.array([[1,.500001],[.5,1.]])
    c,orth,_=mp_cholesky_coordinates(s,80)
    assert float(orth)>1e-7
    # Recurrence reads original lower triangle; upper perturbation survives
    # validation, instead of silently being averaged into a modified matrix.
    base,_,_=mp_cholesky_coordinates(np.array([[1,.5],[.5,1.]]),80)
    assert c==base


def test_three_real_AO_coordinates_agree_without_orbital_truncation():
    mol,s,h,g=ao_data("cc-pVDZ",2.)
    records=[inspect_path(mol,s,h,g,p,"common_ao_incore")[0] for p in ("symmetric","cholesky","generalized_h")]
    assert all(x["accepted"] and x["basis_size"]==10 and x["singlet_dimension"]==55 for x in records)
    assert max(x["total_energy_hartree"] for x in records)-min(x["total_energy_hartree"] for x in records)<1e-10
