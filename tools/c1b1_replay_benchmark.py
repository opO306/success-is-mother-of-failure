"""Local fixed seven-case evidence/cost harness. No world commit, no random sweep."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from functools import partial
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
LABELS=('e0.5_rho-0.01','e0.5_rho-0.005','e0.15_rho-0.005','e1_b10',
        'e0.5_b6','e0.5_rho+0.005','e10_b0')
OLD=ROOT/'runs/c1b1_postverify_survey_20261001'
OUT=ROOT/'runs/c1b1_production_replay_20261001'

def flat(s):return tuple(v for row in s for v in row)

def peak_memory():
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
                ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
                 'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        record=Counters();record.cb=ctypes.sizeof(record)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        psapi=ctypes.WinDLL('psapi',use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(record),record.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return record.PeakWorkingSetSize
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)

def prepare():
    from c1b1_replay.witness import Header,write
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for label in LABELS:
        source=OLD/f'witness_{label}.json'
        payload=source.read_bytes();w=json.loads(payload)
        path=OUT/f'{label}.c1br'
        with path.open('wb') as stream:
            write(stream,Header(flat(w['states'][0]),tuple(w['J'][0]),flat(w['states'][-1]),w['steps'],end='R20_OUTBOUND'),
                  ((j,flat(s)) for j,s in zip(w['J'][1:],w['states'][1:])))
        rows.append({'label':label,'steps':w['steps'],'source_sha256':hashlib.sha256(payload).hexdigest(),
                     'source_bytes':len(payload),'witness_bytes':path.stat().st_size,
                     'witness_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (OUT/'witness_manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows

def execute(label, mode='fast'):
    # Producer-side imports only; none of these modules enter the verifier worker.
    from fractions import Fraction as Q
    from a_numeric import FixedPoint
    from a_reference import c1b1_two_atom as c
    from a_reference import c1b1_runtime as runtime
    runtime.select(mode)  # reject unsupported modes before constructing a run
    w=json.loads((OLD/f'witness_{label}.json').read_bytes())
    initial=w['states'][0]
    run=c.new_run(FixedPoint(96,48),Q(40),tuple(Q(v,1<<48) for v in initial[0]),
        tuple(Q(v,1<<80) for v in initial[1]),tuple(Q(v,1<<48) for v in initial[2]),
        tuple(Q(v,1<<80) for v in initial[3]),momentum_profile=FixedPoint(96,80),validated_only=False)
    cpu=wall=0.0
    whole=time.perf_counter()
    for i in range(1,w['steps']+1):
        tc,tw=time.process_time(),time.perf_counter()
        runtime.step(run, mode=mode)
        cpu+=time.process_time()-tc;wall+=time.perf_counter()-tw
        a,b=run.atoms
        if (tuple(a.r),tuple(a.p),tuple(b.r),tuple(b.p))!=tuple(tuple(x) for x in w['states'][i]) or tuple(run.J_cache)!=tuple(w['J'][i]):
            raise AssertionError(f'fresh reference differs at {label} step {i}')
    return {'label':label,'runtime_mode':mode,'steps':run.t_steps,'cpu_seconds':cpu,'step_wall_seconds':wall,
            'worker_wall_seconds':time.perf_counter()-whole,'peak_working_set_bytes':peak_memory(),
            'all_states_equal_old_raw_inputs':True}

def replay(args):
    label,full=args
    from c1b1_replay import verify
    from c1b1_replay.provenance import FORBIDDEN
    result=verify(OUT/f'{label}.c1br',materialize=full)
    imported=sorted(n for n in sys.modules if n.split('.')[0] in FORBIDDEN)
    assert not imported,imported
    row=asdict(result)
    row.update(label=label,mode='full' if full else 'stream',peak_working_set_bytes=peak_memory(),forbidden_imports=imported)
    row['summary_bytes']=len(json.dumps(row,separators=(',',':')).encode())
    (OUT/f'{label}_{row["mode"]}.json').write_text(json.dumps(row,indent=2)+'\n')
    assert result.verdict.value=='VALID',row
    return row

def batch(kind, runtime_mode='fast'):
    import threading
    import psutil
    parent=psutil.Process()
    stop=threading.Event()
    rss_peak=[0]
    def sample():
        while not stop.is_set():
            total=0
            for process in [parent]+parent.children(recursive=True):
                try:total+=process.memory_info().rss
                except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            rss_peak[0]=max(rss_peak[0],total)
            stop.wait(0.05)
    monitor=threading.Thread(target=sample,daemon=True)
    monitor.start()
    start,cpu=time.perf_counter(),time.process_time()
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(partial(execute,mode=runtime_mode),LABELS)) if kind=='executor' else list(pool.map(replay,[(x,kind=='full') for x in LABELS]))
    elapsed=time.perf_counter()-start
    stop.set();monitor.join()
    output={'kind':kind,'workers':4,'batch_wall_seconds':elapsed,
            'parent_cpu_seconds':time.process_time()-cpu,'worker_cpu_seconds_sum':sum(r['cpu_seconds'] for r in rows),
            'peak_memory_note':'per-worker OS lifetime PeakWorkingSetSize; sum is an upper bound, not simultaneous peak',
            'worker_peak_sum_upper_bound_bytes':sum(r['peak_working_set_bytes'] for r in rows),'rows':rows}
    output['aggregate_rss_peak_sampled_bytes']=rss_peak[0]
    output['aggregate_rss_sampling_seconds']=0.05
    if kind == 'executor':
        # Runtime activation must not overwrite the original cost evidence.
        from uuid import uuid4
        destination=ROOT/'runs/c1b1_runtime_producer_batches'/str(uuid4())
        destination.mkdir(parents=True,exist_ok=False)
        output['runtime_mode']=runtime_mode
        output['historical_input_directory']=str(OLD)
    else:
        destination=OUT
    (destination/f'{kind}_batch.json').write_text(json.dumps(output,indent=2)+'\n')
    print(kind,output['batch_wall_seconds'],output['worker_cpu_seconds_sum'],flush=True)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='prepare':print(json.dumps(prepare(),indent=2))
    elif mode in ('executor','stream','full'):batch(mode,sys.argv[2] if len(sys.argv)>2 else 'fast')
    else:raise SystemExit('prepare|executor|stream|full')
