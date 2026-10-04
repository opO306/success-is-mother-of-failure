"""Fair disk-restore-inclusive pipelines; canonical timings remain immutable."""
import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
from .. import corpus,representations as r


def timed(fun):
    values=[];cpus=[]
    for _ in range(5):
        wall,cpu=time.perf_counter(),time.process_time();answer=fun()
        values.append(time.perf_counter()-wall);cpus.append(time.process_time()-cpu)
    return answer,dict(wall_median_seconds=statistics.median(values),cpu_median_seconds=statistics.median(cpus),
                       repetitions=5,wall_samples_seconds=values)


def main():
    p=argparse.ArgumentParser();p.add_argument("--capture",required=True);p.add_argument("--output",required=True)
    args=p.parse_args();cap=Path(args.capture);out=Path(args.output);out.mkdir(exist_ok=False)
    spec=json.loads((cap/"seal.json").read_text())["protocol"];rows=[]
    for key in ["A","B"]:
        with np.load(cap/(key+"_corpus.npz")) as z:data={k:z[k].copy() for k in z.files}
        contract=json.loads((cap/(key+"_contract.json")).read_text());data["electrons"]=contract["N_e"]
        cas=out/(key+"_current_state_cas")
        for name,v in zip(spec["states"],data["states"]):
            directory=cap/(key+"_"+name);bind=r.binding(v,contract)
            started=time.perf_counter();identity=r.cas_checkpoint(v,bind,cas,spec["block_sizes"][key])
            encode=time.perf_counter()-started
            def dense():
                meta=json.loads((directory/"dense.json").read_bytes())
                if meta["binding"]!=bind or meta["phase"]!=r.PHASE:raise ValueError("REFUSED: dense binding")
                value=(directory/"dense.bin").read_bytes()
                if r.sha(value)!=bind["source_state_digest"]:raise ValueError("REFUSED: dense content")
                return np.frombuffer(value,dtype="<c16").copy()
            def adaptive():
                return r.adaptive_decode(json.loads((directory/"adaptive.json").read_bytes()),
                                         (directory/"adaptive.bin").read_bytes(),bind)
            def blocks():
                return r.block_restore(json.loads((directory/"blocks/manifest.json").read_bytes()),
                                       directory/"blocks",bind)
            loaders={"REF":dense,"A":adaptive,"C":blocks,"D":lambda:r.cas_restore(identity,cas,bind)}
            for candidate,loader in loaders.items():
                restored,decode=timed(loader)
                if r.raw(restored)!=r.raw(v):raise ValueError("STOP: common pipeline restore")
                observed,obs=timed(lambda:corpus.observe(loader(),data))
                density,den=timed(lambda:corpus.density(loader(),data))
                waves,ev=timed(lambda:corpus.evolve(loader(),data,spec["times_atomic"]))
                if not np.array_equal(waves,corpus.evolve(v,data,spec["times_atomic"])):
                    raise ValueError("STOP: common pipeline evolution")
                rows.append(dict(corpus=key,state=name,candidate=candidate,decode=decode,
                                 restore_plus_observable=obs,restore_plus_density=den,restore_plus_evolution=ev,
                                 exact_initial_and_future_bytes=True,D_initial_checkpoint_encode_seconds=encode if candidate=="D" else None))
    record=dict(scope="same initial states; disk restore plus same retained-H/U numerical kernels; 5 repeats; cache uncontrolled",
                B="INDEX ONLY: no equivalent physical pipeline",rows=rows)
    with (out/"results.json").open("x") as f:json.dump(record,f,indent=2);f.write("\n")
    print("common physical pipelines",len(rows),"PASS")


if __name__=="__main__":main()
