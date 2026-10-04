"""Fault injection against representation structures, not physics approval."""
import copy
import json
from fractions import Fraction

import numpy as np
import pytest
from electronic_pilot.representation_survey import representations as r
from electronic_pilot.representation_survey import verify


@pytest.fixture
def state():
    v=np.array([.4+.1j,.31-.2j,.13+.21j,.08-.019j,.123456789+.008123456789j],dtype=complex)
    v/=np.linalg.norm(v)
    contract=dict(law_fingerprint="synthetic-H",basis_contract="full-five",N_e=2,sector="synthetic-singlet",dimension=5)
    return v,r.binding(v,contract)


def test_adaptive_exact_bytes_and_independent_certificate(state):
    v,b=state;meta,payload=r.adaptive_encode(v,b,hot_count=1)
    assert r.raw(r.adaptive_decode(meta,payload,b))==r.raw(v)
    assert r.raw(verify.adaptive(meta,payload,b))==r.raw(v)
    assert Fraction(meta["certificate"]["numerator"],meta["certificate"]["denominator"])>0
    decision=r.adaptive_preview(meta,payload,np.eye(len(v)),1e-10,b)
    assert decision["decision"]=="REFINE"
    assert not decision["returned_approximate_physical_result"]


@pytest.mark.parametrize("damage",["radius","payload","hot_index","phase","stale"])
def test_adaptive_damage_refused(state,damage):
    v,b=state;meta,payload=r.adaptive_encode(v,b,1);wanted=copy.deepcopy(b)
    if damage=="radius":meta["certificate"]["numerator"]=0
    elif damage=="payload":payload=payload[:-1]+bytes([payload[-1]^1])
    elif damage=="hot_index":meta["hot"]=[0,0]
    elif damage=="phase":meta["phase"]="relative phase discarded"
    else:wanted["law_fingerprint"]="other"
    with pytest.raises((ValueError,KeyError)):r.adaptive_decode(meta,payload,wanted)
    with pytest.raises((ValueError,KeyError)):verify.adaptive(meta,payload,wanted)


def test_radius_shrink_cannot_enable_preview(state):
    v,b=state;meta,payload=r.adaptive_encode(v,b,1)
    meta["certificate"]["numerator"]=0
    with pytest.raises(ValueError):r.adaptive_preview(meta,payload,np.eye(5),1e-10,b)


def test_exact_representable_center_bound_zero():
    v=np.array([.5,.5j,-.5,-.5j]);b=r.binding(v,{"law":"test"})
    meta,payload=r.adaptive_encode(v,b,0)
    assert meta["certificate"]["numerator"]==0
    assert r.adaptive_preview(meta,payload,np.eye(4),1e-10,b)["decision"]=="BOUND_WITHIN_TOLERANCE"


@pytest.mark.parametrize("damage",["missing","order","phase","stale","hash","content","source_digest","range"])
def test_block_faults_refused(tmp_path,state,damage):
    v,b=state;folder=tmp_path/"blocks";meta=r.block_encode(v,b,folder,2);wanted=copy.deepcopy(b)
    if damage=="missing":meta["blocks"].pop()
    elif damage=="order":meta["blocks"][0],meta["blocks"][1]=meta["blocks"][1],meta["blocks"][0]
    elif damage=="phase":meta["phase"]="phase damaged"
    elif damage=="stale":wanted["sector"]="triplet"
    elif damage=="hash":meta["blocks"][0]["content_hash"]="0"*64
    elif damage=="content":
        p=folder/meta["blocks"][0]["file"];p.write_bytes(bytes(len(p.read_bytes())))
    elif damage=="source_digest":wanted["source_state_digest"]="0"*64
    else:meta["blocks"][1]["start"]-=1
    with pytest.raises(ValueError):r.block_restore(meta,folder,wanted)
    with pytest.raises(ValueError):verify.blocks(meta,folder,wanted)


def test_block_restore_stream_and_parallel(tmp_path,state):
    v,b=state;folder=tmp_path/"blocks";meta=r.block_encode(v,b,folder,2)
    assert r.raw(verify.blocks(meta,folder,b))==r.raw(v)
    h=np.arange(25,dtype=float).reshape(5,5);h=h+h.T
    value,io=r.stream_quadratic(meta,folder,h,b)
    assert abs(value-np.vdot(v,h@v).real)<1e-12
    assert io["read_calls"]==12
    assert io["read_bytes"]==4*v.nbytes
    a=r.parallel_checks(meta,folder,b,1);c=r.parallel_checks(meta,folder,b,2)
    assert a["hashes"]==c["hashes"] and a["norm"]==c["norm"]


def test_summary_collision_and_authority_concealment():
    plus=np.array([1,1j])/np.sqrt(2);minus=plus.conj()
    ka=np.outer(plus,plus.conj()).real;kb=np.outer(minus,minus.conj()).real
    obs={"energy":1.,"dipole":[0,0,0]}
    ba=r.binding(plus,{"law":"same"});bb=r.binding(minus,{"law":"same"})
    a=r.summary_encode(plus,ba,obs,ka);b=r.summary_encode(minus,bb,obs,kb)
    result=verify.collision(a["summary"],b["summary"],1.)
    assert result["authoritative"]=="REJECTED" and result["summary_payload_equal"]
    assert a["binding"]!=b["binding"]
    a["authoritative"]=True
    with pytest.raises(ValueError):r.summary_validate(a,ba)


@pytest.mark.parametrize("field",["law_fingerprint","basis_contract","N_e","sector","dimension","source_state_digest","representation_version"])
def test_state_binding_fields_refused(tmp_path,state,field):
    v,b=state;meta,payload=r.adaptive_encode(v,b,1)
    expected=copy.deepcopy(b);expected[field]="stale"
    with pytest.raises(ValueError):r.adaptive_decode(meta,payload,expected)


def test_checkpoint_restore_and_wrong_reference(tmp_path,state):
    v,b=state;identity=r.cas_checkpoint(v,b,tmp_path/"cas",2)
    assert r.raw(r.cas_restore(identity,tmp_path/"cas",b))==r.raw(v)
    path=tmp_path/"cas/nodes"/(identity+".json");node=json.loads(path.read_bytes())
    node["blocks"][0]["content_hash"]=node["blocks"][1]["content_hash"]
    forged=r.sha(r.dump(node));(path.parent/(forged+".json")).write_bytes(r.dump(node))
    with pytest.raises(ValueError):r.cas_restore(forged,tmp_path/"cas",b)


def test_dedup_different_bytes_cannot_share(tmp_path,state):
    v,b=state;store=tmp_path/"cas";r.cas_checkpoint(v,b,store,2)
    p=store/"objects"/r.sha(r.raw(v[:2]));p.write_bytes(bytes(p.stat().st_size))
    with pytest.raises(ValueError):r.cas_checkpoint(v,b,store,2)


def test_dag_exact_duplicate_and_copy_on_write(tmp_path,state):
    v,b=state;store=tmp_path/"cas"
    a=r.cas_checkpoint(v,b,store,2)
    before=len(list((store/"objects").iterdir()))
    again=r.cas_checkpoint(v,b,store,2,a)
    assert len(list((store/"objects").iterdir()))==before
    changed=v.copy();changed[3]+=1e-14
    cb=r.binding(changed,{k:x for k,x in b.items() if k not in ["source_state_digest","representation_version"]})
    child=r.cas_checkpoint(changed,cb,store,2,again)
    assert len(list((store/"objects").iterdir()))==before+1
    assert r.raw(r.cas_restore(child,store,cb))==r.raw(changed)


def test_singlet_density_is_two_electron():
    from electronic_pilot.representation_survey.corpus import unpack,pack,density
    v=np.array([.5,.7j,.5]);v/=np.linalg.norm(v)
    w=unpack(v,2)
    assert np.max(abs(pack(w)-v))<1e-15
    data={"electrons":2,"c":np.eye(2)}
    d=density(v,data)
    assert abs(np.trace(d)-2)<1e-14
    assert np.max(abs(d-verify.independent_density(v,data)))<1e-15
