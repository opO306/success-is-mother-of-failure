"""Connected AO engine x MO contraction experiment with fixed saved C/v.

Each engine uses the SAME pre-existing eightfold canonical AO representative
rule in both transformation arms. Raw native AO asymmetry is separately saved.
No MO tensor or Hamiltonian is averaged, repaired, or cut off.
"""
from pathlib import Path
import time,resource
import numpy as np
from scipy.linalg import eigh
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from electronic_pilot.ground_state_audit_v0 import operator
from electronic_pilot.ao_micro_v0.reuse import one_electron_unique
from .transform import four,diagnostic,difference,interaction

def pair_indices(n):
    i,j=np.tril_indices(n);return i,j

def expand8(packed,n):
    a=np.arange(n);hi=np.maximum(a[:,None],a);lo=np.minimum(a[:,None],a)
    pairs=hi*(hi+1)//2+lo
    first=pairs[:,:,None,None];second=pairs[None,None,:,:]
    hi=np.maximum(first,second);lo=np.minimum(first,second)
    return packed[hi*(hi+1)//2+lo]

def pack8(raw):
    i,j=pair_indices(len(raw));a,b=np.tril_indices(len(i))
    return raw[i[a],j[a],i[b],j[b]]

def lower(a):
    i,j=np.tril_indices(len(a));out=np.empty_like(a);out[i,j]=a[i,j];out[j,i]=a[i,j];return out

def main():
    from pyscf import ao2mo,lib
    lib.num_threads(1);root=Path('runs/h2_adversarial_v0/factorial_v0');root.mkdir(parents=True,exist_ok=False)
    native=Path('runs/h2_adversarial_v0/libint_v0')
    original=Path('/mnt/c/Users/zun24/성공은 실패의 어머니/runs/h2_qz44_sealed_v1/curve/R_0.4.npz')
    vp=Path('docs/active/h2_ground_state_audit_v0/evidence/v_direct_reproduced.npy')
    paths=[original,vp,Path(__file__),Path('electronic_pilot/adversarial_v0/transform.py'),
           Path('electronic_pilot/ao_micro_v0/reuse.py'),Path('electronic_pilot/ground_state_audit_v0/operator.py'),
           Path('electronic_pilot/ao_micro_v0/protocol.json'),*[native/(x+'.npy') for x in ('s','t','v','g')]]
    bindings={str(p):sha(p) for p in paths};guard=read('electronic_pilot/ao_micro_v0/protocol.json')['guards']
    write(root/'input_seal.json',dict(bindings=bindings,guards=guard,C_fixed=True,v_fixed=True,
       AO_representative='existing lower-triangle S/h and eightfold lower pair packed representative, no average',
       energy_accepted_only_with_all_existing_guards=True))
    base=np.load(original,allow_pickle=False);c=base['c'];v=np.load(vp,allow_pickle=False);n=len(c)
    inputs=[(base['s'],base['h'],base['eri_s8']),
            (lower(np.load(native/'s.npy')),lower(np.load(native/'t.npy')+np.load(native/'v.npy')),pack8(np.load(native/'g.npy')))]
    rows=[];baseline_h=baseline_g=None
    for engine,(s,h,g8) in enumerate(inputs):
        ao=expand8(g8,n)
        assert np.array_equal(ao,ao2mo.restore(1,g8,n))
        for transform in (0,1):
            started=time.perf_counter();label=f'cell_{engine}{transform}';dest=root/label;dest.mkdir()
            if transform==0:
                hm=one_electron_unique(h,c);g=ao2mo.restore(1,ao2mo.incore.full(g8,c,compact=True),n)
            else:hm=c.T@h@c;g=four(ao,c)
            np.save(dest/'h.npy',hm,allow_pickle=False);np.save(dest/'g.npy',g,allow_pickle=False)
            if engine==0 and transform==0:baseline_h=hm.copy();baseline_g=g.copy()
            H,states=operator.dense(hm,g);asym=float(abs(H-H.T).max());action=H@v
            E0=-2.61803113362157;rayleigh=float(v@action/(v@v));ev=eigh(s,eigvals_only=True)
            row=dict(engine='libcint_canonical' if engine==0 else 'Libint_canonical',
                     transform='historical_compact' if transform==0 else 'independent_direct',cell=label,
                     Smin=float(ev[0]),condition=float(ev[-1]/ev[0]),orthogonality_l2=float(np.linalg.norm(c.T@s@c-np.eye(n),ord=2)),
                     h_asymmetry=float(abs(hm-hm.T).max()),ERI_symmetry=diagnostic(g),
                     difference_from_baseline_h=difference(hm,baseline_h),difference_from_baseline_g=difference(g,baseline_g),
                     H_asymmetry=asym,same_v_rayleigh_hartree=rayleigh,same_v_action_delta_l2=float(np.linalg.norm(action-E0*v)),
                     electronic_energy_hartree=None,BO_energy_hartree=None,eigen_residual_l2=None,accepted=False,failure_stage=None,
                     full_matrix_sha256=__import__('hashlib').sha256(H.tobytes()).hexdigest())
            for stage,failed in [('overlap_floor',row['Smin']<=guard['Smin_floor']),('orthonormalization',row['orthogonality_l2']>guard['orth_l2_max']),('singlet_hermiticity',asym>guard['H_asym_max'])]:
                if failed:row['failure_stage']=stage;break
            if row['failure_stage'] is None:
                e,w=eigh(H,subset_by_index=(0,1),driver='evr');res=float(np.linalg.norm(H@w[:,0]-e[0]*w[:,0]));norm=float(abs(w[:,0]@w[:,0]-1))
                row.update(electronic_energy_hartree=float(e[0]),BO_energy_hartree=float(e[0])+2.5,eigen_residual_l2=res,vector_norm_error=norm,
                           next_singlet_gap=float(e[1]-e[0]))
                if res>guard['eigen_l2_max'] or norm>guard['norm_max']:row['failure_stage']='eigensolve'
                else:row['accepted']=True
            row.update(runtime_seconds=time.perf_counter()-started,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            write(dest/'result.json',row);rows.append(row);print('FACTORIAL',label,row['accepted'],row['failure_stage'],rayleigh,flush=True)
            del H,g,hm
        del ao
    vals=[r['same_v_rayleigh_hartree'] for r in rows]
    write(root/'summary.json',dict(rows=rows,same_v_rayleigh_interaction_hartree=interaction(*[vals[i] for i in (0,2,1,3)]),
        accepted_ground_energy_interaction_hartree=None if not all(r['accepted'] for r in rows) else interaction(*[rows[i]['electronic_energy_hartree'] for i in (0,2,1,3)]),
        interaction_is_not_an_error_bound=True,not_certified=True))
    assert bindings=={p:sha(p) for p in bindings};write(root/'postcheck.json',dict(unchanged=True,bindings=bindings))

if __name__=='__main__':main()
