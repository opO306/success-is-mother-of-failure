"""Independent checker of GPU_SHORT_TRAJECTORY_V1 (protocol 'checker'). Imports none of the trajectory runner, the
one-step runner, pv_host, the campaigns or any GPU code. Its own literal KDK loop with mpmath iv objects:

    F = forces(q); for each step: p = p + F; q = q + p * CDT; F = literal E2 forces(q); p = p + F

(frozen RwForce, K.domain, K.H, K.CDT, K.endpoints_key, K.decide), its own digest code, its own initial states (FCC_N
lift, the N12 / N16 window start = its own state 500 after running 500 steps, the probe constructions from the protocol rule).

    python -m experiments.gpu_short_trajectory_v1.checker DIR [--phase s10|s100] [--workers W]
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

from mpmath import iv

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/active/gpu_short_trajectory_v1/bundle.json.gz"
BUNDLE_SHA_FILE = ROOT / "docs/active/gpu_short_trajectory_v1/bundle.json.gz.sha256"
EV = "rw:R1+R2"
CHECKS = {10: (0, 1, 2, 5, 10), 100: (0, 1, 2, 5, 10, 20, 50, 100)}
STAGES = ("F_s", "p_half", "q1", "F1", "p1")
LABEL = {"F_s": "F", "p_half": "P", "q1": "Q", "F1": "F", "p1": "P"}
_FORCE = {}


# ---------------------------------------------------------------------------
# encoding and digests (the checker's own implementation of protocol 'digests')
# ---------------------------------------------------------------------------
def _end(e):
    s, h, x, bc = e
    m = int(h, 16)
    return (0, 0, 0, 0) if m == 0 else (s, m, x, bc)


def _rows(rows):
    return None if rows is None else [[(_end(e[0]), _end(e[1])) for e in r] for r in rows]


def _txt(m):
    s, man, e, bc = m
    return "0.0.0.0" if not man else f"{s}.{man:x}.{e}.{bc}"


def vtext(label, X):
    """X: rows of raw (lo, hi) endpoint tuples."""
    parts = []
    for r in X:
        for lo_hi in r:
            parts.append(_txt(lo_hi[0]))
            parts.append(_txt(lo_hi[1]))
    return f"{label}:{len(X)}:" + ",".join(parts)


def vdig(label, X):
    return hashlib.sha256(vtext(label, X).encode()).hexdigest()


def sdig(q, pm):
    return hashlib.sha256((vtext("Q", q) + "|" + vtext("P", pm)).encode()).hexdigest()


def _norm(X):
    return [[tuple((0, 0, 0, 0) if not e[1] else tuple(e) for e in x) for x in r] for r in X]


# ---------------------------------------------------------------------------
# the literal CPU trajectory
# ---------------------------------------------------------------------------
def _force(p):
    if p not in _FORCE:
        from experiments.rewrite_pilot_a3 import adapter as AD
        from experiments.rewrite_pilot_a3 import rwforce as RW
        AD.prepare(EV)
        iv.prec = p
        _FORCE[p] = RW.RwForce(AD._PLAN)
    return _FORCE[p]


def my_forces(q, p):
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    force = _force(p)
    iv.prec = p
    h, zero = LI.c(K.H), LI.c(Fraction(0))
    n = len(q)
    F = [[zero] * 3 for _ in range(n)]
    pid = 0
    for i in range(n):
        for j in range(i + 1, n):
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
            st = K.domain(r2)
            if st != K.PROVEN:
                return "DOMAIN_STOP_" + st, pid, None
            try:
                g = force(r2)
            except K.DomainStop as e:
                return "DOMAIN_STOP_" + e.kind, pid, None
            for k in range(3):
                t = (h * g) * d[k]
                F[j][k] = F[j][k] + t
                F[i][k] = F[i][k] - t
            pid += 1
    return "OK", None, F


def _raw(X):
    return _norm([[x._mpi_ for x in r] for r in X])


def _read(q, pm):
    from exact_expression_gate_v1 import common as K
    qv, pv = [x for r in q for x in r], [x for r in pm for x in r]
    key = K.endpoints_key(qv + pv)
    try:
        cells = K.decide(qv, pv)
        d = "UNDECIDED_AT_PRECISION" if cells is None else cells
    except K.OutOfRange:
        d = "OUT_OF_RANGE"
    return {"decide": d, "endpoints_key": key}


def my_traj(q0, p0, p, last, start=0, T=100, keep=()):
    """Literal KDK from (q0, p0) (iv objects) for `last` steps; records steps start .. start + T - 1."""
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    iv.prec = p
    cdt = LI.c(K.CDT)
    q, pm = q0, p0
    out = {"steps": [], "full": {}, "read": {}, "stop": None, "completed": 0, "kept": {}, "start_state": None}
    st, pid, F = my_forces(q, p)
    if st != "OK":
        out["stop"] = {"status": st, "stop_state": 0, "stop_pair": pid}
        return out
    checks = CHECKS[100] if T > 10 else CHECKS[10]
    if start == 0:
        out["full"][0] = {"q": _raw(q), "p_mom": _raw(pm), "F": _raw(F)}
    for s in range(last):
        ph = [[pm[a][k] + F[a][k] for k in range(3)] for a in range(len(q))]
        q1 = [[q[a][k] + ph[a][k] * cdt for k in range(3)] for a in range(len(q))]
        inside = start <= s < start + T
        rec = {"s": s - start, "F_s": vdig("F", _raw(F)), "p_half": vdig("P", _raw(ph)), "q1": vdig("Q", _raw(q1))} \
            if inside else None
        st, pid, F1 = my_forces(q1, p)
        if st != "OK":
            if inside:
                out["steps"].append(rec)
            out["stop"] = {"status": st, "stop_state": s + 1 - start, "stop_pair": pid}
            return out
        p1 = [[ph[a][k] + F1[a][k] for k in range(3)] for a in range(len(q))]
        if inside:
            rq, rp, rf = _raw(q1), _raw(p1), _raw(F1)
            rec.update(F1=vdig("F", rf), p1=vdig("P", rp), state=sdig(rq, rp), force=vdig("F", rf))
            out["steps"].append(rec)
            if s - start in keep:
                out["kept"][s - start] = {"F_s": _raw(F), "p_half": _raw(ph), "q1": rq, "F1": rf, "p1": rp}
        out["completed"] = s + 1 - start
        rel = s + 1 - start
        if rel in checks:
            out["full"][rel] = {"q": _raw(q1), "p_mom": _raw(p1), "F": _raw(F1)}
        if rel in (10, T) and rel >= 1:
            out["read"][rel] = _read(q1, p1)
        q, pm, F = q1, p1, F1
        if rel == T:
            break
    return out


# ---------------------------------------------------------------------------
# the checker's own initial states
# ---------------------------------------------------------------------------
def own_initial(traj, p):
    """(q0, p0) as iv objects and the number of steps to run before the window starts."""
    import exact_expression_gate_v0.lang_iv as LI
    from experiments.multiatom_parallel_v1 import scenarios as SC
    iv.prec = p
    L = LI.c
    Z = Fraction(0)
    if traj["kind"] == "MAIN":
        q0, p0 = SC.initial(traj["N"])
        return [[L(x) for x in r] for r in q0], [[L(x) for x in r] for r in p0], traj["start_step"]
    role, m = traj["role"], traj["search_m"]
    if role.startswith("P3_"):
        x1 = L(Fraction(1)) if role == "P3_F0_VIOLATED" else L(Fraction(6)) if role == "P3_MULTI_VIOLATED" else             iv.mpf(["6", "6.5"])
        q = [[L(Z)] * 3, [x1, L(Z), L(Z)], [L(Z), L(Fraction(20)), L(Z)]]
        pm = [[L(Z)] * 3, [L(Fraction(-m)), L(Z), L(Z)], [L(Z)] * 3]
        return q, pm, 0
    sites = SC.fcc_sites(12)
    i = 3
    j = next(j for j in range(i + 1, 12) if sum((a - b) ** 2 for a, b in zip(sites[i], sites[j])) == 2)
    q0, p0 = SC.initial(12)
    p0 = [list(r) for r in p0]
    p0[j] = [p0[j][k] + m * (sites[i][k] - sites[j][k]) for k in range(3)]
    return [[L(x) for x in r] for r in q0], [[L(x) for x in r] for r in p0], 0


_OWN = {}


def _own_task(args):
    traj, T, keep = args
    key = (traj["id"], T, tuple(keep))
    if key not in _OWN:
        p = traj["p"]
        q0, p0, start = own_initial(traj, p)
        o = my_traj(q0, p0, p, start + T, start=start, T=T, keep=set(keep))
        o["initial"] = {"q": _raw(q0), "p_mom": _raw(p0)}
        _OWN[key] = (traj["id"], T, o)
    return _OWN[key]


# ---------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------
def _first_diff(X, Y):
    for a, (rx, ry) in enumerate(zip(X, Y)):
        for k, (x, y) in enumerate(zip(rx, ry)):
            for e, end in enumerate(("lower", "upper")):
                if x[e] != y[e]:
                    return {"atom": a, "component": "xyz"[k], "end": end, "cpu": list(x[e]), "gpu": list(y[e])}
    return None


def check(d, bundle_path=BUNDLE, bundle_sha_file=BUNDLE_SHA_FILE, phase="s100", expect_complete=True, workers=1):
    d = Path(d)
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    raw = Path(bundle_path).read_bytes()
    sealed = Path(bundle_sha_file).read_text(encoding="utf-8").strip()
    ok("bundle_hash_matches_sealed_file", hashlib.sha256(raw).hexdigest() == sealed)
    b = json.loads(gzip.decompress(raw))
    trajs = {t["id"]: t for t in b["main"] + b["probes"]}
    for t in b["main"]:
        if t["tie"] is not None:
            ok("bundle_replica_equals_verified_reference", t["tie"]["equals_reference"], t["id"])
    envf = d / "env.json"
    if envf.exists():
        env = json.loads(envf.read_text(encoding="utf-8"))
        ok("seal_clean", env["status_porcelain"] == "" and not env["sealed_sources_dirty"], env["status_porcelain"][:200])
        ok("env_bundle_sha", env["bundle_sha256"] == sealed)

    runs = [json.loads(gzip.decompress(f.read_bytes())) | {"_file": f.name} for f in sorted((d / "runs").glob("*.json.gz"))]
    need = {}
    for r in runs:
        if r["traj_id"] in trajs:
            need[r["traj_id"]] = max(need.get(r["traj_id"], 0), r["T"])
    # the first divergence needs the checker's vectors at the dumped steps
    keep = {}
    for r in runs:
        if r.get("dump") and r["traj_id"] in trajs:
            keep.setdefault(r["traj_id"], set()).add(r["dump"]["s"])
    tasks = [(trajs[i], T, sorted(keep.get(i, ()))) for i, T in sorted(need.items())]
    if workers > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(min(workers, len(tasks))) as pool:
            res = list(pool.map(_own_task, tasks))
    else:
        res = [_own_task(t) for t in tasks]
    own = {i: o for i, T, o in res}

    # own trajectory vs the bundle (the replica of stream.run) and the bundle's initial states
    for i, o in own.items():
        t = trajs[i]
        T = need[i]
        if t["start_step"]:
            s0 = o["full"].get(0)
            ok("own_start_state_equals_bundle_q0_p0", s0 is not None and (s0["q"], s0["p_mom"]) ==
               (_rows(t["q0"]), _rows(t["p0"])), i)
        else:
            ok("own_initial_equals_bundle_q0_p0", (o["initial"]["q"], o["initial"]["p_mom"]) ==
               (_rows(t["q0"]), _rows(t["p0"])), i)
        ok("own_steps_equal_bundle_replica", o["steps"][:T] == t["steps"][:T], i)
        ok("own_outcome_equals_bundle", (o["stop"] or {"status": "OK", "stop_state": None, "stop_pair": None})
           == t["cpu_outcome"], f"{i}: own {o['stop']} bundle {t['cpu_outcome']}")
        for rel, full in o["full"].items():
            if str(rel) in t["full"]:
                ok("own_full_equals_bundle", {k: full[k] for k in ("q", "p_mom", "F")} ==
                   {k: _rows(t["full"][str(rel)][k]) for k in ("q", "p_mom", "F")}, f"{i} rel {rel}")
        for rel, rd in o["read"].items():
            if str(rel) in t["read"]:
                ok("own_read_equals_bundle", rd == t["read"][str(rel)], f"{i} rel {rel}")

    stats = {"runs": 0, "traj_exact": 0, "traj_mismatch": 0, "stops_exact": 0, "stops_mismatch": 0, "refused": 0,
             "steps_compared": 0, "steps_mismatch": 0}
    first_div, layouts, prefix = [], {}, {}
    for r in runs:
        f = r["_file"]
        if r["kind"] == "REFUSAL":
            stats["refused"] += 1
            ok("refusal_run_refused", r["status"] == "REFUSED_DEVICE_PRECISION" and r["steps"] == [] and
               r["full"] == {} and r["read"] is None, f)
            continue
        t = trajs.get(r["traj_id"])
        ok("run_known", t is not None, f)
        if t is None:
            continue
        stats["runs"] += 1
        T = r["T"]
        ok("run_settings_clean", r["fault"] == 0 and r["pvfault"] == 0 and r["work_limbs"] == 16 and
           r["upload_p"] == t["p"] and r["p"] == t["p"] and r["N"] == t["N"], f)
        ok("C0_runner_inputs_equal_bundle", (_rows(r["echo_q0"]), _rows(r["echo_p0"])) == (_rows(t["q0"]), _rows(t["p0"])), f)
        if r["status"].startswith("REFUSED"):
            stats["refused"] += 1
            ok("refused_without_state", r["read"] is None and not r.get("final"), f)
            continue
        o = own[t["id"]]
        want = o["stop"] or {"status": "OK", "stop_state": None, "stop_pair": None}
        got = {"status": r["status"], "stop_state": r["stop_state"], "stop_pair": r["stop_pair"]}
        ok("stop_equal", got == want, f"{f}: gpu {got} cpu {want}")
        idx = [x["s"] for x in r["steps"]]
        ok("step_indices_contiguous", idx == list(range(len(idx))), f)
        osteps = o["steps"][:T] if want["status"] == "OK" else o["steps"]
        ok("step_count_equal", len(r["steps"]) == len(osteps), f"{f}: {len(r['steps'])} vs {len(osteps)}")
        mism = None
        for a, (x, y) in enumerate(zip(osteps, r["steps"])):
            stats["steps_compared"] += 1
            bad = [st for st in STAGES + ("state", "force") if x.get(st) != y.get(st)]
            if bad:
                stats["steps_mismatch"] += 1
                if mism is None:
                    mism = (a, [st for st in STAGES if st in bad] or bad)
        ok("per_step_digests_equal", mism is None and len(r["steps"]) == len(osteps), f"{f}: first {mism}")
        if want["status"] != "OK" and r["steps"]:
            ok("partial_step_after_stop_has_no_F1_p1", "F1" not in r["steps"][-1] or r["steps"][-1].get("F1") is None, f)
        ev = (want["stop_state"] + 1) if want["status"] != "OK" else T + 1
        ok("force_evaluations_reuse", r["force_evals"] == ev, f"{f}: {r['force_evals']} vs {ev}")
        ok("executor_persistent_in_trajectory", r["uploads_in_traj"] == 0 and r["allocs_in_traj"] == 0, f)
        ok("completed_steps_equal", r["completed_steps"] == (T if want["status"] == "OK" else max(want["stop_state"] - 1, 0)),
           f"{f}: {r['completed_steps']}")
        # full checkpoints: equal to the checker's, and the recorded digests match the recorded endpoints
        for rel in CHECKS[T]:
            if want["status"] != "OK" and rel >= want["stop_state"]:
                continue
            g = r["full"].get(str(rel))
            ok("checkpoint_present", g is not None, f"{f} rel {rel}")
            if g is None:
                continue
            gq, gp, gF = _rows(g["q"]), _rows(g["p_mom"]), _rows(g["F"])
            c = o["full"].get(rel)
            ok("checkpoint_endpoints_equal", c is not None and (gq, gp, gF) == (c["q"], c["p_mom"], c["F"]),
               f"{f} rel {rel}")
            if rel == 0:
                ok("digest_self_consistent", r["steps"] and vdig("F", gF) == r["steps"][0]["F_s"], f"{f} rel 0")
            elif rel - 1 < len(r["steps"]):
                y = r["steps"][rel - 1]
                ok("digest_self_consistent", (vdig("Q", gq), vdig("P", gp), vdig("F", gF), sdig(gq, gp)) ==
                   (y["q1"], y["p1"], y["F1"], y["state"]), f"{f} rel {rel}")
        if want["status"] == "OK":
            ok("final_read_equal", r["read"] == o["read"].get(T), f"{f}: {str(r['read'])[:80]} vs {str(o['read'].get(T))[:80]}")
        good = mism is None and got == want and len(r["steps"]) == len(osteps) and r["force_evals"] == ev and \
            (want["status"] != "OK" or r["read"] == o["read"].get(T))
        if want["status"] == "OK":
            stats["traj_exact" if good else "traj_mismatch"] += 1
        else:
            stats["stops_exact" if good else "stops_mismatch"] += 1
        if mism is not None:
            fd = {"file": f, "traj": t["id"], "T": T, "first_divergence_step": mism[0], "first_divergence_stage": mism[1][0]}
            dump = r.get("dump")
            kept = o["kept"].get(mism[0])
            if dump and dump["s"] == mism[0] and kept:
                st = mism[1][0]
                if st in STAGES and dump.get(st) is not None:
                    diff = _first_diff(kept[st], _rows(dump[st]))
                    fd.update(diff or {"note": "endpoints equal - digest serialization differs"})
            first_div.append(fd)
        view = json.dumps({"steps": r["steps"], "status": got, "read": r["read"],
                           "full": r["full"]}, sort_keys=True)
        layouts.setdefault((t["id"], T), []).append((r["block"], r["grid"], view))
        if r["block"] == 32:
            prefix[(t["id"], T)] = r["steps"]
    for key, runs_ in layouts.items():
        ok("layouts_identical", len({v for _, _, v in runs_}) == 1, f"{key}: {len(runs_)} runs")
    for (i, T), steps in prefix.items():
        if T == 100 and (i, 10) in prefix:
            ok("S100_prefix_equals_S10", steps[:10] == prefix[(i, 10)], i)
    if expect_complete:
        for t in b["main"]:
            ok("S10_layouts_complete", sorted(x[0] for x in layouts.get((t["id"], 10), [])) == [32, 64, 128, 256], t["id"])
            if phase == "s100":
                ok("S100_present", (t["id"], 100) in layouts, t["id"])
        for t in b["probes"]:
            ok("probe_present", (t["id"], 10) in layouts, t["id"])
        ok("refusal_run_present", any(r["kind"] == "REFUSAL" for r in runs))
    bad = sum(v[1] for v in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "phase": phase, "counts": counts, "issues": issues[:80],
            "stats": stats, "first_divergence": first_div[:40]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--phase", default="s100")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    res = check(a.dir, phase=a.phase, workers=a.workers)
    Path(a.dir, f"checker_verdict_{a.phase}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], {k: v for k, v in res["counts"].items() if v[1]}, res["issues"][:6], res["stats"])
    sys.exit(0 if res["verdict"] == "EVIDENCE OK" else 1)


if __name__ == "__main__":
    main()
