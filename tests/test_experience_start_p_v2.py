"""EXPERIENCE_START_P_V2: multi-source sealed bundle with de-duplication, start-p decisions, fixed-W6 service loop, the
sealed cost rules (analysis and checker implementations agree), and the twelve fault injections the independent checker
must detect. The fixture runs on the desktop with a scratch request N=6 T=100 (not an evaluation request; disclosed in
V1 amendment 1) plus the cross-platform anchor pass; its outputs are scratch, never evidence."""

import hashlib
import json
import random
import shutil
import sys
from pathlib import Path

import psutil
import pytest

from experiments.experience_start_p_v2 import analyze as AN
from experiments.experience_start_p_v2 import campaign as CA
from experiments.experience_start_p_v2 import checker as CK
from experiments.experience_start_p_v2 import experience as EX
from experiments.experience_start_p_v2 import policies as POLS
from experiments.experience_start_p_v2 import service as ESV
from experiments.multiatom_parallel_v1 import scenarios as SC
from experiments.multiatom_parallel_v1.run import initial_digest

REQ = [(6, 100)]


def _store():
    return EX.ExperienceStore(CA.BUNDLE, CA.BUNDLE_SHA)


def _init(N):
    return initial_digest(*SC.initial(N))


def test_bundle_rebuild_is_deterministic_and_deduplicated():
    b = EX.build_bundle()
    assert hashlib.sha256(EX.canonical_bytes(b)).hexdigest() == CA.BUNDLE_SHA
    assert b["n_records"] == 315 and b["dedup"]["n_dropped"] == 0
    dup = EX.build_bundle(extra_records=[b["records"][0]])          # same (source, run_id): dropped, counted
    assert dup["n_records"] == 315 and dup["dedup"]["n_dropped"] == 1
    other = dict(b["records"][1], run_id="x", physics_contract_hash="0" * 64)
    with pytest.raises(ValueError):
        EX.build_bundle(extra_records=[other])


def test_store_sealed_and_decisions():
    s, (ph, nu) = _store(), EX.current_contracts()
    with pytest.raises(ValueError):
        EX.ExperienceStore(CA.BUNDLE, "0" * 64)
    for N, T in CA.REQUESTS:
        lk = POLS.decide("EXACT_LOOKUP", N, T, "rw:R1+R2", _init(N), s, ph, nu)
        assert not lk["exact_hit"] and lk["start_p"] == 64
        lo = POLS.decide("FAMILY_MIN", N, T, "rw:R1+R2", _init(N), s, ph, nu)
        hi = POLS.decide("FAMILY_MAX", N, T, "rw:R1+R2", _init(N), s, ph, nu)
        assert lo["start_p"] == lo["FAMILY_MIN"] < hi["start_p"] == hi["FAMILY_MAX"]
        assert POLS.decide("BASE64", N, T, "rw:R1+R2", _init(N), s, ph, nu)["start_p"] == 64
    wrong = POLS.decide("FAMILY_MAX", 40, 100, "rw:R1+R2", _init(40), s, "f" * 64, nu)
    assert not wrong["contracts_match"] and wrong["start_p"] == 64


def test_service_fixed_w6_first_p_then_p2():
    seq = iter(["UNDECIDED_AT_PRECISION", "DECIDED"])
    plans = []

    def ex(plan, N, T):
        plans.append(plan)
        return {"outcome": next(seq), "completed_steps": T, "endpoints_scaled": None, "effective_p": plan.precision}
    r = ESV.run_request(40, 100, {"policy": "FAMILY_MIN", "start_p": 106}, ex)
    assert r["p_sequence"] == [106, 212] and r["status"] == "DECIDED"
    assert all((p.backend, p.worker_count, p.main_cpu, p.worker_cpus) == ("CPU_PARALLEL", 6, 0, (1, 2, 3, 4, 5, 0))
               for p in plans)


def test_linux_shim_inactive_off_linux():
    from experiments.multiatom_parallel_v1 import run as M
    src = (Path(CA.__file__).parent / "linux_shim" / "sitecustomize.py").read_text(encoding="utf-8")
    exec(compile(src, "sitecustomize", "exec"), {"__name__": "x"})
    if not sys.platform.startswith("linux"):
        assert not hasattr(M, "CPU_CLOCK") and M.cycles.__module__ == M.__name__


def _synthetic(rng):
    return {f"r{i}": {p: (rng.uniform(1, 50), rng.uniform(1, 200)) for p in CK.POLICIES} for i in range(4)}


def test_cost_rules_two_implementations_agree():
    rng = random.Random(7)
    cases = [_synthetic(rng) for _ in range(300)]
    # MAX much cheaper only in the expensive request, 15 % dearer in the three others: totals favour MAX,
    # the equal-weight mean (1.04) favours MIN
    cases.append({"a": {"BASE64": (2.6, 6.5), "FAMILY_MIN": (1.31, 3.22), "FAMILY_MAX": (1.51, 3.70)},
                  "b": {"BASE64": (4.0, 11.3), "FAMILY_MIN": (1.94, 5.50), "FAMILY_MAX": (2.23, 6.33)},
                  "c": {"BASE64": (10, 46), "FAMILY_MIN": (4.86, 22.7), "FAMILY_MAX": (5.59, 26.1)},
                  "d": {"BASE64": (25, 110), "FAMILY_MIN": (24.9, 111.5), "FAMILY_MAX": (17.4, 78.0)}})
    seen = set()
    for c in cases:
        own, tot = CK.own_cost_verdicts(c)
        full = [{p: {"service_wall_s": v[p][0], "cpu_s": v[p][1]} for p in v} for v in c.values()]
        totals = {p: {"wall": sum(v[p][0] for v in c.values()), "cpu": sum(v[p][1] for v in c.values())} for p in CK.POLICIES}
        v, _ = AN.min_vs_max(totals, full)
        assert v == own["MIN_vs_MAX"]
        seen.add(v)
    assert CK.own_cost_verdicts(cases[-1])[0]["MIN_vs_MAX"] == "DISTRIBUTION_SENSITIVE"
    assert {"MAX_WIN", "MIN_WIN", "MIXED"} <= seen


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    d = tmp_path_factory.mktemp("exp2_ev")
    me = psutil.Process()
    keep = me.cpu_affinity()
    try:
        c = CA.Camp(d)
        c.setup(check_topology=False)
        c.open_store()
        c.snapshot("anchor")
        c.anchor()
        CA.evaluate(c, REQ, 1)
        CA.references(c)
    finally:
        me.cpu_affinity(keep)
    # scratch fixture on the loaded desktop: mark the groups clean so the cost path is exercised (never evidence)
    f = d / "load_snapshots.jsonl"
    rows = [dict(json.loads(ln), contaminated=False) for ln in f.read_text(encoding="utf-8").splitlines()]
    f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (d / "analysis.json").write_text(json.dumps(AN.analyze(d, REQ, 1)), encoding="utf-8")
    return d


def _check(d, **kw):
    return CK.check(d, requests=REQ, reps=1, **kw)


def _failed(v, name):
    return v["counts"].get(name, [0, 0])[1] > 0


def _copy(ev, tmp_path):
    d = tmp_path / "ev"
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
    assert v["analysis_checked"]


def test_01_evaluation_result_in_bundle(evidence, tmp_path):
    cand = json.loads((evidence / "candidate_v2" / "candidate_experience.jsonl").read_text(encoding="utf-8").splitlines()[0])

    def f(b):
        r = dict(cand, verification_status="VERIFIED")
        r["record_sha256"] = EX.record_sha256(r)
        b["records"].append(r)
        b["n_records"] += 1
    v = _check(evidence, **_tampered_bundle(tmp_path, f))
    assert _failed(v, "bundle_sources_allowed") and _failed(v, "bundle_records_equal_rebuilt_from_sources")


def test_02_duplicate_training_evidence(evidence, tmp_path):
    def f(b):
        b["records"].append(dict(b["records"][0]))
        b["n_records"] += 1
    v = _check(evidence, **_tampered_bundle(tmp_path, f))
    assert _failed(v, "bundle_no_duplicates")


def test_03_other_contract_mixed_in(evidence, tmp_path):
    v = _check(evidence, **_tampered_bundle(tmp_path, lambda b: b["records"][3].update(physics_contract_hash="0" * 64)))
    assert _failed(v, "bundle_records_single_contract")


def test_04_family_min_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    name = "N6_T100__FAMILY_MIN__r0"
    _edit(d / "service" / f"{name}.json", lambda s: s["decision"].update(FAMILY_MIN=s["decision"]["FAMILY_MIN"] - 1))
    _edit(d / "decisions" / f"{name}.json", lambda s: s.update(FAMILY_MIN=s["FAMILY_MIN"] - 1))
    assert _failed(_check(d), "decision_rederived")

    def g(b):
        fk = next(k for k, v in b["family"].items() if v["T"] == 100)
        b["family"][fk]["FAMILY_MIN"] -= 1
    assert _failed(_check(evidence, **_tampered_bundle(tmp_path, g)), "bundle_family_equals_source")


def test_05_family_max_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    name = "N6_T100__FAMILY_MAX__r0"
    _edit(d / "service" / f"{name}.json", lambda s: s["decision"].update(FAMILY_MAX=s["decision"]["FAMILY_MAX"] + 2))
    _edit(d / "decisions" / f"{name}.json", lambda s: s.update(FAMILY_MAX=s["FAMILY_MAX"] + 2))
    assert _failed(_check(d), "decision_rederived")

    def g(b):
        fk = next(k for k, v in b["family"].items() if v["T"] == 1000)
        b["family"][fk]["FAMILY_MAX"] += 1
    assert _failed(_check(evidence, **_tampered_bundle(tmp_path, g)), "bundle_family_equals_source")


def test_06_first_p_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "service/N6_T100__FAMILY_MAX__r0.json", lambda s: s["passes"][0].update(p=s["passes"][0]["p"] + 3))
    assert _failed(_check(d), "first_p_is_decision")


def test_07_p2_fallback_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    s = json.loads((d / "service/N6_T100__BASE64__r0.json").read_text(encoding="utf-8"))
    assert len(s["passes"]) >= 2
    _edit(d / "service/N6_T100__BASE64__r0.json", lambda s: s["passes"][1].update(p=s["passes"][1]["p"] + 5))
    assert _failed(_check(d), "p2_rederived")


def test_08_failed_pass_deleted(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        assert s["passes"][0]["record"]["outcome"] != "DECIDED"
        del s["passes"][0]
        for j, pz in enumerate(s["passes"]):
            pz["index"] = j
            pz["p_source"] = "decision" if j == 0 else "P2"
        s["p_sequence"] = [pz["p"] for pz in s["passes"]]
        s["n_passes"] = len(s["passes"])
    _edit(d / "service/N6_T100__BASE64__r0.json", f)
    assert _failed(_check(d), "first_p_is_decision")


def test_09_endpoint_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        r = s["passes"][-1]["record"]
        k = r["endpoints_key"]
        r["endpoints_key"] = k[:-2] + ("1" if k[-2] != "1" else "2") + k[-1]
    _edit(d / "service/N6_T100__FAMILY_MIN__r0.json", f)
    assert _failed(_check(d), "bit_identical_to_serial_reference")


def test_10_exact_hit_forged(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "decisions/N6_T100__EXACT_LOOKUP__r0.json",
          lambda s: s.update(exact_hit=True, exact_lowest_observed_success_p=106))
    v = _check(d)
    assert _failed(v, "exact_lookup_is_miss") and _failed(v, "decision_rederived")


def test_11_other_worker_plan(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "service/N6_T100__FAMILY_MIN__r0.json",
          lambda s: s["passes"][0]["plan"].update(worker_count=4, worker_cpus=[1, 2, 3, 4]))
    assert _failed(_check(d), "plan_is_fixed_W6")


def test_12_cost_verdict_altered(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    an = json.loads((d / "analysis.json").read_text(encoding="utf-8"))
    flip = {"MAX_WIN": "MIN_WIN"}.get(an["rules"]["MIN_vs_MAX"], "MAX_WIN")
    _edit(d / "analysis.json", lambda a: a["rules"].update(MIN_vs_MAX=flip))
    assert _failed(_check(d), "analysis_verdict_rederived")
    d2 = tmp_path / "ev2"
    shutil.copytree(evidence, d2)
    _edit(d2 / "analysis.json", lambda a: a["totals"]["FAMILY_MAX"].update(wall=a["totals"]["FAMILY_MAX"]["wall"] * 0.5))
    assert _failed(_check(d2), "analysis_totals_rederived")
