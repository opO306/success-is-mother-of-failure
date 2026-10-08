"""Actual completion -> immutable candidate. Never verifies or activates its own output."""
import hashlib
import json
import os
import resource
import signal
import time
from contextlib import contextmanager
from .common import check_seals,raw_hash,HERE,write_new,digest,ns


def require_live_session(session):
    if session.get('origin')!='OBSERVED_REAL' or session.get('test_only') or os.name!='posix': raise ValueError('REAL_SESSION_REQUIRED')
    if not session.get('session_id') or not session.get('boot_id'): raise ValueError('SESSION_ID_REQUIRED')


def cpu_clock(gpu=None):
    def used(which):
        r=resource.getrusage(which); return ns(r.ru_utime+r.ru_stime)
    active=0
    if gpu is not None:
        import psutil
        if not gpu.proc.is_alive(): raise ValueError('GPU_WORKER_DIED_CPU_UNKNOWN')
        t=psutil.Process(gpu.proc.pid).cpu_times(); active=ns(t.user+t.system)
    return {'controller':used(resource.RUSAGE_SELF),'waited_children':used(resource.RUSAGE_CHILDREN),'live_gpu':active}


@contextmanager
def deadline(seconds):
    def expired(signum,frame): raise TimeoutError('PER_CALL_BUDGET_EXPIRED')
    old=signal.signal(signal.SIGALRM,expired); signal.setitimer(signal.ITIMER_REAL,seconds)
    try: yield
    finally: signal.setitimer(signal.ITIMER_REAL,0); signal.signal(signal.SIGALRM,old)


def capture(directory,session,method,repeat,store,*,gpu=None,snapshot=None,reason='',seconds=480):
    from pathlib import Path
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    require_live_session(session); check_seals()
    if session['code_manifest_sha256']!=raw_hash(HERE/'code_seal.json'): raise ValueError('CODE_SEAL_MISMATCH')
    # Import execution authority only inside the explicitly authorized capture path.
    from experiments.adaptive_execution_v1 import service as SVC
    from .inspector import initial_state
    N,T=session['N'],session['T']; initial=initial_state(N)
    strategy={'SERIAL':'FIXED_SERIAL','W6':'FIXED_W6','GPU':'FIXED_GPU','LEGACY':'ADAPTIVE'}[method]
    run_id=f'{session["session_id"]}/{method}/{repeat}'
    start_cpu=cpu_clock(gpu); start=time.monotonic_ns()
    try:
        with deadline(seconds):
            svc=SVC.run_request({'id':run_id,'N':N,'T':T,'start':'FIXED_START:163'},strategy,session['env'],None,store,
                    gpu=gpu,goal=session['goal'],gate100=False,run_id=run_id,workdir=directory,keep_gpu_detail=True)
    except BaseException as error:
        write_new(directory/'FAILED.json',{'status':'STOP','run_id':run_id,'error_type':type(error).__name__,
                   'wall_ns':time.monotonic_ns()-start,'cpu_status':'UNCONFIRMED_FAILED_ATTEMPT; NO_PROMOTION'})
        raise
    end=time.monotonic_ns(); end_cpu=cpu_clock(gpu)
    deltas={k:end_cpu[k]-start_cpu[k] for k in start_cpu}
    if any(x<0 for x in deltas.values()): raise ValueError('CPU_CLOCK_REVERSED')
    first=svc['passes'][0]['attempts'][0]['plan'] if svc.get('passes') else {}
    observed={'CPU_SERIAL':'SERIAL','CPU_PARALLEL':'W6','GPU_HYBRID':'GPU'}.get(first.get('backend'))
    obj=dict(kind='OBSERVED_REAL',state='CANDIDATE',run_id=run_id,session_id=session['session_id'],
          session_sha256=digest(session),code_manifest_sha256=session['code_manifest_sha256'],repeat=repeat,
          method=observed,goal=session['goal'],initial_state=initial,
          initial_sha256=hashlib.sha256(json.dumps(initial).encode()).hexdigest(),service=svc,
          selection={'requested_method':method,'reason':reason,'plan':first,
                     'profile_snapshot':None if snapshot is None or snapshot.profile_bytes is None else hashlib.sha256(snapshot.profile_bytes).hexdigest()},
          observation={'origin':'OS_MONOTONIC_AND_PROCESS_CPU','pid':os.getpid(),'start_wall_ns':start,
                       'end_wall_ns':end,'wall_ns':end-start,'cpu_ns':sum(deltas.values()),'cpu_deltas_ns':deltas},
          correctness_level='EXECUTOR_UNVERIFIED; INDEPENDENT_REPLAY_REQUIRED')
    write_new(directory/f'{method}_{repeat}.json',obj)
    return obj
