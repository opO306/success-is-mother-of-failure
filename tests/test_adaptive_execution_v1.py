"""ADAPTIVE_EXECUTION_V1 tests: environment, placement, selector rules, adapter re-checks, GPU status classes, start p,
service fallbacks, checker independence, a small real fixture (GPU + CPU, T = 100) that the checker must pass, and the
13 sealed fault injections that the checker must detect."""

from __future__ import annotations

import ast
import gzip
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from experiments.adaptive_execution_v1 import adapters as AD
from experiments.adaptive_execution_v1 import campaign as CAMP
from experiments.adaptive_execution_v1 import checker as CK
from experiments.adaptive_execution_v1 import environment as ENV
from experiments.adaptive_execution_v1 import experience as EXP
from experiments.adaptive_execution_v1 import profiles as PRO
from experiments.adaptive_execution_v1 import selector as SEL
from experiments.adaptive_execution_v1 import service as SVC
from experiments.precision_pilot_a1 import policies as POL

HERE = Path(__file__).resolve().parents[1] / "experiments" / "adaptive_execution_v1"


# ---------------------------------------------------------------------------
# synthetic environments (no hardware needed)
# ---------------------------------------------------------------------------
def fake_env(smt=True, n_cores=8, quota=None, allowed=None, gpu_arch="sm_89"):
    real = ENV.collect()
    cpus = list(range(2 * n_cores if smt else n_cores))
    core = {str(c): f"0:{c // 2 if smt else c}" for c in cpus}
    e = dict(real, logical_cpus=len(cpus), physical_cores=n_cores, smt_enabled=smt,
             allowed_cpus=allowed if allowed is not None else cpus, cpu_quota=quota, core_of_cpu=core,
             gpu={"name": "X", "driver": "1", "memory": "1", "compute_cap": "8.9", "arch": gpu_arch} if gpu_arch else None)
    e["env_id"] = ENV.env_id(e)
    return e


def perf_of(env, rows):
    data = {"schema": "adaptive-perf-v1", "env_id": env["env_id"], "gate100_passed": True, "rows": rows}
    return PRO.PerfProfile(data, hashlib.sha256(PRO.canonical_bytes(data)).hexdigest())


def row(env, N, T, kind, wall, cpu, p=163):
    if kind == "GPU":
        pid, plan = SEL.gpu_placement_id(env), {"backend": "GPU_HYBRID", "main_cpu": None, "worker_cpus": []}
    else:
        m, w, pid = SEL.placements(env)[kind]
        plan = {"backend": "CPU_SERIAL" if kind == "SERIAL" else "CPU_PARALLEL", "main_cpu": m, "worker_cpus": list(w)}
    r = {"N": N, "T": T, "strategy": kind, "p_measured": p, "placement_id": pid, "plan": plan,
         "env_id": env["env_id"], "wall_s": [wall] * 3, "cpu_s": [cpu] * 3}
    r["row_id"] = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
    return r


def test_env_id_volatile_and_identity():
    e = ENV.collect()
    assert ENV.env_id(e) == e["env_id"]
    assert ENV.env_id(dict(e, hostname="other", notes="x")) == e["env_id"]
    assert ENV.env_id(dict(e, cpu_model="other")) != e["env_id"]
    assert ENV.env_id(dict(e, cpu_quota=4.0)) != e["env_id"]
    assert CK.own_env_id(e) == e["env_id"]


def test_placement_smt_quota_allowed():
    e = fake_env(smt=True, n_cores=8)
    pl = SEL.placements(e)
    assert pl["SERIAL"][0] == 0
    assert pl["W6"][1] == (2, 4, 6, 8, 10, 0) and pl["W6"][0] == 0          # one CPU per core, siblings unused
    assert pl["W4"] == (0, (2, 4, 6, 8), pl["W4"][2])
    assert SEL.placements(fake_env(quota=4.6))["W3"] and "W4" not in SEL.placements(fake_env(quota=4.6))
    assert "W6" not in SEL.placements(fake_env(n_cores=5))
    e2 = fake_env(smt=False, n_cores=16, allowed=[3, 5, 7, 9, 11, 13, 15])
    assert SEL.placements(e2)["W6"] == (3, (5, 7, 9, 11, 13, 3), SEL.placements(e2)["W6"][2])
    for env in (e, e2, fake_env(quota=4.6)):
        assert {k: (v[0], list(v[1])) for k, v in SEL.placements(env).items()} == \
            {k: (v[0], list(v[1])) for k, v in CK.own_placements(env).items()}


def test_selector_rules():
    e = fake_env()
    # no profile / unmeasured class -> serial; GPU never guessed
    assert SEL.select(12, 1000, 163, "WALL_MIN", e, None).backend == "CPU_SERIAL"
    prof = perf_of(e, [row(e, 12, 1000, "SERIAL", 40, 40), row(e, 12, 1000, "W6", 10, 50),
                       row(e, 12, 1000, "GPU", 8, 8), row(e, 8, 100, "SERIAL", 2.7, 2.6, 107),
                       row(e, 8, 100, "W4", 1.39, 3.0, 107), row(e, 8, 100, "W6", 1.31, 4.0, 107)])
    assert SEL.select(12, 1000, 163, "WALL_MIN", e, prof).backend == "GPU_HYBRID"
    assert "PERF_CLASS_UNMEASURED" in SEL.select(14, 1000, 163, "WALL_MIN", e, prof).reasons
    p162 = SEL.select(12, 1000, 162, "WALL_MIN", e, prof)                    # GPU-unsupported p -> best CPU
    assert (p162.backend, p162.worker_count, p162.p) == ("CPU_PARALLEL", 6, 162)
    t = SEL.select(8, 100, 107, "WALL_MIN", e, prof)                          # W4 / W6 within 6% -> no tie, W6
    assert (t.backend, t.worker_count) == ("CPU_PARALLEL", 6)
    prof2 = perf_of(e, [row(e, 8, 100, "W4", 1.33, 3.0, 107), row(e, 8, 100, "W6", 1.31, 4.0, 107)])
    t2 = SEL.select(8, 100, 107, "WALL_MIN", e, prof2)                        # within 5%: fewer CPU seconds wins
    assert (t2.worker_count, any(r.startswith("TIE") for r in t2.reasons)) == (4, True)
    assert SEL.select(12, 1000, 163, "CPU_MIN", e, prof).backend == "CPU_SERIAL"
    with pytest.raises(SEL.Refusal):
        SEL.select(12, 1000, 163, "WALL_MIN", fake_env(n_cores=7), prof)       # profile of another env_id
    rows = {"rows": [dict(v) for v in prof._rows.values()]}
    for (N, T, p, g) in ((12, 1000, 163, "WALL_MIN"), (12, 1000, 162, "WALL_MIN"), (8, 100, 107, "WALL_MIN"),
                         (14, 1000, 163, "WALL_MIN"), (12, 1000, 163, "CPU_MIN")):
        pl = SEL.select(N, T, p, g, e, prof)
        assert (pl.backend, pl.worker_count) == CK.own_choice(N, T, p, g, e, rows, True)


def test_gpu_eligibility_and_refusals():
    e = fake_env()
    assert SEL.gpu_eligible(12, 1000, 163, e, False) == (True, [])
    assert not SEL.gpu_eligible(12, 1000, 162, e, True)[0]
    assert not SEL.gpu_eligible(14, 1000, 163, e, True)[0]
    assert not SEL.gpu_eligible(16, 100, 109, e, False)[0]                    # T=100 needs gate100
    assert SEL.gpu_eligible(16, 100, 109, e, True)[0]
    assert not SEL.gpu_eligible(12, 1000, 163, fake_env(gpu_arch="sm_75"), True)[0]
    assert not SEL.gpu_eligible(12, 1000, 163, fake_env(gpu_arch=None), True)[0]
    with pytest.raises(SEL.Refusal):
        SEL.fixed("GPU", 8, 100, 107, e, True)
    u3 = SEL.simulated_env(ENV.collect(), "U3_cpu_unverified")
    with pytest.raises(SEL.Refusal) as r:
        SEL.select(12, 1000, 163, "WALL_MIN", u3, None)
    assert r.value.code == "REFUSED_UNVERIFIED_ENVIRONMENT"


def test_adapter_recheck_refuses_bad_plans():
    e = fake_env()
    g = SEL.AdaptivePlan(SEL.EVALUATOR, 162, "GPU_HYBRID", 0, None, (), "x", "GPU_V1", 32, "WALL_MIN", (), (),
                         e["env_id"])
    assert "GPU_P" in AD.validate_plan(g, 12, 1000, e, True)
    assert "GPU_DOMAIN" in AD.validate_plan(g.__class__(**{**g.__dict__, "p": 163}), 14, 1000, e, True)
    assert "GPU_T100_NOT_CONNECTED" in AD.validate_plan(g.__class__(**{**g.__dict__, "p": 109}), 16, 100, e, False)
    sib = SEL.AdaptivePlan(SEL.EVALUATOR, 163, "CPU_PARALLEL", 3, 4, (0, 1, 2), "x", None, None, "WALL_MIN", (), (),
                           e["env_id"])
    assert "WORKERS_SHARE_A_CORE" in AD.validate_plan(sib, 12, 1000, e, True)
    out = SEL.AdaptivePlan(SEL.EVALUATOR, 163, "CPU_SERIAL", 0, 99, (), "x", None, None, "WALL_MIN", (), (),
                           e["env_id"])
    assert "CPU_NOT_ALLOWED" in AD.validate_plan(out, 12, 1000, e, True)
    w6 = SEL.fixed("W6", 12, 1000, 163, e)
    assert AD.validate_plan(w6, 12, 1000, e, True) == []
    assert "OVER_QUOTA" in AD.validate_plan(w6, 12, 1000, dict(e, cpu_quota=3.0), True)


def test_gpu_status_classes():
    pr = {"outcome": "DECIDED"}
    assert AD.classify_gpu({"status": "OK", "pass_record": pr, "device_p": 163, "device_p_echo": [163]}, 163) == "OK"
    assert AD.classify_gpu({"status": "REFUSED_DEVICE_WIDTH: x", "pass_record": {"outcome": "UNDECIDED_AT_PRECISION"},
                            "device_p": 163, "device_p_echo": [163]}, 163) == "DEVICE_REFUSAL"   # problem E
    assert AD.classify_gpu({"status": "DEVICE_ERROR"}, 163) == "DEVICE_ERROR"
    assert AD.classify_gpu({"status": "OK", "pass_record": pr, "device_p": 163, "device_p_echo": [166]}, 163) == \
        "GPU_PRECISION_MISMATCH"
    assert AD.classify_gpu({"status": "DOMAIN_STOP_UNPROVEN", "pass_record": {"outcome": "DOMAIN_UNPROVEN"},
                            "device_p": 64, "device_p_echo": [64]}, 64) == "OK"


def test_start_p_chain_and_fingerprints():
    env, store = ENV.collect(), EXP.load_store()
    b = json.loads(EXP.BUNDLE.read_text(encoding="utf-8"))
    exp = {(12, 1000, "CHAIN"): 163, (16, 1000, "CHAIN"): 163, (8, 100, "CHAIN"): 107, (14, 1000, "CHAIN"): 163,
           (16, 100, "CHAIN"): 109, (12, 1000, "BASE64"): 64, (12, 1000, "FIXED_START:162"): 162}
    for (N, T, s), p in exp.items():
        d = EXP.start_decision(N, T, s, store, env)
        assert d["start_p"] == p == CK.own_start(N, T, s, b)
    assert EXP.start_decision(8, 100, "CHAIN", store, env)["start_source"] == "EXACT_MEMORY"
    # the initial state identity does not depend on p; fingerprints separate N, T and contracts
    from experiments.experience_start_p_v1.experience import fingerprint
    d8 = EXP.initial_state_digest(8)
    assert d8 == CK.own_initial_digest(8) != EXP.initial_state_digest(12)
    import experiments.gpu_long_trajectory_v1.long as LG
    from experiments.gpu_short_trajectory_v1.traj import enc
    for p in (64, 163):                                                        # the GPU start state at p is the
        q, pm = LG.initial(8, p)                                               # checker's own lift of the same
        assert (json.loads(json.dumps(enc(q))), json.loads(json.dumps(enc(pm)))) == CK.own_echo(8, p)   # state
    f = lambda **k: fingerprint(*[k.get(x, y) for x, y in (("ph", "a"), ("nu", "b"), ("ev", "e"), ("d", d8),  # noqa
                                                            ("T", 100))])
    assert len({f(), f(ph="z"), f(nu="z"), f(ev="z"), f(d="z"), f(T=1000)}) == 6
    with pytest.raises(ValueError):
        EXP.load_store(sha="0" * 64)


def test_own_p2_equals_frozen_policy():
    import random
    rnd = random.Random(7)
    for _ in range(300):
        p = rnd.randint(64, 900)
        T = rnd.choice((100, 1000))
        out = rnd.choice(("UNDECIDED_AT_PRECISION", "DOMAIN_UNPROVEN"))
        k = rnd.randint(0, T)
        sc = None
        if out == "UNDECIDED_AT_PRECISION":
            sc = [[str(rnd.randint(-10**6, 10**6) / 7), str(rnd.randint(-10**6, 10**6) / 7)] for _ in range(4)]
            sc = [[str(min(int(float(a) * 7), int(float(b) * 7))) + "/7", str(max(int(float(a) * 7),
                                                                               int(float(b) * 7))) + "/7"]
                  for a, b in sc]
        h = [{"requested_p": p, "outcome": out, "completed_steps": k, "endpoints_scaled": sc}]
        assert CK.own_next(h[-1], T, {p}) == POL.next_p("P2", None, h, T)


def test_checker_and_analysis_independent():
    banned = {"experiments.adaptive_execution_v1." + m for m in
              ("environment", "profiles", "selector", "adapters", "service", "experience", "campaign")}
    banned |= {"experiments.gpu_long_trajectory_v1.long", "experiments.gpu_long_trajectory_v1.support",
               "experiments.gpu_force_feasibility_v1.gpu_host", "experiments.gpu_pair_vector_v1.pv_host",
               "experiments.gpu_one_step_v1.one_step", "experiments.gpu_short_trajectory_v1.traj"}
    for f in ("checker.py", "analyze.py"):
        tree = ast.parse((HERE / f).read_text(encoding="utf-8"))
        names = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | \
            {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert not names & banned, (f, names & banned)
    assert set(CK.SUPPORT_P) == set(PRO.CORRECTNESS["GPU_V1"]["support_p"])
    assert CK.GPU_SOURCES == dict(PRO.CORRECTNESS["GPU_V1"]["gpu_sources"])
    assert {k: tuple(v) for k, v in CK.DOMAIN.items()} == {k: tuple(v) for k, v in
                                                           PRO.CORRECTNESS["GPU_V1"]["domain_N"].items()}


def test_perf_profile_seal(tmp_path):
    e = fake_env()
    data = {"schema": "adaptive-perf-v1", "env_id": e["env_id"], "rows": [row(e, 12, 1000, "SERIAL", 1, 1)]}
    p = tmp_path / f"perf_{e['env_id'][:16]}.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    Path(str(p) + ".sha256").write_text(hashlib.sha256(PRO.canonical_bytes(data)).hexdigest(), encoding="utf-8")
    assert PRO.find_perf(e["env_id"], tmp_path).env_id == e["env_id"]
    assert PRO.find_perf(fake_env(n_cores=7)["env_id"], tmp_path) is None
    data["rows"][0]["wall_s"] = [0.1] * 3
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        PRO.find_perf(e["env_id"], tmp_path)


# ---------------------------------------------------------------------------
# the real fixture (GPU + CPU)
# ---------------------------------------------------------------------------
REQ = {"TA": {"id": "TA", "N": 12, "T": 100, "start": "FIXED_START:163"},
       "TB": {"id": "TB", "N": 5, "T": 100, "start": "CHAIN"},
       "TC": {"id": "TC", "N": 16, "T": 100, "start": "BASE64"},
       "TD": {"id": "TD", "N": 12, "T": 100, "start": "FIXED_START:162"}}


def _save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(obj, sort_keys=True).encode(), mtime=0))


def _run(fx, out, rid, label, rep=1, faults=()):
    goal = {"ADAPTIVE_WALL": "WALL_MIN", "ADAPTIVE_CPU": "CPU_MIN"}.get(label)
    s = SVC.run_request(REQ[rid], "ADAPTIVE" if goal else label, fx["env"], fx["perf"], fx["store"], gpu=fx["w"],
                        goal=goal, gate100=True, run_id=f"r{rep}/{rid}__{label}", faults=faults)
    s.update(label=label, repeat=rep)
    _save(out / "services" / f"r{rep}" / f"{rid}__{label}.json.gz", s)
    return s


def _flush_log(fx, out):
    p = out / "gpu_worker_log" / "r1.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(p.read_text()) if p.exists() else []
    p.write_text(json.dumps(old + fx["w"].log))
    fx["w"].log = []


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    env0 = ENV.collect()
    g = env0.get("gpu")
    if not g or g["arch"] not in PRO.CORRECTNESS["GPU_V1"]["verified_arch"]:
        pytest.skip("needs a verified GPU (sm_86 / sm_89)")
    out = tmp_path_factory.mktemp("ae1_base")
    rec = CAMP.phase_env(out)
    env = rec["env"]
    (out / "gate100.json").write_text(json.dumps({"passed": True, "cases": [], "fixture": "TEST_ONLY"}))
    rows = [row(env, 12, 100, "SERIAL", 6, 6), row(env, 12, 100, "W6", 2, 9), row(env, 12, 100, "GPU", 1, 1),
            row(env, 16, 100, "SERIAL", 11, 11), row(env, 16, 100, "GPU", 1, 1),
            row(env, 5, 100, "SERIAL", 1.0, 1.0, 106), row(env, 5, 100, "W3", 0.9, 2.0, 106),
            row(env, 5, 100, "W6", 0.5, 2.5, 106)]
    data = {"schema": "adaptive-perf-v1", "env_id": env["env_id"], "gate100_passed": True, "rows": rows,
            "fixture": "TEST_ONLY"}
    pp = out / "perf.json"
    pp.write_text(json.dumps(data), encoding="utf-8")
    Path(str(pp) + ".sha256").write_text(hashlib.sha256(PRO.canonical_bytes(data)).hexdigest(), encoding="utf-8")
    w = AD.GpuWorker(rec["lib"]["path"])
    assert w.ready, w.hello
    f = {"env": env, "perf": PRO.load_perf(pp), "perf_path": pp, "store": EXP.load_store(), "w": w, "out": out}
    f["s"] = {(rid, lab, rep): _run(f, out, rid, lab, rep) for rid, lab, rep in
              (("TA", "ADAPTIVE_WALL", 1), ("TB", "ADAPTIVE_WALL", 1), ("TB", "ADAPTIVE_WALL", 2),
               ("TB", "FIXED_SERIAL", 1), ("TC", "ADAPTIVE_WALL", 1), ("TD", "ADAPTIVE_WALL", 1))}
    _flush_log(f, out)
    CK.replay(out, workers=3)
    yield f
    w.close()


def test_fixture_choices_and_meaning(fx):
    s = fx["s"]
    ta, tb, tc, td = (s[("TA", "ADAPTIVE_WALL", 1)], s[("TB", "ADAPTIVE_WALL", 1)], s[("TC", "ADAPTIVE_WALL", 1)],
                      s[("TD", "ADAPTIVE_WALL", 1)])
    assert [pz["backend"] for pz in ta["passes"]] == ["GPU_HYBRID"] and ta["status"] == "DECIDED"
    assert [(pz["backend"], pz["attempts"][-1]["plan"]["worker_count"]) for pz in tb["passes"]] == \
        [("CPU_PARALLEL", 6)] and tb["p_sequence"] == [106]
    assert tc["p_sequence"] == [64, 109] and [pz["backend"] for pz in tc["passes"]] == ["GPU_HYBRID"] * 2
    assert td["p_sequence"] == [162] and td["passes"][0]["backend"] == "CPU_PARALLEL"   # 162 not moved to 163
    assert td["passes"][0]["effective_p"] == 162
    assert tc["execution_label"] == "GPU_FULL_RETRY" and tb["execution_label"] == "CPU_ONLY"
    own = CK.own_records(fx["out"])
    for sv in s.values():
        for pz in sv["passes"]:
            o = own[(sv["N"], sv["T"], pz["requested_p"])]
            assert all(pz[k] == o[k] for k in CK.FIELDS)


def test_fixture_checker_ok(fx):
    v = CK.check(fx["out"], fx["perf_path"])
    assert v["verdict"] == "EVIDENCE OK", v["errors"]


def test_device_refusal_and_error_fall_back_to_cpu(fx, tmp_path):
    class Refusing:
        ready = True
        log = []

        def run(self, N, T, p, block, rid, **f):
            self.log.append({"request_id": rid, "status": "REFUSED_DEVICE_WIDTH: x"})
            return {"status": "REFUSED_DEVICE_WIDTH: x", "pass_record": {"outcome": "UNDECIDED_AT_PRECISION"},
                    "device_p": p, "device_p_echo": [p]}, 0.01
    s = SVC.run_request(REQ["TA"], "ADAPTIVE", fx["env"], fx["perf"], fx["store"], gpu=Refusing(), goal="WALL_MIN",
                        gate100=True, run_id="refusal")
    assert s["events"][0]["event"] == "DEVICE_REFUSAL"
    assert [a["plan"]["backend"] for a in s["passes"][0]["attempts"]] == ["GPU_HYBRID", "CPU_SERIAL"]
    assert s["p_sequence"] == [163] and s["status"] == "DECIDED"                  # not escalated by P2
    assert s["execution_label"] == "GPU_WITH_CPU_FALLBACK"
    e = SVC.run_request(REQ["TA"], "ADAPTIVE", fx["env"], fx["perf"], fx["store"], gpu=fx["w"], goal="WALL_MIN",
                        gate100=True, run_id="deverr", faults={"DEVICE_ERROR"})
    fx["w"].log = []
    assert e["events"][0]["event"] == "DEVICE_ERROR" and e["passes"][0]["backend"] == "CPU_SERIAL"


# ---------------------------------------------------------------------------
# fault injections: each must make the checker fail
# ---------------------------------------------------------------------------
def _copy(fx, tmp_path):
    d = tmp_path / "ev"
    shutil.copytree(fx["out"], d, ignore=shutil.ignore_patterns("build"))
    return d


def _edit(path, fn):
    s = json.loads(gzip.decompress(path.read_bytes()))
    fn(s)
    path.write_bytes(gzip.compress(json.dumps(s, sort_keys=True).encode(), mtime=0))


def _fails(d, fx, needle, **kw):
    CK.replay(d, workers=2)
    v = CK.check(d, kw.pop("profile", fx["perf_path"]), **kw)
    assert v["verdict"] != "EVIDENCE OK"
    assert any(needle in e for e in v["errors"]), v["errors"]


def _fault_run(fx, d, rid, faults):
    s = _run(fx, d, rid, "ADAPTIVE_WALL", 1, faults)
    _flush_log(fx, d)
    return s


def test_F1_env_disguised(fx, tmp_path):
    d = _copy(fx, tmp_path)
    e = json.loads((d / "env.json").read_text())
    e["env"]["gpu"]["arch"] = "sm_75"
    (d / "env.json").write_text(json.dumps(e))
    _fails(d, fx, "ENV_ID_RECOMPUTE_MISMATCH")


def test_F2_row_of_another_env(fx, tmp_path):
    d = _copy(fx, tmp_path)
    data = json.loads(fx["perf_path"].read_text())
    data["rows"][0]["env_id"] = "f" * 64
    pp = d / "perf_other.json"
    pp.write_text(json.dumps(data))
    Path(str(pp) + ".sha256").write_text(hashlib.sha256(PRO.canonical_bytes(data)).hexdigest())
    _fails(d, fx, "PERF_ROW_OTHER_ENV", profile=pp)


def test_F3_unsupported_p_moved(fx, tmp_path):
    d = _copy(fx, tmp_path)
    s = _fault_run(fx, d, "TD", {"F3"})
    assert s["passes"][0]["backend"] == "GPU_HYBRID"
    _fails(d, fx, "GPU_PASS_OUTSIDE_PROFILE")


def test_F4_model_at_other_p(fx, tmp_path):
    d = _copy(fx, tmp_path)
    _fault_run(fx, d, "TA", {"F4"})
    _fails(d, fx, "GPU_PRECISION")


def test_F5_forged_next_p(fx, tmp_path):
    d = _copy(fx, tmp_path)
    _fault_run(fx, d, "TC", {"F5"})
    _fails(d, fx, "P_SEQUENCE")


def test_F6_failed_pass_deleted(fx, tmp_path):
    d = _copy(fx, tmp_path)
    _fault_run(fx, d, "TC", {"F6"})
    _fails(d, fx, "PASS_INDICES")


def test_F7_retry_from_last_state(fx, tmp_path):
    d = _copy(fx, tmp_path)
    _fault_run(fx, d, "TC", {"F7"})
    _fails(d, fx, "GPU_START_NOT_ORIGINAL")


def test_F8_wrong_placement(fx, tmp_path):
    d = _copy(fx, tmp_path)
    sib = [c for c in fx["env"]["allowed_cpus"] if fx["env"]["core_of_cpu"][str(c)] ==
           fx["env"]["core_of_cpu"][str(fx["env"]["allowed_cpus"][0])]]

    def bad(s):
        a = s["passes"][0]["attempts"][-1]
        cpus = a["plan"]["worker_cpus"]
        cpus[0] = sib[-1] if len(sib) > 1 else 10 ** 6                          # SMT sibling or a CPU not allowed
        a["result"]["runner"]["plan"]["worker_cpus"] = list(cpus)
    _edit(d / "services" / "r1" / "TB__ADAPTIVE_WALL.json.gz", bad)
    _fails(d, fx, "PLACEMENT")


def test_F9_endpoint_one_ulp(fx, tmp_path):
    d = _copy(fx, tmp_path)

    def bad(s):
        k = s["passes"][-1]["endpoints_key"]
        s["passes"][-1]["endpoints_key"] = k[:-1] + ("0" if k[-1] != "0" else "1")
    _edit(d / "services" / "r1" / "TA__ADAPTIVE_WALL.json.gz", bad)
    _fails(d, fx, "RESULT_ENDPOINTS_KEY")


def test_F10_evaluation_record_in_store(fx, tmp_path):
    d = _copy(fx, tmp_path)
    b = json.loads(EXP.BUNDLE.read_text(encoding="utf-8"))
    b["records"].append({"run_id": "candidate", "verification_status": "UNVERIFIED"})
    bp = tmp_path / "bundle.json"
    bp.write_text(json.dumps(b))
    _fails(d, fx, "EXPERIENCE_BUNDLE_HASH", bundle_path=bp)


def test_F11_correctness_failure_as_perf_success(fx, tmp_path):
    d = _copy(fx, tmp_path)

    def bad(s):
        s["passes"][0]["cells"] = [0] * len(s["passes"][0]["cells"] or [0])
    _edit(d / "services" / "r2" / "TB__ADAPTIVE_WALL.json.gz", bad)
    _fails(d, fx, "REPEAT_DIFFERS_FROM_REPEAT_1")


def test_F12_device_error_hidden(fx, tmp_path):
    d = _copy(fx, tmp_path)
    s = _fault_run(fx, d, "TA", {"DEVICE_ERROR", "F12"})
    assert not s["events"] and len(s["passes"][0]["attempts"]) == 2
    _fails(d, fx, "GPU_EVENT_MISSING_FROM_LEDGER")


def test_F13_executed_plan_differs(fx, tmp_path):
    d = _copy(fx, tmp_path)
    _fault_run(fx, d, "TB", {"F13"})
    _fails(d, fx, "EXECUTED_PLAN_DIFFERS")
