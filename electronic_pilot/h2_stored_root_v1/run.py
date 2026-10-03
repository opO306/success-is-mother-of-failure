"""Prepare -> synthetic tests -> seal -> all-five fail-closed audit -> stop."""
import argparse
import datetime
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import sys
from .checker import (CASES,DOC,LADDER,OLD_RAW,RAW,decimal,dyadic,exact_direction,
    factor,ladder,linux,matrix_file,measured,pair,read_ev,read_hs,read_observed,root,sha,write)

def protected():
    old=Path('docs/active/h2_internal_convergence_v0/evidence')
    manifest=json.loads((old/'final_seal.json').read_text())
    paths={k.removeprefix('worktree:'):v for k,v in manifest['bound_sha256'].items()}
    for ent in json.loads((old/'raw_inventory.json').read_text())['entries']:
        paths[ent['path']]=ent['sha256']
    # Verify earlier original archives, source trees, vendor and every historical audit binding too.
    proto=json.loads((old/'protocol.json').read_text())
    for key,val in proto.items():
        if isinstance(val,dict) and 'sha256' in key.lower():
            for k,v in val.items():
                if isinstance(v,str) and len(v)==64 and key!='archive_file_sha256':
                    paths[k.removeprefix('worktree:')]=v
    archive=Path('C:/Users/zun24/Downloads/H2SOLV Fortran solver for diatomic molecules in explicitly correlated exponential basis.zip')
    paths[archive.as_posix()]='3a2756179b4f74abe450b5383fd9d8c656501cc5e39b39af74de42ffcd4d615d'
    paths['runs/h2_representation_pilot1/resume_v1_20261003/afba_v1_0.tar.gz']='a0f2967b1d110e88fd929f3effd1b8616a6e4fcb0477a988cb564952814a86db'
    for p in (Path('runs/h2_representation_pilot1/resume_v1_20261003/vendor_original').rglob('*')):
        if p.is_file(): paths[p.as_posix()]=sha(p)
    paths['runs/h2_representation_pilot1/vendor_build_resume_v2_20261003/vendor_build/h2solv/f/h2solv']='46aafcbf195a1c7f888615bcadb1bcd8bb6ec5915b5fa9beb0dff3915d7a2109'
    return paths

def verify(bindings):
    bad=[k for k,v in bindings.items() if not Path(k).is_file() or sha(k)!=v]
    if bad: raise ValueError('protected byte mismatch: '+str(bad))
    return len(bindings)

def prepare():
    if (DOC/'evidence/protocol.json').exists(): raise ValueError('do not overwrite existing seal')
    RAW.mkdir(parents=True,exist_ok=True);(DOC/'evidence').mkdir(parents=True,exist_ok=True)
    bound=protected();verify(bound);write(RAW/'protected_before.json',bound)
    cmds=[['git','status','--porcelain'],['git','branch','--show-current'],['git','rev-parse','HEAD'],
          ['git','ls-remote','origin','refs/heads/master','refs/heads/codex/h2-representation-pilot1'],
          ['git','rev-list','--left-right','--count','origin/codex/h2-representation-pilot1...HEAD']]
    state=[]
    for argv in cmds:
        p=subprocess.run(argv,capture_output=True,text=True,check=True);state.append(dict(argv=argv,stdout=p.stdout,stderr=p.stderr))
    write(DOC/'evidence/git_start.json',state)
    src=Path('electronic_pilot/h2_stored_root_v1/interval_ldl.cpp')
    argv=['wsl','-e','g++','-std=c++17','-O2','-Wall','-Wextra',linux(src),'-o',linux(RAW/'interval_ldl'),'-lmpfr','-lgmp']
    p=subprocess.run(argv,capture_output=True,text=True,encoding='utf8',timeout=120)
    (DOC/'evidence/build.stdout').write_text(p.stdout,encoding='utf8')
    (DOC/'evidence/build.stderr').write_text(p.stderr,encoding='utf8')
    write(DOC/'evidence/build.json',dict(argv=argv,exit=p.returncode,binary_sha256=sha(RAW/'interval_ldl') if p.returncode==0 else None))
    if p.returncode: raise RuntimeError('compile failed')
    print('Prepared independent checker; no real factorization executed.',flush=True)

def seal():
    bound=json.loads((RAW/'protected_before.json').read_text());verify(bound)
    if not (DOC/'evidence/synthetic_tests.log').exists(): raise ValueError('synthetic tests must precede sealing')
    log=(DOC/'evidence/synthetic_tests.log').read_text()
    if 'failed' in log or 'error' in log or 'passed' not in log: raise ValueError('synthetic preflight not passed')
    code={p.as_posix():sha(p) for base in ('electronic_pilot/h2_stored_root_v1','tests/h2_stored_root_v1')
          for p in Path(base).glob('*') if p.is_file()}
    code[(DOC/'PLAN.md').as_posix()]=sha(DOC/'PLAN.md');code[(RAW/'interval_ldl').as_posix()]=sha(RAW/'interval_ldl')
    inputs=[]
    for name in CASES:
        base=OLD_RAW/'cases'/name/'AUDIT';n,h,s,meta=read_hs(base/'audit_HS.bin')
        e,v,evprec=read_ev(base/'audit_EV.bin',n);en,wa=read_observed(base/'audit_invsg.log')
        inputs.append(dict(name=name,**meta,EV_precision_counts=evprec,E_returned=decimal(e,180),
            E_pair=[str(pair(e)[0]),pair(e)[1]],initial_EN=decimal(en,180),
            initial_EN_pair=[str(pair(en)[0]),pair(en)[1]],WA1=wa,
            files={p.as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in
                   (base/'audit_HS.bin',base/'audit_EV.bin',base/'audit_invsg.log')}))
    protocol=dict(sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        start_HEAD='ab3569b29f436df28a49369c0f126af719d26294',precision_ladder=LADDER,
        bracket_delta='2^-64',bisection_iterations=8,bracket_resolution='2^-70',
        mode='all-five per-case precondition rejection; never run dependent stages for failed S; aggregate STOP',
        root_stop='endpoint count other than (0,1), uncertain, E outside, consistency contradiction',
        second_root='deferred bounded cost; no automatic spectral search',residual_digits=240,
        numerical_acceptance='MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD',timeout_per_factor_seconds=600,
        protected_sha256=bound,implementation_sha256=code,inputs=inputs,
        final_policy='5/5 success required; NOT_CERTIFIED overall; no R04/B2/sweeps/push')
    write(DOC/'evidence/protocol.json',protocol)
    write(DOC/'evidence/protocol_seal.json',dict(sha256=sha(DOC/'evidence/protocol.json'),sealed_before_real_factorization=True))
    print('Sealed '+sha(DOC/'evidence/protocol.json'),flush=True)

def execute():
    protocol=json.loads((DOC/'evidence/protocol.json').read_text())
    if sha(DOC/'evidence/protocol.json')!=json.loads((DOC/'evidence/protocol_seal.json').read_text())['sha256']:
        raise ValueError('protocol seal mismatch')
    verify(protocol['protected_sha256']);verify(protocol['implementation_sha256'])
    results=[]
    for inp in protocol['inputs']:
        name=inp['name'];directory=RAW/'cases'/name
        if (directory/'result.json').exists(): raise ValueError('no automatic repeat')
        base=OLD_RAW/'cases'/name/'AUDIT';n,h,s,meta=read_hs(base/'audit_HS.bin')
        e,v,_=read_ev(base/'audit_EV.bin',n);en,wa=read_observed(base/'audit_invsg.log')
        print(name+' SPD audit start',flush=True)
        checked=ladder(n,s,'SPD',directory/'SPD');final=checked['final']
        witness=exact_direction(s,final)
        spd=final['status']=='COMPLETE' and final['positive']==n and final['negative']==0
        if spd and (final['lambda_min_lower_pair'] is None or dyadic(int(final['lambda_min_lower_pair'][0]),final['lambda_min_lower_pair'][1])<=0):
            raise ValueError('missing positive metric margin')
        if final['status']=='NOT_SPD' and not witness['negative_witness']:
            raise ValueError('interval rejection has no independently exact negative witness')
        result=dict(name=name,dimension=n,SPD=checked,SPD_status='STORED_S_SPD_CERTIFIED' if spd else
            'STORED_S_NOT_SPD_EXACT_NEGATIVE_DIRECTION' if final['status']=='NOT_SPD' else 'SPD_UNRESOLVED',
            exact_direction=witness,S_symmetry='EXACT_BY_PACKED_LOWER_TRIANGLE_RESTORATION; independent upper triangle not exported',
            rank=n if spd else None,rank_status='FULL_RANK_CERTIFIED' if spd else 'FULL_RANK_UNRESOLVED',
            WA1=wa,initial_EN=decimal(en,180),initial_inertia=None,WA1_status='NOT_EXECUTED_S_PRECONDITION_FAILED',
            root=dict(status='NOT_EXECUTED_S_PRECONDITION_FAILED',low=None,high=None,inertia_low=None,inertia_high=None,width=None,E_inside=None),
            second_root='NOT_EXECUTED_BOUNDED_SCOPE')
        print(name+' '+result['SPD_status'],flush=True)
        # Actual test-only stored-matrix copy: negative first diagonal, unchanged authority.
        mutant=list(s);mutant[0]=-abs(s[0])-1
        mf=ladder(n,mutant,'SPD',directory/'fault_indefinite')
        mw=exact_direction(mutant,mf['final'])
        result['fault_indefinite']=dict(status='DETECTED' if mf['final']['status']=='NOT_SPD' and mw['negative_witness'] else 'DETECTOR_FAILED',
            result=mf,exact_witness=mw,authoritative_unchanged=True)
        if result['fault_indefinite']['status']!='DETECTED': raise ValueError('fault detector failed; STOP')
        if spd:
            ii=ladder(n,[a-en*b for a,b in zip(h,s)],'INERTIA',directory/'initial_inertia')
            result['initial_inertia']=ii
            result['WA1_status']='MATCH' if ii['final']['status']=='COMPLETE' and ii['final']['negative']==wa else (
                'MISMATCH' if ii['final']['status']=='COMPLETE' else 'INERTIA_UNRESOLVED')
            result['root']=root(n,h,s,e,directory/'root')
        result['residual']=measured(n,h,s,e,v,spd)
        if spd and result['root']['status']=='LOWEST_ROOT_ENCLOSED':
            lo=dyadic(int(result['root']['low_pair'][0]),result['root']['low_pair'][1])
            hi=dyadic(int(result['root']['high_pair'][0]),result['root']['high_pair'][1])
            from mpmath import mp
            with mp.workdps(240):
                cv=lambda x:mp.mpf(x.numerator)/x.denominator
                rho=mp.mpf(result['residual']['transformed_residual']);rq=mp.mpf(result['residual']['E_RQ'])
                # Numerical consistency checks, no new acceptance tolerance.
                result['eigenpair_consistency']=dict(grade='MEASURED',RQ_inside=cv(lo)<=rq<=cv(hi),
                    RQ_cauchy_consistent=abs(rq-cv(e))<=rho,
                    residual_spectral_interval_intersects=not(cv(e)+rho<cv(lo) or cv(e)-rho>cv(hi)),
                    rho_interval_contained_in_lowest_bracket=cv(lo)<=cv(e)-rho and cv(e)+rho<=cv(hi))
        else: result['eigenpair_consistency']=dict(grade='UNRESOLVED_PRECONDITION_OR_ROOT_FAILED')
        write(directory/'result.json',result);write(DOC/'evidence/cases'/name/'result.json',result)
        results.append(result)
        print(name+' root '+result['root']['status'],flush=True)
    verify(protocol['protected_sha256']);verify(protocol['implementation_sha256'])
    passed=all(r['SPD_status']=='STORED_S_SPD_CERTIFIED' and r['root']['status']=='LOWEST_ROOT_ENCLOSED'
        and all(r['eigenpair_consistency'].get(k,False) for k in ('RQ_inside','RQ_cauchy_consistent','residual_spectral_interval_intersects','rho_interval_contained_in_lowest_bracket'))
        for r in results)
    table=dict(cases=results,classification='H2SOLV_VENDOR_LOWEST_ROOT_SUPPORTED' if passed else 'H2SOLV_LOWEST_ROOT_UNRESOLVED',
        WA1_classification='WA1_INERTIA_SEMANTICS_SUPPORTED' if all(r['WA1_status']=='MATCH' for r in results) else
            'WA1_ROOT_COUNT_INTERPRETATION_CONTRADICTED' if any(r['WA1_status']=='MISMATCH' for r in results) else 'WA1_SEMANTICS_UNRESOLVED',
        protected_files_unchanged=len(protocol['protected_sha256']),STOP=True,NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True)
    write(DOC/'evidence/table.json',table)
    print(table['classification']+' / STOP',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=('prepare','seal','execute'))
    {'prepare':prepare,'seal':seal,'execute':execute}[ap.parse_args().stage]()
