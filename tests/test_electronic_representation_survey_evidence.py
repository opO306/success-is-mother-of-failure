"""Actual one/two-electron evidence and all nine requested fault classes."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest
from electronic_pilot.representation_survey import representations as r,verify
from electronic_pilot.representation_survey.postrun.audit import collision_record

ROOT=Path(__file__).parents[1]/"docs/active/electronic_representation_survey_v1"
RESULT=json.loads((ROOT/"desktop_results.json").read_text())
SPEC=json.loads((ROOT/"desktop_seal.json").read_text())["protocol"]


def actual(key):
    with np.load(ROOT/(key+"_corpus.npz")) as z:data={k:z[k].copy() for k in z.files}
    contract=json.loads((ROOT/(key+"_contract.json")).read_text())
    data.update(contract=contract,electrons=contract["N_e"])
    return data


@pytest.mark.parametrize("key",["A","B"])
@pytest.mark.parametrize("name",["ground","excited","plus","minus","global_phase"])
def test_actual_full_reconstruction(key,name):
    data=actual(key);v=data["states"][SPEC["states"].index(name)]
    bind=r.binding(v,data["contract"]);path=ROOT/"prototypes"/(key+"_"+name)
    a=json.loads((path/"adaptive.json").read_bytes());payload=(path/"adaptive.bin").read_bytes()
    c=json.loads((path/"blocks/manifest.json").read_bytes())
    for restored in [r.adaptive_decode(a,payload,bind),verify.adaptive(a,payload,bind),
                     r.block_restore(c,path/"blocks",bind),verify.blocks(c,path/"blocks",bind)]:
        assert r.raw(restored)==r.raw(v)
        check=verify.physical(v,restored,data,SPEC["times_atomic"],SPEC["state_tolerance"])
        assert check["PASS"] and check["raw_bytes_equal"]


@pytest.mark.parametrize("key",["A","B"])
def test_actual_summary_collision_independent_future(key):
    data=actual(key)
    p=[json.loads((ROOT/"prototypes"/(key+"_"+name)/"summary.json").read_bytes())["summary"] for name in ["plus","minus"]]
    record=RESULT["collisions"][key]
    audit=collision_record(record,*p,data,SPEC["times_atomic"])
    assert audit["PASS"] and audit["authoritative"]=="REJECTED"
    hidden=copy.deepcopy(record);hidden["authoritative"]="AUTHORITATIVE CANDIDATE"
    assert not collision_record(hidden,*p,data,SPEC["times_atomic"])["PASS"]


@pytest.mark.parametrize("key",["A","B"])
@pytest.mark.parametrize("fault",["missing_block","block_order","phase","stale_binding","summary_collision_hidden",
                                  "radius_shrink","content_hash","checkpoint_wrong_block","false_dedup"])
def test_actual_nine_fault_classes(tmp_path,key,fault):
    data=actual(key);v=data["states"][2];bind=r.binding(v,data["contract"])
    folder=ROOT/"prototypes"/(key+"_plus")
    a=json.loads((folder/"adaptive.json").read_bytes());payload=(folder/"adaptive.bin").read_bytes()
    c=json.loads((folder/"blocks/manifest.json").read_bytes())
    if fault=="radius_shrink":
        assert a["certificate"]["numerator"]>0
        a["certificate"]["numerator"]=0
        with pytest.raises(ValueError):verify.adaptive(a,payload,bind)
        with pytest.raises(ValueError):r.adaptive_preview(a,payload,data["h"],1e-9,bind)
    elif fault=="summary_collision_hidden":
        meta=json.loads((folder/"summary.json").read_bytes());meta["authoritative"]=True
        with pytest.raises(ValueError):r.summary_validate(meta,bind)
    elif fault in ["checkpoint_wrong_block","false_dedup"]:
        store=tmp_path/"cas";ident=r.cas_checkpoint(v,bind,store,SPEC["block_sizes"][key])
        node=json.loads((store/"nodes"/(ident+".json")).read_bytes())
        if fault=="false_dedup":
            p=store/"objects"/node["blocks"][0]["content_hash"];p.write_bytes(bytes(p.stat().st_size))
            with pytest.raises(ValueError):r.cas_checkpoint(v,bind,store,SPEC["block_sizes"][key])
        else:
            node["blocks"][0]["content_hash"]=node["blocks"][1]["content_hash"]
            forged=r.sha(r.dump(node));(store/"nodes"/(forged+".json")).write_bytes(r.dump(node))
            with pytest.raises(ValueError):r.cas_restore(forged,store,bind)
    else:
        if fault=="missing_block":c["blocks"].pop()
        elif fault=="block_order":c["blocks"][0],c["blocks"][1]=c["blocks"][1],c["blocks"][0]
        elif fault=="phase":c["phase"]="discarded imaginary coherence"
        elif fault=="stale_binding":bind=dict(bind,law_fingerprint="stale")
        else:c["blocks"][0]["content_hash"]="0"*64
        with pytest.raises(ValueError):verify.blocks(c,folder/"blocks",bind)
        with pytest.raises(ValueError):r.block_restore(c,folder/"blocks",bind)


def test_actual_cost_records_preserve_unfavorable_results():
    assert all(x["payload_dedup_fraction"]==0 for x in RESULT["checkpoints"].values())
    previews=[p for row in RESULT["rows"] if row["candidate"]=="A" for p in row["static_preview_decisions"]]
    assert len(previews)==30 and all(p["decision"]=="REFINE" for p in previews)
    assert all(row["correctness"]["raw_bytes_equal"] for row in RESULT["rows"] if row["candidate"] in ["REF","A","C"])
    correction=json.loads((ROOT/"memory_measurement_correction_v1.json").read_text())
    assert not correction["canonical_source_or_physics_changed"]
