"""Sealed, sequential, whole-trajectory performance comparison; no new integrator."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import mpmath as m
from c1b1_o1.model import MASS,DE
from c1b1_o1_diagnostic.kdk import relative,step,angle_difference
from c1b1_o1_diagnostic.study import extend_reference
from c1b1_integrator_benchmark.methods import advance
from c1b1_integrator_benchmark.study import Field,chord_minimum,load as original_load

ROOT=Path(__file__).resolve().parent
SEAL=ROOT/'docs/active/C1B1_KDK20_YOSHIDA40_COST_SEAL_V3.json'
OUT=ROOT/'runs/c1b1_kdk20_yoshida40_cost_v1'
METHODS=('kdk20','yoshida4')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(data,stream,indent=2,allow_nan=False);stream.write('\n')


def load():
    seal=read(SEAL);p=seal['payload']
    encoded=json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    if hashlib.sha256(encoded).hexdigest()!=seal['payload_sha256']:raise ValueError('cost seal hash')
    for name,digest in p['sources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('cost source hash '+name)
    original=original_load()
    if p['parent_payload_sha256']!=hashlib.sha256(json.dumps(original,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest():
        raise ValueError('parent numerical seal changed')
    if [x['id'] for x in original['rows']]!=p['input_order']:raise ValueError('input panel changed')
    return p,original


def checked(rows):
    if any(not r.get('observation_pass') or not r.get('reproduction_pass') for r in rows):
        raise ValueError('numerical observation/reproduction failed')


def single_summary(rows):
    rows=[r for r in rows if r['phase']=='single'];checked(rows);result={}
    for method in METHODS:
        samples=[r for r in rows if r['method']==method]
        if len(samples)!=3:raise ValueError('three measured runs required')
        values={}
        for kind in ('cpu','wall'):
            ts=[r[kind+'_seconds'] for r in samples]
            if min(ts)<=0 or max(ts)/min(ts)>1.2:raise ValueError('runtime variation exceeds sealed 1.2')
            values['median_'+kind]=statistics.median(ts)
            values[kind+'_spread']=max(ts)/min(ts)
        result[method]=values
    result['wall_ratio']=result['yoshida4']['median_wall']/result['kdk20']['median_wall']
    result['cpu_ratio']=result['yoshida4']['median_cpu']/result['kdk20']['median_cpu']
    result['stage_one']='FASTER' if result['wall_ratio']<.9 else 'SIMILAR' if result['wall_ratio']<=1.1 else 'SLOWER'
    return result


def aggregate(rows,ids):
    panel=[r for r in rows if r['phase']=='panel'];checked(panel)
    if len(ids)!=9 or len(panel)!=18 or any(sum(r['id']==key and r['method']==method for r in panel)!=1 for key in ids for method in METHODS):
        raise ValueError('complete nine input pair panel required')
    totals={}
    for method in METHODS:
        subset=[r for r in panel if r['method']==method]
        totals[method]={key:sum(r[key] for r in subset) for key in ('cpu_seconds','wall_seconds','outer_steps','output_bytes')}
        totals[method].update(force_evaluations=sum(r['calls'].get('force',0) for r in subset),
            derivative_evaluations=sum(r['calls'].get('gradient_derivative',0) for r in subset),
            peak_rss_kib=max(r['peak_rss_kib'] for r in subset))
    wall=totals['yoshida4']['wall_seconds']/totals['kdk20']['wall_seconds']
    cpu=totals['yoshida4']['cpu_seconds']/totals['kdk20']['cpu_seconds']
    verdict='A' if max(wall,cpu)<=1.1 else 'B' if min(wall,cpu)>1.1 else 'C'
    return dict(totals=totals,wall_ratio=wall,cpu_ratio=cpu,conclusion=verdict,
        status={'A':'DT40_HIGH_ORDER_CANDIDATE_SUPPORTED','B':'YOSHIDA_ACCURATE_BUT_COSTLIER','C':'INCONCLUSIVE'}[verdict])


def run_trajectory(method,row,out,key,expected,phase='single'):
    if os.getenv('C1B1_REMOTE_BENCHMARK')!='1':raise ValueError('scattering is remote-only')
    if method not in METHODS:raise ValueError('only KDK20 and sealed Yoshida40')
    import resource
    cpu_start=time.process_time();wall_start=time.perf_counter()
    with m.workdps(60):
        mu=m.mpf(MASS.split('/')[0])/m.mpf(MASS.split('/')[1])/2;de=m.mpf(DE)
        h=m.mpf(20 if method=='kdk20' else 40);q,p=relative(row['input']['raw']);initial_p=p[:]
        field=Field(mu);field.force(q);H0=sum(x*x for x in p)/(2*mu)+field.value;L0=q[0]*p[1]-q[1]*p[0]
        minimum=outer_min=m.sqrt(sum(x*x for x in q));max_e=max_l=sweep=m.mpf(0)
        def guard(a,b):
            nonlocal minimum
            minimum=min(minimum,chord_minimum(a,b))
            if minimum<m.mpf('2.4'):raise ValueError('internal chord r_min violation')
        trace=Path(out)/(key+'.jsonl.gz')
        with trace.open('xb') as binary,gzip.GzipFile(fileobj=binary,mode='wb',filename='',mtime=0,compresslevel=9) as gz:
            def record(n):gz.write((json.dumps([n]+[m.nstr(x,60) for x in q+p],separators=(',',':'))+'\n').encode())
            record(0)
            for n in range(1,250001):
                oldq=q
                if method=='kdk20':
                    q,p=step(q,p,h,mu,field.force);guard(oldq,q)
                else:q,p=advance('yoshida4',q,p,h,mu,field,guard)
                radius=m.sqrt(sum(x*x for x in q));outer_min=min(outer_min,chord_minimum(oldq,q))
                sweep+=m.atan2(oldq[0]*q[1]-oldq[1]*q[0],sum(a*b for a,b in zip(oldq,q)))
                H=sum(x*x for x in p)/(2*mu)+field.value;L=q[0]*p[1]-q[1]*p[0]
                max_e=max(max_e,abs(H-H0)/de);max_l=max(max_l,abs(L-L0));record(n)
                if radius>=m.mpf(row['base_radius']) and sum(x*y for x,y in zip(q,p))>0:break
            else:raise ValueError('step limit')
        direction=m.atan2(p[1],p[0]);chi=m.atan2(m.sin(direction-m.atan2(initial_p[1],initial_p[0])),m.cos(direction-m.atan2(initial_p[1],initial_p[0])))
        values=dict(chi=chi,direction=direction,r_min_internal=minimum,r_min_outer=outer_min,r_exit=radius,
            sweep=sweep,H0=H0,L0=L0,time=n*h,energy_max_change_De=max_e,energy_final_change_De=(H-H0)/de,angular_max_change=max_l)
        result={k:m.nstr(v,60) for k,v in values.items()}
        calls=dict(field.calls);endpoint_start=time.process_time()
        ref=extend_reference(row['reference'],m.mpf(row['base_radius']),radius,mu,lambda r:field.scalar(r,'endpoint')[0])
        errors={k:m.nstr(angle_difference(values[k],m.mpf(ref[k])),60) for k in ('chi','direction')}
        errors['r_min']=m.nstr(abs(minimum-m.mpf(ref['r_min'])),60)
        observed=all(m.mpf(errors[k])<=m.mpf('1e-5') for k in ('chi','direction')) and m.mpf(errors['r_min'])<=m.mpf(ref['r_min'])*m.mpf('1e-5') and max_e<=m.mpf('1e-3') and max_l<=m.mpf('1e-20')
        reproduced=True;changes={}
        if expected is not None:
            fields=['chi','direction','r_min_internal','r_exit','energy_max_change_De']
            if method=='kdk20':expected=dict(expected,r_min_internal=expected['r_min_chord'])
            changes={k:m.nstr(abs(values[k]-m.mpf(expected[k])),60) for k in fields}
            reproduced=all(m.mpf(v)<=m.mpf('1e-20') for v in changes.values()) and n==expected.get('outer_steps',expected.get('steps'))
        result.update(method=method,id=row['id'],phase=phase,dps=60,outer_dt=int(h),outer_steps=n,calls=calls,
            endpoint_calls=field.calls['endpoint'],endpoint_cpu_seconds=time.process_time()-endpoint_start,
            errors=errors,matched_continuous=ref,observation_pass=bool(observed),reproduction_pass=bool(reproduced),reproduction_changes=changes,
            r_min_violation=False,q_out=[m.nstr(x,60) for x in q],p_out=[m.nstr(x,60) for x in p],
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,trace_file=trace.name,trace_sha256=sha(trace),trace_bytes=trace.stat().st_size,
            affinity=sorted(os.sched_getaffinity(0)))
        summary=Path(out)/(key+'.json')
        save(summary,result) # necessary numerical output is inside the measured interval
    result.update(cpu_seconds=time.process_time()-cpu_start,wall_seconds=time.perf_counter()-wall_start)
    # Performance bookkeeping cannot timestamp its own final byte; this small
    # metadata rewrite is outside runtime, identically for both methods.
    with summary.open('w',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    result['output_bytes']=trace.stat().st_size+summary.stat().st_size
    return result


def campaign():
    if os.getenv('C1B1_REMOTE_BENCHMARK')!='1':raise ValueError('campaign is remote-only')
    sealed,original=load();OUT.mkdir(parents=True,exist_ok=False);results=[]
    cpu=min(os.sched_getaffinity(0))
    start=time.perf_counter();cpu0=time.process_time()
    def execute(method,case,phase,index):
        key=f'{index:02d}_{phase}_{method}_{case}'
        print('START',key,flush=True)
        subprocess.run([sys.executable,'-B','-u',str(Path(__file__)), 'one',method,case,phase,key,str(cpu)],check=True,timeout=300)
        result=read(OUT/(key+'.json'));result['output_bytes']=sum((OUT/(key+suffix)).stat().st_size for suffix in ('.json','.jsonl.gz'))
        results.append(result);save(OUT/f'progress_{index:02d}.json',results)
        checked([result]);print('DONE',key,result['wall_seconds'],result['errors']['chi'],flush=True)
    try:
        for i,method in enumerate(METHODS):execute(method,'boundary_pass','warmup',i)
        for i,method in enumerate(sealed['single_order'],2):execute(method,'boundary_pass','single',i)
        first=single_summary(results);save(OUT/'single_summary.json',first);print('SINGLE',first,flush=True)
        for j,case in enumerate(sealed['input_order']):
            order=METHODS if j%2==0 else METHODS[::-1]
            for k,method in enumerate(order):execute(method,case,'panel',8+2*j+k)
        panel=aggregate(results,sealed['input_order'])
        save(OUT/'summary.json',dict(single=first,panel=panel,runs=results,status=panel['status'],conclusion=panel['conclusion'],
            campaign_wall_seconds=time.perf_counter()-start,orchestrator_cpu_seconds=time.process_time()-cpu0,
            warmup_excluded=True,production_changed=False,O1='STOPPED / NOT PASSED'))
        print('CONCLUSION',panel['conclusion'],panel['status'],flush=True)
    except BaseException as exc:
        save(OUT/'failure.json',dict(conclusion='C',status='INCONCLUSIVE',reason=str(exc),runs=results));raise


if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='campaign':campaign()
    elif len(sys.argv)==7 and sys.argv[1]=='one':
        if os.getenv('C1B1_REMOTE_BENCHMARK')!='1':raise SystemExit('scattering is remote-only')
        _,_,method,case,phase,key,cpu=sys.argv
        os.sched_setaffinity(0,{int(cpu)});sealed,original=load()
        row=next(r for r in original['rows'] if r['id']==case)
        expected=next((r for r in read(ROOT/sealed['prior_results'])['raw_numerical_summary']['all_results'] if r['method']==method and r['id']==case and r['dps']==60),None)
        if method=='kdk20' and case=='boundary_pass':expected=next(r for r in original['baseline_cause'] if r['dt']==20 and r['dps']==60)
        run_trajectory(method,row,OUT,key,expected,phase)
    else:raise SystemExit('campaign or one method case phase key cpu')
