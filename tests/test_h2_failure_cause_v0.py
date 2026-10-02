"""Residual-verifier faults and independent singlet-construction identities."""
from fractions import Fraction
import ast
from pathlib import Path
import numpy as np
import pytest
from electronic_pilot.failure_cause_v0.exact_guard import (
    exact_norm_bounds,residual_dyadics,sqrt_enclosure,interval_product,adaptive_guard)
from electronic_pilot.failure_cause_v0.same_basis import expand,project,direct_pair_matrix,four_leg_transform


def test_exact_residual_against_independent_fraction_loops():
    s=[[1.,.125],[.125,2.]];c=[[.75,-.0625],[.25,.5]]
    integer,den=residual_dyadics(s,c)
    for i in range(2):
        for j in range(2):
            expected=sum(Fraction(c[p][i])*Fraction(s[p][q])*Fraction(c[q][j]) for p in range(2) for q in range(2))-int(i==j)
            assert Fraction(integer[i][j],den)==expected


def test_enclosure_both_sides_of_guard_and_ambiguous():
    eye=np.eye(2)
    assert exact_norm_bounds(eye.tolist(),eye.tolist())['relation']=='BELOW'
    assert exact_norm_bounds(eye.tolist(),(eye*1.0001).tolist())['relation']=='ABOVE'
    assert exact_norm_bounds((eye*(1+8e-11)).tolist(),eye.tolist())['relation']=='UNRESOLVED'


@pytest.mark.parametrize('value',[Fraction(0),Fraction(2),Fraction(1,10**20),Fraction(25,49)])
def test_outward_sqrt(value):
    lo,hi=map(Fraction,sqrt_enclosure(value))
    assert lo*lo<=value<=hi*hi and hi-lo<=Fraction(1,10**40)


def test_interval_product_encloses_fraction_entries():
    a=np.array([[1.,1e-14],[-1e3,2.]]);b=np.array([[.125,-.2],[8.,.5]])
    lo,hi=interval_product(a,a,b,b)
    for i in range(2):
        for j in range(2):
            exact=sum(Fraction(float(a[i,k]))*Fraction(float(b[k,j])) for k in range(2))
            assert Fraction(float(lo[i,j]))<=exact<=Fraction(float(hi[i,j]))


def test_adaptive_fast_paths_and_stop_without_false_pass():
    eye=np.eye(2)
    assert adaptive_guard(eye,eye)['exact_fallback'] is None
    assert adaptive_guard(eye,eye*1.0001)['relation']=='ABOVE'
    ambiguous=adaptive_guard(eye*(1+8e-11),eye)
    assert ambiguous['exact_fallback'] is not None and ambiguous['relation']=='UNRESOLVED'
    assert not ambiguous['production_applied'] and not ambiguous['changes_original_QZ44']


@pytest.mark.parametrize('value',[float('nan'),float('inf')])
def test_nonfinite_refused(value):
    with pytest.raises((ValueError,OverflowError)): exact_norm_bounds([[value]],[[1.]])


def test_singlet_projection_and_direct_pair_construction():
    n=3;v=np.arange(1,7,dtype=float)
    ci=expand(v,n)
    assert np.allclose(project(ci),v) and np.allclose(ci,ci.T)
    assert abs((ci*ci).sum()-v@v)<1e-13
    h=np.array([[1.,.2,-.1],[.2,2.,.3],[-.1,.3,3.]])
    factors=np.arange(1,10,dtype=float).reshape(n,n);factors=factors+factors.T
    g=np.einsum('ij,kl->ijkl',factors,factors)/100
    product=np.kron(h,np.eye(n))+np.kron(np.eye(n),h)+g.transpose(0,2,1,3).reshape(n*n,n*n)
    u=np.column_stack([expand(np.eye(6)[k],n).ravel() for k in range(6)])
    assert np.max(abs(direct_pair_matrix(h,g)-u.T@product@u))<2e-14


def test_four_leg_transform_against_full_sum():
    g=np.arange(16,dtype=float).reshape((2,)*4)/17
    c=np.array([[.7,-.2],[.3,.8]])
    reference=np.empty_like(g)
    for i,j,k,l in np.ndindex(g.shape):
        reference[i,j,k,l]=sum(g[p,q,r,s]*c[p,i]*c[q,j]*c[r,k]*c[s,l] for p,q,r,s in np.ndindex(g.shape))
    assert np.max(abs(four_leg_transform(g,c)-reference))<3e-16


def test_verifier_imports_no_executor_or_custom_CI():
    for name in ('exact_guard.py','same_basis.py'):
        source=Path('electronic_pilot/failure_cause_v0')/name
        tree=ast.parse(source.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert not any(x in (node.module or '') for x in ('ao_micro','numerical_cause','electronic_pilot.solver'))


def test_hash_drift(tmp_path):
    from electronic_pilot.failure_cause_v0.run import sha,verify
    p=tmp_path/'data';p.write_bytes(b'original');bound={str(p):sha(p)}
    verify(bound);p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='DRIFT'): verify(bound)
