"""ADAPTIVE_EXECUTION_V1 independent checker (protocol 'checker').

Imports none of environment / profiles / selector / adapters / service / experience / campaign of this experiment and
no GPU code. It re-derives from the evidence files and the sealed files: env_id, the performance profile seal, the
experience bundle seal and the start p, GPU eligibility, CPU placement, the WALL_MIN / CPU_MIN choice, P2, the original
start state, the precision echo, the final results (own replay: own KDK loop, own readout; the force primitive is the
GPU_SHORT_TRAJECTORY_V1 checker's my_forces = E2 RwForce, disclosed), repeat identity and the GPU event log.

    python -m experiments.adaptive_execution_v1.checker OUT --phase replay|gate|final [--profile FILE] [--workers W]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/active/experience_start_p_v2/training_bundle.json"
BUNDLE_SHA = "ec19eda9c6966be265709398480b4de4aa6bfcdb1ddb38de5f5f9d0602283ae3"
EVALUATOR = "rw:R1+R2"
VOLATILE = ("hostname", "collected_at", "loadavg", "notes")
# own copies of the sealed correctness profile (protocol 'correctness_profile')
SUPPORT_P = (64, 73, 78, 109, 128, 161, 163, 166, 192)
ARCH = ("sm_86", "sm_89")
MPMATH = (("1.3.0", "python"),)
DOMAIN = {1000: (12, 16, 40), 100: (12, 16, 40, 64, 128)}
PHYSICS = "5d76fa2ab73bc3139519815c399d3d3e9d782362ab94a9f0cb1227bec460021a"
NUMERIC = "85653a0a815e4f1f2d5f548e17545c5cb0cf38bf17ea788c409ab85bc7748f55"
GPU_SOURCES = {
    "experiments/gpu_pair_vector_v1/pv1.cu": "840d503768ace8f960ae7550139836878c548d183c249e309a1754365ab583c1",
    "experiments/gpu_force_feasibility_v1/g0.cu": "dc519a9cd3ddc4b2a778cb1497bba324bdedcd8bb3e42b6a4514dc2ee49c21de",
    "experiments/gpu_force_feasibility_v1/gpu_host.py": "dd255cb31b7f07ecb428515b36432f829bed124e75536de89af8a3c201163abe",
    "experiments/gpu_pair_vector_v1/pv_host.py": "bded5b8e8080db947612f0d1101adda766b66157d8bc57a10e6df0da55b376f2",
    "experiments/gpu_force_feasibility_v1/compile_plan.py": "cc63a1e53da6e2c4221b9f7f1d298f987bbe35fdcb46231baa3833a5975ac63b",
    "experiments/gpu_long_trajectory_v1/support.py": "4c58017af84ff0ca630db0179b586986c36edd4a795fd249bbc91b3270477cfb",
    "experiments/gpu_long_trajectory_v1/long.py": "4bf01067a91a8b3972b1a55e37fa0eaa00df2da70a39636a58d5650e4c1e7d94",
    "experiments/gpu_one_step_v1/one_step.py": "cacf8077d8eee6c67d140060fcae467737e97c1c7c4d34c3029738bfde112300",
    "experiments/gpu_short_trajectory_v1/traj.py": "ff4f126e5299189326f5f5590c4d99b4f13ad8310cdb3c13c2c4b3e6ae777eab",
}
P_MIN, P_MAX, GUARD, MAX_PASSES, TIE = 64, 1024, 8, 24, 0.05
FINAL = ("DECIDED", "DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE", "INVALID_EVIDENCE")
FIELDS = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key")


def load(path):
    p = Path(path)
    raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == ".gz" else raw)


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# own env_id, initial digest, fingerprint, start p
# ---------------------------------------------------------------------------
def own_env_id(env):
    return hashlib.sha256(json.dumps({k: v for k, v in env.items() if k not in VOLATILE + ("env_id",)},
                                     sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def own_initial_digest(N):
    from experiments.multiatom_parallel_v1 import scenarios as SC
    q0, p0 = SC.initial(N)
    txt = json.dumps({"q": [[str(x) for x in r] for r in q0], "p": [[str(x) for x in r] for r in p0]})
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def own_start(N, T, start, bundle):
    if start == "BASE64":
        return 64
    if start.startswith("FIXED_START:"):
        return int(start.split(":")[1])
    fp = hashlib.sha256(json.dumps([PHYSICS, NUMERIC, EVALUATOR, own_initial_digest(N), T]).encode()).hexdigest()
    fk = f"FCC_N|T={T}|{EVALUATOR}|{PHYSICS}|{NUMERIC}"
    e = bundle["exact"].get(fp)
    if start == "CHAIN" and e and e.get("lowest_observed_success_p"):
        return e["lowest_observed_success_p"]
    f = bundle["family"].get(fk)
    return f["FAMILY_MAX"] if f else 64


# ---------------------------------------------------------------------------
# own P2 (rule text of PRECISION_PILOT_A1)
# ---------------------------------------------------------------------------
def _rhe(x):
    fl = x.numerator // x.denominator
    rem = x - fl
    return fl + 1 if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and fl % 2 == 1) else fl


def _clog2(x):
    e = 0
    while Fraction(2) ** e < x:
        e += 1
    while Fraction(2) ** (e - 1) >= x:
        e -= 1
    return e


def own_next(last, T, tried):
    if last["outcome"] in FINAL:
        return None
    p, out = last["requested_p"], last["outcome"]
    if out == "UNDECIDED_AT_PRECISION" and last.get("endpoints_scaled"):
        extra = None
        for lo, hi in last["endpoints_scaled"]:
            lo, hi = Fraction(lo), Fraction(hi)
            if _rhe(lo) == _rhe(hi):
                continue
            mid = (lo + hi) / 2
            margin = Fraction(1, 2) - abs(mid - _rhe(mid))
            e = 32 if margin <= 0 else _clog2((hi - lo) / margin)
            extra = e if extra is None else max(extra, e)
        nxt = p + max(extra or 0, 1) + GUARD
    elif out == "DOMAIN_UNPROVEN":
        k = last["completed_steps"]
        nxt = 2 * p if k <= 0 else -((-p * T) // k) + GUARD
    else:
        nxt = 2 * p
    nxt = max(nxt, p + 1)
    if nxt > P_MAX:
        return "CAP" if max(tried) >= P_MAX else P_MAX
    return nxt


# ---------------------------------------------------------------------------
# own placement / eligibility / choice
# ---------------------------------------------------------------------------
def own_placements(env):
    seen, cpus = set(), []
    for c in sorted(env["allowed_cpus"]):
        core = env["core_of_cpu"].get(str(c))
        if core is None or core in seen:
            continue
        seen.add(core)
        cpus.append(c)
    q = env.get("cpu_quota")
    lim = len(cpus) if q is None else min(len(cpus), int(q))
    out = {}
    if lim >= 1:
        out["SERIAL"] = (cpus[0], [])
    for W in (3, 4, 6):
        need = 6 if W == 6 else W + 1
        if lim >= need:
            out[f"W{W}"] = (cpus[0], cpus[1:6] + [cpus[0]]) if W == 6 else (cpus[0], cpus[1:W + 1])
    return out


def own_gpu_ok(N, T, p, env, g100):
    g = env.get("gpu")
    return bool(g and g.get("arch") in ARCH and (env["mpmath_version"], env["mpmath_backend"]) in MPMATH
                and env["contracts"]["gpu_sources"] == GPU_SOURCES and p in SUPPORT_P and N in DOMAIN.get(T, ())
                and (T == 1000 or g100))


def _med(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def own_choice(N, T, p, goal, env, prof, g100):
    """(backend, W) the sealed rule gives."""
    if goal == "CPU_MIN" or prof is None:
        return ("CPU_SERIAL", 0)
    rows = {(r["N"], r["T"], r["strategy"]): r for r in prof["rows"]}
    if not any(k[:2] == (N, T) for k in rows):
        return ("CPU_SERIAL", 0)
    place = own_placements(env)
    cands = []
    for kind in ("SERIAL", "W3", "W4", "W6", "GPU"):
        r = rows.get((N, T, kind))
        if r is None or r["env_id"] != env["env_id"]:
            continue
        if kind == "GPU" and not own_gpu_ok(N, T, p, env, g100):
            continue
        if kind != "GPU":
            if kind not in place:
                continue
            m, w = place[kind]
            if (r["plan"]["main_cpu"], r["plan"]["worker_cpus"]) != (m, w):
                continue
        wk = 0 if kind in ("SERIAL", "GPU") else int(kind[1:])
        cands.append((_med(r["wall_s"]), _med(r["cpu_s"]), wk, kind))
    if not cands:
        return ("CPU_SERIAL", 0)
    best = min(cands)
    tied = [c for c in cands if (c[0] - best[0]) / best[0] <= TIE]
    k = min(tied, key=lambda c: (c[1], c[2], c[3]))[3]
    return ("GPU_HYBRID", 0) if k == "GPU" else ("CPU_SERIAL", 0) if k == "SERIAL" else ("CPU_PARALLEL", int(k[1:]))


# ---------------------------------------------------------------------------
# own replay
# ---------------------------------------------------------------------------
def _scaled(vals_q, vals_p):
    out = []
    for vals, sh in ((vals_q, 48), (vals_p, 80)):
        for v in vals:
            pair = []
            for end in v._mpi_:
                s, m, e, bc = end
                x = Fraction(m) * (Fraction(2) ** e) if m else Fraction(0)
                pair.append(str((-x if s else x) * (1 << sh)))
            out.append(pair)
    return out


def own_pass(N, T, p):
    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    from experiments.gpu_short_trajectory_v1.checker import my_forces
    from experiments.multiatom_parallel_v1 import scenarios as SC
    iv.prec = p
    q0, p0 = SC.initial(N)
    q = [[LI.c(x) for x in r] for r in q0]
    pm = [[LI.c(x) for x in r] for r in p0]
    cdt = LI.c(K.CDT)
    rec = {"completed_steps": 0, "stop": None, "stop_step": None, "cells": None, "endpoints_key": None,
           "endpoints_scaled": None}
    st, _, F = my_forces(q, p)
    if st != "OK":
        rec.update(stop=st.replace("DOMAIN_STOP_", ""), stop_step=0)
    else:
        for s in range(T):
            ph = [[pm[a][k] + F[a][k] for k in range(3)] for a in range(N)]
            q1 = [[q[a][k] + ph[a][k] * cdt for k in range(3)] for a in range(N)]
            st, _, F1 = my_forces(q1, p)
            if st != "OK":
                rec.update(stop=st.replace("DOMAIN_STOP_", ""), stop_step=s + 1, completed_steps=s)
                break
            pm = [[ph[a][k] + F1[a][k] for k in range(3)] for a in range(N)]
            q, F = q1, F1
            rec["completed_steps"] = s + 1
    if rec["stop"]:
        rec["outcome"] = {"VIOLATED": "DOMAIN_VIOLATED_PROVEN", "UNPROVEN": "DOMAIN_UNPROVEN"}[rec["stop"]]
    else:
        qv, pv = [x for r in q for x in r], [x for r in pm for x in r]
        try:
            cells = K.decide(qv, pv)
            rec.update(cells=cells, endpoints_key=K.endpoints_key(qv + pv), endpoints_scaled=_scaled(qv, pv))
            rec["outcome"] = "DECIDED" if cells is not None else "UNDECIDED_AT_PRECISION"
        except K.OutOfRange:
            rec.update(stop="OUT_OF_RANGE", stop_step=rec["completed_steps"], outcome="OUT_OF_RANGE")
    return rec


def _own_task(key):
    import time
    t0 = time.perf_counter()
    N, T, p = key
    r = own_pass(N, T, p)
    r["replay_wall_s"] = time.perf_counter() - t0
    return key, r


def own_echo(N, p):
    """The original state at p, encoded as the GPU runner encodes it (dyadic.encode_iv: a pure encoding helper)."""
    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from experiments.gpu_force_feasibility_v1.dyadic import encode_iv
    from experiments.multiatom_parallel_v1 import scenarios as SC
    iv.prec = p
    q0, p0 = SC.initial(N)
    enc = lambda X: [[encode_iv(LI.c(x)._mpi_) for x in r] for r in X]          # noqa: E731
    return json.loads(json.dumps(enc(q0))), json.loads(json.dumps(enc(p0)))


# ---------------------------------------------------------------------------
# evidence
# ---------------------------------------------------------------------------
def services(out):
    files = sorted((Path(out) / "services").glob("r*/*.json.gz")) + sorted((Path(out) / "cases").glob("*.json.gz"))
    return [(f, load(f)) for f in files]


def results_of(svc):
    for pz in svc["passes"]:
        for a in pz["attempts"]:
            if a.get("result"):
                yield pz, a


def needed_keys(out):
    keys = set()
    for _, s in services(out):
        for pz, a in results_of(s):
            if a["result"].get("outcome") and a["result"].get("status_class") not in ("DEVICE_REFUSAL", "DEVICE_ERROR"):
                keys.add((s["N"], s["T"], a["result"]["requested_p"]))
    g = Path(out) / "gate100.json"
    if g.exists():
        for c in load(g)["cases"]:
            keys.add((c["N"], 100, c["p"]))
    return sorted(keys)


def replay(out, workers=1):
    d = Path(out) / "replay"
    d.mkdir(exist_ok=True)
    todo = [k for k in needed_keys(out) if not (d / f"N{k[0]}_T{k[1]}_p{k[2]}.json").exists()]
    with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
        for (N, T, p), r in ex.map(_own_task, todo):
            (d / f"N{N}_T{T}_p{p}.json").write_text(json.dumps(r, sort_keys=True), encoding="utf-8")
            print("REPLAY", N, T, p, r["outcome"], f"{r['replay_wall_s']:.1f}s", flush=True)


def own_records(out):
    d = Path(out) / "replay"
    return {tuple(int(x[1:]) for x in f.stem.split("_")): load(f) for f in d.glob("N*_T*_p*.json")}


def check(out, profile_path=None, bundle_path=BUNDLE, phase="final", expect_repeats=None):
    out = Path(out)
    errs, notes = [], []
    envrec = load(out / "env.json")
    env = envrec["env"]
    if own_env_id(env) != env["env_id"]:
        errs.append("ENV_ID_RECOMPUTE_MISMATCH (env record changed after the id was made)")
    # performance profile seal
    prof = None
    if profile_path:
        prof = load(profile_path)
        sealed = Path(str(profile_path) + ".sha256").read_text(encoding="utf-8").split()[0]
        if hashlib.sha256(canon(prof)).hexdigest() != sealed:
            errs.append("PERF_PROFILE_HASH")
        if prof["env_id"] != env["env_id"]:
            errs.append("PERF_PROFILE_OF_ANOTHER_ENV")
        for r in prof["rows"]:
            if r["env_id"] != prof["env_id"]:
                errs.append(f"PERF_ROW_OTHER_ENV {r['N']}|{r['T']}|{r['strategy']}")
    # experience bundle seal
    braw = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    if hashlib.sha256(canon(braw)).hexdigest() != BUNDLE_SHA:
        errs.append("EXPERIENCE_BUNDLE_HASH (evaluation data mixed into the sealed store?)")
    if any("candidate" in str(s.get("id", "")).lower() for s in braw.get("sources", [])):
        errs.append("CANDIDATE_LISTED_AS_SOURCE")
    g100 = load(out / "gate100.json")["passed"] if (out / "gate100.json").exists() else False
    own = own_records(out)
    svcs = services(out)
    if not svcs and phase != "replay":
        errs.append("NO_SERVICES")
    groups = {}
    for f, s in svcs:
        tag = f"{f.parent.name}/{f.name}"
        senv = s.get("simulated_env") or env
        if s.get("simulated_env"):
            if own_env_id(senv) != senv["env_id"] or senv["env_id"] == env["env_id"]:
                errs.append(f"{tag}: SIMULATED_ENV_ID")
        elif s["env_id"] != env["env_id"]:
            errs.append(f"{tag}: SERVICE_ENV_ID_DIFFERS")
        cpu_ok = (senv["mpmath_version"], senv["mpmath_backend"]) in MPMATH and \
            senv["contracts"]["physics"] == PHYSICS and senv["contracts"]["numeric"] == NUMERIC
        if not cpu_ok:
            if s["passes"] or s["status"] != "REFUSED_UNVERIFIED_ENVIRONMENT":
                errs.append(f"{tag}: UNVERIFIED_ENV_NOT_REFUSED")
            continue
        sprof = prof if (prof and s.get("perf_profile_sha256") and senv["env_id"] == prof["env_id"]) else None
        if s.get("perf_profile_sha256") and sprof is None and not s.get("simulated_env"):
            errs.append(f"{tag}: PROFILE_USED_BUT_NOT_GIVEN_TO_CHECKER")
        req = {"N": s["N"], "T": s["T"]}
        start = s["start_decision"]["start"]
        sp = own_start(s["N"], s["T"], start, braw)
        if s["start_decision"]["start_p"] != sp:
            errs.append(f"{tag}: START_P {s['start_decision']['start_p']} != own {sp}")
        if s["start_decision"]["initial_state_digest"] != own_initial_digest(s["N"]):
            errs.append(f"{tag}: INITIAL_DIGEST")
        if s["start_decision"]["bundle_sha256"] != BUNDLE_SHA:
            errs.append(f"{tag}: BUNDLE_SHA_IN_DECISION")
        # P2 chain
        hist, tried = [], set()
        p_exp = sp
        if [pz["index"] for pz in s["passes"]] != list(range(len(s["passes"]))):
            errs.append(f"{tag}: PASS_INDICES")
        for pz in s["passes"]:
            if pz["requested_p"] != p_exp:
                errs.append(f"{tag}: P_SEQUENCE pass {pz['index']} p {pz['requested_p']} != own {p_exp}")
                break
            res = pz["attempts"][-1]["result"]
            _check_pass(tag, s, pz, senv, sprof, g100, own, errs)
            tried.add(pz["requested_p"])
            hist.append(pz)
            p_exp = own_next({"requested_p": pz["requested_p"], "outcome": pz["outcome"],
                              "completed_steps": pz["completed_steps"],
                              "endpoints_scaled": res.get("endpoints_scaled")}, s["T"], tried)
        if s["status"] in ("DECIDED", "STOP_DOMAIN_VIOLATED_PROVEN", "STOP_OUT_OF_RANGE") and p_exp is not None:
            errs.append(f"{tag}: FINAL_STATUS_BUT_P2_CONTINUES ({p_exp})")
        if s["status"] == "DECIDED" and (not s["passes"] or s["passes"][-1]["outcome"] != "DECIDED"):
            errs.append(f"{tag}: STATUS_DECIDED_WITHOUT_DECIDED_PASS")
        if not s.get("case"):
            groups.setdefault((s["request_id"], s["label"]), []).append((s.get("repeat"), tag, s))
        _ = req
    # repeat identity and strategy identity at the same (N, T, p)
    by_key = {}
    for (rid, lab), lst in groups.items():
        ref = None
        for rep, tag, s in sorted(lst, key=lambda x: x[0] or 0):
            sig = [(pz["requested_p"], *[pz.get(k) for k in FIELDS]) for pz in s["passes"]]
            if ref is None:
                ref = sig
            elif sig != ref:
                errs.append(f"{tag}: REPEAT_DIFFERS_FROM_REPEAT_1")
            for pz in s["passes"]:
                k = (s["N"], s["T"], pz["requested_p"])
                v = tuple(pz.get(x) for x in FIELDS)
                if by_key.setdefault(k, v) != v:
                    errs.append(f"{tag}: SAME_NTP_DIFFERENT_RESULT {k}")
        if expect_repeats and len(lst) != len(expect_repeats) and lab != "ADAPTIVE_CPU":
            errs.append(f"{rid}/{lab}: MISSING_REPEAT ({len(lst)})")
    # GPU worker log vs ledgers
    logs = []
    for f in sorted((out / "gpu_worker_log").glob("r*.json")):
        logs += load(f)
    ev = {}
    for _, s in svcs:
        for e in s["events"]:
            if e["event"] in ("DEVICE_ERROR", "DEVICE_REFUSAL"):
                ev[s["run_id"]] = ev.get(s["run_id"], 0) + 1
    for lg in logs:
        st = lg.get("status") or ""
        if (st == "DEVICE_ERROR" or st.startswith("REFUSED")) and not lg["request_id"].startswith("forced_"):
            rid = lg["request_id"]
            if ev.get(rid, 0) <= 0:
                errs.append(f"GPU_EVENT_MISSING_FROM_LEDGER {rid} {st}")
            else:
                ev[rid] -= 1
    # forced GPU cases
    fg = out / "cases" / "forced_gpu.json"
    if fg.exists():
        for c in load(fg):
            if not c["adapter_violations"] or c["executed"]:
                errs.append(f"FORCED_GPU_NOT_REFUSED {c['id']}")
    verdict = "EVIDENCE OK" if not errs else "EVIDENCE FAILED"
    return {"verdict": verdict, "errors": errs, "notes": notes, "n_services": len(svcs), "replayed_keys": len(own),
            "gate100_passed": g100, "phase": phase}


def _check_pass(tag, s, pz, env, prof, g100, own, errs):
    N, T, p = s["N"], s["T"], pz["requested_p"]
    lab = s.get("label", s["strategy"])
    att = pz["attempts"]
    final = att[-1]
    res, plan = final["result"], final["plan"]
    for a in att:
        if a.get("result") and a["plan"]["backend"] == "GPU_HYBRID" and \
                a["result"].get("status_class") not in ("DEVICE_REFUSAL", "DEVICE_ERROR"):
            if not own_gpu_ok(N, T, p, env, g100):
                errs.append(f"{tag}: GPU_PASS_OUTSIDE_PROFILE p {p}")
    # choice
    goal = s.get("goal")
    first = att[0]["plan"]
    if s["strategy"] == "ADAPTIVE":
        b, w = own_choice(N, T, p, goal, env, prof, g100)
        if (first["backend"], first["worker_count"]) != (b, w):
            errs.append(f"{tag}: CHOICE pass {pz['index']} {first['backend']}/{first['worker_count']} != own {b}/{w}")
    elif s["strategy"] == "FIXED_SERIAL" and first["backend"] != "CPU_SERIAL":
        errs.append(f"{tag}: FIXED_SERIAL_BACKEND")
    elif s["strategy"] == "FIXED_W6" and (first["backend"], first["worker_count"]) != ("CPU_PARALLEL", 6):
        errs.append(f"{tag}: FIXED_W6_BACKEND")
    if len(att) > 1:
        ev = [e for e in s["events"] if e["pass"] == pz["index"]]
        if not ev or final["plan"]["backend"] != "CPU_SERIAL":
            errs.append(f"{tag}: FALLBACK_WITHOUT_EVENT pass {pz['index']}")
    # placement and executed plan
    if plan["backend"] in ("CPU_SERIAL", "CPU_PARALLEL"):
        place = own_placements(env)
        kind = "SERIAL" if plan["backend"] == "CPU_SERIAL" else f"W{plan['worker_count']}"
        if kind not in place or [plan["main_cpu"], plan["worker_cpus"]] != list(place[kind]):
            errs.append(f"{tag}: PLACEMENT pass {pz['index']} {kind}")
        r = res.get("runner") or {}
        rp = r.get("plan") or {}
        if [rp.get("backend"), rp.get("worker_count"), rp.get("main_cpu"), rp.get("worker_cpus"), rp.get("precision")] \
                != [plan["backend"], plan["worker_count"], plan["main_cpu"], plan["worker_cpus"], p]:
            errs.append(f"{tag}: EXECUTED_PLAN_DIFFERS pass {pz['index']}")
        if plan["backend"] == "CPU_SERIAL" and r.get("affinity") != [plan["main_cpu"]]:
            errs.append(f"{tag}: SERIAL_AFFINITY pass {pz['index']}")
        if plan["backend"] == "CPU_PARALLEL" and (r.get("main_affinity") != [plan["main_cpu"]] or
                                                 r.get("worker_affinity") != [[c] for c in plan["worker_cpus"]]):
            errs.append(f"{tag}: PARALLEL_AFFINITY pass {pz['index']}")
        cores = [env["core_of_cpu"].get(str(c)) for c in plan["worker_cpus"]]
        if len(set(cores)) != len(cores) or any(c not in env["allowed_cpus"] for c in [plan["main_cpu"],
                                                                                         *plan["worker_cpus"]]):
            errs.append(f"{tag}: PLACEMENT_CORES pass {pz['index']}")
        if res.get("initial_sha256") != own_initial_digest(N):
            errs.append(f"{tag}: CPU_START_NOT_ORIGINAL pass {pz['index']}")
        if res.get("effective_p") != p or r.get("effective_p") != p:
            errs.append(f"{tag}: CPU_EFFECTIVE_P pass {pz['index']}")
    elif plan["backend"] == "GPU_HYBRID":
        g = res.get("gpu") or {}
        if g.get("device_p") != p or g.get("device_p_echo") != [p] or res.get("effective_p") != p:
            errs.append(f"{tag}: GPU_PRECISION pass {pz['index']} device {g.get('device_p')} echo "
                        f"{g.get('device_p_echo')} req {p}")
        q0, p0 = own_echo(N, p)
        if g.get("echo_q0") is not None and (g["echo_q0"] != q0 or g["echo_p0"] != p0):
            errs.append(f"{tag}: GPU_START_NOT_ORIGINAL pass {pz['index']}")
        if T == 1000 and g.get("echo_q0") is None:
            errs.append(f"{tag}: GPU_START_NOT_RECORDED pass {pz['index']}")
        exp_ev = (pz["completed_steps"] or 0) + 1 if not pz.get("stop") else (pz["stop_step"] or 0) + 1
        if g.get("force_evals") != exp_ev:
            errs.append(f"{tag}: GPU_FORCE_EVALS pass {pz['index']} {g.get('force_evals')} != {exp_ev}")
    # results
    o = own.get((N, T, p))
    if o is None:
        errs.append(f"{tag}: NOT_REPLAYED {(N, T, p)}")
    else:
        for k in FIELDS:
            if pz.get(k) != o.get(k):
                errs.append(f"{tag}: RESULT_{k.upper()} pass {pz['index']} p {p} {lab}")
                break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--phase", default="final", choices=("replay", "gate", "final"))
    ap.add_argument("--profile")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--expect-repeats")
    a = ap.parse_args()
    replay(a.out, a.workers)                                   # only the (N, T, p) not replayed yet
    if a.phase == "replay":
        return
    reps = None
    if a.expect_repeats:
        x, _, y = a.expect_repeats.partition("-")
        reps = list(range(int(x), int(y or x) + 1))
    v = check(a.out, a.profile, phase=a.phase, expect_repeats=reps)
    Path(a.out, f"checker_verdict_{a.phase}.json").write_text(json.dumps(v, indent=1), encoding="utf-8")
    print(v["verdict"], len(v["errors"]), "errors", flush=True)
    for e in v["errors"][:40]:
        print("  ", e, flush=True)
    sys.exit(0 if v["verdict"] == "EVIDENCE OK" else 1)


if __name__ == "__main__":
    main()
