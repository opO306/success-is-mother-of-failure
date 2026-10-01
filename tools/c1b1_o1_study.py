"""Sealed O-1 phases. Run each phase in a fresh Python process.

seal: only constructs input, no dynamics. produce: reference physics only.
confirm: approved replay/history only. observe: independent calculation only.
run: serial orchestration, STOP at first non-AGREE, retains every artifact.
"""
import argparse
from dataclasses import asdict
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'runs/c1b1_o1_20261001_v1'
INPUT=ROOT/'docs/active/C1B1_O1_INPUTS_V1.json'
PROTOCOL=ROOT/'docs/active/C1B1_O1_PROTOCOL_V1.md'
APPROVAL=ROOT/'docs/active/C1B1_REPLAY_VERIFIER_PRODUCTION_APPROVAL_V1.json'
BASE='f03fb30c89c9f5d610bc1c6c419af8e6098431ec'
SOURCE=Path('D:/reference/ar2_lang2024/S2_ar2_pot.f90')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    # Never overwrite evidence, even failed/partial records.
    with path.open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2); f.write('\n')
def read(path): return json.loads(path.read_bytes())
def flat(run): return tuple(v for atom in run.atoms for row in (atom.r,atom.p) for v in row)

def load_inputs():
    manifest=read(INPUT)
    payload=manifest['payload']
    encoded=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    if hashlib.sha256(encoded).hexdigest()!=manifest['payload_sha256']:
        raise ValueError('input seal mismatch')
    if sha(PROTOCOL)!=payload['protocol_sha256'] or sha(SOURCE)!=payload['public_source_sha256']:
        raise ValueError('protocol/public source seal mismatch')
    for file,digest in payload['protected_sources'].items():
        if sha(ROOT/file)!=digest: raise ValueError('protected source changed: '+file)
    return payload

def case_input(case):
    return next(row for row in load_inputs()['inputs'] if row['id']==case)

def seal():
    from a_numeric import FixedPoint
    from a_reference.c1b1_canonical_state import canonical_initial_state
    from a_reference import c1b1_two_atom as C
    boundary=read(ROOT/'a_reference/fixtures/c1b1_orbit_boundary_v3.json')
    orbit={Q(r['e']):Q(r['b_orb']) for r in boundary['energies']}
    definitions=[('ordinary','0.5','6',None),('small_b','0.5','0.1',None),
                 ('large_b','0.5','14',None),('low_energy','0.01','7',None),
                 ('high_energy','9.9','0',None),('s4d_passing','0.15',None,'-0.005'),
                 ('s4d_no_wall','1','10',None),('boundary_reflect','0.5',None,'0.001'),
                 ('boundary_pass','0.5',None,'-0.001'),('boundary_challenge','0.5',None,'-0.0001')]
    rows=[]
    for label,e,b,rho in definitions:
        b=Q(b) if b is not None else orbit[Q(e)]*(1+Q(rho))
        state=canonical_initial_state(e,b)
        run=C.new_run(FixedPoint(96,48),40,**state,momentum_profile=FixedPoint(96,80))
        rows.append(dict(id=label,E_De=e,b_bohr=str(b),rho=rho,raw=list(flat(run)),
                         origin_step=0,scope='O1_OBSERVATION_ONLY',admission='passed',
                         initial_validation=run.validation))
    files=['a_reference/c1b1_two_atom.py','a_reference/ar2_lang2024.py',
           'a_reference/c1b1_canonical_state.py','a_reference/c1b1_domain_contract.py',
           'a_reference/fixtures/c1b1_orbit_boundary_v3.json','a_numeric/profiles.py']
    payload=dict(schema='c1b1-o1-input-seal-v1',base_head=BASE,inputs=rows,protocol_sha256=sha(PROTOCOL),
        public_source_sha256=sha(SOURCE),approval_sha256=sha(APPROVAL),
        protected_sources={f:sha(ROOT/f) for f in files},
        independent_sources={str(p.relative_to(ROOT)).replace('\\','/'):sha(p)
                             for p in sorted((ROOT/'c1b1_o1').glob('*.py'))},
        driver_sha256=sha(Path(__file__)),max_steps_per_case=250000,
        authorization='Human request 2026-10-01 explicitly permits new separately sealed O-1 inputs and normal replay verification.',
        reuse_pipeline_test_only=False,created_before_any_O1_trajectory=True)
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    save(INPUT,dict(payload=payload,payload_sha256=digest))
    print('SEALED',digest,flush=True)

def produce(case):
    from a_numeric import FixedPoint
    from a_reference import c1b1_two_atom as C
    from c1b1_replay.witness import Header,write
    row=case_input(case);raw=row['raw']
    state={key:tuple(Q(v,1<<bits) for v in raw[i:i+3]) for key,i,bits in
           [('r_i',0,48),('p_i',3,80),('r_j',6,48),('p_j',9,80)]}
    run=C.new_run(FixedPoint(96,48),40,**state,momentum_profile=FixedPoint(96,80))
    assert list(flat(run))==raw
    initial_j=C.impulse(C.relative(run.pos,*run.atoms),Q(20),run.mom)
    states=[raw]; impulses=[list(initial_j)]
    start,cpu=time.perf_counter(),time.process_time()
    entered=False
    cap=load_inputs()['max_steps_per_case']
    for _ in range(cap):
        C.step(run)
        states.append(list(flat(run)));impulses.append(list(run.J_cache))
        q=C.relative(run.pos,*run.atoms)
        r2=sum(v*v for v in q)
        entered |= r2<400
        pj=C.exact(run.mom,run.atoms[1].p)
        if entered and r2>=400 and sum(a*b for a,b in zip(q,pj))>0: break
    else:
        save(OUT/case/'producer_stop.json',dict(reason='sealed step budget',steps=cap))
        raise RuntimeError('sealed step budget, STOP')
    data=dict(id=case,states=states,impulses=impulses,steps=run.t_steps,
              cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start)
    path=OUT/case/'states.json';save(path,data)
    witness=OUT/case/'trajectory.c1br'
    with witness.open('xb') as stream:
        write(stream,Header(tuple(raw),tuple(initial_j),flat(run),run.t_steps,end='R20_OUTBOUND'),
              ((tuple(j),tuple(s)) for j,s in zip(impulses[1:],states[1:])))
    save(OUT/case/'producer.json',dict(id=case,states_sha256=sha(path),witness_sha256=sha(witness),
         steps=run.t_steps,cpu_seconds=data['cpu_seconds'],wall_seconds=data['wall_seconds'],
         evidence='EXECUTED',confirmation='SPECULATIVE'))
    print(case,'EXECUTED',run.t_steps,flush=True)

def confirm(case):
    # Fresh process: no reference/numeric/engine/audit import.
    from c1b1_replay.history import Approval,History
    from c1b1_replay.witness import Reader
    from c1b1_replay.types import Limits
    from c1b1_replay import exact
    from c1b1_replay.provenance import FORBIDDEN
    row=case_input(case);approved=read(APPROVAL);fp=approved['fingerprints']
    assert sha(APPROVAL)==load_inputs()['approval_sha256']
    approval=Approval(approved['designer_decision'],fp['replay_spec'],fp['implementation'],fp['dependency'])
    if not approval.matches(): raise RuntimeError('approved verifier fingerprints no longer match')
    directory=OUT/case; witness=directory/'trajectory.c1br'
    history=History(directory/'confirmed_store',tuple(row['raw']),approval=approval)
    history.enqueue(witness.read_bytes())
    result=history.verify_next();entry=history.entries[-1]
    save(directory/'replay.json',dict(result=asdict(result),status=entry.status,evidence=entry.evidence,
                                    origin_manifest_sha256=sha(INPUT)))
    if entry.status!='CONFIRMED' or entry.evidence!='REPLAY_VERIFIED':
        raise RuntimeError('replay not CONFIRMED; STOP')
    # Bind redundant producer state data to each raw claim in verified witness.
    # This is provenance checking only, never the O-1 continuous calculator.
    data=read(directory/'states.json')
    with witness.open('rb') as stream:
        reader=Reader(stream,Limits());header=reader.header();current=header.initial;j=header.initial_j
        assert data['states'][0]==list(current) and data['impulses'][0]==list(j)
        for i in range(header.n_steps):
            next_j,residual=reader.record();predicted=exact.transition(current,j,next_j)
            current=tuple(a+b for a,b in zip(predicted,residual));j=next_j
            assert data['states'][i+1]==list(current) and data['impulses'][i+1]==list(j)
    forbidden=sorted(n for n in sys.modules if n.split('.')[0] in FORBIDDEN)
    assert not forbidden,forbidden
    save(directory/'confirmed.json',dict(id=case,confirmation='CONFIRMED',evidence='REPLAY_VERIFIED',
        input_manifest_sha256=sha(INPUT),states_sha256=sha(directory/'states.json'),
        witness_sha256=sha(witness),retained_witness_sha256=sha(entry.witness_path),
        replay_result_sha256=sha(directory/'replay.json'),forbidden_imports=forbidden,steps=header.n_steps,
        approval_sha256=sha(APPROVAL),scope='O1_OBSERVATION_ONLY'))
    print(case,'REPLAY_VERIFIED CONFIRMED',flush=True)

def relative(raw):
    q=[(raw[i+6]-raw[i])/(1<<48) for i in range(3)]
    p=[(raw[i+9]-raw[i+3])/(2*(1<<80)) for i in range(3)]
    return q,p

def observe(case):
    import mpmath as m
    from c1b1_o1.model import Potential,MASS,DE
    from c1b1_o1.continuous import scatter,Unresolved
    from c1b1_o1.compare import converged,classify
    row=case_input(case);directory=OUT/case;confirmation=read(directory/'confirmed.json')
    if confirmation['confirmation']!='CONFIRMED' or confirmation['states_sha256']!=sha(directory/'states.json'):
        raise RuntimeError('confirmed observation binding mismatch')
    if confirmation['input_manifest_sha256']!=sha(INPUT): raise RuntimeError('origin seal changed')
    data=read(directory/'states.json');states=data['states'];n=data['steps']
    q0,p0=relative(states[0]);qf,pf=relative(states[-1]);r_exit=math.hypot(*qf)
    # Actual stored radius is converted from exact integers at EACH precision.
    levels=[];start,cpu=time.perf_counter(),time.process_time()
    try:
        for dps in (40,60,80):
            with m.workdps(dps):
                raw=states[0];q=[m.mpf(raw[i+6]-raw[i])/2**48 for i in range(2)]
                p=[m.mpf(raw[i+9]-raw[i+3])/2**81 for i in range(2)]
                final=states[-1]
                re=m.sqrt(sum((m.mpf(final[i+6]-final[i])/2**48)**2 for i in range(3)))
                mu=m.mpf(Q(MASS).numerator)/Q(MASS).denominator/2
                tc,tw=time.process_time(),time.perf_counter()
                value=scatter(Potential(),mu,q,p,re,dps)
                value.update(dps=dps,target=str(m.power(10,-dps//2)),
                             cpu_seconds=time.process_time()-tc,wall_seconds=time.perf_counter()-tw)
                levels.append(value)
                save(directory/f'independent_{dps}.json',value)
                print(case,'independent',dps,'digits',flush=True)
    except Unresolved as error:
        save(directory/'observation.json',dict(id=case,verdict='UNRESOLVED',reason=str(error),levels=levels))
        return
    stable=converged(levels)
    if not stable:
        save(directory/'observation.json',dict(id=case,verdict='UNRESOLVED',reason='sealed convergence criterion',levels=levels))
        return
    # All-state energy/L observations at 35 digits using the independent PES.
    with m.workdps(35):
        potential=Potential();mu=m.mpf(Q(MASS).numerator)/Q(MASS).denominator/2;de=m.mpf(DE)
        H0=None;sweep=0.0;min_r2=400.0;max_e=m.mpf(0);max_L=Q(0);previous=None
        max_p=0.0;max_r=0.0
        for raw in states:
            qi=[m.mpf(raw[i+6]-raw[i])/2**48 for i in range(3)]
            pi=[m.mpf(raw[i+9]-raw[i+3])/2**81 for i in range(3)]
            radius=m.sqrt(sum(x*x for x in qi));H=sum(x*x for x in pi)/(2*mu)+potential(radius)
            H0=H if H0 is None else H0;max_e=max(max_e,abs(H-H0)/de)
            Lz=Q((raw[6]-raw[0])*(raw[10]-raw[4])-(raw[7]-raw[1])*(raw[9]-raw[3]),2**129)
            if previous is None:L0=Lz
            max_L=max(max_L,abs(Lz-L0));max_p=max(max_p,float(m.sqrt(sum(x*x for x in pi))))
            qd,pd=relative(raw);max_r=max(max_r,float(radius))
            if previous is not None:
                a=previous;d=[b-c for b,c in zip(qd,a)];dd=sum(v*v for v in d)
                s=max(0,min(1,-sum(v*w for v,w in zip(a,d))/dd)) if dd else 0
                min_r2=min(min_r2,sum((v+s*w)**2 for v,w in zip(a,d)))
                sweep+=math.atan2(a[0]*qd[1]-a[1]*qd[0],a[0]*qd[0]+a[1]*qd[1])
            previous=qd
        chi=math.atan2(p0[0]*pf[1]-p0[1]*pf[0],p0[0]*pf[0]+p0[1]*pf[1])
        actual=dict(chi=chi,sweep=sweep,direction=math.atan2(pf[1],pf[0]),r_min=math.sqrt(min_r2),
                    energy=float(max_e),energy_final_De=float((H-H0)/de),
                    energy_states_evaluated=len(states),angular_max_change_exact=str(max_L),
                    angular_final_change_exact=str(Lz-L0),relative_p_out=pf,
                    r_exit=r_exit,steps=n,H0_hartree=m.nstr(H0,32),L0_exact=str(L0))
        # Conservative per-step torque budget, from |δdr|<=sqrt(3)*2^-48,
        # each half kick |δJ|<=sqrt(3)*2^-81, central exact force has zero torque.
        actual['angular_rounding_budget']=n*math.sqrt(3)*(2**-48*(max_p+1)+2**-80*max_r)
    # Orthogonal general continuous ODE check, with independent complex-step force.
    ode=ode_check(row,r_exit,float(levels[-1]['time']),levels[-1])
    judgment=classify(levels[-1],actual,stable)
    if not ode['stable']:
        judgment=dict(verdict='UNRESOLVED',reason='Cartesian ODE structural crosscheck failed')
    if float(max_L)>actual['angular_rounding_budget']:
        judgment=dict(verdict='DISAGREE',reason='angular rounding budget violated')
    result=dict(id=case,**judgment,input=row,independent=levels,A=actual,ode=ode,
        independent_converged=stable,confirmation=confirmation,
        cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start,
        observation_scope='finite inlet to matched actual outlet; not chi at infinity')
    save(directory/'observation.json',result)
    print(case,judgment['verdict'],judgment.get('differences'),flush=True)

def ode_check(row,r_exit,t_ref,reference):
    import cmath
    import numpy as np
    from scipy.integrate import solve_ivp
    from c1b1_o1.model import Potential,MASS,DE
    class Double:
        mpf=staticmethod(float)
        exp=staticmethod(cmath.exp)
    V=Potential(ctx=Double());mu=float(Q(MASS))/2
    q,p=relative(row['raw']);initial=q[:2]+p[:2]
    def rhs(t,y):
        r=math.hypot(y[0],y[1]);derivative=V(complex(r,1e-20)).imag/1e-20
        return [y[2]/mu,y[3]/mu,-derivative*y[0]/r,-derivative*y[1]/r]
    def exit_event(t,y):return math.hypot(y[0],y[1])-r_exit
    exit_event.direction=1;exit_event.terminal=True
    rows=[]
    for tol in (1e-10,1e-12):
        start=time.perf_counter()
        sol=solve_ivp(rhs,(0,t_ref*1.1+80),initial,method='DOP853',rtol=tol,atol=tol*1e-2,events=exit_event)
        if not sol.success or len(sol.t_events[0])!=1:
            return dict(stable=False,reason='DOP853 failed to find matched exit',rows=rows)
        out=sol.y_events[0][0];direction=math.atan2(out[3],out[2]);sweep=0.0
        for a,b in zip(sol.y.T[:-1],sol.y.T[1:]):
            sweep+=math.atan2(a[0]*b[1]-a[1]*b[0],a[0]*b[0]+a[1]*b[1])
        energy=[(y[2]**2+y[3]**2)/(2*mu)+V(math.hypot(y[0],y[1])).real for y in sol.y.T]
        angular=sol.y[0]*sol.y[3]-sol.y[1]*sol.y[2]
        rows.append(dict(tolerance=tol,direction=direction,sweep=sweep,time=float(sol.t_events[0][0]),
            energy_max_change_De=max(abs(e-energy[0]) for e in energy)/float(DE),
            angular_max_change=float(np.max(np.abs(angular-angular[0]))),evaluations=sol.nfev,
            wall_seconds=time.perf_counter()-start))
    difference=abs(math.atan2(math.sin(rows[-1]['direction']-float(reference['direction'])),
                             math.cos(rows[-1]['direction']-float(reference['direction']))))
    stable=difference<=1e-7 and abs(rows[-1]['sweep']-float(reference['sweep']))<=1e-7
    return dict(stable=stable,direction_difference_from_high_precision=difference,rows=rows,
                note='binary64 orthogonal check; primary 40/60/80 digit reference remains quadrature')

def run_all():
    payload=load_inputs();completed=[];start=time.perf_counter()
    for row in payload['inputs']:
        case=row['id']
        for phase in ('produce','confirm','observe'):
            result=subprocess.run([sys.executable,str(Path(__file__)),phase,case],cwd=ROOT)
            if result.returncode:
                save(OUT/'campaign_stop.json',dict(case=case,phase=phase,exit_code=result.returncode,completed=completed))
                raise SystemExit(result.returncode)
        observation=read(OUT/case/'observation.json');completed.append(observation)
        if observation['verdict']!='AGREE':break
    done={x['id'] for x in completed}
    summary=dict(schema='c1b1-o1-results-v1',input_manifest_sha256=sha(INPUT),
        rows=completed,not_run=[dict(id=r['id'],status='NOT_RUN_AFTER_STOP') for r in payload['inputs'] if r['id'] not in done],
        counts={v:sum(r['verdict']==v for r in completed) for v in ('AGREE','DISAGREE','UNRESOLVED')},
        wall_seconds=time.perf_counter()-start,stopped=any(r['verdict']!='AGREE' for r in completed),
        base_head=BASE,physics_contract_changed=False,push=False)
    save(OUT/'summary.json',summary)
    print('O1',summary['counts'],'STOP=',summary['stopped'],flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['seal','produce','confirm','observe','run'])
    parser.add_argument('case',nargs='?');args=parser.parse_args()
    if args.phase=='seal':seal()
    elif args.phase=='run':run_all()
    else:globals()[args.phase](args.case)
