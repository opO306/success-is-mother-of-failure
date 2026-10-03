"""Narrow post-disagreement AO checks, chosen by state-weighted influence."""
from pathlib import Path
import time
import mpmath as mp
import numpy as np
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from electronic_pilot.reconstruction_v0.post import orbitals
from electronic_pilot.ao_micro_v0.gaussian import eri


def canonical(idx):
    i,j=sorted(idx[:2],reverse=True);k,l=sorted(idx[2:],reverse=True)
    return (i,j,k,l) if i*(i+1)//2+j>=k*(k+1)//2+l else (k,l,i,j)


def main():
    root=Path('runs/h2_reconstruction_v0/run_io_v2');out=Path('runs/h2_reconstruction_v0/cause_spots_v0');out.mkdir(exist_ok=False)
    inp=Path('runs/h2_reconstruction_v0/influence_v0/influence.json');definition=Path('docs/active/h2_adversarial_v0/evidence/basis_definitions.json')
    rows=read(inp)['largest_16_weighted_AO_ERI_differences'];classes=[]
    for row in rows:
        idx=canonical(row['index'])
        if idx not in classes:classes.append(idx)
        if len(classes)==4:break
    paths=[Path(__file__),Path('electronic_pilot/reconstruction_v0/post.py'),Path('electronic_pilot/ao_micro_v0/gaussian.py'),inp,definition]
    paths.extend(root/a/'fixed_input/g_canonical.bin' for a in ('L','I'))
    binding={str(p):sha(p) for p in paths};orbs=orbitals(read(definition)['records']['cc-pVQZ'])
    write(out/'seal.json',dict(bindings=binding,classes=classes,selection='first four distinct canonical classes among pre-preserved largest sixteen absolute state-weighted AO variations; no reference or new ground solve',decimal_digits=[60,80],convergence_abs='1e-45',physical_space_unchanged=True))
    g={a:np.memmap(root/a/'fixed_input/g_canonical.bin',dtype='<f8',mode='r',shape=(60,)*4) for a in ('L','I')};result=[];start=time.perf_counter()
    for idx in classes:
        calc=[]
        for dps in (60,80):
            with mp.workdps(dps):
                perms=[idx,(idx[2],idx[3],idx[0],idx[1]),(idx[1],idx[0],idx[2],idx[3])]
                calc.append(dict(decimal_digits=dps,independent_values=[str(eri(*(orbs[i] for i in p))) for p in perms]))
        with mp.workdps(100):
            high=list(map(mp.mpf,calc[-1]['independent_values']));low=list(map(mp.mpf,calc[0]['independent_values']))
            errors={a:mp.mpf(float(g[a][idx]))-high[0] for a in ('L','I')};weights=mp.fsum(mp.mpf(row['weight']) for row in rows if canonical(row['index'])==idx)
            result.append(dict(index=idx,calculations=calc,precision_change=str(max(abs(a-b) for a,b in zip(high,low))),permutation_spread=str(max(high)-min(high)),
                         AO_signed_errors={a:str(x) for a,x in errors.items()},closer_for_this_entry=min(errors,key=lambda a:abs(errors[a])),
                         sampled_state_weight_sum=str(weights),sampled_signed_energy_error={a:str(weights*x) for a,x in errors.items()}))
    write(out/'cause_spots.json',dict(classes=result,runtime_seconds=time.perf_counter()-start,new_eigensolver_calls=0,new_ground_energies=0,full_AO_accuracy_bound=None,
         evidence='independent higher-accuracy integration of exactly the supplied dyadic Gaussian definition, converged 60/80 digits; empirical local evidence, not an engine-wide oracle or rigorous enclosure',
         selected_weight_scope='only preserved top-sixteen entries of four classes; no full permutation multiplicity or unsampled AO terms inferred',no_arm_output_corrected=True))
    if binding!={p:sha(p) for p in binding}:raise ValueError('cause spot source/input drift')
    write(out/'postcheck.json',dict(unchanged=True,bindings=binding))


if __name__=='__main__':main()
