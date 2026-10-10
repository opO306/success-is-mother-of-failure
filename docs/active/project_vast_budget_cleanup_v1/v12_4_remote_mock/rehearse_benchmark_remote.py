"""Free, NON-OFFICIAL timing rehearsal of the unchanged search benchmark on the remote PC (aic-2DESK-TOP).

Why: on Vast the 320 tests alone took 75.14 s of offline.py's 120 s total wall/CPU budget, and the benchmark has never
run anywhere. This calls the extracted package's own offline.benchmark exactly as offline.main does after the tests
(lines 158-163: Tablet/register/benchmark, then check_sources), pinned to ONE CPU. Windows has no os.sched_getaffinity,
so only for this rehearsal it is provided from psutil (affects a recorded host field, not the measured calls).
Result is a different machine's timing: an indication, never a verdict input or the official measurement.
  python -I rehearse_benchmark_remote.py EXTRACTED_SOURCE OUT
"""
import json,os,sys,time
from pathlib import Path
import psutil


def main():
    source,out=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()
    out.mkdir(parents=True,exist_ok=False)
    me=psutil.Process();me.cpu_affinity([min(me.cpu_affinity())])
    if not hasattr(os,'sched_getaffinity'):os.sched_getaffinity=lambda pid:set(psutil.Process().cpu_affinity())
    sys.path.insert(0,str(source));os.chdir(source)
    start_wall=time.monotonic_ns();start_cpu=time.process_time_ns()
    from experiments.adaptive_experience_tablet_v0 import offline
    from experiments.adaptive_experience_tablet_v0.catalog import Tablet
    from experiments.adaptive_execution_real_learning_pilot_v0.governance import Roots
    original=offline.ROOT/'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/run_20261008_approved_3/recovered/output_actual'
    if offline.ROOT.resolve()!=source:raise ValueError('EXTRACTED_SOURCE_ROOT')
    tablet=Tablet(out/'tablet',original,Roots(**offline.read(original/'manager/roots.json')))
    entry=tablet.register('A','b775509603dc3f07e578ccce4aea11021cee013c7eea8feb8268f01a8e91482f','manager/events/event_000000.json')
    t1=time.monotonic_ns()
    result=offline.benchmark(offline.read(original/'A/session.json')['env'],lambda:tablet.load(entry))
    t2=time.monotonic_ns()
    code=offline.check_sources()
    t3=time.monotonic_ns()
    record=dict(role='NON_OFFICIAL_REMOTE_PC_TIMING_REHEARSAL',code_sha256=code,python=sys.version,cpu_affinity=me.cpu_affinity(),
                register_seconds=(t1-start_wall)/1e9,benchmark_seconds=(t2-t1)/1e9,check_sources_seconds=(t3-t2)/1e9,
                total_wall_seconds=(t3-start_wall)/1e9,total_process_cpu_seconds=(time.process_time_ns()-start_cpu)/1e9,
                lookup_target_met=[r['lookup_target_met'] for r in result['index_growth']],benchmark=result)
    (out/'rehearsal.json').write_bytes(json.dumps(record,sort_keys=True,indent=2,default=str).encode())
    print(json.dumps({k:record[k] for k in ('register_seconds','benchmark_seconds','check_sources_seconds','total_wall_seconds','total_process_cpu_seconds','lookup_target_met')}))


if __name__=='__main__':main()
