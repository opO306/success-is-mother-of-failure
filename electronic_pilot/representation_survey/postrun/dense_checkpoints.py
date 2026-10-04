"""Serialize the same actual DAG states as dense raw+binding reference."""
import argparse
import json
import statistics
import time
from pathlib import Path
from .. import representations as r


def main():
    p=argparse.ArgumentParser();p.add_argument("--capture",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();cap=Path(a.capture);out=Path(a.output);out.mkdir(exist_ok=False);results={}
    for key in ["A","B"]:
        folder=out/key;folder.mkdir();store=cap/(key+"_checkpoint_store")
        meta_bytes=0;payload_bytes=0;encode=[];restore=[]
        for path in sorted((store/"nodes").iterdir()):
            node=json.loads(path.read_bytes());ident=path.stem
            v=r.cas_restore(ident,store,node["binding"])
            data=r.raw(v);meta=r.dump(dict(binding=node["binding"],dtype="<c16",shape=[len(v)],phase=r.PHASE))
            start=time.perf_counter();(folder/(ident+".bin")).write_bytes(data);(folder/(ident+".json")).write_bytes(meta)
            encode.append(time.perf_counter()-start)
            start=time.perf_counter();read=(folder/(ident+".bin")).read_bytes();json.loads((folder/(ident+".json")).read_bytes())
            restore.append(time.perf_counter()-start)
            if read!=data:raise ValueError("STOP: dense checkpoint restore bytes")
            payload_bytes+=len(data);meta_bytes+=len(meta)
        results[key]=dict(payload_bytes=payload_bytes,metadata_bytes=meta_bytes,total_bytes=payload_bytes+meta_bytes,
                          checkpoint_count=len(encode),encode_median_seconds=statistics.median(encode),
                          restore_median_seconds=statistics.median(restore),same_DAG_states_raw_exact=True)
    with (out/"results.json").open("x") as f:json.dump(results,f,indent=2);f.write("\n")
    print("dense actual checkpoints",results)


if __name__=="__main__":main()
