"""Repository integration evidence, full regression, paired trajectories and CPU cost."""
from __future__ import annotations
import ast
import copy
import gzip
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import types
import xml.etree.ElementTree as ET
from fractions import Fraction as Q
from pathlib import Path
from . import evidence as E, candidate_b as B, fast_primitives as FP
from a_reference import c1b1_two_atom as C, c1b1_fast_impulse as FAST, c1b1_impulse_primitives as RP
from a_reference import c1b1_stress_survey as X


def functions(path):
    return {f.name:f for f in ast.parse(Path(path).read_bytes()).body if isinstance(f,ast.FunctionDef)}


def clean(fn):
    fn = copy.deepcopy(fn)
    if isinstance(fn.body[0],ast.Expr) and isinstance(fn.body[0].value,ast.Constant) and isinstance(fn.body[0].value.value,str):
        fn.body.pop(0)
    return ast.dump(fn,include_attributes=False)


def repo_equivalence():
    a,b = functions(B.__file__),functions(FAST.__file__)
    expected = copy.deepcopy(a['_model_R'])
    expected.name = '_impulse_model_R_fast'
    actual = copy.deepcopy(b['_impulse_model_R_fast'])
    guard = actual.body.pop(1)
    assert ast.unparse(guard.test) == 'not 0 < R[0] <= R[1]'
    assert isinstance(guard.body[0],ast.Raise)
    assert clean(expected) == clean(actual)
    expected = copy.deepcopy(a['_model'])
    for node in ast.walk(expected):
        if isinstance(node,ast.Name) and node.id == '_model_R':
            node.id = '_impulse_model_R_fast'
    assert clean(expected) == clean(b['_model'])
    assert clean(a['impulse']) == clean(b['impulse'])
    p,q = functions(FP.__file__),functions(RP.__file__)
    assert p.keys() == q.keys()
    assert all(clean(p[k]) == clean(q[k]) for k in p)
    assert FAST.step_fast.__code__ is C.step.__code__
    assert FAST.step_fast.__globals__['impulse'] is FAST.impulse
    assert C.step.__globals__['impulse'] is C.impulse
    return True


def raw(run):
    return dict(step=run.t_steps,atoms=[dict(species=a.species,r=a.r,p=a.p) for a in run.atoms],J_cache=run.J_cache)


def make_run(spec):
    if 'refusal' in spec:
        from a_numeric.profiles import FixedPoint
        z=(Q(0),)*3
        kind=spec['refusal']
        if kind=='domain':
            p=(Q(6000),Q(0),Q(0))
            return C.new_run(X.POS,40,(Q(0),Q(-1),Q(0)),tuple(-q for q in p),
                             (Q(-3),Q(1),Q(0)),p,momentum_profile=X.MOM,validated_only=False)
        if kind=='impulse_overflow':
            return C.new_run(X.POS,40,z,z,(Q(3),Q(0),Q(0)),z,momentum_profile=FixedPoint(8,4),validated_only=False)
        if kind=='momentum_overflow':
            p=(Q(12799,100),Q(0),Q(0))
            return C.new_run(X.POS,40,z,tuple(-q for q in p),(Q(5),Q(0),Q(0)),p,
                             momentum_profile=FixedPoint(24,16),validated_only=False)
        if kind=='position_overflow':
            p=(Q(10),Q(0),Q(0))
            return C.new_run(FixedPoint(40,32),40,(Q(108),Q(0),Q(0)),tuple(-q for q in p),
                             (Q(127999,1000),Q(0),Q(0)),p,momentum_profile=X.MOM)
        raise ValueError(kind)
    st = X.canonical(Q(spec['e']),Q(spec['b_frac'])*X.RE)
    return C.new_run(X.POS,40,st['r_i'],st['p_i'],st['r_j'],st['p_j'],momentum_profile=X.MOM)


def outgoing(run):
    dr = C.relative(run.pos,*run.atoms)
    dp = tuple(b-a for a,b in zip(C.exact(run.mom,run.atoms[0].p),C.exact(run.mom,run.atoms[1].p)))
    return sum(x*x for x in dr) >= 400 and sum(x*y for x,y in zip(dr,dp)) > 0


def capture(fn, *args):
    try:
        return dict(kind='value',raw=fn(*args))
    except (C.ExecutorLimitExceeded,C.PhysicsDomainExceeded,C.ContractViolation,C.IntegratorDomainExceeded) as exc:
        return dict(kind='refusal',type=type(exc).__name__,reason=exc.reason,message=str(exc))
    except C.VMHalt as exc:
        return dict(kind='halt',type=type(exc).__name__,reason=exc.reason,message=str(exc))


def paired(spec,f):
    ref = make_run(spec)
    fast = copy.copy(ref)
    initial = raw(ref)
    assert raw(fast) == initial
    impulses = 0
    h = hashlib.sha256()
    f.write(E.canonical(dict(id=spec['id'],initial=initial)) + b'\n')
    for _ in range(spec['cap']):
        calls,fast_calls = [],[]
        def observed(dr,dt,p):
            try:
                value=C.impulse(dr,dt,p)
            except (C.ExecutorLimitExceeded,C.PhysicsDomainExceeded,C.ContractViolation,C.VMHalt) as exc:
                result=dict(kind='refusal' if not isinstance(exc,C.VMHalt) else 'halt',type=type(exc).__name__,reason=exc.reason,message=str(exc))
                calls.append(dict(dr=list(map(str,dr)),dt=str(dt),result=result))
                raise
            calls.append(dict(dr=list(map(str,dr)),dt=str(dt),result=dict(kind='value',raw=value)))
            return value
        def compared(dr,dt,p):
            try:
                value=FAST.impulse(dr,dt,p)
            except (C.ExecutorLimitExceeded,C.PhysicsDomainExceeded,C.ContractViolation,C.VMHalt) as exc:
                result=dict(kind='refusal' if not isinstance(exc,C.VMHalt) else 'halt',type=type(exc).__name__,reason=exc.reason,message=str(exc))
                rec=dict(dr=list(map(str,dr)),dt=str(dt),result=result)
                fast_calls.append(rec)
                assert rec==calls[len(fast_calls)-1]
                raise
            result=dict(kind='value',raw=value)
            rec = dict(dr=list(map(str,dr)),dt=str(dt),result=result)
            fast_calls.append(rec)
            assert rec == calls[len(fast_calls)-1]
            return value
        rs = types.FunctionType(C.step.__code__,dict(C.step.__globals__,impulse=observed))
        fs = types.FunctionType(FAST.step_fast.__code__,dict(FAST.step_fast.__globals__,impulse=compared))
        before = raw(ref)
        ro,fo = capture(rs,ref),capture(fs,fast)
        assert ro == fo and calls == fast_calls and raw(ref) == raw(fast)
        if ro['kind'] != 'value':
            assert raw(ref) == before
        row = dict(id=spec['id'],REF_state=raw(ref),FAST_state=raw(fast),
                   REF_impulses=calls,FAST_impulses=fast_calls,REF_result=ro,FAST_result=fo)
        encoded = E.canonical(row)
        f.write(encoded+b'\n');h.update(encoded+b'\n')
        impulses += len(calls)
        if ro['kind'] != 'value':
            return dict(id=spec['id'],steps=ref.t_steps,records=ref.t_steps+1,impulses=impulses,
                        end=ro['kind'],result=ro,witness_sha256=h.hexdigest())
        if outgoing(ref):
            return dict(id=spec['id'],steps=ref.t_steps,records=ref.t_steps,impulses=impulses,end='outgoing_R20',witness_sha256=h.hexdigest())
    return dict(id=spec['id'],steps=ref.t_steps,records=ref.t_steps,impulses=impulses,end='step_cap',witness_sha256=h.hexdigest())


def trajectory(inputs,out):
    rows=[]
    with gzip.open(out / 'trajectory.witnesses.jsonl.gz','wb') as f:
        for spec in (*inputs['trajectories'],*inputs['refusals']):
            r = paired(spec,f);rows.append(r);print(r,flush=True)
    success={s['id'] for s in inputs['trajectories']}
    refused={s['id'] for s in inputs['refusals']}
    return rows, dict(all_impulses_equal=True,all_states_equal=True,same_refusal_step=True,
                      scattering_completed=bool(rows) and all(r['end']=='outgoing_R20' if r['id'] in success
                                                              else r['id'] in refused and r['end'] in ('refusal','halt') for r in rows))


def complete_trajectory(run,step,cap, *, stored=None):
    for _ in range(cap):
        step(run)
        if stored is not None:
            stored.append(raw(run))
        if outgoing(run):
            return raw(run)
    raise ValueError('benchmark trajectory reached cap')


def measured(fn):
    c,t = time.process_time(),time.perf_counter()
    value = fn()
    return value,dict(cpu_seconds=time.process_time()-c,wall_seconds=time.perf_counter()-t)


def benchmark(inputs):
    config = inputs['benchmark']
    reps = config['repetitions']
    assert reps >= 3 and config['threads'] == 1 and config['warmup'] >= 1
    # Affinity is an execution resource setting only, not a world law.
    import psutil
    proc=psutil.Process()
    prior_affinity=proc.cpu_affinity()
    cpu=prior_affinity[-1]
    proc.cpu_affinity([cpu])
    samples=[]
    try:
        base=make_run(inputs['trajectories'][0])
        dr=C.relative(base.pos,*base.atoms)
        for _ in range(config['warmup']):
            for impulse,step in ((C.impulse,C.step),(FAST.impulse,FAST.step_fast)):
                impulse(dr,Q(20),X.MOM)
                step(copy.copy(base))
                complete_trajectory(copy.copy(base),step,inputs['trajectories'][0]['cap'])
        for rep in range(reps):
            methods=[('REF',C.impulse,C.step),('FAST',FAST.impulse,FAST.step_fast)]
            if rep & 1:
                methods.reverse()
            for name,impulse,step in methods:
                value,clock=measured(lambda:[impulse(dr,Q(20),X.MOM) for _ in range(1000)])
                samples.append(dict(rep=rep,method=name,workload='impulse',calls=1000,result_sha256=E.digest(value),**clock))
                states=[]
                run=copy.copy(base)
                _,clock=measured(lambda:[step(run) for _ in range(1000)])
                samples.append(dict(rep=rep,method=name,workload='step',calls=1000,result_sha256=E.digest(raw(run)),**clock))
                for spec in inputs['trajectories']:
                    run=make_run(spec)
                    states=[]
                    value,clock=measured(lambda:complete_trajectory(run,step,spec['cap'],stored=states))
                    # Raw state collection is identical inside the measured span; hashing is outside.
                    samples.append(dict(rep=rep,method=name,workload='trajectory',id=spec['id'],calls=run.t_steps,
                                        result_sha256=E.digest(states),final_sha256=E.digest(value),**clock))
                    print('benchmark',rep,name,spec['id'],clock,flush=True)
        medians={}
        for workload in ('impulse','step','trajectory'):
            values={}
            for name in ('REF','FAST'):
                per_rep=[sum(s['cpu_seconds'] for s in samples if s['method']==name and s['workload']==workload and s['rep']==r) for r in range(reps)]
                wall=[sum(s['wall_seconds'] for s in samples if s['method']==name and s['workload']==workload and s['rep']==r) for r in range(reps)]
                values[name]=dict(median_cpu_seconds=statistics.median(per_rep),median_wall_seconds=statistics.median(wall))
            medians[workload]=dict(**values,cpu_speedup=values['REF']['median_cpu_seconds']/values['FAST']['median_cpu_seconds'],
                                  wall_speedup=values['REF']['median_wall_seconds']/values['FAST']['median_wall_seconds'])
        same=True
        for s in samples:
            peers=[r for r in samples if r['workload']==s['workload'] and r.get('id')==s.get('id')]
            same &= all(r['result_sha256']==s['result_sha256'] and r['calls']==s['calls'] for r in peers)
        return dict(cpu=platform.processor(),affinity_cpu=cpu,threads=1,repetitions=reps,warmup=config['warmup'],
                    python=sys.version,samples=samples,medians=medians,
                    limits='local background load uncontrolled; single CPU; trajectory includes raw-state collection, excludes admission and hashing'),dict(completed=True,repeat_results_equal=bool(same))
    finally:
        proc.cpu_affinity(prior_affinity)


def local_full(out):
    command=[sys.executable,'-m','pytest','tests','-q','-n','6','--junitxml',str(out/'local_full.junit.xml')]
    env=dict(os.environ)
    env['PATH']=r'C:\Program Files\Git\usr\bin'+os.pathsep+env['PATH']
    started=time.perf_counter()
    with (out/'local_full.pytest.log').open('wb') as f:
        rc=subprocess.run(command,cwd=E.ROOT,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
    root=ET.parse(out/'local_full.junit.xml').getroot()
    cases=root.findall('.//testcase')
    failures=sum(c.find('failure') is not None for c in cases)
    errors=sum(c.find('error') is not None for c in cases)
    xfailed=sum(c.find('skipped') is not None and c.find('skipped').get('type')=='pytest.xfail' for c in cases)
    skips=sum(c.find('skipped') is not None for c in cases)-xfailed
    passed=len(cases)-failures-errors-xfailed-skips
    payload=dict(command=command,returncode=rc,passed=passed,failures=failures,errors=errors,actual_skips=skips,
                 strict_xfailed=xfailed,wall_seconds=time.perf_counter()-started,official_baseline=3289,
                 pytest_log_sha256=E.sha(out/'local_full.pytest.log'),junit_sha256=E.sha(out/'local_full.junit.xml'))
    return payload,dict(exit_zero=rc==0,no_failures=failures==0,no_errors=errors==0,no_actual_skips=skips==0,baseline_not_reduced=passed>=3289)


def execute(name,out):
    prerequisites={'audit':E.CLOSURE,'local_full':(*E.CLOSURE,'audit'),
                   'trajectory':(*E.CLOSURE,'audit','local_full'),'benchmark':(*E.CLOSURE,'audit','local_full','trajectory')}
    assert E.check_run(out,required=prerequisites[name])['status']=='PASS'
    inputs=json.loads((out/'inputs.json').read_bytes())
    if name=='audit':
        audit=json.loads((E.HERE/'audit_acceptance.json').read_bytes())
        matches=all(E.sha(E.ROOT/path)==h for path,h in audit['reviewed_sources'].items())
        return audit,dict(reviewed_source_matches=matches,primitive_audit=audit['primitive_audit']=='PASS',repo_ast_equivalence=repo_equivalence())
    if name=='local_full':
        return local_full(out)
    if name=='trajectory':
        return trajectory(inputs,out)
    if name=='benchmark':
        return benchmark(inputs)
    raise ValueError(name)
