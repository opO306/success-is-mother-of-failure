"""ADAPTIVE_EXECUTION_V1 campaign (protocol 'official_host', 'requests', 'strategies', 'order_and_repeats').

    python -m experiments.adaptive_execution_v1.campaign --out OUT --phase env
    python -m experiments.adaptive_execution_v1.campaign --out OUT --phase gate100
    python -m experiments.adaptive_execution_v1.campaign --out OUT --phase calibrate
    python -m experiments.adaptive_execution_v1.campaign --out OUT --phase evaluate --repeats 1      (correctness run)
    python -m experiments.adaptive_execution_v1.campaign --out OUT --phase evaluate --repeats 2-5    (after the checker gate)
    python -m experiments.adaptive_execution_v1.campaign --out OUT --phase local                     (U4: real local env)

The replay is the checker's (checker.py --phase replay). Every phase writes its own files; nothing is overwritten.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from experiments.adaptive_execution_v1 import adapters as AD
from experiments.adaptive_execution_v1 import environment as ENV
from experiments.adaptive_execution_v1 import experience as EXP
from experiments.adaptive_execution_v1 import profiles as PRO
from experiments.adaptive_execution_v1 import selector as SEL
from experiments.adaptive_execution_v1 import service as SVC

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROTOCOL = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
REQUESTS = PROTOCOL["requests (sealed evaluation set)"]
CAL_CLASSES = PROTOCOL["performance_profile"]["calibration_classes"]
CAL_REPEATS = PROTOCOL["performance_profile"]["calibration_repeats"]
GATE100 = ({"N": 12, "p": 163}, {"N": 16, "p": 163}, {"N": 16, "p": 109}, {"N": 16, "p": 64}, {"N": 40, "p": 109})
STRATS = ("ADAPTIVE_WALL", "FIXED_SERIAL", "FIXED_W6", "FIXED_GPU")
GPU_FIXED_REQUESTS = ("R1", "R2", "R3", "R4", "R8")
FORCED_GPU = ({"id": "R5", "N": 8, "T": 100, "p": 107}, {"id": "R6", "N": 12, "T": 1000, "p": 162},
              {"id": "R7", "N": 14, "T": 1000, "p": 163})
SOURCES = ("environment.py", "profiles.py", "selector.py", "adapters.py", "service.py", "experience.py", "campaign.py",
           "checker.py", "analyze.py", "protocol.json")


def git(*a):
    try:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


def save(path, obj, gz=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, indent=None if gz else 1, sort_keys=True).encode("utf-8")
    if gz:
        path.write_bytes(gzip.compress(data, mtime=0))
    else:
        path.write_bytes(data)


def load(path):
    p = Path(path)
    raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == ".gz" else raw)


def loadavg():
    try:
        return Path("/proc/loadavg").read_text().split()[:3]
    except OSError:
        return None


def execution_seal():
    return {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "status_porcelain": git("status", "--porcelain"),
            "sources_sha256_lf": {f: ENV.sha_lf(HERE / f) for f in SOURCES if (HERE / f).exists()}}


# ---------------------------------------------------------------------------
# env / build
# ---------------------------------------------------------------------------
def phase_env(out):
    env = ENV.collect()
    rec = {"env": env, "seal": execution_seal(), "lib": None}
    if env.get("gpu"):
        from experiments.gpu_pair_vector_v1 import pv_host as PH
        lib, arch, _ = PH.build(out / "build")
        rec["lib"] = {"path": str(lib), "arch": arch, "sha256": hashlib.sha256(Path(lib).read_bytes()).hexdigest()}
    save(out / "env.json", rec)
    print("ENV", env["env_id"], env["cpu_model"], (env.get("gpu") or {}).get("name"), flush=True)
    return rec


def _env(out):
    rec = load(out / "env.json")
    now = ENV.collect()
    if now["env_id"] != rec["env"]["env_id"]:
        raise SystemExit(f"ENV_CHANGED_DURING_JOB {now['env_id']} != {rec['env']['env_id']}")
    return rec


def _worker(rec):
    if not rec["lib"]:
        return None
    w = AD.GpuWorker(rec["lib"]["path"])
    print("GPU_WORKER", w.hello, flush=True)
    return w


# ---------------------------------------------------------------------------
# gate100: the T = 100 GPU connection gate (adapter record vs CPU serial record)
# ---------------------------------------------------------------------------
def phase_gate100(out):
    rec = _env(out)
    env = rec["env"]
    w = _worker(rec)
    cases, ok = [], w is not None and w.ready
    for c in GATE100:
        N, p = c["N"], c["p"]
        if not ok:
            break
        g = SEL.fixed("GPU", N, 100, p, env, True)          # the gate itself: GPU T=100 allowed for this test only
        r = AD.gpu_pass(w, g, N, 100, f"gate100_N{N}_p{p}", keep_detail=True)
        s = AD.cpu_pass(SEL.fixed("SERIAL", N, 100, p, env), N, 100)
        same = {k: r.get(k) == s.get(k) for k in AD.OUTCOME_KEYS}
        evals = (r["gpu"] or {}).get("force_evals")
        exp_evals = (r.get("completed_steps") or 0) + 1
        good = (r["status_class"] == "OK" and s["status_class"] == "OK" and all(same.values())
                and r.get("effective_p") == p and evals == exp_evals
                and (r["gpu"] or {}).get("uploads_in_traj") == 0 and (r["gpu"] or {}).get("allocs_in_traj") == 0)
        cases.append({"N": N, "T": 100, "p": p, "gpu": r, "cpu": s, "fields_equal": same, "pass": good})
        print("GATE100", N, p, r.get("outcome"), s.get("outcome"), good, flush=True)
        ok = ok and good
    if w:
        w.close()
    passed = bool(cases) and ok and len(cases) == len(GATE100)
    save(out / "gate100.json", {"passed": passed, "env_id": env["env_id"], "cases": cases,
                                "gpu_worker_log": w.log if w else []})
    print("GATE100_PASSED" if passed else "GATE100_NOT_PASSED", flush=True)
    return passed


# ---------------------------------------------------------------------------
# calibrate: the performance profile of this env_id
# ---------------------------------------------------------------------------
def _cal_plans(env, N, T, p, gate100):
    place = SEL.placements(env)
    plans = {}
    for kind in ("SERIAL", "W3", "W4", "W6"):
        if kind in place:
            m, wk, pid = place[kind]
            plans[kind] = SEL.AdaptivePlan(SEL.EVALUATOR, p, "CPU_SERIAL" if kind == "SERIAL" else "CPU_PARALLEL",
                                           len(wk), m, wk, pid, None, None, None, (f"CALIBRATE_{kind}",), (),
                                           env["env_id"], f"CALIBRATE_{kind}")
    if SEL.gpu_eligible(N, T, p, env, gate100)[0]:
        plans["GPU"] = SEL.fixed("GPU", N, T, p, env, gate100)
    return plans


def phase_calibrate(out):
    rec = _env(out)
    env = rec["env"]
    g100 = load(out / "gate100.json")["passed"] if (out / "gate100.json").exists() else False
    w = _worker(rec)
    raw = {}
    for c in CAL_CLASSES:
        N, T, p = c["N"], c["T"], c["p"]
        plans = _cal_plans(env, N, T, p, g100)
        if "GPU" in plans and not (w and w.ready):
            del plans["GPU"]
        kinds = list(plans)
        for rep in range(CAL_REPEATS):
            order = kinds[rep % len(kinds):] + kinds[:rep % len(kinds)]
            for kind in order:
                la = loadavg()
                plan = plans[kind]
                if kind == "GPU":
                    r = AD.gpu_pass(w, plan, N, T, f"cal_N{N}_T{T}_{kind}_{rep}", keep_detail=False)
                else:
                    r = AD.cpu_pass(plan, N, T)
                raw.setdefault((N, T, kind), []).append({"rep": rep, "wall_s": r["wall_s"], "cpu_s": r["cpu_s"],
                                                         "status_class": r["status_class"], "load_before": la,
                                                         "outcome": {k: r.get(k) for k in AD.OUTCOME_KEYS},
                                                         "effective_p": r.get("effective_p"),
                                                         "placement_ok": r.get("executed_placement_ok", True)})
                print("CAL", N, T, kind, rep, f"{r['wall_s']:.2f}s", r["status_class"], r.get("outcome"), flush=True)
    rows = []
    for (N, T, kind), reps in sorted(raw.items()):
        plan = _cal_plans(env, N, T, next(c["p"] for c in CAL_CLASSES if (c["N"], c["T"]) == (N, T)), g100)[kind]
        good = all(x["status_class"] == "OK" and x["placement_ok"] for x in reps) and \
            len({json.dumps(x["outcome"], sort_keys=True) for x in reps}) == 1
        row = {"N": N, "T": T, "strategy": kind, "p_measured": plan.p, "placement_id": plan.placement_id,
               "plan": plan.record(), "env_id": env["env_id"], "wall_s": [x["wall_s"] for x in reps],
               "cpu_s": [x["cpu_s"] for x in reps], "load_before": [x["load_before"] for x in reps],
               "outcome": reps[0]["outcome"], "all_ok": good}
        row["row_id"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        if good:
            rows.append(row)
    prof = {"schema": "adaptive-perf-v1", "env_id": env["env_id"], "env": env, "gate100_passed": g100,
            "gpu_worker_startup": w.hello if w else None, "rows": rows,
            "rejected_rows": sorted(f"{k[0]}|{k[1]}|{k[2]}" for k in raw if not any(
                (r["N"], r["T"], r["strategy"]) == k for r in rows)), "seal": execution_seal()}
    if w:
        w.close()
    save(out / "perf_profile.json", prof)
    sha = hashlib.sha256(PRO.canonical_bytes(prof)).hexdigest()
    (out / "perf_profile.json.sha256").write_text(sha + "\n", encoding="utf-8")
    raw_out = {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in raw.items()}
    save(out / "calibration_raw.json", raw_out)
    print("PERF_PROFILE", sha, len(rows), "rows", flush=True)


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------
def _repeats(spec):
    a, _, b = spec.partition("-")
    return list(range(int(a), int(b or a) + 1))


def _service(req, strat, env, perf, store, w, g100, out_dir, run_id, keep, faults=()):
    goal = {"ADAPTIVE_WALL": "WALL_MIN", "ADAPTIVE_CPU": "CPU_MIN"}.get(strat)
    s = SVC.run_request(req, "ADAPTIVE" if goal else strat, env, perf, store, gpu=w, goal=goal, gate100=g100,
                        run_id=run_id, keep_gpu_detail=keep, faults=faults)
    s["label"] = strat
    return s


def phase_evaluate(out, repeats, profile_path=None, requests=REQUESTS):
    rec = _env(out)
    env = rec["env"]
    perf = PRO.load_perf(profile_path) if profile_path else PRO.find_perf(env["env_id"])
    if perf is None:
        raise SystemExit(f"ENV_NOT_SEALED: no sealed performance profile for {env['env_id']}")
    if perf.env_id != env["env_id"]:
        raise SystemExit("PERF_PROFILE_OF_ANOTHER_ENV")
    g100 = load(out / "gate100.json")["passed"]
    store = EXP.load_store()
    w = _worker(rec)
    has_w6 = "W6" in SEL.placements(env)
    for r in repeats:
        d = out / "services" / f"r{r}"
        strats = list(STRATS)
        strats = strats[(r - 1) % len(strats):] + strats[:(r - 1) % len(strats)]
        for req in requests:
            for st in strats:
                if st == "FIXED_GPU" and (req["id"] not in GPU_FIXED_REQUESTS or (req["T"] == 100 and not g100)):
                    continue
                if st == "FIXED_W6" and not has_w6:
                    continue
                la0 = loadavg()
                s = _service(req, st, env, perf, store, w, g100, d, f"r{r}/{req['id']}__{st}", keep=(r == 1))
                s.update(repeat=r, load_before=la0, load_after=loadavg())
                save(d / f"{req['id']}__{st}.json.gz", s, gz=True)
                for pz in s["passes"]:
                    save(out / "candidates" / f"r{r}__{req['id']}__{st}__pass{pz['index']}.json",
                         EXP.candidate_record({**s, "run_id": f"r{r}/{req['id']}__{st}"}, pz, env["env_id"]))
                print("SVC", r, req["id"], st, s["status"], s["p_sequence"],
                      [pz["backend"] for pz in s["passes"]], f"{s['service_wall_s']:.2f}s", flush=True)
        if r == 1:
            _cases(out, env, perf, store, w, g100)
        save(out / "gpu_worker_log" / f"r{r}.json", w.log if w else [])
        if w:
            w.log = []
    if w:
        save(out / "gpu_worker_startup.json", w.hello)
        w.close()


def _cases(out, env, perf, store, w, g100):
    d = out / "cases"
    req1 = next(q for q in REQUESTS if q["id"] == "R1")
    for req in REQUESTS:                                       # ADAPTIVE_CPU once
        s = _service(req, "ADAPTIVE_CPU", env, perf, store, w, g100, d, f"cases/{req['id']}__ADAPTIVE_CPU", False)
        save(d / f"{req['id']}__ADAPTIVE_CPU.json.gz", s, gz=True)
        print("CASE ADAPTIVE_CPU", req["id"], s["status"], s["p_sequence"], flush=True)
    s = _service(req1, "ADAPTIVE_WALL", env, None, store, w, g100, d, "cases/U1", False)       # no profile
    s["case"] = "U1_perf_unknown"
    save(d / "U1.json.gz", s, gz=True)
    for case in ("U2_gpu_unverified", "U3_cpu_unverified"):
        e = SEL.simulated_env(env, case)
        s = _service(req1, "ADAPTIVE_WALL", e, PRO.find_perf(e["env_id"]), store, w, g100, d, f"cases/{case}", False)
        s["case"], s["simulated_env"] = case, e
        save(d / f"{case.split('_')[0]}.json.gz", s, gz=True)
        print("CASE", case, s["status"], [a["plan"]["backend"] for pz in s["passes"] for a in pz["attempts"]],
              flush=True)
    forced = []
    for f in FORCED_GPU:
        plan = SEL.AdaptivePlan(SEL.EVALUATOR, f["p"], "GPU_HYBRID", 0, None, (), SEL.gpu_placement_id(env), "GPU_V1",
                                32, "WALL_MIN", ("FORCED_GPU_TEST",), (), env["env_id"], "FORCED_GPU")
        v = AD.validate_plan(plan, f["N"], f["T"], env, g100)
        wr = w.run(f["N"], f["T"], f["p"], 32, f"forced_{f['id']}")[0] if w and w.ready else None
        forced.append({**f, "adapter_violations": v, "worker_status": (wr or {}).get("status"),
                       "executed": bool(wr and wr.get("pass_record"))})
        print("CASE FORCED_GPU", f, v, (wr or {}).get("status"), flush=True)
    save(d / "forced_gpu.json", forced)


# ---------------------------------------------------------------------------
# local (U4): the real local environment without a performance profile
# ---------------------------------------------------------------------------
def phase_local(out):
    rec = phase_env(out)
    env = rec["env"]
    store = EXP.load_store()
    perf = PRO.find_perf(env["env_id"])
    sel = {}
    for req in REQUESTS:
        dec = EXP.start_decision(req["N"], req["T"], req["start"], store, env)
        try:
            plan = SEL.select(req["N"], req["T"], dec["start_p"], "WALL_MIN", env, perf, False)
            sel[req["id"]] = {"start": dec["start_p"], "source": dec["start_source"], "plan": plan.record()}
        except SEL.Refusal as e:
            sel[req["id"]] = {"refusal": e.code}
    save(out / "local_selection.json", sel)
    req5 = next(q for q in REQUESTS if q["id"] == "R5")
    s = SVC.run_request(req5, "ADAPTIVE", env, perf, store, gpu=None, goal="WALL_MIN", run_id="local/R5")
    save(out / "local_R5.json", s)
    print("LOCAL", {k: (v.get("plan") or {}).get("backend", v.get("refusal")) for k, v in sel.items()},
          s["status"], s["p_sequence"], f"{s['service_wall_s']:.2f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", required=True, choices=("env", "gate100", "calibrate", "evaluate", "local"))
    ap.add_argument("--repeats", default="1")
    ap.add_argument("--profile")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.environ.setdefault("ESP2_LINUX_CLOCK", "1")
    t0 = time.perf_counter()
    if a.phase == "env":
        phase_env(out)
    elif a.phase == "gate100":
        phase_gate100(out)
    elif a.phase == "calibrate":
        phase_calibrate(out)
    elif a.phase == "evaluate":
        phase_evaluate(out, _repeats(a.repeats), a.profile)
    else:
        phase_local(out)
    print("PHASE_DONE", a.phase, f"{time.perf_counter() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
