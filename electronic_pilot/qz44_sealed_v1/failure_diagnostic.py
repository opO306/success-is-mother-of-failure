"""Failure-only frozen-data diagnosis; never changes the curve or gate.

MP operations here consume canonical binary64 AO data and the saved C. They
are not independent HP integrals or a new accepted numerical calculation.
"""
import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path
import numpy as np
from .seal import sha,verify


def mp_eri(g8,c,indices,digits):
    import gmpy2 as gp
    i,j,k,l=map(int,indices);n=len(c)
    with gp.context(gp.get_context(),precision=int(digits*3.322)+32):
        cols={a:[gp.mpfr(float(c[p,a])) for p in range(n)] for a in (i,j,k,l)}
        def pairs(a,b):
            out=[]
            for p in range(n):
                for q in range(p+1):
                    weight=cols[a][p]*cols[b][q]
                    if p!=q: weight+=cols[a][q]*cols[b][p]
                    if weight: out.append((p*(p+1)//2+q,weight))
            return out
        left=pairs(i,j);right=pairs(k,l);value=gp.mpfr(0)
        for a,x in left:
            for b,y in right:
                high,low=(a,b) if a>=b else (b,a)
                value+=x*y*gp.mpfr(float(g8[high*(high+1)//2+low]))
        return str(value),dict(left_nonzero_pair_densities=len(left),right_nonzero_pair_densities=len(right),products=len(left)*len(right),bits=gp.get_context().precision)


def worker(r,root,output):
    import resource
    from pyscf import ao2mo
    import mpmath as mm
    started=time.perf_counter();root=Path(root)
    source=root/f'R_{r:g}.json';row=json.loads(source.read_text());record=row['paths'][0]
    artifact=source.with_suffix('.npz')
    if sha(artifact)!=row['artifact_sha256']: raise ValueError('frozen artifact mismatch')
    with np.load(artifact) as a: s,h,g8,c=(a[k] for k in ('s','h','eri_s8','c'))
    gm=ao2mo.restore(1,ao2mo.incore.full(g8,c,compact=True),len(s))
    delta=gm-gm.transpose(2,3,0,1)
    t=tuple(map(int,np.unravel_index(abs(delta).argmax(),delta.shape)))
    swap=t[2:]+t[:2]
    out=dict(R_bohr=r,first_numerical_failure=record['failure_stage'],accepted_in_original_fresh_run=record['accepted'],
        original_BO_energy=record['total_energy_hartree'],original_orthogonality_l2=record['orthogonality_l2'],
        original_Smin=record['Smin'],original_condition=record['condition'],
        worst_MO_pair_interchange=dict(indices=t,swapped=swap,value=float(gm[t]),counterpart=float(gm[swap]),difference=float(delta[t])),
        recomputed_pair_residual_matches_original=bool(float(abs(delta).max())==record['transformed_ERI_symmetry']['pair_swap_max']),
        input_sha256=dict(record=sha(source),canonical_AO_and_C=sha(artifact)),MP={},
        caveat='Selected transformed integral contraction of rounded canonical AO with fixed saved C. It is not an all-entry bound, eigenenergy error bound, independent AO generator, or alternate accepted curve.')
    for digits in (60,80):
        one,cost=mp_eri(g8,c,t,digits);two,_=mp_eri(g8,c,swap,digits)
        with mm.workdps(90):
            out['MP'][str(digits)]=dict(value=one,counterpart=two,pair_difference=str(mm.mpf(one)-mm.mpf(two)),
                forward_difference_from_binary64=str(mm.mpf(float(gm[t]))-mm.mpf(one)),cost=cost)
    if record['failure_stage']=='orthonormalization':
        from electronic_pilot.numerical_cause.high_precision import mp_cholesky_coordinates
        with mm.workdps(80):
            sm=mm.matrix([[mm.mpf(float(x)) for x in row] for row in s]);cm=mm.matrix([[mm.mpf(float(x)) for x in row] for row in c])
            out['fixed_binary64_C_80digit_orthogonality_frobenius_upper']=str(mm.norm(cm.T*sm*cm-mm.eye(len(s))))
        _,error,_=mp_cholesky_coordinates(s,80)
        out['diagnostic_80digit_Cholesky_orthogonality_frobenius_upper']=error
        out['coordinate_refinement_used_in_curve']=False
    out.update(wall_seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    Path(output).write_text(json.dumps(out,indent=2)+'\n')
    print('failure diagnostic',r,out['first_numerical_failure'],out['MP']['80']['forward_difference_from_binary64'],flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);args=p.parse_args();root=Path(args.root)
    gatepath=root/'comparison/gate.json';gate=json.loads(gatepath.read_text())
    if gate['numerical_pass']: raise ValueError('gate passed: precision research must stop')
    seal=json.loads((root/'seal.json').read_text());verify(seal['frozen_sha256']|seal['extension_sha256'])
    target=root/'failure_diagnostic';target.mkdir(exist_ok=False)
    (target/'seal.json').write_text(json.dumps(dict(gate_sha256=sha(gatepath),source_sha256=sha(__file__),selected_failure_points=gate['failed_points'],arithmetic='60/80 decimal digits MPFR; existing MP Cholesky diagnostic only',policy='No numerical path edits or curve replacements'),indent=2)+'\n')
    started=time.perf_counter();rows=[]
    for failure in gate['failed_points']:
        r=failure['R_bohr'];output=target/f'R_{r:g}.json'
        job=mp.get_context('spawn').Process(target=worker,args=(r,str(root),str(output)))
        job.start();job.join()
        if job.exitcode!=0: raise RuntimeError(f'diagnostic failed {job.exitcode}; no retry')
        rows.append(json.loads(output.read_text()))
        (target/'results.json').write_text(json.dumps(dict(rows=rows,wall_seconds=time.perf_counter()-started),indent=2)+'\n')
    verify(seal['frozen_sha256']|seal['extension_sha256'])

if __name__=='__main__': main()
