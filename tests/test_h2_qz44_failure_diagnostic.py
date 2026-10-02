"""Separate contraction test; frozen original preflight test stays unchanged."""
import numpy as np
from electronic_pilot.qz44_sealed_v1.failure_diagnostic import mp_eri


def test_sparse_pair_contraction_against_full_four_index_contraction():
    from pyscf import ao2mo
    # Deterministic artificial s8 tensor and dense coefficient matrix; all
    # nonzero coefficients retained. Direct tensor contraction is separate.
    n=4;pairs=n*(n+1)//2
    g8=np.array([(.03*(k+1)) for k in range(pairs*(pairs+1)//2)])
    c=np.array([[1.,.1,-.2,.3],[.2,.8,.1,-.4],[.1,.2,.7,.3],[.3,-.1,.2,.9]])
    g=ao2mo.restore(1,g8,n)
    for indices in ((0,1,2,3),(3,3,0,1),(1,1,1,1)):
        i,j,k,l=indices
        independent=np.einsum('pqrs,p,q,r,s',g,c[:,i],c[:,j],c[:,k],c[:,l])
        value,cost=mp_eri(g8,c,indices,60)
        assert abs(float(value)-independent)<3e-15
        swap,_=mp_eri(g8,c,indices[2:]+indices[:2],80)
        assert abs(float(value)-float(swap))<1e-14
        assert cost['left_nonzero_pair_densities']==pairs
