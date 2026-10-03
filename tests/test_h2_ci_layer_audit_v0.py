"""Independent operator algebra, semantic fault injection, and STOP gates."""
import ast
import math
from pathlib import Path
import numpy as np
import pytest
from electronic_pilot.ci_layer_audit_v0 import fermion, baseline
from electronic_pilot.ci_layer_audit_v0.run import basis_check, comparison, verify, sha


def tiny_input():
    h=np.array([[1.,.125],[.125,2.]])
    g=np.empty((2,)*4)
    for p,q,r,s in np.ndindex(g.shape):
        a=tuple(sorted((p,q)));b=tuple(sorted((r,s)))
        g[p,q,r,s]=(1+2*a[0]+3*a[1]+5*b[0]+7*b[1])/32
    return h,g  # within-pair identities; deliberate pair-interchange defect


def test_fermion_anticommutation_and_pauli():
    for det in [(),(0,),(1,),(0,2),(1,3)]:
        for p in range(4):
            a=fermion.operate(det,[(p,True),(p,False)])
            b=fermion.operate(det,[(p,False),(p,True)])
            assert sum(x[1] for x in (a,b) if x is not None and x[0]==det)==1
            assert fermion.operate(det,[(p,True),(p,True)]) is None
            assert fermion.operate(det,[(p,False),(p,False)]) is None
    left=fermion.operate((0,2),[(0,False),(2,False)])
    right=fermion.operate((0,2),[(2,False),(0,False)])
    assert left[0]==right[0] and left[1]==-right[1]


@pytest.mark.parametrize('pair',[(0,0),(0,1),(2,5),(50,56)])
def test_singlet_norm_spin_and_permutation_mapping(pair):
    dets, radical=fermion.singlet(pair)
    assert len({d for d,_ in dets})==len(dets)
    assert sum(c*c for _,c in dets)==2**radical
    assert fermion.spin_zero(pair)
    terms=fermion.alpha_beta_terms(pair)
    assert sum(c*c for _,_,c in terms)==pytest.approx(1)
    assert all(c>0 for _,_,c in terms)


def test_semantic_mapping_full60_and_independent_order():
    b=baseline.catalog(60,True)
    out=basis_check(baseline.catalog(60),b,fermion.state_catalog(60))
    assert out['status']=='MATCH' and set(out['dimensions'].values())=={1830}
    row=next(x for x in out['rows'] if x['pair']==[50,56])
    assert row['A_index']!=row['prior_lower_index']
    shuffled=list(reversed(b))
    assert basis_check(baseline.catalog(60),shuffled,fermion.state_catalog(60))['status']=='MATCH'


@pytest.mark.parametrize('fault',['duplicate','missing','normalization','occupation','spin'])
def test_mapping_fault_injection_stops(fault):
    a=baseline.catalog(3);b=baseline.catalog(3,True);c=fermion.state_catalog(3)
    if fault=='duplicate': b.append(dict(b[0]))
    elif fault=='missing': b.pop()
    elif fault=='normalization': b[1]['normalization']='wrong_sqrt2'
    elif fault=='occupation': b[1]['occupation']=[[0,2]]
    else: b[1]['S']=1
    assert basis_check(a,b,c)['status']=='STOP'


def test_second_quantization_against_manual_first_quantized_wavefunctions():
    h,g=tiny_input()
    # Explicit antisymmetric wavefunctions; no determinant mapping helper.
    wave=np.zeros((3,4,4))
    wave[0,0,1]=1/math.sqrt(2);wave[0,1,0]=-1/math.sqrt(2)
    wave[1,0,3]=.5;wave[1,3,0]=-.5;wave[1,1,2]=-.5;wave[1,2,1]=.5
    wave[2,2,3]=1/math.sqrt(2);wave[2,3,2]=-1/math.sqrt(2)
    product=np.zeros((4,4,4,4))
    for a,b,c,d in np.ndindex(product.shape):
        if a%2==c%2 and b==d: product[a,b,c,d]+=h[a//2,c//2]
        if a==c and b%2==d%2: product[a,b,c,d]+=h[b//2,d//2]
        if a%2==c%2 and b%2==d%2: product[a,b,c,d]+=g[a//2,c//2,b//2,d//2]
    pairs=[(0,0),(0,1),(1,1)]
    manual=np.einsum('iab,abcd,jcd->ij',wave,product,wave)
    for i,j in np.ndindex((3,3)):
        assert abs(fermion.value(h,g,pairs[i],pairs[j])-manual[i,j])<2e-15
        assert abs(fermion.breakdown(h,g,pairs[i],pairs[j])['value']-manual[i,j])<2e-15


def test_known_coefficients_and_fault_sensitivity():
    h,g=tiny_input()
    closed=fermion.breakdown(h,g,(0,0),(0,0))
    assert closed['value']==2*h[0,0]+g[0,0,0,0]
    mixed=fermion.breakdown(h,g,(0,0),(0,1))
    expected=math.sqrt(2)*h[0,1]+(g[0,0,0,1]+g[0,1,0,0])/math.sqrt(2)
    assert mixed['value']==pytest.approx(expected,abs=2e-15)
    assert comparison(expected,expected*math.sqrt(2),1e-10)['mismatch']
    assert comparison(expected,-expected,1e-10)['mismatch']
    opened=fermion.breakdown(h,g,(0,1),(0,1))
    assert float(opened['contribution']['exchange'])>0
    assert comparison(opened['value'],opened['value']-2*float(opened['contribution']['exchange']),1e-10)['mismatch']


def test_nonzero_threshold_and_relative_zero_semantics():
    assert not comparison(0,0,1e-10)['mismatch']
    assert comparison(0,0,1e-10)['relative_difference'] is None
    assert comparison(0,2e-10,1e-10)['mismatch']
    assert not comparison(0,1e-10,1e-10)['mismatch']


def test_localized_e_product_before_packing_restores_raw_operator():
    h,g=tiny_input();k,trace,f=baseline.uncompressed_absorption(h,g)
    assert abs(trace-trace.T).max()>0 and abs(f-f.T).max()>0
    for bra in [(0,0),(0,1),(1,1)]:
        for ket in [(0,0),(0,1),(1,1)]:
            result,_=fermion.e_product_element(k,bra,ket)
            assert abs(result-fermion.value(h,g,bra,ket))<2e-15


def test_independent_evaluator_import_boundary_and_no_solver_calls():
    tree=ast.parse(Path(fermion.__file__).read_text())
    modules=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): modules.extend(x.name for x in node.names)
        if isinstance(node,ast.ImportFrom): modules.append(node.module)
    assert set(modules)<={'decimal','fractions','itertools','math'}
    source=Path('electronic_pilot/ci_layer_audit_v0/run.py').read_text()
    assert 'eigsh(' not in source and 'eigh(' not in source
    assert 'reference_pachucki' not in source


def test_byte_drift_stops(tmp_path):
    p=tmp_path/'data';p.write_bytes(b'sealed');bound={str(p):sha(p)}
    verify(bound);p.write_bytes(b'tampered')
    with pytest.raises(ValueError,match='BYTE DRIFT'): verify(bound)
