"""Fresh workers call the V0 functions unchanged; no reference input to worker."""
import argparse
import json
import multiprocessing as mp
import time
import traceback
from pathlib import Path
from .seal import make_seal,verify,sha


def worker(r,output,guard,frozen):
    import resource
    started=time.perf_counter()
    try:
        verify(frozen)
        import numpy as np
        from pyscf import ao2mo
        from electronic_pilot.numerical_cause.core import ao_data,symmetry
        from electronic_pilot.ao_micro_v0.reuse import canonical_ao,transform
        # Same numerical call order as the final V0 C_v1 worker. Raw full AO
        # generation is diagnostic; it never replaces the canonical AO inputs.
        mol,raw_s,raw_h,raw_g=ao_data('cc-pVQZ',r)
        s,h,g8=canonical_ao(mol);expanded=ao2mo.restore(1,g8,len(s))
        ao=dict(raw_S_asymmetry=float(abs(raw_s-raw_s.T).max()),raw_h_asymmetry=float(abs(raw_h-raw_h.T).max()),raw_ERI_symmetry=symmetry(raw_g),
            canonical_S_asymmetry=float(abs(s-s.T).max()),canonical_h_asymmetry=float(abs(h-h.T).max()),canonical_ERI_symmetry=symmetry(expanded),
            change_max=dict(S=float(abs(raw_s-s).max()),h=float(abs(raw_h-h).max()),ERI=float(abs(raw_g-expanded).max())),
            lower_representatives_match_raw=bool(np.array_equal(s[np.tril_indices(len(s))],raw_s[np.tril_indices(len(s))]) and np.array_equal(h[np.tril_indices(len(s))],raw_h[np.tril_indices(len(s))])))
        del raw_g,expanded
        solve_started=time.perf_counter()
        record,c=transform(mol,s,h,g8,'AO_and_MO_integral_reuse',guard,solve=True)
        record.update(kind='curve',basis='cc-pVQZ',R_bohr=r,electrons=2,sector='singlet',wall_seconds=time.perf_counter()-solve_started)
        artifact=Path(output).with_suffix('.npz')
        np.savez_compressed(artifact,s=s,h=h,eri_s8=g8,c=c)
        verify(frozen)
        row=dict(R_bohr=r,basis='cc-pVQZ',paths=[record],AO=ao,artifact_sha256=sha(artifact),source_seal_valid=True)
    except Exception as exc:
        row=dict(R_bohr=r,basis='cc-pVQZ',status='IMPLEMENTATION_ERROR_PRESERVED',error=repr(exc),traceback=traceback.format_exc())
    row.update(wall_seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    Path(output).write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    seal=make_seal(root)
    rows=[];started=time.perf_counter()
    bound=seal['frozen_sha256']|seal['extension_sha256']
    for r in seal['R_grid_bohr']:
        verify(bound)
        output=root/f'R_{r:g}.json';start=time.perf_counter()
        job=mp.get_context('spawn').Process(target=worker,args=(r,str(output),seal['numerical_guards'],bound))
        job.start();job.join()
        if job.exitcode!=0 or not output.exists(): raise RuntimeError(f'worker exit {job.exitcode}; no retry')
        row=json.loads(output.read_text());row['worker_wall_with_startup_seconds']=time.perf_counter()-start
        rows.append(row)
        (root/'results.json').write_text(json.dumps(dict(seal_sha256=sha(root/'seal.json'),rows=rows,wall_seconds=time.perf_counter()-started),indent=2)+'\n')
        if row.get('status')=='IMPLEMENTATION_ERROR_PRESERVED': raise RuntimeError('implementation error preserved; STOP')
        record=row['paths'][0]
        print(len(rows),44,r,record['accepted'],record['failure_stage'],record['total_energy_hartree'],flush=True)
    verify(bound);verify(seal['runtime_sha256'])
    (root/'post_run_seal_check.json').write_text(json.dumps(dict(verified=True,frozen_count=len(seal['frozen_sha256']),extension_count=len(seal['extension_sha256']),runtime_count=len(seal['runtime_sha256']),results_sha256=sha(root/'results.json')),indent=2)+'\n')

if __name__=='__main__': main()
