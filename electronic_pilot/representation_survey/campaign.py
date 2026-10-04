"""Sealed canonical survey, small exact corpus and bounded synthetic size."""
import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import scipy
from . import corpus, verify
from . import representations as rep


def exclusive(path,obj):
    with Path(path).open("x",encoding="utf-8") as f:
        json.dump(obj,f,indent=2,allow_nan=False);f.write("\n")


def sources():
    return {p.name:rep.sha(p.read_bytes()) for p in Path(__file__).parent.iterdir() if p.is_file()}


def timed(fun,repeats):
    values=[];cpus=[]
    for _ in range(repeats):
        wall,cpu=time.perf_counter(),time.process_time()
        value=fun()
        values.append(time.perf_counter()-wall);cpus.append(time.process_time()-cpu)
    return value,dict(wall_median_seconds=statistics.median(values),cpu_median_seconds=statistics.median(cpus),
                      repetitions=repeats,wall_samples_seconds=values)


def size(directory):
    return sum(p.stat().st_size for p in Path(directory).rglob("*") if p.is_file())


def memory(directory,state,matrix=None):
    results=[]
    for mode in ["dense","blocks"]:
        cmd=[sys.executable,"-m","electronic_pilot.representation_survey.memory_worker",
             "--mode",mode,"--directory",str(directory),"--state",str(state)]
        if matrix:cmd+=["--matrix",str(matrix)]
        result=subprocess.run(cmd,capture_output=True,text=True,check=True)
        results.append(json.loads(result.stdout))
    return results


def run(root,output,spec):
    corpora,origin=corpus.build(root,output,spec)
    rows=[];collisions={};checkpoints={};memory_results={};parallel={}
    for key,data in corpora.items():
        store=output/(key+"_checkpoint_store")
        block_size=spec["block_sizes"][key]
        data["ref_waves"]=np.array([corpus.evolve(v,data,spec["times_atomic"]) for v in data["states"]])
        # Independent full matrix exponentials for the known +/- challenge.
        independent=max(verify.evolution_check(data["states"][j],data["ref_waves"][j],data,spec["times_atomic"]) for j in [2,3])
        if independent>spec["evolution_tolerance"]:raise ValueError("STOP: REF spectral/expm mismatch")
        summary=[];dense_checkpoint_bytes=0;node_ids=[];restore_times=[];checkpoint_times=[]
        for j,(name,v) in enumerate(zip(spec["states"],data["states"])):
            directory=output/(key+"_"+name);directory.mkdir()
            bind=rep.binding(v,data["contract"])
            observed=corpus.observe(v,data);density=corpus.density(v,data)
            dense_start=time.perf_counter()
            (directory/"dense.bin").write_bytes(rep.raw(v))
            (directory/"dense.json").write_bytes(rep.dump(dict(binding=bind,dtype="<c16",shape=[len(v)],phase=rep.PHASE)))
            dense_encode=time.perf_counter()-dense_start
            refbytes=(directory/"dense.bin").stat().st_size+(directory/"dense.json").stat().st_size
            dense_restore,dense_decode_t=timed(lambda:np.frombuffer((directory/"dense.bin").read_bytes(),dtype="<c16").copy(),spec["timing_repeats"])
            _,dense_observe_t=timed(lambda:corpus.observe(v,data),spec["timing_repeats"])
            _,dense_evolve_t=timed(lambda:corpus.evolve(v,data,spec["times_atomic"]),spec["timing_repeats"])
            _,dense_density_t=timed(lambda:corpus.density(v,data),spec["timing_repeats"])
            rows.append(dict(corpus=key,state=name,candidate="REF",serialized_bytes=refbytes,coefficient_bytes=len(v)*16,
                             metadata_bytes=refbytes-len(v)*16,certificate_bytes=0,encode_seconds=dense_encode,
                             decode=dense_decode_t,observable=dense_observe_t,density=dense_density_t,evolution=dense_evolve_t,
                             correctness=verify.physical(v,dense_restore,data,spec["times_atomic"],spec["state_tolerance"])))
            start=time.perf_counter();meta,payload=rep.adaptive_encode(v,bind,spec["hot_count"])
            (directory/"adaptive.json").write_bytes(rep.dump(meta));(directory/"adaptive.bin").write_bytes(payload)
            encode=time.perf_counter()-start
            a,dec=timed(lambda:rep.adaptive_decode(json.loads((directory/"adaptive.json").read_bytes()),
                                                  (directory/"adaptive.bin").read_bytes(),bind),spec["timing_repeats"])
            independent_a=verify.adaptive(meta,payload,bind)
            if rep.raw(independent_a)!=rep.raw(v):raise ValueError("STOP: independent adaptive reconstruction")
            previews=[rep.adaptive_preview(meta,payload,op,tol,bind) for op,tol in
                      [(data["s"],spec["norm_tolerance"]),(data["h"],spec["observable_tolerance"]),
                       (data["dipoles"][2],spec["observable_tolerance"])]]
            _,obs_t=timed(lambda:corpus.observe(rep.adaptive_decode(meta,payload,bind),data),spec["timing_repeats"])
            _,ev_t=timed(lambda:corpus.evolve(rep.adaptive_decode(meta,payload,bind),data,spec["times_atomic"]),spec["timing_repeats"])
            _,den_t=timed(lambda:corpus.density(rep.adaptive_decode(meta,payload,bind),data),spec["timing_repeats"])
            abytes=len(payload)+len(rep.dump(meta))
            rows.append(dict(corpus=key,state=name,candidate="A",serialized_bytes=abytes,metadata_bytes=len(rep.dump(meta)),
                             certificate_bytes=len(rep.dump(meta["certificate"])),compressed_residual_bytes=meta["residual_bytes"],
                             encode_seconds=encode,decode=dec,observable=obs_t,density=den_t,evolution=ev_t,
                             static_preview_decisions=previews,evolution_policy="ALWAYS EXACT REFINE; all roots",
                             correctness=verify.physical(v,a,data,spec["times_atomic"],spec["state_tolerance"])))
            start=time.perf_counter();b=rep.summary_encode(v,bind,observed,density,spec["summary_decimal_places"])
            (directory/"summary.json").write_bytes(rep.dump(b));bt=time.perf_counter()-start
            summary.append(b)
            _,index_t=timed(lambda:rep.summary_validate(json.loads((directory/"summary.json").read_bytes()),bind),spec["timing_repeats"])
            rows.append(dict(corpus=key,state=name,candidate="B",serialized_bytes=len(rep.dump(b)),
                             metadata_bytes=len(rep.dump(b))-len(rep.dump(b["summary"])),certificate_bytes=0,
                             encode_seconds=bt,index_read=index_t,decode=None,observable=None,density=None,evolution=None,
                             correctness="NO STATE RECONSTRUCTION; descriptive observable values only"))
            start=time.perf_counter();c=rep.block_encode(v,bind,directory/"blocks",block_size);ct=time.perf_counter()-start
            decoded,cd=timed(lambda:rep.block_restore(json.loads((directory/"blocks/manifest.json").read_bytes()),
                                                     directory/"blocks",bind),spec["timing_repeats"])
            independent_c=verify.blocks(c,directory/"blocks",bind)
            if rep.raw(independent_c)!=rep.raw(v):raise ValueError("STOP: independent block reconstruction")
            _,obs_t=timed(lambda:corpus.observe(rep.block_restore(c,directory/"blocks",bind),data),spec["timing_repeats"])
            _,ev_t=timed(lambda:corpus.evolve(rep.block_restore(c,directory/"blocks",bind),data,spec["times_atomic"]),spec["timing_repeats"])
            _,den_t=timed(lambda:corpus.density(rep.block_restore(c,directory/"blocks",bind),data),spec["timing_repeats"])
            stream_energy,counters=rep.stream_quadratic(c,directory/"blocks",data["h"],bind)
            if abs(stream_energy-observed["energy"])>spec["observable_tolerance"]:raise ValueError("STOP: streamed action mismatch")
            count_restore=dict(read_bytes=0,read_calls=0)
            rep.block_restore(c,directory/"blocks",bind,count_restore)
            rows.append(dict(corpus=key,state=name,candidate="C",serialized_bytes=size(directory/"blocks"),
                             metadata_bytes=len(rep.dump(c)),certificate_bytes=0,block_count=len(c["blocks"]),
                             encode_seconds=ct,decode=cd,observable=obs_t,density=den_t,evolution=ev_t,
                             streaming_energy_error=abs(stream_energy-observed["energy"]),streaming_energy_IO=counters,
                             restore_payload_IO=count_restore,
                             correctness=verify.physical(v,decoded,data,spec["times_atomic"],spec["state_tolerance"])))
            if name=="plus":
                np.save(directory/"state.npy",v);np.save(directory/"h.npy",data["h"])
                memory_results[key]=memory(directory/"blocks",directory/"state.npy",directory/"h.npy")
                parallel[key]=[timed(lambda:rep.parallel_checks(c,directory/"blocks",bind,workers),spec["parallel_repeats"])[1]
                               for workers in spec["parallel_workers"]]
            parent=None
            for ti,wave in enumerate(data["ref_waves"][j]):
                wb=rep.binding(wave,data["contract"])
                start=time.perf_counter();identity=rep.cas_checkpoint(wave,wb,store,block_size,parent)
                checkpoint_times.append(time.perf_counter()-start);node_ids.append(identity)
                start=time.perf_counter();restored=rep.cas_restore(identity,store,wb);restore_times.append(time.perf_counter()-start)
                if rep.raw(restored)!=rep.raw(wave):raise ValueError("STOP: checkpoint restore bytes")
                replay=corpus.evolve(restored,data,[0.5])[0]
                replay_ref=corpus.evolve(wave,data,[0.5])[0]
                if not np.array_equal(replay,replay_ref):raise ValueError("STOP: checkpoint replay")
                dense_checkpoint_bytes+=len(wave)*16;parent=identity
        ka=corpus.density(data["ref_waves"][2,0],data);kb=corpus.density(data["ref_waves"][3,0],data)
        future_density=max(float(np.max(abs(corpus.density(a,data)-corpus.density(b,data)))) for a,b in
                           zip(data["ref_waves"][2,1:],data["ref_waves"][3,1:]))
        future_dipole=max(float(max(abs(np.array(corpus.observe(a,data)["dipole"])-np.array(corpus.observe(b,data)["dipole"]))))
                           for a,b in zip(data["ref_waves"][2,1:],data["ref_waves"][3,1:]))
        col=verify.collision(summary[2]["summary"],summary[3]["summary"],max(future_density,future_dipole))
        col.update(initial_density_max=float(np.max(abs(ka-kb))),future_density_kernel_max=future_density,
                   future_dipole_difference_max=future_dipole,
                   descriptive_payload_equal_bytes=rep.dump(summary[2]["summary"])==rep.dump(summary[3]["summary"]),
                   source_bindings_equal=summary[2]["binding"]==summary[3]["binding"],
                   global_phase_summary_equal=summary[2]["summary"]==summary[4]["summary"],
                   global_phase_projector_error=verify.physical(data["states"][2],data["states"][4],data,[],spec["state_tolerance"])["projector_error"],
                   distinct_plus_minus_projector_error=verify.physical(data["states"][2],data["states"][3],data,[],spec["state_tolerance"])["projector_error"])
        collisions[key]=col
        objects=list((store/"objects").iterdir());nodes=list((store/"nodes").iterdir())
        object_bytes=sum(p.stat().st_size for p in objects);node_bytes=sum(p.stat().st_size for p in nodes)
        checkpoints[key]=dict(checkpoint_count=len(node_ids),dense_raw_bytes=dense_checkpoint_bytes,
                              unique_payload_bytes=object_bytes,manifest_bytes=node_bytes,total_bytes=object_bytes+node_bytes,
                              unique_blocks=len(objects),payload_dedup_fraction=1-object_bytes/dense_checkpoint_bytes,
                              checkpoint_encode_median_seconds=statistics.median(checkpoint_times),
                              restore_median_seconds=statistics.median(restore_times),
                              state_hash_and_replay_all_exact=True,history_used_as_evolution_input=False)
    synth=output/"synthetic";synth.mkdir()
    n=spec["synthetic_dimension"];idx=np.arange(n,dtype=np.int64)
    v=((idx%251-125)/128+1j*(idx%257-128)/256).astype(complex)
    v/=np.linalg.norm(v)
    sb=rep.binding(v,dict(law_fingerprint="NON_PHYSICAL_SYNTHETIC",basis_contract="fixed-periodic-byte-test",
                          N_e="NOT_APPLICABLE",sector="SYNTHETIC",dimension=n))
    sm=rep.block_encode(v,sb,synth/"blocks",spec["synthetic_block_size"])
    np.save(synth/"state.npy",v)
    memory_results["synthetic"]=memory(synth/"blocks",synth/"state.npy")
    parallel["synthetic"]=[timed(lambda:rep.parallel_checks(sm,synth/"blocks",sb,workers),spec["parallel_repeats"])[1]
                            for workers in spec["parallel_workers"]]
    checks=[rep.parallel_checks(sm,synth/"blocks",sb,w) for w in spec["parallel_workers"]]
    if checks[0]["hashes"]!=checks[1]["hashes"] or checks[0]["norm"]!=checks[1]["norm"]:
        raise ValueError("STOP: serial/thread reduction mismatch")
    if not all(row["correctness"]["PASS"] and row["correctness"]["raw_bytes_equal"] for row in rows if row["candidate"] in ["REF","A","C"]):
        raise ValueError("STOP: physical reconstruction comparison")
    if collisions["A"]["authoritative"]!="REJECTED":raise ValueError("STOP: known summary collision hidden")
    return dict(status="SURVEY COMPLETED / NOT PRODUCTION / NOT CERTIFIED",corpus_provenance=origin,rows=rows,
                collisions=collisions,checkpoints=checkpoints,peak_RSS=memory_results,parallel=parallel,
                role_classification={"A":"AUTHORITATIVE CANDIDATE via exact reconstruction; preview bound only",
                                     "B":"AUTHORITATIVE REJECTED / OBSERVER INDEX ONLY",
                                     "C":"STORAGE/EXECUTION ARCHITECTURE ONLY",
                                     "D":"STORAGE/EXECUTION ARCHITECTURE ONLY"},
                dense_H_U_cost_not_removed=True,synthetic_physical_evidence=False)


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);args=p.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    root=Path.cwd();spec=json.loads(Path(__file__).with_name("protocol.json").read_text())
    receipt=json.loads((output.parent/"git_start.json").read_text())
    before=sources()
    exclusive(output/"seal.json",dict(protocol=spec,source_sha256=before,git_receipt=receipt,
                                     host=platform.node(),python=sys.version,versions=dict(numpy=np.__version__,scipy=scipy.__version__),
                                     environment={k:os.environ.get(k) for k in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"]}))
    for path in Path(__file__).parent.iterdir():
        if path.is_file():(output/(path.name+".executed.txt")).write_bytes(path.read_bytes())
    start=time.perf_counter()
    try:
        result=run(root,output,spec)
        if sources()!=before:raise ValueError("STOP: source changed during survey")
        protected=receipt["protected_sha256"]
        if any(rep.sha((root/k).read_bytes())!=v for k,v in protected.items()):
            raise ValueError("STOP: historical tracked bytes changed")
        result.update(wall_seconds=time.perf_counter()-start,source_unchanged=True,protected_tracked_unchanged=True)
        exclusive(output/"results.json",result)
        print(result["status"],"wall",result["wall_seconds"],flush=True)
    except Exception as e:
        exclusive(output/"failure.json",dict(error=repr(e),traceback=traceback.format_exc(),wall_seconds=time.perf_counter()-start))
        raise


if __name__=="__main__":main()
