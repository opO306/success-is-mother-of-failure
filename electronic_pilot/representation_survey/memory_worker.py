"""Fresh Linux process RSS for dense versus actual block loading."""
import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
from .representations import load_block, stream_quadratic, validate_manifest


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode", choices=["dense","blocks"], required=True)
    p.add_argument("--directory", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--matrix")
    args=p.parse_args()
    directory=Path(args.directory)
    meta=json.loads((directory/"manifest.json").read_text())
    before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    wall,cpu=time.perf_counter(),time.process_time()
    if args.mode=="dense":
        v=np.load(args.state)
        if args.matrix:
            h=np.load(args.matrix)
            answer=float(np.vdot(v,h@v).real)
            working=v.nbytes+h.nbytes
        else:
            answer=float(np.vdot(v,v).real)
            working=v.nbytes
        counts=dict(read_bytes=Path(args.state).stat().st_size+(Path(args.matrix).stat().st_size if args.matrix else 0),
                    read_calls=1+int(bool(args.matrix)), working_array_bytes=working)
    elif args.matrix:
        h=np.load(args.matrix,mmap_mode="r")
        answer,counts=stream_quadratic(meta,directory,h,meta["binding"])
        counts["operator_backend"]="read-only mmap; operator read_bytes not instrumented"
    else:
        validate_manifest(meta,meta["binding"])
        counts=dict(read_bytes=0,read_calls=0,working_array_bytes=0)
        parts=[]
        for k in range(len(meta["blocks"])):
            v=load_block(meta,directory,k,counts)
            counts["working_array_bytes"]=max(counts["working_array_bytes"],v.nbytes)
            parts.append(float(np.vdot(v,v).real))
        import math
        answer=math.fsum(parts)
    result=dict(mode=args.mode,answer=answer,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                initial_rss_highwater_bytes=before,wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
                counters=counts,scope="fresh process highwater RSS; includes interpreter; OS cache not controlled")
    print(json.dumps(result))


if __name__=="__main__":main()
