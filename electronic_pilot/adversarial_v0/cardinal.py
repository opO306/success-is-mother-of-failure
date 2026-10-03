"""One-point representation diagnostic; historical numerical path unchanged."""
import argparse,time,resource
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from electronic_pilot.ao_micro_v0.reuse import canonical_ao,transform
from electronic_pilot.numerical_cause.core import coordinates

def run(name,output,definitions):
    from pyscf import gto,lib
    lib.num_threads(1);dest=Path(output);dest.mkdir(parents=True,exist_ok=False)
    spec=read(definitions)['records'][name];guard=read('electronic_pilot/ao_micro_v0/protocol.json')['guards']
    bindings={p:sha(p) for p in [definitions,__file__,'electronic_pilot/ao_micro_v0/reuse.py',
             'electronic_pilot/numerical_cause/core.py','electronic_pilot/solver.py','electronic_pilot/ao_micro_v0/protocol.json']}
    write(dest/'input_seal.json',dict(name=name,R_bohr=.4,bindings=bindings,guards=guard))
    start=time.perf_counter();mol=gto.M(atom=[('H',(0,0,-.2)),('H',(0,0,.2))],unit='Bohr',
         basis={'H':spec['raw_PySCF_H_basis']},spin=0,charge=0,cart=False,symmetry=False,verbose=0)
    s,h,g8=canonical_ao(mol);ev=eigh(s,eigvals_only=True);np.save(dest/'overlap_spectrum.npy',ev,allow_pickle=False)
    row=dict(basis=name,R_bohr=.4,basis_size=len(s),Smin=float(ev[0]),condition=float(ev[-1]/ev[0]),accepted=False,
             total_energy_hartree=None,electronic_energy_hartree=None,orthogonality_l2=None,failure_stage=None,
             eigen_residual_l2=None,transformed_ERI_symmetry=None,singlet_asymmetry=None)
    if ev[0]<=guard['Smin_floor']:row['failure_stage']='overlap_floor'
    else:
        c=coordinates(s,h,'cholesky');orth=float(np.linalg.norm(c.T@s@c-np.eye(len(s)),ord=2));row['orthogonality_l2']=orth
        if orth>guard['orth_l2_max']:row['failure_stage']='orthonormalization'
        else:
            final,c=transform(mol,s,h,g8,'AO_and_MO_integral_reuse',guard,solve=True);row.update(final)
            np.savez(dest/'AO_C.npz',s=s,h=h,eri_s8=g8,c=c)
    row.update(runtime_seconds=time.perf_counter()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               not_certified=True,diagnostic_only=True,reference_BO_hartree=-.120230341178823)
    if row['accepted']:row['signed_reference_difference_hartree']=row['total_energy_hartree']+.120230341178823
    write(dest/'result.json',row)
    if bindings!={p:sha(p) for p in bindings}:raise ValueError('sealed source/input changed')
    write(dest/'postcheck.json',dict(unchanged=True,bindings=bindings))
    print('CARDINAL',name,row['accepted'],row['failure_stage'],row['total_energy_hartree'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--basis',required=True);p.add_argument('--output',required=True)
    p.add_argument('--definitions',required=True);a=p.parse_args();run(a.basis,a.output,a.definitions)
