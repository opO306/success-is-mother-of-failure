"""Observation benchmark runner; primary trajectories require a remote marker."""
import argparse
from collections import Counter
import concurrent.futures
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time
import mpmath as m
from c1b1_o1.model import MASS,DE,SOURCE
from c1b1_o1_diagnostic.kdk import Lang,relative,angle_difference,step as baseline_step
from c1b1_o1_diagnostic.study import extend_reference
from .methods import advance,coefficients,first_gate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/c1b1_dt40_integrator_benchmark_20261001_v1'
SEAL=ROOT/'docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_SEAL_V1.json'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def save(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(data,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')


def chord_minimum(a,b):
    d=[y-x for x,y in zip(a,b)];dd=sum(x*x for x in d)
    t=max(m.mpf(0),min(m.mpf(1),-sum(x*y for x,y in zip(a,d))/dd)) if dd else m.mpf(0)
    return m.sqrt(sum((x+t*y)**2 for x,y in zip(a,d)))


class Field:
    def __init__(self,mu,pes_type=Lang):
        self.mu=mu;self.pes=pes_type();self.calls=Counter();self.cached_q=None;self.cached_force=None;self.value=None
        self.gradient_seconds=0.0
    def scalar(self,r,kind):
        self.calls[kind]+=1
        return self.pes.value_derivative(r)
    def force(self,q):
        if q!=self.cached_q:
            r=m.sqrt(sum(x*x for x in q));self.value,dv=self.scalar(r,'force')
            self.cached_force=[-dv*x/r for x in q];self.cached_q=q[:]
        return self.cached_force
    def gradient_force(self,q,h):
        f=self.force(q);r=m.sqrt(sum(x*x for x in q));dv=-sum(x*y for x,y in zip(f,q))/r
        start=time.process_time();d2=m.diff(lambda x:self.scalar(x,'gradient_derivative')[1],r)
        self.gradient_seconds+=time.process_time()-start;self.calls['gradient_vectors']+=1
        return [v+h*h*dv*d2*x/(24*self.mu*r) for v,x in zip(f,q)]


def load():
    data=read(SEAL);payload=data['payload']
    if hashlib.sha256(canonical(payload)).hexdigest()!=data['payload_sha256']:raise ValueError('benchmark seal mismatch')
    for name,digest in payload['sources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('source mismatch '+name)
    if sha(SOURCE)!=payload['public_source_sha256']:raise ValueError('Lang source mismatch')
    return payload


def make_seal():
    old=read(ROOT/'docs/active/C1B1_O1_RESULTS_V1.json')
    cause=read(ROOT/'docs/active/C1B1_O1_CAUSE_ISOLATION_RESULTS_V1.json')
    from c1b1_o1_diagnostic.study import load_seal,verify_artifacts
    protected=load_seal();verify_artifacts(old['artifacts']);verify_artifacts(cause['artifacts'])
    rows=[]
    with m.workdps(80):
        for result in old['rows']:
            states=read(ROOT/f"runs/c1b1_o1_20261001_v1/{result['id']}/states.json")['states']
            q,_=relative(states[-1]);radius=m.sqrt(sum(x*x for x in q))
            rows.append(dict(id=result['id'],input=result['input'],reference=result['independent'][-1],baseline_A=result['A'],baseline_KDK40_differences=result['differences'],base_radius=m.nstr(radius,80),confirmation=result['confirmation'],states_sha256=sha(ROOT/f"runs/c1b1_o1_20261001_v1/{result['id']}/states.json")))
        coef={method:{name:[m.nstr(v,60) for v in value] if isinstance(value,list) else m.nstr(value,60) for name,value in data.items()} for method,data in coefficients().items()}
    trace=ROOT/'runs/c1b1_o1_cause_isolation_20261001_v1/hp_kdk_dt20_dps60.jsonl.gz'
    n=34568;indices={round(i*n/1023) for i in range(1024)};samples=[]
    with gzip.open(trace,'rt',encoding='utf-8') as stream:
        for line in stream:
            record=json.loads(line)
            if record[0] in indices:samples.append(record)
    paths=list((ROOT/'c1b1_integrator_benchmark').glob('*.py'))+[ROOT/'tests/test_c1b1_integrator_benchmark.py',ROOT/'docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_PROTOCOL_V1.md']
    paths += list((ROOT/'c1b1_o1').glob('*.py'))+list((ROOT/'c1b1_o1_diagnostic').glob('*.py'))
    sources={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths}
    payload=dict(schema='c1b1-dt40-integrator-benchmark-seal-v1',head='508bba4fd01826aa6fb52f91c5011413a114f1aa',rows=rows,candidates=['yoshida4','chin4a'],outer_dt=40,precision=[40,60],coefficients=coef,sources=sources,public_source_sha256=sha(SOURCE),samples=samples,samples_trace_sha256=sha(trace),baseline_cause= cause['rows'],old_O1_artifacts=old['artifacts'],old_cause_artifacts=cause['artifacts'],protected_sources=protected['protected'],budget=dict(hourly_usd=1,total_usd=1,max_seconds=3600),workers=4,original_O1='STOPPED / NOT PASSED',phase_one_case='boundary_pass',not_run=['boundary_challenge'],criteria=dict(angle=1e-5,r_min_relative=1e-5,energy_De=1e-3,L=1e-20,precision_absolute=1e-20,kernel_cost_max=2,kernel_cost_spread_max=1.2,gain_if_slower_min=10))
    save(SEAL,dict(payload=payload,payload_sha256=hashlib.sha256(canonical(payload)).hexdigest()))
    print('SEALED',len(rows),'inputs',len(samples),'stored-state cost samples',flush=True)


def simulate(job):
    if os.getenv('C1B1_REMOTE_BENCHMARK')!='1':raise ValueError('trajectory integration is remote-only')
    import resource
    method,case,dps,cpu=job;os.sched_setaffinity(0,{cpu})
    payload=load();row=next(x for x in payload['rows'] if x['id']==case)
    key=f'{method}_{case}_dps{dps}';start=time.perf_counter();cpustart=time.process_time()
    with m.workdps(dps):
        mu=m.mpf(MASS.split('/')[0])/m.mpf(MASS.split('/')[1])/2;de=m.mpf(DE);h=m.mpf(40)
        q,p=relative(row['input']['raw']);initial_p=p[:];field=Field(mu);field.force(q)
        h0=sum(x*x for x in p)/(2*mu)+field.value;l0=q[0]*p[1]-q[1]*p[0]
        minimum=m.sqrt(sum(x*x for x in q));outer_min=minimum;sweep=m.mpf(0);max_e=max_l=m.mpf(0)
        def guard(a,b):
            nonlocal minimum
            minimum=min(minimum,chord_minimum(a,b))
            if minimum<m.mpf('2.4'):raise ValueError('internal drift chord r_min violation')
        trace=OUT/(key+'.jsonl.gz');trace.parent.mkdir(parents=True,exist_ok=True)
        try:
            with trace.open('xb') as binary,gzip.GzipFile(fileobj=binary,mode='wb',mtime=0) as gz:
                def record(n,q,p):gz.write((json.dumps([n]+[m.nstr(x,dps) for x in q+p],separators=(',',':'))+'\n').encode())
                record(0,q,p)
                for n in range(1,250001):
                    oldq=q;q,p=advance(method,q,p,h,mu,field,guard)
                    radius=m.sqrt(sum(x*x for x in q));outer_min=min(outer_min,chord_minimum(oldq,q))
                    sweep+=m.atan2(oldq[0]*q[1]-oldq[1]*q[0],sum(a*b for a,b in zip(oldq,q)))
                    H=sum(x*x for x in p)/(2*mu)+field.value;L=q[0]*p[1]-q[1]*p[0]
                    max_e=max(max_e,abs(H-h0)/de);max_l=max(max_l,abs(L-l0));record(n,q,p)
                    if n%10000==0:print(key,'step',n,'R',m.nstr(radius,9),flush=True)
                    if radius>=m.mpf(row['base_radius']) and sum(a*b for a,b in zip(q,p))>0:break
                else:raise ValueError('step limit exceeded')
            direction=m.atan2(p[1],p[0]);chi=m.atan2(m.sin(direction-m.atan2(initial_p[1],initial_p[0])),m.cos(direction-m.atan2(initial_p[1],initial_p[0])))
            values=dict(chi=chi,direction=direction,r_min_internal=minimum,r_min_outer=outer_min,r_exit=radius,sweep=sweep,energy_max_change_De=max_e,energy_final_change_De=(H-h0)/de,angular_max_change=max_l,H0=h0,L0=l0,time=n*h)
            result={k:m.nstr(v,dps) for k,v in values.items()}
            result.update(method=method,id=case,dps=dps,cpu_affinity=cpu,outer_dt=40,outer_steps=n,calls=dict(field.calls),gradient_cpu_seconds=field.gradient_seconds,cpu_seconds=time.process_time()-cpustart,wall_seconds=time.perf_counter()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,q_out=[m.nstr(x,dps) for x in q],p_out=[m.nstr(x,dps) for x in p],trace_sha256=sha(trace),trace_file=trace.name,r_min_violation=False,domain_status='ALL_INTERNAL_DRIFT_CHORDS_CHECKED')
            endpoint=time.process_time();ref=extend_reference(row['reference'],m.mpf(row['base_radius']),radius,mu,lambda r:field.scalar(r,'endpoint')[0])
            result['endpoint_cpu_seconds']=time.process_time()-endpoint;result['endpoint_calls']=field.calls['endpoint'];result['matched_continuous']=ref
            result['errors']={k:m.nstr(angle_difference(m.mpf(result[k]),m.mpf(ref[k])),dps) for k in ('chi','direction')}
            result['errors']['r_min']=m.nstr(abs(minimum-m.mpf(ref['r_min'])),dps)
            result['observation_pass']=float(result['errors']['chi'])<=1e-5 and float(result['errors']['direction'])<=1e-5 and float(result['errors']['r_min'])<=float(ref['r_min'])*1e-5 and float(max_e)<=1e-3 and float(max_l)<=1e-20
            result['negative_internal_dt']=method=='yoshida4'
        except ValueError as exc:
            result=dict(method=method,id=case,dps=dps,status='STOP',reason=str(exc),calls=dict(field.calls),cpu_seconds=time.process_time()-cpustart,wall_seconds=time.perf_counter()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save(OUT/(key+'.json'),result);print('RESULT',key,result.get('errors',result.get('reason')),flush=True)
    return result


def cost_probe(cpu):
    os.sched_setaffinity(0,{cpu});payload=load();report={}
    with m.workdps(60):
        mu=m.mpf(MASS.split('/')[0])/m.mpf(MASS.split('/')[1])/2
        samples=[([m.mpf(x) for x in rec[1:3]],[m.mpf(x) for x in rec[3:5]]) for rec in payload['samples']]
        for method in ('kdk20','yoshida4','chin4a'):
            repetitions=[]
            for _ in range(3):
                field=Field(mu);total_cpu=total_wall=0.0;timed_calls=Counter()
                for q,p in samples:
                    field.force(q);before=field.calls.copy();c=time.process_time();t=time.perf_counter()
                    if method=='kdk20':
                        out,_=baseline_step(q,p,m.mpf(20),mu,field.force);chord_minimum(q,out)
                    else:advance(method,q,p,m.mpf(40),mu,field,lambda a,b:chord_minimum(a,b))
                    total_cpu+=time.process_time()-c;total_wall+=time.perf_counter()-t;timed_calls.update(field.calls-before)
                repetitions.append(dict(cpu_seconds=total_cpu,wall_seconds=total_wall,timed_calls=dict(timed_calls)))
            report[method]=dict(samples=len(samples),repetitions=repetitions,median_cpu=statistics.median(x['cpu_seconds'] for x in repetitions),median_wall=statistics.median(x['wall_seconds'] for x in repetitions),cpu_spread=max(x['cpu_seconds'] for x in repetitions)/min(x['cpu_seconds'] for x in repetitions))
    for method in ('yoshida4','chin4a'):
        report[method]['cost_ratio_per_outer40']=report[method]['median_cpu']/(2*report['kdk20']['median_cpu'])
    report['scope']='stored-state one-step kernel cost only; baseline trajectory not recreated';report['affinity_cpu']=cpu
    save(OUT/'kernel_cost_probe.json',report);return report


def precision_stable(a,b):
    if 'errors' not in a or 'errors' not in b:return False,{}
    with m.workdps(70):
        fields=['chi','direction','r_min_internal','r_exit','energy_max_change_De']
        diffs={k:abs(m.mpf(a[k])-m.mpf(b[k])) for k in fields}
        for k in ('q_out','p_out'):
            for i,(x,y) in enumerate(zip(a[k],b[k])):diffs[k+str(i)]=abs(m.mpf(x)-m.mpf(y))
        return max(diffs.values())<=m.mpf('1e-20'),{k:m.nstr(v,40) for k,v in diffs.items()}


def campaign():
    if os.getenv('C1B1_REMOTE_BENCHMARK')!='1':raise ValueError('remote marker required')
    payload=load();cpus=sorted(os.sched_getaffinity(0))[:4]
    if len(cpus)<4:raise ValueError('four independent CPU slots required')
    jobs=[(method,'boundary_pass',dps,cpus[i]) for i,(method,dps) in enumerate([(a,b) for a in payload['candidates'] for b in (60,40)])]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:first=list(pool.map(simulate,jobs))
    cost=cost_probe(cpus[0]);gates={};survivors=[]
    base=next(r for r in payload['baseline_cause'] if r['dt']==20);base_error=float(base['differences']['chi'])
    for method in payload['candidates']:
        a=next(r for r in first if r['method']==method and r['dps']==40);b=next(r for r in first if r['method']==method and r['dps']==60)
        stable,changes=precision_stable(a,b);error=float(b.get('errors',{}).get('chi',math.inf));ratio=cost[method]['cost_ratio_per_outer40'];gain=base_error/error if error else math.inf
        domain='errors' in b and not b['r_min_violation'];conservation='errors' in b and float(b['energy_max_change_De'])<=1e-3 and float(b['angular_max_change'])<=1e-20
        verdict=first_gate(error,ratio,gain,stable,domain,conservation)
        if cost[method]['cpu_spread']>1.2 or cost['kdk20']['cpu_spread']>1.2:verdict='UNRESOLVED_COST'
        if 'errors' in b and not b['observation_pass'] and verdict in ('PROMISING_PARETO','BEATS_KDK20_KERNEL'):verdict='REJECT_OBSERVABLE'
        gates[method]=dict(verdict=verdict,precision_stable=stable,precision_changes=changes,cost_ratio=ratio,accuracy_gain_over_KDK20=gain)
        if verdict in ('PROMISING_PARETO','BEATS_KDK20_KERNEL'):survivors.append(method)
    save(OUT/'first_stage_gates.json',gates);print('GATES',gates,flush=True)
    panel=[]
    for method in survivors:
        jobs=[(method,row['id'],dps,cpus[i%len(cpus)]) for i,(row,dps) in enumerate((r,d) for r in payload['rows'] if r['id']!='boundary_pass' for d in (60,40))]
        # Each active worker receives one affinity slot. Submit in four-job waves.
        for offset in range(0,len(jobs),4):
            wave=jobs[offset:offset+4]
            with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:panel.extend(pool.map(simulate,wave))
            recent=[r for r in panel if r in panel[-len(wave):]]
            if any('errors' not in r or not r['observation_pass'] for r in recent):
                print('PANEL STOP',method,flush=True);break
    all_results=first+panel
    panel_status={}
    for method in survivors:
        ids=sorted({r['id'] for r in all_results if r['method']==method})
        observed=[]
        for case in ids:
            pair=[r for r in all_results if r['method']==method and r['id']==case]
            a=next((r for r in pair if r['dps']==40),{});b=next((r for r in pair if r['dps']==60),{})
            stable,changes=precision_stable(a,b)
            observed.append(dict(id=case,precision_stable=stable,precision_changes=changes,observation_pass=b.get('observation_pass',False),result=b))
        panel_status[method]=dict(rows=observed,complete=len(observed)==9,passed=len(observed)==9 and all(r['precision_stable'] and r['observation_pass'] for r in observed))
    conclusion='B' if not survivors else 'C'
    # A is limited to measured kernel cost; full baseline remote CPU is unavailable.
    kernel_winners=[method for method in survivors if gates[method]['verdict']=='BEATS_KDK20_KERNEL' and panel_status[method]['passed']]
    if kernel_winners:conclusion='A_KERNEL_ONLY'
    elif survivors and all(x['complete'] for x in panel_status.values()) and all(gates[x]['cost_ratio']>1 for x in survivors):conclusion='B_KERNEL_COST'
    save(OUT/'summary.json',dict(schema='c1b1-dt40-integrator-benchmark-results-v1',first=first,cost_probe=cost,gates=gates,survivors=survivors,panel=panel_status,all_results=all_results,conclusion=conclusion,status='NO_CANDIDATE_BEATS_BASELINE' if not survivors else 'DIAGNOSTIC_FINISHED',original_O1='STOPPED / NOT PASSED',production_changed=False,full_baseline_recreated=False,not_run=['boundary_challenge'],seal_sha256=sha(SEAL)))
    print('CONCLUSION',conclusion,'survivors',survivors,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['seal','campaign']);args=parser.parse_args()
    make_seal() if args.phase=='seal' else campaign()
