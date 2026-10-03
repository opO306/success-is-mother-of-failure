"""Local causal measurements on the fixed-C factorial; no eigensolve."""
from pathlib import Path
import numpy as np
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from .factorial import expand8,pack8,lower
from .transform import difference

def main():
    root=Path('runs/h2_adversarial_v0/conditioning_v0');root.mkdir(parents=True,exist_ok=False)
    original=Path('/mnt/c/Users/zun24/성공은 실패의 어머니/runs/h2_qz44_sealed_v1/curve/R_0.4.npz')
    fact=Path('runs/h2_adversarial_v0/factorial_v0');native=Path('runs/h2_adversarial_v0/libint_v0')
    inputs=[original,Path(__file__),fact/'summary.json',*[fact/(f'cell_{a}{b}')/'g.npy' for a in (0,1) for b in (0,1)],
            native/'g.npy',native/'s.npy',native/'t.npy',native/'v.npy']
    bindings={str(p):sha(p) for p in inputs};write(root/'input_seal.json',dict(bindings=bindings))
    data=np.load(original,allow_pickle=False);c=data['c'];n=len(c);g0=expand8(data['eri_s8'],n);g1=expand8(pack8(np.load(native/'g.npy')),n)
    s1=lower(np.load(native/'s.npy'));ds=s1-data['s'];dh=lower(np.load(native/'t.npy')+np.load(native/'v.npy'))-data['h']
    transformed_overlap_delta=c.T@ds@c
    eigen=np.linalg.eigvalsh(data['s']);stats=dict(condition_S=float(eigen[-1]/eigen[0]),
       condition_C=float(np.linalg.cond(c)),max_absolute_C=float(abs(c).max()),
       AO_delta_S_max=float(abs(ds).max()),AO_delta_h_max=float(abs(dh).max()),AO_delta_ERI_max=float(abs(g1-g0).max()),
       transformed_overlap_delta_l2=float(np.linalg.norm(transformed_overlap_delta,ord=2)))
    records=[]
    cells=[read(fact/(f'cell_{a}{b}')/'result.json') for a in (0,1) for b in (0,1)]
    selected={tuple(row['ERI_symmetry']['pair']['index']) for row in cells}
    selected.update(tuple(row['difference_from_baseline_g']['index']) for row in cells)
    arrays=[np.load(fact/(f'cell_{a}{b}')/'g.npy',mmap_mode='r') for a in (0,1) for b in (0,1)]
    for idx in sorted(selected):
        i,j,k,l=idx
        weight=np.einsum('a,b,c,d->abcd',c[:,i],c[:,j],c[:,k],c[:,l],optimize=True)
        terms=weight*(g1-g0);largest=np.unravel_index(int(abs(terms).argmax()),terms.shape)
        records.append(dict(MO_index=list(idx),cell_values=[float(a[idx]) for a in arrays],
          direct_AO_engine_effect=np.sum(terms).item(),absolute_weighted_AO_delta_sum=float(abs(terms).sum()),
          largest_weighted_AO_delta_index=list(map(int,largest)),largest_weighted_contribution=float(terms[largest]),
          largest_component_AO_delta=float((g1-g0)[largest]),largest_component_C4_weight=float(weight[largest]),
          baseline_sum_absolute_integral_terms=float(abs(weight*g0).sum())))
    write(root/'diagnostic.json',dict(conditioning=stats,selected_MO_elements=records,
          measurements_not_rigorous_bounds=True,all_AO_inputs_binary64=True,high_precision_integrals=False))
    assert bindings=={p:sha(p) for p in bindings}
    print('CONDITIONING',stats,flush=True)

if __name__=='__main__':main()
