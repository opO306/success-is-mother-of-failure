"""Sample smaps_rollup RSS; preserve getrusage contamination separately."""
import argparse
import json
import resource
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
from .. import representations as r


def rss():
    text=Path("/proc/self/smaps_rollup").read_text()
    return int(next(x for x in text.splitlines() if x.startswith("Rss:")).split()[1])*1024


def status_peak():
    return int(next(x for x in Path("/proc/self/status").read_text().splitlines() if x.startswith("VmHWM:")).split()[1])*1024


def child(root,key,candidate):
    folder=Path(root)/(key+"_plus" if key!="synthetic" else "synthetic")
    meta=json.loads((folder/"blocks/manifest.json").read_bytes());bind=meta["binding"]
    samples=[rss()];event=threading.Event()
    def sample():
        while not event.wait(.002):samples.append(rss())
    thread=threading.Thread(target=sample);thread.start()
    wall,cpu=time.perf_counter(),time.process_time()
    counters={}
    if candidate=="REF":
        v=np.load(folder/"state.npy");samples.append(rss())
        if key=="synthetic":answer=float(np.vdot(v,v).real)
        else:
            h=np.load(folder/"h.npy");samples.append(rss());answer=float(np.vdot(v,h@v).real)
        operation="dense norm" if key=="synthetic" else "dense energy"
    elif candidate=="A":
        a=json.loads((folder/"adaptive.json").read_bytes());payload=(folder/"adaptive.bin").read_bytes()
        v=r.adaptive_decode(a,payload,bind);samples.append(rss())
        h=np.load(folder/"h.npy");samples.append(rss());answer=float(np.vdot(v,h@v).real)
        operation="exact adaptive decode plus dense energy"
    elif candidate=="B":
        meta_b=json.loads((folder/"summary.json").read_bytes())
        answer=r.summary_validate(meta_b,bind)["energy"];samples.append(rss())
        operation="index read ONLY; no equivalent physical computation"
    elif candidate=="C" and key!="synthetic":
        h=np.load(folder/"h.npy",mmap_mode="r")
        answer,counters=r.stream_quadratic(meta,folder/"blocks",h,bind)
        samples.append(rss());operation="streamed dense-coupling energy"
    elif candidate=="C":
        import math
        parts=[]
        for k in range(len(meta["blocks"])):
            v=r.load_block(meta,folder/"blocks",k);samples.append(rss());parts.append(float(np.vdot(v,v).real))
        answer=math.fsum(parts);operation="streamed norm"
    else:
        result=r.parallel_checks(meta,folder/"blocks",bind,2)
        answer=result["norm"];samples.append(rss());operation="two-thread block norm/hash verification ONLY"
    event.set();thread.join()
    return dict(corpus=key,candidate=candidate,operation=operation,answer=answer,
                wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
                observed_peak_RSS_bytes=max(samples),initial_RSS_bytes=samples[0],samples=len(samples),
                kernel_reported_VmHWM_bytes=status_peak(),getrusage_highwater_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                counters=counters,
                RSS_scope="smaps_rollup resident pages at boundaries and 2ms samples; observed maximum, not certified absolute peak; includes interpreter")


def parent(root,output):
    records=[];random_access={};physical_parallel={}
    for key in ["A","B","synthetic"]:
        candidates=["REF","A","B","C","D"] if key!="synthetic" else ["REF","C","D"]
        for candidate in candidates:
            cmd=[sys.executable,"-m","electronic_pilot.representation_survey.postrun.rss","--root",str(root),
                 "--corpus",key,"--candidate",candidate]
            result=subprocess.run(cmd,capture_output=True,text=True,check=True)
            records.append(json.loads(result.stdout))
        folder=Path(root)/(key+"_plus" if key!="synthetic" else "synthetic")
        meta=json.loads((folder/"blocks/manifest.json").read_bytes());bind=meta["binding"]
        measured=[]
        for _ in range(5):
            counters=dict(read_calls=0,read_bytes=0);start=time.perf_counter()
            v=r.load_block(meta,folder/"blocks",len(meta["blocks"])-1,counters)
            measured.append(time.perf_counter()-start)
        random_access[key]=dict(wall_median_seconds=statistics.median(measured),wall_samples_seconds=measured,
                                coefficient_read_bytes=counters["read_bytes"],coefficient_read_calls=counters["read_calls"],
                                manifest_bytes=(folder/"blocks/manifest.json").stat().st_size,
                                scope="single last-block coefficient query; not full state or observable")
        a=r.parallel_checks(meta,folder/"blocks",bind,1);b=r.parallel_checks(meta,folder/"blocks",bind,2)
        physical_parallel[key]=dict(hash_equal=a["hashes"]==b["hashes"],norm_bit_equal=a["norm"]==b["norm"])
        if not all(physical_parallel[key].values()):raise ValueError("STOP: parallel check mismatch")
    value=dict(measurement_status="POSTRUN MEASUREMENT ONLY; physics/source/tolerances unchanged",
               canonical_getrusage_peaks="INVALID FOR COMPARISON: inherited parent highwater reproduced",
               rows=records,random_access=random_access,parallel_exact_block_reduction=physical_parallel,
               disk_cache_control="NOT CONTROLLED; logical coefficient bytes only; no disk-sector byte claim")
    with Path(output).open("x") as f:json.dump(value,f,indent=2);f.write("\n")
    print("postrun RSS/random-access",len(records),"records")


def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--output")
    p.add_argument("--corpus");p.add_argument("--candidate");a=p.parse_args()
    if a.output:parent(a.root,a.output)
    else:print(json.dumps(child(a.root,a.corpus,a.candidate)))


if __name__=="__main__":main()
