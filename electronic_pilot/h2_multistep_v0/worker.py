"""Same immutable V5Z kernels/guards, arbitrary sealed request geometry.

No historical hash scan here. Actual kernels/config are loaded exclusively
from the campaign snapshot. Start/end audit binds those bytes.
"""
import argparse,json,math,resource,sys,time
from pathlib import Path
import numpy as np
import scipy
from scipy.linalg import eigh
from electronic_pilot.h2_nuclear_v0.scalar import geometry
from electronic_pilot.h2_force_v0.interface import BASIS,MODE,GUARDS,refusal
from electronic_pilot.ao_micro_v0.reuse import canonical_ao,transform
from electronic_pilot.numerical_cause.core import coordinates
from electronic_pilot.h2_multistep_v0.kit import persist,sha

def run(request_path,request_sha,snapshot,dest):
    snapshot=Path(snapshot).resolve();dest=Path(dest);dest.mkdir(exist_ok=False)
    if sha(request_path)!=request_sha:raise ValueError('request hash')
    request=json.loads(Path(request_path).read_text(encoding='utf8'))
    g=geometry(request['requested_R'])
    from pyscf import gto,lib,__version__ as pyscf_version
    lib.num_threads(1)
    spec=json.loads((snapshot/'config/basis.json').read_text(encoding='utf8'))['records'][BASIS]
    start=time.perf_counter()
    row=dict(requested_R=request['requested_R'],label=request['label'],step_index=request['step_index'],
        geometry=g,actual_stored_positions_bohr=None,basis=BASIS,mode=MODE,guards=GUARDS,
        arithmetic='IEEE binary64',driver='evr',energy_convention='EBO=Ee+1/R',
        accepted=False,failure_stage=None,total_energy_hartree=None)
    try:
        mol=gto.M(atom=[('H',xyz) for xyz in g['positions_bohr']],unit='Bohr',basis={'H':spec['raw_PySCF_H_basis']},
            spin=0,charge=0,cart=False,symmetry=False,verbose=0)
        row['actual_stored_positions_bohr']=mol.atom_coords(unit='Bohr').tolist()
        if row['actual_stored_positions_bohr']!=g['positions_bohr']:raise ValueError('stored positions')
        s,h,g8=canonical_ao(mol);ev=eigh(s,eigvals_only=True)
        np.save(dest/'overlap_spectrum.npy',ev,allow_pickle=False)
        row.update(basis_size=len(s),Smin=float(ev[0]),condition=float(ev[-1]/ev[0]))
        if ev[0]<=GUARDS['Smin_floor']:row['failure_stage']='overlap_floor'
        else:
            c=coordinates(s,h,'cholesky');orth=float(np.linalg.norm(c.T@s@c-np.eye(len(s)),ord=2))
            row['orthogonality_l2']=orth
            if orth>GUARDS['orth_l2_max']:row['failure_stage']='orthonormalization'
            else:
                final,c=transform(mol,s,h,g8,MODE,GUARDS,solve=True);row.update(final)
                np.savez(dest/'AO_C.npz',s=s,h=h,c=c,positions=mol.atom_coords(unit='Bohr'))
        reason=refusal(row)
        if reason:row.update(accepted=False,failure_stage=row['failure_stage'] or reason,total_energy_hartree=None,electronic_energy_hartree=None)
    except Exception as exc:
        row.update(accepted=False,failure_stage='calculator_exception',exception=repr(exc),total_energy_hartree=None,electronic_energy_hartree=None)
    row.update(runtime_seconds=time.perf_counter()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        numerical_guard_status='ACCEPTED' if row['accepted'] else 'REFUSED',
        runtime_module_origins={name:Path(module.__file__).resolve().as_posix() for name,module in list(sys.modules.items())
            if name.startswith('electronic_pilot') and getattr(module,'__file__',None)},
        external_versions=dict(numpy=np.__version__,scipy=scipy.__version__,pyscf=pyscf_version),
        NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True)
    nonfinite={k:repr(v) for k,v in row.items() if isinstance(v,float) and not math.isfinite(v)}
    for key in nonfinite:row[key]=None
    if nonfinite:row['nonfinite_diagnostics']=nonfinite
    persist(dest/'result.json',row)
    print(request['step_index'],request['label'],row['numerical_guard_status'],row['total_energy_hartree'],flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--sha',required=True)
    p.add_argument('--snapshot',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    run(a.request,a.sha,a.snapshot,a.output)
