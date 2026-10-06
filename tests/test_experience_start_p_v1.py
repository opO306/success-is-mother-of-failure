"""EXPERIENCE_START_P_V1: sealed read-only store, start-p decisions, service first-p behaviour, and the ten fault
injections the independent checker must detect. The fixture uses N=5 T=100 (a training request) for Part A and
N=6 T=100 (not an evaluation request) for Part B, so no evaluation outcome is seen before the seal."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import psutil
import pytest

from experiments.experience_start_p_v1 import campaign as CA
from experiments.experience_start_p_v1 import checker as CK
from experiments.experience_start_p_v1 import experience as EX
from experiments.experience_start_p_v1 import policies as POLS
from experiments.experience_start_p_v1 import service as ESV
from experiments.multiatom_parallel_v1 import scenarios as SC
from experiments.multiatom_parallel_v1.run import initial_digest

LAPTOP = {"logical": 6, "physical": 6, "cores": [{"smt": False, "group_cpus": [[0, [k]]]} for k in range(6)]}


def _store():
    return EX.ExperienceStore(CA.BUNDLE, CA.BUNDLE_SHA)


def _init(N):
    return initial_digest(*SC.initial(N))


def test_store_is_sealed_and_read_only(tmp_path):
    s = _store()
    with pytest.raises(ValueError):
        EX.ExperienceStore(CA.BUNDLE, "0" * 64)
    with pytest.raises(TypeError):
        s._exact["x"] = {}
    e = s.exact(next(iter(s._exact)))
    e["lowest_observed_success_p"] = 1                      # a copy: the store is unchanged
    assert s.exact(next(iter(s._exact)))["lowest_observed_success_p"] != 1


def test_decisions_from_store_only():
    s, (ph, nu) = _store(), EX.current_contracts()
    d = POLS.decide("EXACT_MEMORY", 5, 100, "rw:R1+R2", _init(5), s, ph, nu)
    assert d["exact_hit"] and d["start_p"] == d["exact_lowest_observed_success_p"] and d["start_source"] == "EXACT_MEMORY"
    d = POLS.decide("EXACT_MEMORY", 7, 100, "rw:R1+R2", _init(7), s, ph, nu)
    assert not d["exact_hit"] and d["start_p"] == 64
    lo = POLS.decide("FAMILY_MIN", 7, 100, "rw:R1+R2", _init(7), s, ph, nu)
    hi = POLS.decide("FAMILY_MAX", 7, 100, "rw:R1+R2", _init(7), s, ph, nu)
    assert lo["start_p"] == lo["FAMILY_MIN"] <= hi["start_p"] == hi["FAMILY_MAX"]
    assert POLS.decide("P2_BASE", 7, 100, "rw:R1+R2", _init(7), s, ph, nu)["start_p"] == 64
    wrong = POLS.decide("FAMILY_MIN", 7, 100, "rw:R1+R2", _init(7), s, "f" * 64, nu)       # other physics contract
    assert not wrong["contracts_match"] and wrong["start_p"] == 64


def test_service_first_p_then_p2():
    seq = iter(["UNDECIDED_AT_PRECISION", "DECIDED"])

    def ex(plan, N, T):
        return {"outcome": next(seq), "completed_steps": T, "endpoints_scaled": None, "effective_p": plan.precision}
    r = ESV.run_request(7, 100, {"policy": "FAMILY_MIN", "start_p": 106}, LAPTOP, ex)
    assert r["p_sequence"][0] == 106 and r["status"] == "DECIDED" and len(r["p_sequence"]) == 2
    assert r["p_sequence"][1] == 106 * 2                    # P2 with no endpoints doubles


A, B = [(5, 100)], [(6, 100)]


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    d = tmp_path_factory.mktemp("exp_ev")
    me = psutil.Process()
    keep = me.cpu_affinity()
    try:
        c = CA.Camp(d)
        c.setup(check_topology=False)
        c.topology = LAPTOP
        c.open_store()
        c.snapshot("A_N5_T100__r0")
        for pol in CA.POL_A:
            c.run(f"A_N5_T100__{pol}__r0", pol, 5, 100)
        c.snapshot("B_N6_T100__r0")
        c.decide("B_N6_T100__EXACT_MEMORY_lookup__r0", "EXACT_MEMORY", 6, 100)
        for pol in CA.POL_B:
            c.run(f"B_N6_T100__{pol}__r0", pol, 6, 100)
        todo = sorted({(s["N"], s["T"], p) for f in (d / "service").glob("*.json")
                       for s in [json.loads(f.read_text(encoding="utf-8"))] for p in s["p_sequence"]})
        for N, T, p in todo:
            c.reference(N, T, p)
    finally:
        me.cpu_affinity(keep)
    return d


def _check(d, **kw):
    return CK.check(d, part_a=A, part_b=B, reps=1, **kw)


def _failed(v, name):
    return v["counts"].get(name, [0, 0])[1] > 0


def _copy(ev, tmp_path, tag="ev"):
    d = tmp_path / tag
    shutil.copytree(ev, d)
    return d


def _edit(path, fn):
    s = json.loads(path.read_text(encoding="utf-8"))
    fn(s)
    path.write_text(json.dumps(s), encoding="utf-8")


def _tampered_bundle(tmp_path, fn):
    b = json.loads(Path(CA.BUNDLE).read_text(encoding="utf-8"))
    fn(b)
    p = tmp_path / "bundle.json"
    data = json.dumps(b, sort_keys=True, separators=(",", ":")).encode()
    p.write_bytes(data)
    sh = tmp_path / "bundle.sha256"
    sh.write_text(hashlib.sha256(data).hexdigest(), encoding="utf-8")       # hash made consistent on purpose
    return {"bundle_path": p, "bundle_sha_file": sh}


def test_clean_fixture(evidence):
    v = _check(evidence)
    assert {k for k, c in v["counts"].items() if c[1]} <= {"seal_clean"}, v["issues"]


def test_1_unverified_experience_as_trusted(evidence, tmp_path):
    v = _check(evidence, **_tampered_bundle(tmp_path, lambda b: b["records"][0].update(verification_status="UNVERIFIED")))
    assert _failed(v, "bundle_records_all_verified")


def test_2_other_physics_mixed(evidence, tmp_path):
    v = _check(evidence, **_tampered_bundle(tmp_path, lambda b: b["records"][3].update(physics_contract_hash="0" * 64)))
    assert _failed(v, "bundle_records_single_contract")


def test_3_exact_memory_other_initial_digest(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    for f in (d / "service/A_N5_T100__EXACT_MEMORY__r0.json",):
        _edit(f, lambda s: s["decision"].update(initial_state_digest="1" * 64))
    _edit(d / "decisions/A_N5_T100__EXACT_MEMORY__r0.json", lambda s: s.update(initial_state_digest="1" * 64))
    assert _failed(_check(d), "decision_rederived")


def test_4_campaign_result_used_later(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    base = json.loads((d / "service/B_N6_T100__P2_BASE__r0.json").read_text(encoding="utf-8"))
    observed = base["final_p"]                                   # a result of this campaign
    for f in (d / "service/B_N6_T100__FAMILY_MIN__r0.json",):
        _edit(f, lambda s: s["decision"].update(start_p=observed))
    _edit(d / "decisions/B_N6_T100__FAMILY_MIN__r0.json", lambda s: s.update(start_p=observed))
    assert _failed(_check(d), "decision_rederived")


def test_5_lowest_success_altered(evidence, tmp_path):
    def f(b):
        k = next(iter(b["exact"]))
        b["exact"][k]["lowest_observed_success_p"] += 1
    v = _check(evidence, **_tampered_bundle(tmp_path, f))
    assert _failed(v, "bundle_exact_equals_source")


def test_6_family_min_max_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "service/B_N6_T100__FAMILY_MAX__r0.json", lambda s: s["decision"].update(FAMILY_MAX=s["decision"]["FAMILY_MAX"] + 2))
    _edit(d / "decisions/B_N6_T100__FAMILY_MAX__r0.json", lambda s: s.update(FAMILY_MAX=s["FAMILY_MAX"] + 2))
    assert _failed(_check(d), "decision_rederived")

    def g(b):
        fk = next(k for k, v in b["family"].items() if v["T"] == 100)
        b["family"][fk]["FAMILY_MIN"] -= 1
    assert _failed(_check(evidence, **_tampered_bundle(tmp_path, g)), "bundle_family_equals_source")


def test_7_first_p_record_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "service/A_N5_T100__EXACT_MEMORY__r0.json", lambda s: s["passes"][0].update(p=s["passes"][0]["p"] + 3))
    assert _failed(_check(d), "first_p_is_decision")


def test_8_p2_fallback_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    s = json.loads((d / "service/A_N5_T100__P2_BASE__r0.json").read_text(encoding="utf-8"))
    assert len(s["passes"]) >= 2
    _edit(d / "service/A_N5_T100__P2_BASE__r0.json", lambda s: s["passes"][1].update(p=s["passes"][1]["p"] + 5))
    assert _failed(_check(d), "p2_rederived")


def test_9_endpoint_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        r = s["passes"][-1]["record"]
        k = r["endpoints_key"]
        r["endpoints_key"] = k[:-2] + ("1" if k[-2] != "1" else "2") + k[-1]
    _edit(d / "service/B_N6_T100__FAMILY_MIN__r0.json", f)
    assert _failed(_check(d), "bit_identical_to_serial_reference")


def test_10_failed_pass_deleted(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        assert s["passes"][0]["record"]["outcome"] != "DECIDED"
        del s["passes"][0]
        for j, pz in enumerate(s["passes"]):
            pz["index"] = j
        s["p_sequence"] = [pz["p"] for pz in s["passes"]]
        s["n_passes"] = len(s["passes"])
    _edit(d / "service/A_N5_T100__P2_BASE__r0.json", f)
    assert _failed(_check(d), "first_p_is_decision")
