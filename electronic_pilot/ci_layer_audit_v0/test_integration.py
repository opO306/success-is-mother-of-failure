"""Tiny synthetic integration only; run explicitly in the PySCF environment."""
import numpy as np
from . import baseline, fermion


def test_old_exports_and_action_on_symmetric_integrals():
    h=np.array([[1.,.125],[.125,2.]])
    density=np.array([[.5,.125],[.125,.75]])
    g=np.einsum('pq,rs->pqrs',density,density)
    states=[(0,0),(0,1),(1,1)]
    wanted=[(bra,ket) for bra in states for ket in states]
    expected=np.array([fermion.value(h,g,*x) for x in wanted]).reshape(3,3)
    for prior in (False,True):
        assert max(abs(np.array(baseline.entries(h,g,wanted,prior)).reshape(3,3)-expected).ravel())<2e-15
    op=baseline.PriorAction(h,g)
    for ket in states:
        observed=op([(ket,1)],states)
        assert max(abs(observed-np.array([fermion.value(h,g,bra,ket) for bra in states])))<2e-15


def test_asymmetric_pair_input_exposes_absorption_packing_fault():
    h=np.array([[1.,.125],[.125,2.]])
    g=np.empty((2,)*4)
    for p,q,r,s in np.ndindex(g.shape):
        a=sorted((p,q));b=sorted((r,s));g[p,q,r,s]=(1+2*a[0]+3*a[1]+5*b[0]+7*b[1])/32
    op=baseline.PriorAction(h,g);states=[(0,0),(0,1),(1,1)];ket=(0,1)
    output=op([(ket,1)],states);raw=np.array([fermion.value(h,g,bra,ket) for bra in states])
    assert max(abs(output-raw))>1e-5
    index=int(abs(output-raw).argmax());before,_,_=baseline.uncompressed_absorption(h,g)
    unpacked,_=fermion.e_product_element(before,states[index],ket)
    packed,_=fermion.e_product_element(op.k,states[index],ket)
    assert abs(unpacked-raw[index])<2e-15
    assert abs(packed-output[index])<2e-15
