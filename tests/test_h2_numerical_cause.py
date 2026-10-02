"""Coordinate equivalence and fail-closed diagnostic checks, without PySCF."""
import json
from pathlib import Path
import sys
import types

import numpy as np
import pytest
from scipy.linalg import eigh
from electronic_pilot.numerical_cause import core
from electronic_pilot.solver import singlet_matrix


def example():
    v = np.array([[1,.2,.3],[.1,1,.4],[.3,.1,1.]])
    s = v.T@v+np.eye(3)*.3
    h = np.array([[-1.,.1,.2],[.1,.4,.3],[.2,.3,1.1]])
    b = np.array([[.5,.1,.2],[.1,.4,.3],[.2,.3,.6]])
    eri = np.einsum("ij,kl->ijkl", b,b)
    return s,h,eri


def transform(eri,c):
    return np.einsum("pqrs,pi,qj,rk,sl->ijkl",eri,c,c,c,c,optimize=True)


@pytest.mark.parametrize("path",core.PATHS)
def test_full_span_orthonormality_and_spectrum(path):
    s,h,eri = example()
    ca = core.coordinates(s,h,"symmetric")
    cb = core.coordinates(s,h,path)
    assert cb.shape == s.shape
    assert np.linalg.matrix_rank(cb) == len(s)
    assert np.linalg.norm(cb.T@s@cb-np.eye(len(s)),ord=2) < 1e-12
    ma = singlet_matrix(ca.T@h@ca,transform(eri,ca))[0]
    mb = singlet_matrix(cb.T@h@cb,transform(eri,cb))[0]
    # Every root, rather than only the common lowest-root implementation.
    assert np.max(np.abs(eigh(ma,eigvals_only=True)-eigh(mb,eigvals_only=True))) < 1e-12
    u = ca.T@s@cb
    # Explicit product-coordinate map and independent symmetric projector.
    pairs=[(i,j) for i in range(3) for j in range(i,3)]
    p=np.zeros((9,6))
    for k,(i,j) in enumerate(pairs):
        p[3*i+j,k]+=1/np.sqrt(2*(1+(i==j)))
        p[3*j+i,k]+=1/np.sqrt(2*(1+(i==j)))
    q=p.T@np.kron(u,u)@p
    assert np.max(np.abs(q.T@ma@q-mb)) < 1e-12


@pytest.mark.parametrize("path",core.PATHS)
def test_small_overlap_not_silently_deleted(path):
    s=np.diag([1.,1e-12])
    c=core.coordinates(s,np.diag([-1.,2.]),path)
    assert c.shape == (2,2)
    assert np.linalg.det(c) != 0


@pytest.mark.parametrize("fault,expected",[("overlap","overlap_floor"),("orth","orthonormalization"),
                                          ("eri","singlet_hermiticity"),("h","singlet_hermiticity")])
def test_fault_refused_before_eigenvalue_acceptance(monkeypatch,fault,expected):
    s,h,eri=example()
    if fault=="overlap":
        s=np.diag([1.,1.,1e-12])
    real_coordinates=core.coordinates
    if fault=="orth":
        def broken(*args):
            c=real_coordinates(*args)
            c[:,0]*=1.001
            return c
        monkeypatch.setattr(core,"coordinates",broken)
    if fault=="h":
        h[0,1]+=.1
    if fault=="eri":
        eri[0,0,1,2]+=.2
    monkeypatch.setitem(sys.modules,"pyscf",types.SimpleNamespace(ao2mo=types.SimpleNamespace(
        kernel=lambda g,c,**kwargs:transform(g,c))))
    row,_=core.inspect_path(types.SimpleNamespace(energy_nuc=lambda:.5),s,h,eri,"symmetric","common_ao_incore")
    assert row["failure_stage"]==expected
    assert not row["accepted"]
    assert row["electronic_energy_hartree"] is None
    assert row["total_energy_hartree"] is None


def test_parent_tolerances_and_reference_are_unchanged():
    p=json.loads(Path("electronic_pilot/numerical_cause/protocol.json").read_text())
    old=json.loads(Path(p["parent_protocol"]).read_text())
    for key in ("overlap_min_eigenvalue_floor","orthonormalization_max_norm","eigen_residual_max_l2_hartree"):
        assert p[key]==old[key]
    assert p["hermitian_max_asymmetry"]==1e-10
    source=Path("electronic_pilot/numerical_cause/core.py").read_text()
    assert "reference_pachucki" not in source
    assert "ref_min" not in source


def test_asymmetric_eri_permutation_fault_is_detected():
    _,_,eri=example()
    assert max(core.symmetry(eri).values())==0
    eri[0,1,1,2]+=.1
    assert min(core.symmetry(eri).values())>.09


def test_fresh_curve_record_view_preserves_refusals_and_rss():
    from electronic_pilot.numerical_cause.physical_compare import curve_records
    data={"rows":[{"R_bohr":1.4,"process_peak_rss_bytes":123,"paths":[{"accepted":True,"total_energy_hartree":-1.17}]},
                  {"R_bohr":1.3,"paths":[{"accepted":False,"failure_stage":"singlet_hermiticity"}]}]}
    records=curve_records(data,[])["rows"]
    assert records[0]["process_peak_rss_bytes"]==123
    assert "process_peak_rss_bytes" not in data["rows"][0]["paths"][0]
    assert records[1]["status"]=="FAILED_PRESERVED"
    assert "total_energy_hartree" not in records[1]


def selection_example():
    spec=json.loads(Path("electronic_pilot/numerical_cause/protocol.json").read_text())
    spec=dict(spec,controls={"test":[2.]})
    paths=[dict(path=p,backend=b,accepted=True,total_energy_hartree=-1.,basis_size=2,singlet_dimension=3,
                C_singular_values=[1.,1.],shared_AO_sha256={"s":"S","h":"H","eri_s1":"G"})
           for p in spec["paths"] for b in spec["transform_backends"]]
    control={"rows":[dict(basis="test",R_bohr=2.,original=dict(accepted=True,energy=-1.),paths=paths)]}
    import copy
    comparison=copy.deepcopy(control)
    return control,comparison,spec


def test_selection_tie_is_sealed_and_reference_free():
    from electronic_pilot.numerical_cause.select import select
    control,comparison,spec=selection_example()
    choice=select(control,comparison,spec)
    assert choice["path"]=="cholesky"
    assert choice["backend"]=="original_outcore"
    assert choice["reference_used"] is False


@pytest.mark.parametrize("fault",["AO","energy","dimension"])
def test_selection_rejects_faulty_equivalence(fault):
    from electronic_pilot.numerical_cause.select import select
    control,comparison,spec=selection_example()
    if fault=="AO":
        control["rows"][0]["paths"][0]["shared_AO_sha256"]["h"]="different"
        with pytest.raises(ValueError,match="AO inputs differ"):
            select(control,comparison,spec)
    else:
        for r in control["rows"][0]["paths"]:
            if fault=="energy":
                r["total_energy_hartree"]+=1e-7
            else:
                r["singlet_dimension"]-=1
        assert select(control,comparison,spec)["status"]=="NO_QUALIFIED_PATH"


def test_selection_incomplete_controls_refused():
    from electronic_pilot.numerical_cause.select import select
    control,comparison,spec=selection_example()
    control["rows"]=[]
    with pytest.raises(ValueError,match="incomplete controls"):
        select(control,comparison,spec)
