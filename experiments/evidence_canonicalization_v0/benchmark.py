"""Stored-file overhead only; historical references are not activated knowledge."""
import argparse
import copy
import time
import tracemalloc
from pathlib import Path
from . import fingerprints as FP,history
from .policy import check_policy
from experiments.adaptive_execution_real_learning_pilot_v0.common import read,write_new,digest


def measure_record(obj,session,directory,*,repeat):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    path=directory/f'sample_{repeat}.json'
    if tracemalloc.is_tracing(): raise ValueError('BENCHMARK_REQUIRES_ISOLATED_TRACE')
    tracemalloc.start(); start=time.monotonic_ns()
    try:
        _,metrics=FP.save_and_check(path,obj,session,writer=write_new)
        observer=FP.write_metrics(directory/'evidence_metrics'/f'sample_{repeat}.json',metrics,writer=write_new)
        metrics.update(observer)
        elapsed=time.monotonic_ns()-start; _,peak=tracemalloc.get_traced_memory()
    finally: tracemalloc.stop()
    metrics.update(total_ns=elapsed,traced_peak_bytes=peak,
             additional_record_bytes=max(0,path.stat().st_size-len(FP.canonical(obj))),
             trace_scope='ISOLATED_BENCHMARK_ONLY; INCLUDES_TRACE_COST_CONSERVATIVELY')
    return metrics


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--out',required=True,type=Path); args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False); p=history.load_originals(); policy=check_policy(); rows=[]
    session=copy.deepcopy(p['session']); session.update(origin='FORMAT_BENCHMARK_ONLY',evidence_version=2,
             initial_content_version=FP.CONTENT_VERSION,evidence_policy_sha256=FP.policy_hash())
    for i,original in enumerate(p['records']):
        obj=copy.deepcopy(original); obj.update(kind='FORMAT_BENCHMARK_ONLY',session_sha256=digest(session))
        obj=FP.stamp(obj)
        original_size=len(FP.canonical(original)); limit=original['observation']['wall_ns']//100
        metrics=[measure_record(obj,session,args.out/f'record_{i:02d}',repeat=j) for j in range(policy['benchmark_repeats'])]
        for m in metrics: m['additional_record_bytes']=m['record_bytes']-original_size+m['observer_record_bytes']
        maximum=max(m['total_ns'] for m in metrics); status='WITHIN_SEALED_OVERHEAD_GOAL' if maximum<=limit else 'OVERHEAD_NOT_ACCEPTABLE'
        rows.append(dict(original_path=p['record_paths'][i],original_raw_sha256=p['record_raw_hashes'][i],
               reference_wall_ns=original['observation']['wall_ns'],limit_ns=limit,maximum_ns=maximum,
               status=status,metrics=metrics,source='PINNED_HISTORICAL_REFERENCE; NOT_VERIFIED_PERFORMANCE_KNOWLEDGE'))
    report=dict(status='OVERHEAD_NOT_ACCEPTABLE' if any(r['status']=='OVERHEAD_NOT_ACCEPTABLE' for r in rows)
                      else 'WITHIN_SEALED_OVERHEAD_GOAL',rows=rows,new_physics_calls=0,gpu_calls=0,
            independent_replays=0,originals_changed=False,benchmark_only=True,
            metrics_storage='Separate aggregate report; actual service also writes a small evidence_metrics record',
            cross_host_performance='NOT_REUSED_FOR_SELECTION')
    write_new(args.out/'benchmark_report.json',report)
    return 0 if report['status']=='WITHIN_SEALED_OVERHEAD_GOAL' else 2


if __name__=='__main__': raise SystemExit(main())
