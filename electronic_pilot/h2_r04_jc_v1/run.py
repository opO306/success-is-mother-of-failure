"""Prepare, preflight, seal, execute bounded campaign, seal energies, STOP."""
import argparse,datetime,json,shutil,subprocess,time
from fractions import Fraction as F
from pathlib import Path
import mpmath as mp
from . import contract as c
from .instrument import clocks,enumeration,strip
from .measure import timed,Peak
from electronic_pilot.h2_internal_convergence_v0.observe import parse as observe
from electronic_pilot.h2_stored_root_v1 import checker as ck

RAW=Path('runs/h2_representation_pilot1/r04_jc_v1_20261004')
DOC=Path('docs/active/h2_r04_jc_v1')
CODE=Path('electronic_pilot/h2_r04_jc_v1')
ORIGINAL=Path('runs/h2_representation_pilot1/resume_v1_20261003/vendor_original/h2solv')
VENDOR=Path('runs/h2_representation_pilot1/vendor_build_resume_v2_20261003/vendor_build/h2solv/f/h2solv')

def read(path):return json.loads(Path(path).read_text())
def verify(bindings):
    bad=[p for p,h in bindings.items() if not Path(p).is_file() or ck.sha(p)!=h]
    if bad:raise ValueError('hash mismatch: '+str(bad))
    return len(bindings)

def prior():
    old=Path('docs/active/h2_stored_root_v1/evidence')
    p=read(old/'protocol.json');bound={**p['protected_sha256'],**p['implementation_sha256']}
    for key,val in read(old/'final_seal.json')['bound_sha256'].items():
        bound[key.removeprefix('worktree:')]=val
    for ent in read(old/'raw_inventory.json')['entries']:bound[ent['path']]=ent['sha256']
    return bound

def prepare():
    if (DOC/'evidence/protocol.json').exists() or (RAW/'enumeration_build').exists():raise ValueError('exclusive new capture only')
    RAW.mkdir(parents=True,exist_ok=True);(DOC/'evidence').mkdir(parents=True,exist_ok=True)
    bound=prior();verify(bound)
    if (RAW/'protected_before.json').exists():
        if read(RAW/'protected_before.json')!=bound:raise ValueError('preparation recovery binding mismatch')
    else:ck.write(RAW/'protected_before.json',bound)
    commands=[['git','rev-parse','HEAD'],['git','branch','--show-current'],['git','status','--porcelain'],
              ['git','ls-remote','origin','refs/heads/master','refs/heads/codex/h2-representation-pilot1'],
              ['git','rev-list','--left-right','--count','origin/codex/h2-representation-pilot1...HEAD']]
    git=[]
    for cmd in commands:
        p=subprocess.run(cmd,capture_output=True,text=True,check=True);git.append(dict(argv=cmd,stdout=p.stdout,stderr=p.stderr))
    ck.write(DOC/'evidence/git_start.json',git)
    src=(ORIGINAL/'f/h2solv.f').read_bytes()
    for name,modified in [('enumeration',enumeration(src)),('audit',clocks(src))]:
        build=RAW/f'{name}_build/h2solv';shutil.copytree(ORIGINAL,build)
        (build/'f/h2solv.f').write_bytes(modified)
        cmd=['wsl','-e','make','-C',ck.linux(build/'f'),'h2solv','LD=gfortran -fopenmp',
             'MPFR=/usr/lib/x86_64-linux-gnu/libmpfr.a /usr/lib/x86_64-linux-gnu/libgmp.a']
        start=time.perf_counter();p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',timeout=150)
        (RAW/f'{name}_build.stdout').write_text(p.stdout,encoding='utf8');(RAW/f'{name}_build.stderr').write_text(p.stderr,encoding='utf8')
        ck.write(DOC/f'evidence/{name}_build.json',dict(argv=cmd,exit=p.returncode,wall_seconds=time.perf_counter()-start,
                 stripped_source_sha256=__import__('hashlib').sha256(strip(modified)).hexdigest(),
                 modified_sha256=ck.sha(build/'f/h2solv.f'),binary_sha256=ck.sha(build/'f/h2solv') if not p.returncode else None))
        if p.returncode:raise RuntimeError('build failed; STOP, preserve logs')
    rows=[]
    for omega in range(1,10):
        dest=RAW/'enumeration'/f'omega{omega}';dest.mkdir(parents=True)
        lines=c.input_bytes(3,F(1),80,60,F(-2)).decode().splitlines();lines[7]=f'{omega} OMEGA'
        data=('\n'.join(lines)+'\n').encode();(dest/'input.inp').write_bytes(data)
        timed(['/bin/sh','-c','cd "$1" && exec "$2"','r04',ck.linux(dest),ck.linux(RAW/'enumeration_build/h2solv/f/h2solv')],dest,stdin=data)
        words=(dest/'basis.dat').read_text().splitlines();native=[tuple(map(int,l.split())) for l in words[1:]]
        if int(words[0])!=len(native) or native!=c.basis(omega):raise ValueError('native enumeration disagreement')
        rows.append(dict(OMEGA=omega,dimension=len(native),native_order_and_tuples_match=True,
                         tuples_sha256=ck.sha(dest/'basis.dat'),energy_executed=False))
    ck.write(DOC/'evidence/basis_enumeration.json',rows)
    print('Prepared native enumeration and observation copies; no R04 energy computed.',flush=True)

def seal():
    dest=DOC/'evidence/protocol.json'
    if dest.exists():raise ValueError('sealed protocol immutable')
    bound=read(RAW/'protected_before.json');verify(bound)
    log=(DOC/'evidence/preflight.log').read_text()
    if 'passed' not in log or 'failed' in log or 'error' in log:raise ValueError('preflight not passed')
    implementation={p.as_posix():ck.sha(p) for folder in (CODE,Path('tests/h2_r04_jc_v1')) for p in folder.glob('*') if p.is_file()}
    for p in [DOC/'PLAN.md',DOC/'evidence/basis_enumeration.json',DOC/'evidence/preflight.log',
              RAW/'audit_build/h2solv/f/h2solv',RAW/'audit_build/h2solv/f/h2solv.f']:
        implementation[p.as_posix()]=ck.sha(p)
    protocol=dict(sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),start_HEAD='1503b6765b2f8db595200b3dc4725c879eead812',
        physical=dict(ZA=1,ZB=1,electrons=2,R_bohr='0.4',clamped=True,nonrelativistic=True,symmetry='singlet gerade 1Sigma_g+',
                      nuclear_repulsion='already in HAM; never add 1/R again',x='0',y='0',u_equals_w=True),
        selected={k:dict(OMEGA=o,dimension=len(c.basis(o))) for k,o in c.SIZES.items()},
        nested='same common u transferred from MEDIUM optimizer; degree-prefix tuple sets; restrictions 1,1',
        numerical=dict(NMAX_ladder=list(c.NMAX),NDIGITS_ladder=list(c.NDIGITS),Omega=5,u='1',fixed_integral_digits=80,
            stability='1e-10 Eh empirical, not formal error bound',precision_comparison_NMAX=120,
            choice='ND60 only if ND60/80 agree at NMAX120; N80 if 80/100 AND 100/120 agree; otherwise N100 if 100/120 agree; else STOP'),
        optimizer=dict(seed='1',bounds=['0.5','1.5'],method='MEDIUM bounded pattern search; seed then both neighbors of current best at 1/4,1/8,1/16; ties lower u',
            max_evaluations=7,steps=['1/4','1/8','1/16'],termination='fixed three levels complete, minimum step 1/16; no optimality claim',
            objective='own accepted finite variational energy only',precision='chosen calibration settings',failure='any rejected trial => STOP; no range expansion',
            shared_u='one MEDIUM optimization; common u used for all sizes; calibration seed reusable with cost charged once'),
        EN=dict(initial='-2',subsequent='most recent accepted own E minus 1/256',max_root_retries=1,
            retry='same finite problem; returned finite own E minus 1/256 even if MAXIT; only hint, not accepted energy; re-audit',
            no_ground_claim_from_hint=True),
        final_points='fresh SMALL/MEDIUM/LARGE each; fresh NMAX+20 spot each; no Omega beyond7',
        validation='unchanged V1 interval checker + 240-digit measured residual/RQ and same four consistency checks; no new tolerance',
        noninterference='fresh unchanged VENDOR for every final point, identical scientific stdout and wf bytes',
        cost='same GNU time + outer wall wrapper; OMP/OPENBLAS/MKL=1; Windows checker sampled RSS distinct; include calibration, optimization, spots, validation, refused attempts',
        comparison_gate='all final/spot energies and source hashes sealed before separate reference comparison; fresh V5Z only if target met',
        max_scope='three sizes at R=.4 only; no B2, curve, production, A adoption, push',
        protected_sha256=bound,implementation_sha256=implementation)
    ck.write(dest,protocol);ck.write(DOC/'evidence/protocol_seal.json',dict(sha256=ck.sha(dest),sealed_before_R04_energy=True))
    print('Protocol sealed before R04 energies: '+ck.sha(dest),flush=True)

def check_seal():
    p=read(DOC/'evidence/protocol.json')
    if ck.sha(DOC/'evidence/protocol.json')!=read(DOC/'evidence/protocol_seal.json')['sha256']:raise ValueError('protocol hash changed')
    verify(p['protected_sha256']);verify(p['implementation_sha256']);return p

def energy(row):return ck.dyadic(int(row['E_pair'][0]),row['E_pair'][1])

def phase_times(path):
    events={}
    for line in Path(path).read_text().splitlines():
        tag,ticks,rate=line.split()
        if tag in events:raise ValueError('duplicate clock tag')
        events[tag]=F(int(ticks),int(rate))
    diff=lambda a,b:float(events[b]-events[a])
    return dict(integrals=diff('INTEGRAL_START','INTEGRAL_END'),
                matrix_build_and_allocation=diff('CALCEN_START','MATRIX_END')-diff('INTEGRAL_START','INTEGRAL_END'),
                precision_conversion_and_setup=diff('MATRIX_END','SNAPSHOT_START'),
                matrix_snapshot=diff('SNAPSHOT_START','INVSG_START'),
                eigensolve_with_iteration_and_return_observers=diff('INVSG_START','INVSG_END'),
                CALCEN_total=diff('CALCEN_START','CALCEN_END'))

def attempt(label,omega,u,nmax,nd,en):
    dest=RAW/'runs'/label
    if dest.exists():raise ValueError('refuse overwrite/repeated capture '+label)
    dest.mkdir(parents=True);data=c.input_bytes(omega,u,nmax,nd,en);(dest/'input.inp').write_bytes(data)
    start=time.perf_counter()
    with Peak() as peak:
        native=timed(['/bin/sh','-c','cd "$1" && exec "$2"','r04',ck.linux(dest),ck.linux(RAW/'audit_build/h2solv/f/h2solv')],dest,stdin=data)
        observation=observe(dest/'audit_invsg.log');ck.write(dest/'observation.json',observation)
        n,h,s,meta=ck.read_hs(dest/'audit_HS.bin');e,v,prec=ck.read_ev(dest/'audit_EV.bin',n)
        if (n,meta['OMEGA'],meta['NMAX'],meta['NDIGITS'])!=(len(c.basis(omega)),omega,nmax,nd):raise ValueError('input/capture mismatch')
        initial,wa=ck.read_observed(dest/'audit_invsg.log')
        validstart=time.perf_counter();spdproof=ck.ladder(n,s,'SPD',dest/'SPD');sf=spdproof['final']
        spd=sf['status']=='COMPLETE' and sf['positive']==n and sf['negative']==0 and sf['lambda_min_lower_pair'] is not None
        if spd:spd=ck.dyadic(int(sf['lambda_min_lower_pair'][0]),sf['lambda_min_lower_pair'][1])>0
        root=dict(status='NOT_EXECUTED_REJECTED_ITERATION_OR_SPD',inertia_low=None,inertia_high=None,E_inside=None)
        wa_status='NOT_EXECUTED';consistency={};residual=None;initialproof=None
        if spd and observation['inverse_iteration_supported']:
            initialproof=ck.ladder(n,[a-initial*b for a,b in zip(h,s)],'INERTIA',dest/'initial_inertia')
            wa_status='MATCH' if initialproof['final']['status']=='COMPLETE' and initialproof['final']['negative']==wa else 'MISMATCH_OR_UNRESOLVED'
            root=ck.root(n,h,s,e,dest/'root');residual=ck.measured(n,h,s,e,v,True)
            if root['status']=='LOWEST_ROOT_ENCLOSED':
                low=ck.dyadic(int(root['low_pair'][0]),root['low_pair'][1]);high=ck.dyadic(int(root['high_pair'][0]),root['high_pair'][1])
                with mp.workdps(240):
                    cv=lambda f:mp.mpf(f.numerator)/f.denominator
                    rho=mp.mpf(residual['transformed_residual']);rq=mp.mpf(residual['E_RQ'])
                    consistency=dict(RQ_inside=cv(low)<=rq<=cv(high),RQ_cauchy=abs(rq-cv(e))<=rho,
                        residual_intersects=not(cv(e)+rho<cv(low) or cv(e)-rho>cv(high)),rho_contained=cv(low)<=cv(e)-rho and cv(e)+rho<=cv(high))
        validation_seconds=time.perf_counter()-validstart
        ck.write(dest/'independent.json',dict(SPD=spdproof,initial_inertia=initialproof,root=root,residual=residual,consistency=consistency))
        obskeys=('inverse_iteration_supported','maxit_exhausted','converged_by_eigenvalue_test','solver_factorization_error_free',
                 'structure_errors','actual_iteration_count','termination_reason','final_ierror','ITMAX')
        row=dict(label=label,OMEGA=omega,dimension=n,u=ck.decimal(u),NMAX=nmax,NDIGITS=nd,energy=ck.decimal(e,180),
             E_pair=[str(ck.pair(e)[0]),ck.pair(e)[1]],initial_EN=ck.decimal(initial,180),WA1=wa,WA1_status=wa_status,
             observation={k:observation[k] for k in obskeys},SPD=bool(spd),SPD_summary={k:sf[k] for k in ('status','positive','negative','uncertain','lambda_min_lower_pair')},
             root={k:val for k,val in root.items() if k!='trace'},residual=residual,consistency=consistency,
             phase_seconds=phase_times(dest/'r04_clocks.log'),native_process=native,validation_seconds=validation_seconds,
             HS_precision_counts=meta['precision_counts'],EV_precision_counts=prec,
             hashes={p.name:ck.sha(p) for p in [dest/'input.inp',dest/'audit_HS.bin',dest/'audit_EV.bin',dest/'audit_invsg.log',dest/'independent.json']})
        row['status']=c.acceptance(row)
    row.update(total_wall_seconds=time.perf_counter()-start,controller_peak_rss_bytes=peak.peak)
    ck.write(dest/'result.json',row);ck.write(DOC/'evidence/runs'/f'{label}.json',row)
    print(label+' '+row['status']+' E='+row['energy'][:36]+' validation='+str(round(validation_seconds,3)),flush=True)
    return row

def evaluate(label,omega,u,nmax,nd,en,rows):
    for retry in range(c.MAX_ROOT_RETRIES+1):
        r=attempt(f'{label}_try{retry}',omega,u,nmax,nd,en);rows.append(r)
        if r['status']=='ACCEPTED_FINITE_STORED_PROBLEM':return r
        if r['status']=='REFUSED_SPD':raise ValueError('S precondition failed; no EN retry')
        en=energy(r)-F(1,256)
    raise ValueError(label+' refused after sealed retry bound')

def vendor_check(row):
    source=RAW/'runs'/row['label'];dest=RAW/'vendor_checks'/row['label'];dest.mkdir(parents=True)
    m=timed(['/bin/sh','-c','cd "$1" && exec "$2"','r04',ck.linux(dest),ck.linux(VENDOR)],dest,stdin=(source/'input.inp').read_bytes())
    equality=(dest/'stdout').read_bytes()==(source/'stdout').read_bytes()
    a={p.name:ck.sha(p) for p in source.glob('wf*.dat')};b={p.name:ck.sha(p) for p in dest.glob('wf*.dat')}
    result=dict(scientific_stdout_identical=equality,wavefunctions_identical=a==b and bool(a),vendor_wavefunction_hashes=b,measurement=m)
    ck.write(DOC/'evidence/vendor_checks'/f"{row['label']}.json",result)
    if not equality or a!=b or not a:raise ValueError('observer noninterference failed')
    return result

def execute():
    protocol=check_seal()
    if (DOC/'evidence/campaign.json').exists():raise ValueError('campaign already attempted; no automatic rerun')
    rows=[];start=time.perf_counter();campaign=dict(status='RUNNING',all_runs=rows,final={},spots={},vendor_checks={},cumulative_final_wall_seconds={})
    try:
        en=F(-2);cal={}
        for n in c.NMAX:
            r=evaluate(f'cal_n{n}d60',5,F(1),n,60,en,rows);en=energy(r)-F(1,256);cal[f'n{n}d60']=r
        r=evaluate('cal_n120d80',5,F(1),120,80,en,rows);cal['n120d80']=r;en=energy(r)-F(1,256)
        nmax,nd=c.choose_numeric({k:energy(v) for k,v in cal.items()})
        calibration=dict(points={k:v['label'] for k,v in cal.items()},chosen_NMAX=nmax,chosen_NDIGITS=nd,
                         energy_changes={f'{a}_to_{b}':ck.decimal(energy(cal[b])-energy(cal[a])) for a,b in
                            [('n60d60','n80d60'),('n80d60','n100d60'),('n100d60','n120d60'),('n120d60','n120d80')]})
        ck.write(DOC/'evidence/calibration.json',calibration);campaign['calibration']=calibration
        optstart=time.perf_counter();best=cal[f'n{nmax}d{nd}'];u=F(1);evals=[dict(u='1',label=best['label'],reused_calibration=True)]
        for step in c.OPT_STEPS:
            center=u;choices=[(energy(best),u,best)]
            for trial in (center-step,center+step):
                if not c.OPT_BOUNDS[0]<=trial<=c.OPT_BOUNDS[1]:raise ValueError('sealed pattern exceeded bounds')
                r=evaluate(f'opt_{len(evals)}',5,trial,nmax,nd,en,rows);en=energy(r)-F(1,256)
                evals.append(dict(u=ck.decimal(trial),label=r['label'],reused_calibration=False));choices.append((energy(r),trial,r))
            _,u,best=min(choices,key=lambda v:(v[0],v[1]))
        optimizer=dict(evaluations=evals,evaluation_count=len(evals),selected_u=ck.decimal(u),selected_label=best['label'],
                       extra_wall_seconds=time.perf_counter()-optstart,status='BOUNDED_SEARCH_COMPLETED_NO_OPTIMALITY_CERTIFICATE')
        ck.write(DOC/'evidence/optimizer.json',optimizer);campaign['optimizer']=optimizer
        for size,omega in c.SIZES.items():
            r=evaluate('final_'+size,omega,u,nmax,nd,en,rows);en=energy(r)-F(1,256);campaign['final'][size]=r
            campaign['vendor_checks'][size]=vendor_check(r)
            spot=evaluate('spot_'+size,omega,u,nmax+20,nd,en,rows);en=energy(spot)-F(1,256);campaign['spots'][size]=spot
            change=abs(energy(spot)-energy(r))
            if change>c.STABILITY:raise ValueError(size+' higher numerical spot failed stability')
            campaign['cumulative_final_wall_seconds'][size]=time.perf_counter()-start
        campaign['representation_changes']={f'{a}_to_{b}':ck.decimal(energy(campaign['final'][b])-energy(campaign['final'][a]))
            for a,b in [('SMALL','MEDIUM'),('MEDIUM','LARGE')]}
        campaign['status']='R04_FINITE_CAMPAIGN_ACCEPTED';campaign['numerical_stability_supported']=True
        campaign['nested_energy_nonincreasing']=all(energy(campaign['final'][b])<=energy(campaign['final'][a]) for a,b in [('SMALL','MEDIUM'),('MEDIUM','LARGE')])
    except Exception as exc:
        campaign.update(status='R04_B1_UNRESOLVED',failure=repr(exc))
        raise
    finally:
        campaign.update(total_campaign_wall_seconds=time.perf_counter()-start,STOP=True,NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True)
        ck.write(DOC/'evidence/campaign.json',campaign)
        verify(protocol['protected_sha256']);verify(protocol['implementation_sha256'])
        files={p.as_posix():ck.sha(p) for p in (DOC/'evidence').rglob('*') if p.is_file()}
        for p in (RAW/'runs').rglob('*'):
            if p.is_file():files[p.as_posix()]=ck.sha(p)
        seal=dict(sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=campaign['status'],
                  all_B1_energies_before_reference=True,bound_sha256=files)
        ck.write(DOC/'evidence/energy_seal.json',seal)
        print('Energy seal '+ck.sha(DOC/'evidence/energy_seal.json')+' / '+campaign['status']+' / STOP',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=('prepare','seal','execute'))
    {'prepare':prepare,'seal':seal,'execute':execute}[ap.parse_args().stage]()
