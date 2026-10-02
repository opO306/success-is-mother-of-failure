"""Presealed failure-only audit; immutable evidence inputs and separate stages."""
import argparse
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import time
import traceback


BASE='61bad943a1865ac1a6b2e89a6577fe03cb4f6b85'


def sha(p):
    with Path(p).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def verify(mapping):
    bad=[p for p,h in mapping.items() if sha(p)!=h]
    if bad: raise ValueError('FROZEN INPUT/SOURCE DRIFT: '+repr(bad))


def load_input(root,r):
    import numpy as np
    root=Path(root);record=json.loads((root/f'R_{r:g}.json').read_text())
    artifact=root/f'R_{r:g}.npz'
    if sha(artifact)!=record['artifact_sha256']: raise ValueError('artifact hash mismatch')
    with np.load(artifact) as a: arrays=[a[k] for k in ('s','h','eri_s8','c')]
    if arrays[0].shape!=(60,60) or arrays[3].shape!=(60,60): raise ValueError('full AO60 required')
    return record,arrays


def seal(target,evidence):
    spec=json.loads(Path(__file__).with_name('protocol.json').read_text())
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    if head!=BASE or branch!=spec['expected_branch']: raise ValueError('unexpected Git start')
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'electronic_pilot',
          'tests/test_h2_static_pilot.py','tests/test_h2_numerical_cause.py','tests/test_h2_ao_micro_v0.py',
          'tests/test_h2_qz44_sealed_v1.py','tests/test_h2_qz44_failure_diagnostic.py',
          'docs/active/h2_static_pilot_v2','docs/active/h2_numerical_cause_v1','docs/active/h2_ao_micro_v0','docs/active/h2_qz44_sealed_v1'],text=True).splitlines()
    protected={p:sha(p) for p in paths}
    for p,v in protected.items():
        if hashlib.sha256(subprocess.check_output(['git','show',BASE+':'+p])).hexdigest()!=v: raise ValueError('base byte drift '+p)
    sources={str(p):sha(p) for p in Path(__file__).parent.glob('*') if p.is_file()}
    sources['tests/test_h2_failure_cause_v0.py']=sha('tests/test_h2_failure_cause_v0.py')
    inputs={}
    for r in [spec['stage_A_R']]+spec['stage_C_R']:
        for suffix in ('json','npz'):
            p=Path(evidence)/f'R_{r:g}.{suffix}';inputs[str(p)]=sha(p)
    env={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}
    if set(env.values())!={'1'}: raise ValueError('numeric threads must remain1')
    out=dict(spec=spec,head=head,branch=branch,protected_sha256=protected,source_sha256=sources,
             input_sha256=inputs,evidence_root=str(evidence),thread_environment=env,
             packages=subprocess.check_output([__import__('sys').executable,'-m','pip','freeze'],text=True))
    (target/'seal.json').write_text(json.dumps(out,indent=2)+'\n')
    return out


def worker(stage,evidence,r,path,guard,output):
    import resource
    import numpy as np
    from .exact_guard import exact_norm_bounds,adaptive_guard
    started=time.perf_counter()
    try:
        record,(s,h,g8,c)=load_input(evidence,r)
        if stage=='A':
            binary=float(np.linalg.norm(c.T@s@c-np.eye(60),ord=2))
            start=time.perf_counter();rigorous=exact_norm_bounds(s.tolist(),c.tolist(),str(guard['orth_l2_max']))
            out=dict(stage=stage,R_bohr=r,binary64_operator_residual=binary,
                frozen_binary64_residual=record['paths'][0]['orthogonality_l2'],
                binary64_bit_identical=binary==record['paths'][0]['orthogonality_l2'],
                exact=rigorous,exact_seconds=time.perf_counter()-start,
                classification='MEASUREMENT_ERROR' if rigorous['relation']=='BELOW' and binary>guard['orth_l2_max'] else
                    'NUMERICAL_IMPLEMENTATION_ERROR' if rigorous['relation']=='ABOVE' else 'UNRESOLVED',
                original_refusal_unchanged=True)
        elif stage=='B':
            out=dict(stage=stage,R_bohr=r,prototype=adaptive_guard(s,c,str(guard['orth_l2_max'])))
        else:
            from .same_basis import run_reference
            row,other_c,vector=run_reference(s,h,g8,c,path,guard)
            cert=exact_norm_bounds(s.tolist(),other_c.tolist(),str(guard['orth_l2_max']))
            validated=row['failure_stage'] is None and cert['relation']=='BELOW'
            if row.get('wavefunction_spin_square',1)>guard['eigen_l2_max']: validated=False
            out=dict(stage='C1',R_bohr=r,reference=row,orthogonality_exact=cert,
                reference_validated=validated,original_BO_energy=record['paths'][0]['total_energy_hartree'],
                BO_energy=None if row['energy'] is None else row['energy']+1/r)
            if vector is not None:
                art=Path(output).with_suffix('.npz')
                np.savez_compressed(art,c=other_c,vector=vector)
                out['artifact_sha256']=sha(art)
        out.update(wall_seconds=time.perf_counter()-started,
                   peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    except Exception as exc:
        out=dict(stage=stage,R_bohr=r,path=path,status='ERROR_PRESERVED',error=repr(exc),traceback=traceback.format_exc(),
                 wall_seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    Path(output).write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(stage,r,path,out.get('classification',out.get('BO_energy',out.get('status'))),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence-root',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();target=Path(args.output);target.mkdir(parents=True,exist_ok=False)
    sealed=seal(target,Path(args.evidence_root));bound=sealed['protected_sha256']|sealed['source_sha256']|sealed['input_sha256']
    guard=json.loads(Path('electronic_pilot/ao_micro_v0/protocol.json').read_text())['guards']
    started=time.perf_counter();rows=[]
    jobs=[('A',.5,None),('B',.5,None)]
    jobs += [('C',r,path) for r in sealed['spec']['stage_C_R'] for path in sealed['spec']['C1_paths']]
    for stage,r,path in jobs:
        verify(bound)
        if stage=='B' and rows[0]['classification']!='MEASUREMENT_ERROR': continue
        name=f'{stage}_R_{r:g}'+('' if path is None else '_'+path)
        output=target/(name+'.json')
        job=mp.get_context('spawn').Process(target=worker,args=(stage,args.evidence_root,r,path,guard,str(output)))
        job.start();job.join()
        if job.exitcode or not output.exists(): raise RuntimeError('worker failed, STOP without retry')
        rows.append(json.loads(output.read_text()))
        (target/'results.json').write_text(json.dumps(dict(rows=rows,wall_seconds=time.perf_counter()-started),indent=2)+'\n')
        if rows[-1].get('status')=='ERROR_PRESERVED': raise RuntimeError('diagnostic error preserved, STOP')
    verify(bound)
    (target/'post_run_check.json').write_text(json.dumps(dict(verified=True,protected_count=len(sealed['protected_sha256']),
        source_count=len(sealed['source_sha256']),input_count=len(sealed['input_sha256']),results_sha256=sha(target/'results.json')),indent=2)+'\n')

if __name__=='__main__': main()
