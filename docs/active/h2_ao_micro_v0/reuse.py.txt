"""Canonical exact-integral reuse; no matrix averaging or H repair.

AO S/h: explicitly evaluate lower shell/index representatives and reuse.
AO ERI: unique eightfold packed integral driver.
MO ERI: compact fourfold transform; identical within-pair quantities reused.
MO pair interchange is still independently computed and its error measured.
Full singlet assembly is the unchanged historical function.
"""
import numpy as np
from scipy.linalg import eigh
from electronic_pilot.numerical_cause.core import coordinates,symmetry,digest
from electronic_pilot.solver import singlet_matrix


def canonical_ao(mol):
    n=mol.nao_nr();s=np.empty((n,n));h=np.empty((n,n));loc=mol.ao_loc_nr()
    for i in range(mol.nbas):
        for j in range(i+1):
            sb=mol.intor_by_shell('int1e_ovlp_sph',(i,j))
            hb=mol.intor_by_shell('int1e_kin_sph',(i,j))+mol.intor_by_shell('int1e_nuc_sph',(i,j))
            for p in range(loc[i],loc[i+1]):
                for q in range(loc[j],loc[j+1]):
                    if p<q: continue
                    s[p,q]=s[q,p]=sb[p-loc[i],q-loc[j]]
                    h[p,q]=h[q,p]=hb[p-loc[i],q-loc[j]]
    return s,h,mol.intor('int2e',aosym='s8')


def one_electron_unique(h,c):
    # Only one bilinear evaluation for each exact transpose class. Matrix h
    # is never averaged; the counterpart is an identical stored quantity.
    n=len(c); hc=h@c; result=np.empty((n,n))
    for i in range(n):
        for j in range(i+1):
            result[i,j]=result[j,i]=np.dot(c[:,i],hc[:,j])
    return result


def first_failure(row,guard):
    checks=(('overlap_floor',row['Smin']<=guard['Smin_floor']),
            ('orthonormalization',row['orthogonality_l2']>guard['orth_l2_max']),
            ('singlet_hermiticity',row['singlet_asymmetry']>guard['H_asym_max']))
    for stage,fail in checks:
        if fail: return stage
    if row.get('eigen_residual_l2') is not None:
        if row['eigen_residual_l2']>guard['eigen_l2_max'] or row['vector_norm_error']>guard['norm_max'] or not np.isfinite(row['total_energy_hartree']):
            return 'eigensolve'
    return None


def transform(mol,s,h,g8,mode,guard,solve=False):
    from pyscf import ao2mo
    n=len(s);c=coordinates(s,h,'cholesky')
    if mode=='AO_reuse_only':
        # Full AO-expanded ndarray follows the old uncompressed transformation.
        eri=ao2mo.kernel(ao2mo.restore(1,g8,n),c,compact=False).reshape((n,)*4)
        hm=c.T@h@c
    elif mode=='AO_and_MO_integral_reuse':
        # This changes the summation/representation, not the integral operator.
        eri=ao2mo.restore(1,ao2mo.incore.full(g8,c,compact=True),n)
        hm=one_electron_unique(h,c)
    else: raise ValueError('unknown predeclared mode')
    mat,*_=singlet_matrix(hm,eri)
    ev=eigh(s,eigvals_only=True)
    row=dict(mode=mode,basis_size=n,singlet_dimension=len(mat),Smin=float(ev[0]),condition=float(ev[-1]/ev[0]),
        overlap_eigenvalues=ev.tolist(),orthogonality_l2=float(np.linalg.norm(c.T@s@c-np.eye(n),ord=2)),
        transformed_h_asymmetry=float(abs(hm-hm.T).max()),transformed_ERI_symmetry=symmetry(eri),
        singlet_asymmetry=float(abs(mat-mat.T).max()),max_abs_C=float(abs(c).max()),
        accepted=False,failure_stage=None,eigen_residual_l2=None,vector_norm_error=None,
        electronic_energy_hartree=None,total_energy_hartree=None,
        AO_sha256={'s':digest(s),'h':digest(h),'eri_s8':digest(g8)},
        iteration_count=None,not_certified=True)
    row['failure_stage']=first_failure(row,guard)
    if solve and row['failure_stage'] is None:
        e,v=eigh(mat,subset_by_index=(0,1),driver='evr')
        row.update(electronic_energy_hartree=float(e[0]),total_energy_hartree=float(e[0])+float(mol.energy_nuc()),
            nuclear_repulsion_hartree=float(mol.energy_nuc()),eigen_residual_l2=float(np.linalg.norm(mat@v[:,0]-e[0]*v[:,0])),
            vector_norm_error=float(abs(v[:,0]@v[:,0]-1)))
        row['failure_stage']=first_failure(row,guard)
        row['accepted']=row['failure_stage'] is None
    return row,c
