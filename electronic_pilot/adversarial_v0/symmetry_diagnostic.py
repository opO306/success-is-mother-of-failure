"""Check angular convention algebra and measure the failed inversion tail.

Even projection is a diagnostic applied to the unchanged saved state. It is
not a replacement result or tolerance change, and cannot make the audit PASS.
"""
from pathlib import Path
import math
import numpy as np
import mpmath as mp
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from .symmetry import operators,angular_generator

def monomials(l):return [(a,b,l-a-b) for a in range(l,-1,-1) for b in range(l-a,-1,-1)]

def cart_generator(l):
    powers=monomials(l);lookup={p:i for i,p in enumerate(powers)};g=np.zeros((len(powers),len(powers)))
    for i,(a,b,c) in enumerate(powers):
        if a:g[i,lookup[(a-1,b+1,c)]]=-a
        if b:g[i,lookup[(a+1,b-1,c)]]=b
    return g

def main():
    root=Path('runs/h2_adversarial_v0/symmetry_diagnostic_v0');root.mkdir(parents=True,exist_ok=False)
    definitions=Path('runs/h2_adversarial_v0/definitions_v1/basis_definitions.json')
    original=Path('/mnt/c/Users/zun24/성공은 실패의 어머니/runs/h2_qz44_sealed_v1/curve/R_0.4.npz')
    base=Path('docs/active/h2_ground_state_audit_v0/evidence');vp=base/'v_direct_reproduced.npy';op=base/'direct_state_order.npy'
    matrix_path=Path('runs/h2_ground_state_audit_v0/validation_v0/H_SC.npy')
    # The exact independently assembled matrix path is supplied by prior evidence.
    if not matrix_path.exists():matrix_path=Path('runs/h2_ground_state_audit_v0/validation_v0/H_ind_SC.npy')
    bindings={str(p):sha(p) for p in [definitions,original,vp,op,Path(__file__),Path('electronic_pilot/adversarial_v0/symmetry.py')]}
    write(root/'input_seal.json',dict(bindings=bindings,diagnostic_projection_not_replacement=True))
    row=read(definitions)['records']['cc-pVQZ'];J,G,F=operators(row);angular={}
    for sh in row['actual_shells']:
        l=sh['l'];p=np.asarray(sh['polynomial_map']);g,f=angular_generator(l);cart=cart_generator(l)
        cartf=np.diag([(-1)**b for a,b,c in monomials(l)])
        angular[str(l)]=dict(generator_polynomial_identity_max=float(abs(p.T@cart-g@p.T).max()),
                            reflection_polynomial_identity_max=float(abs(p.T@cartf-f@p.T).max()))
    from pyscf import gto
    mol=gto.M(atom=[('H',(0,0,-.2)),('H',(0,0,.2))],basis={'H':row['raw_PySCF_H_basis']},unit='Bohr',spin=0,cart=False,verbose=0)
    points=np.array([[.23,.41,.57],[-.61,.19,-.37],[.43,-.29,.13]])
    values=mol.eval_gto('GTOval_sph',points);inverted=mol.eval_gto('GTOval_sph',-points)
    reflected=mol.eval_gto('GTOval_sph',points*np.array([1.,-1.,1.]))
    conventions=dict(angular_algebra=angular,inversion_function_values_max=float(abs(inverted-values@J.T).max()),
                     reflection_function_values_max=float(abs(reflected-values@F.T).max()),AO_integral_calls=0)
    data=np.load(original,allow_pickle=False);v=np.load(vp);order=np.load(op);mp.mp.dps=80
    c=mp.matrix(data['c'].tolist());s=mp.matrix(data['s'].tolist());u=c**-1*mp.matrix(J.T.tolist())*c
    V=mp.zeros(len(c))
    for amp,(i,j) in zip(v,order):
        i,j=int(i),int(j)
        if i==j:V[i,i]=mp.mpf(float(amp))
        else:V[i,j]=V[j,i]=mp.mpf(float(amp))/mp.sqrt(2)
    invertedV=u*V*u.T;even=(V+invertedV)/2;odd=(V-invertedV)/2
    metric=c.T*s*c
    def norm2(a):
        left=metric*a.T*metric
        return mp.fsum(left[i,j]*a[j,i] for i in range(len(c)) for j in range(len(c)))
    tail=dict(odd_S_metric_norm_squared=str(norm2(odd)),even_S_metric_norm_squared=str(norm2(even)),
              unchanged_state_S_metric_norm_squared=str(norm2(V)),strict_symmetry_status='UNRESOLVED; original inversion residual remains above 1e-10')
    evenv=np.asarray([float(even[int(i),int(j)]*(1 if i==j else mp.sqrt(2))) for i,j in order]);evenv/=np.linalg.norm(evenv)
    np.save(root/'diagnostic_even_projected_vector.npy',evenv,allow_pickle=False)
    # Reuse the already independently checked matrix only to measure this perturbation.
    if matrix_path.exists():
        matrix=np.load(matrix_path,allow_pickle=False);E=float(v@matrix@v/(v@v));Eeven=float(evenv@matrix@evenv)
        tail.update(matrix_sha256=sha(matrix_path),Rayleigh_original=E,Rayleigh_even_projection=Eeven,
                    Rayleigh_shift_hartree=Eeven-E,vector_change_l2=float(np.linalg.norm(evenv-v)),
                    diagnostic_only_not_recomputed_ground_state=True)
    else:tail['Rayleigh_shift_status']='UNAVAILABLE: prior matrix path not found; vector alone saved'
    write(root/'diagnostic.json',dict(conventions=conventions,inversion_tail=tail,not_certified=True))
    assert bindings=={p:sha(p) for p in bindings}
    print('SYMMETRY DIAGNOSTIC',conventions,tail,flush=True)

if __name__=='__main__':main()
