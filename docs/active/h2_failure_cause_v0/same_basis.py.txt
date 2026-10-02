"""Independent singlet determinant action, transformation and eigensolver.

Shares rounded canonical AO data and PySCF format utilities. No imports from
the custom executor/CI/orthogonalization modules; no Hamiltonian averaging.
"""
import time
import numpy as np
from scipy.linalg import eigh
from scipy.sparse.linalg import LinearOperator,eigsh


def pairs(n):
    i,j=np.tril_indices(n)
    return i,j,np.sqrt(2*(1+(i==j)))


def expand(v,n):
    i,j,norm=pairs(n);ci=np.zeros((n,n))
    np.add.at(ci,(i,j),v/norm);np.add.at(ci,(j,i),v/norm)
    return ci


def project(ci):
    i,j,norm=pairs(len(ci))
    return (ci[i,j]+ci[j,i])/norm


def direct_pair_matrix(h,g):
    n=len(h);ii,jj,norm=pairs(n);d=len(ii);mat=np.empty((d,d))
    for a,(i,j) in enumerate(zip(ii,jj)):
        k,l=ii,jj
        one=2*(h[i,k]*(j==l)+h[i,l]*(j==k)+h[j,k]*(i==l)+h[j,l]*(i==k))
        two=g[i,k,j,l]+g[i,l,j,k]+g[j,k,i,l]+g[j,l,i,k]
        mat[a]=(one+two)/(norm[a]*norm)
    return mat


def four_leg_transform(g,c):
    for axis in range(4):
        g=np.tensordot(g,c,axes=(axis,0))
        g=np.moveaxis(g,-1,axis)
    return g


def lower_h(h,c):
    hc=h@c;n=len(c);out=np.empty((n,n))
    for i in range(n):
        for j in range(i+1): out[i,j]=out[j,i]=np.dot(c[:,i],hc[:,j])
    return out


def run_reference(s,h,g8,saved_c,path,guard):
    from pyscf import ao2mo, fci,lib
    lib.num_threads(1)
    started=time.perf_counter();n=len(s);dims=n*(n+1)//2
    if path=='frozen_C_and_compact_transform':
        c=saved_c.copy()
        gm=ao2mo.restore(1,ao2mo.incore.full(g8,c,compact=True),n)
    elif path=='generalized_h_C_and_four_leg_numpy_transform':
        c=eigh(h,s,type=1,driver='gvd')[1]
        full=four_leg_transform(ao2mo.restore(1,g8,n),c)
        i,j=np.tril_indices(n)
        gm=ao2mo.restore(1,full[i[:,None],j[:,None],i[None,:],j[None,:]].copy(),n)
        del full
    else: raise ValueError('unknown sealed diagnostic path')
    hm=lower_h(h,c)
    transformed_seconds=time.perf_counter()-started
    mat=direct_pair_matrix(hm,gm)
    h_asym=float(abs(mat-mat.T).max())
    orth=float(np.linalg.norm(c.T@s@c-np.eye(n),ord=2))
    row=dict(path=path,basis_size=n,singlet_dimension=dims,orthogonality_l2=orth,
             H_asymmetry=h_asym,MO_pair_interchange=float(abs(gm-gm.transpose(2,3,0,1)).max()),
             transformation_seconds=transformed_seconds,energy=None,eigen_residual=None,
             arithmetic='binary64',failure_stage=None,not_certified=True)
    # Diagnostic reference cannot silently feed a non-Hermitian matrix to eigsh.
    if h_asym>guard['H_asym_max']:
        row['failure_stage']='independent_H_hermiticity';return row,c,None
    # direct_spin1 has no direct_spin0 transpose_sum/averaging of ERI pairs.
    h2=fci.direct_spin1.absorb_h1e(hm,gm,n,(1,1),fac=.5)
    link=fci.cistring.gen_linkstr_index_trilidx(range(n),1)
    calls=0
    def hop(v):
        nonlocal calls
        calls+=1
        out=fci.direct_spin1.contract_2e(h2,expand(v,n),n,(1,1),link_index=(link,link))
        return project(out)
    probes=[np.ones(dims)/np.sqrt(dims),np.cos(np.arange(dims)*.37)]
    discrepancies=[float(np.linalg.norm(hop(v)-mat@v)/np.linalg.norm(v)) for v in probes]
    row['determinant_vs_pair_action_l2']=discrepancies
    start=time.perf_counter()
    op=LinearOperator((dims,dims),matvec=hop,dtype=float)
    e,v=eigsh(op,k=1,which='SA',v0=probes[0],tol=1e-12,maxiter=500,ncv=40)
    vector=v[:,0];energy=float(e[0])
    row.update(energy=energy,eigen_residual=float(np.linalg.norm(mat@vector-energy*vector)),
               determinant_residual=float(np.linalg.norm(hop(vector)-energy*vector)),
               eigenvector_norm_error=float(abs(vector@vector-1)),operator_calls=calls,
               eigensolver_seconds=time.perf_counter()-start,
               wavefunction_spin_square=float(fci.spin_op.spin_square(expand(vector,n),n,(1,1))[0]))
    if row['eigen_residual']>guard['eigen_l2_max'] or row['eigenvector_norm_error']>guard['norm_max']:
        row['failure_stage']='independent_eigen_residual'
    row['wall_seconds']=time.perf_counter()-started
    return row,c,vector
