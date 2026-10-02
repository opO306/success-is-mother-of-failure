"""Two conditional stages with immutable fresh-worker logs and source seals."""
import argparse
import hashlib
import json
import multiprocessing as mp
import resource
import subprocess
import time
import traceback
from pathlib import Path
import numpy as np
from electronic_pilot.numerical_cause.core import ao_data,symmetry
from .reuse import canonical_ao,transform


def worker(r,output,stage,selection,guard):
    started=time.perf_counter()
    try:
        from pyscf import ao2mo
        mol,raw_s,raw_h,raw_g=ao_data('cc-pVQZ',r)
        s,h,g8=canonical_ao(mol);expanded=ao2mo.restore(1,g8,len(s))
        raw=json.loads((Path(selection)/f'R_{r:g}.json').read_text())
        row=dict(R_bohr=r,basis='cc-pVQZ',AO_raw=dict(S_asymmetry=float(abs(raw_s-raw_s.T).max()),h_asymmetry=float(abs(raw_h-raw_h.T).max()),ERI_symmetry=symmetry(raw_g)),
            AO_reused=dict(S_asymmetry=float(abs(s-s.T).max()),h_asymmetry=float(abs(h-h.T).max()),ERI_symmetry=symmetry(expanded)),
            AO_change_max=dict(S=float(abs(raw_s-s).max()),h=float(abs(raw_h-h).max()),ERI=float(abs(raw_g-expanded).max())),
            selected_class_representative=dict(indices=raw['ERI_class']['canonical'],raw_value=float(raw_g[tuple(raw['ERI_class']['canonical'])]),reused_value=float(expanded[tuple(raw['ERI_class']['canonical'])])),paths=[])
        del raw_g,expanded
        modes=['AO_reuse_only','AO_and_MO_integral_reuse'] if stage=='B' else ['AO_and_MO_integral_reuse']
        for mode in modes:
            path_started=time.perf_counter()
            record,c=transform(mol,s,h,g8,mode,guard,solve=stage=='C')
            record['wall_seconds']=time.perf_counter()-path_started
            row['paths'].append(record)
        artifact=Path(output).with_suffix('.npz')
        np.savez_compressed(artifact,s=s,h=h,eri_s8=g8,c=c)
        row['artifact_sha256']=hashlib.sha256(artifact.read_bytes()).hexdigest()
    except Exception as exc:
        row=dict(R_bohr=r,status='IMPLEMENTATION_ERROR_PRESERVED',error=repr(exc),traceback=traceback.format_exc())
    row.update(wall_seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    Path(output).write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--stage',choices=('B','C'),required=True);p.add_argument('--suffix',default='');args=p.parse_args()
    root=Path(args.root);spec=json.loads(Path(__file__).with_name('protocol.json').read_text())
    a=json.loads((root/'spot/results.json').read_text())
    if not a['stage_B_gate_supported'] or len(a['rows'])!=4: raise ValueError('Stage A gate incomplete')
    gates={'A_sha256':hashlib.sha256((root/'spot/results.json').read_bytes()).hexdigest()}
    if args.stage=='C':
        b=json.loads((root/('B'+args.suffix)/'results.json').read_text())
        if len(b['rows'])!=4 or any(x['paths'][1]['failure_stage'] is not None for x in b['rows']):
            raise ValueError('Stage B symmetry-aware representation still refused; no C expansion')
        gates['B_sha256']=hashlib.sha256((root/('B'+args.suffix)/'results.json').read_bytes()).hexdigest()
    target=root/(args.stage+args.suffix); target.mkdir(exist_ok=False)
    seal=dict(stage=args.stage,protocol=spec,gates=gates,git=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path(__file__).parent.glob('*') if x.is_file()},
        packages=subprocess.check_output([__import__('sys').executable,'-m','pip','freeze'],text=True))
    (target/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    rows=[];started=time.perf_counter()
    for r in spec['R_bohr']:
        output=target/f'R_{r:g}.json'
        job=mp.get_context('spawn').Process(target=worker,args=(r,str(output),args.stage,str(root/'selection'),spec['guards']))
        job.start();job.join()
        if job.exitcode!=0 or not output.exists(): raise RuntimeError(f'worker exit {job.exitcode}, no retry')
        row=json.loads(output.read_text());rows.append(row)
        (target/'results.json').write_text(json.dumps(dict(rows=rows,wall_seconds=time.perf_counter()-started),indent=2)+'\n')
        print(args.stage,r,[(x['mode'],x['failure_stage'],x['singlet_asymmetry'],x['total_energy_hartree']) for x in row.get('paths',[])],flush=True)
        if row.get('status')=='IMPLEMENTATION_ERROR_PRESERVED': raise RuntimeError('preserved implementation error; STOP')

if __name__=='__main__': main()
