"""Build the sealed GPU_SHORT_TRAJECTORY_V1 bundle (protocol 'bundle'). CPU only, before any trajectory runner code.

A runtime replica of exact_expression_gate_v1.stream.run (its own source + two observer lines: after the drift and
after the second kick) records per-step digests, full states at the checkpoint indices and the final reads. Runs tied
to a verified V2 Vast serial reference must end equal to it. Probes: multi-step domain stops found by a small search.
The replica's input lift also passes an already-interval input through unchanged (the P3_MULTI_UNPROVEN probe's
interval position); every other value is lifted exactly as stream.run does.

    python -m experiments.gpu_short_trajectory_v1.samples OUT.json.gz
"""

from __future__ import annotations

import gzip
import hashlib
import inspect
import json
import sys
import time
import types
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as Q
from pathlib import Path

from mpmath import iv

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "docs/active/experience_start_p_v2/vast_run/records.json.gz"
EV = "rw:R1+R2"
IDENTITY_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key", "initial_sha256")
DRIFT_ANCHOR = '            q = [[add(q[a][k], mul(p[a][k], cdt)) for k in range(3)] for a in range(n)]\n'
KICK2_ANCHOR = '            out["completed_steps"] = s\n'
CHECK_T10 = (0, 1, 2, 5, 10)
CHECK_T100 = (0, 1, 2, 5, 10, 20, 50, 100)
WINDOW = 100
# (N, p, last step run, starts, verified reference or None)
MAIN = ((12, 163, 1000, (0, 500), "N12_T1000__p163"), (16, 163, 1000, (0, 500), "N16_T1000__p163"),
        (40, 109, 100, (0,), "N40_T100__p109"), (64, 109, 100, (0,), "N64_T100__p109"),
        (128, 109, 100, (0,), None), (64, 163, 100, (0,), None))


# ---------------------------------------------------------------------------
# digests (protocol 'digests'; the sampler's own implementation)
# ---------------------------------------------------------------------------
def _et(m):
    s, man, e, bc = m
    return "0.0.0.0" if not man else f"{s}.{man:x}.{e}.{bc}"


def text(label, X):
    return f"{label}:{len(X)}:" + ",".join(_et(end) for r in X for x in r for end in x._mpi_)


def dg(label, X):
    return hashlib.sha256(text(label, X).encode()).hexdigest()


def state_dg(q, pm):
    return hashlib.sha256((text("Q", q) + "|" + text("P", pm)).encode()).hexdigest()


def enc(X):
    from experiments.gpu_force_feasibility_v1.dyadic import encode_iv
    return [[encode_iv(x._mpi_) for x in r] for r in X]


# ---------------------------------------------------------------------------
# replica
# ---------------------------------------------------------------------------
def make_force(p):
    from experiments.rewrite_pilot_a3 import adapter as AD
    from experiments.rewrite_pilot_a3 import rwforce as RW
    AD.prepare(EV)
    iv.prec = p
    return RW.RwForce(AD._PLAN)


def replica_run(force, obs_a, obs_b):
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import stream
    src = inspect.getsource(stream.run)
    if src.count(DRIFT_ANCHOR) != 1 or src.count(KICK2_ANCHOR) != 1:
        raise SystemExit("stream.run source changed: observer anchors not unique")
    src = src.replace(DRIFT_ANCHOR, DRIFT_ANCHOR + '            _OBS_A(s, q, p, F)\n')
    src = src.replace(KICK2_ANCHOR, '            _OBS_B(s, q, p, F)\n' + KICK2_ANCHOR)
    g = dict(vars(stream))

    def ops(exact):
        add, sub, mul, lift = stream._ops(exact)
        return add, sub, mul, (lambda x: x if hasattr(x, "_mpi_") else lift(x))
    g.update(LI=types.SimpleNamespace(c=LI.c, G_of_R2=force), _OBS_A=obs_a, _OBS_B=obs_b, _ops=ops)
    exec(compile(src, "<stream.run replica>", "exec"), g)
    return g["run"]


def reference(name):
    files = json.loads(gzip.open(REF).read())["files"]
    return json.loads(files[f"reference/{name}.json"])


def first_stop_pair(q, force):
    """The first non-PROVEN canonical pair at q (sampler-side literal loop), or None."""
    from exact_expression_gate_v1 import common as K
    n = len(q)
    pid = 0
    for i in range(n):
        for j in range(i + 1, n):
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
            st = K.domain(r2)
            if st != K.PROVEN:
                return st, pid
            try:
                force(r2)
            except K.DomainStop as e:
                return e.kind, pid
            pid += 1
    return None


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


def record(N, p, last, starts, q0, p0, force, checks=CHECK_T100, reads=(10, 100)):
    """One replica run from (q0, p0) (exact Fractions or intervals) to `last`; per-start records."""
    import exact_expression_gate_v0.lang_iv as LI
    iv.prec = p
    lift = (lambda x: x if hasattr(x, "_mpi_") else LI.c(x))
    Lq, Lp = [[lift(x) for x in r] for r in q0], [[lift(x) for x in r] for r in p0]
    rec = {st: {"steps": {}, "full": {}, "read": {}} for st in starts}
    last_q = {"q": Lq, "state": 0}

    def obs_a(s, q, pm, F):
        t = s - 1
        last_q.update(q=q, state=s)
        if s == 1 and 0 in starts:
            rec[0]["full"][0] = {"q": enc(Lq), "p_mom": enc(Lp), "F": enc(F)}
        for st in starts:
            if st <= t < st + WINDOW:
                rec[st]["steps"][t - st] = {"s": t - st, "F_s": dg("F", F), "p_half": dg("P", pm), "q1": dg("Q", q)}

    def obs_b(s, q, pm, F):
        t = s - 1
        for st in starts:
            if st <= t < st + WINDOW:
                rec[st]["steps"][t - st].update(F1=dg("F", F), p1=dg("P", pm), state=state_dg(q, pm), force=dg("F", F))
            rel = s - st
            if rel in checks:
                rec[st]["full"][rel] = {"q": enc(q), "p_mom": enc(pm), "F": enc(F)}
            if rel in reads:
                rec[st]["read"][rel] = _read(q, pm)
    run = replica_run(force, obs_a, obs_b)
    out = run(q0, p0, p, last, {last}, exact=False)
    stop = None
    if out["stop"] in ("VIOLATED", "UNPROVEN"):
        k = out["stop_step"]
        qk = Lq if k == 0 else last_q["q"]
        if k != 0 and last_q["state"] != k:
            raise SystemExit("stop state and the last drift observer disagree")
        kind, pid = first_stop_pair(qk, force)
        if kind != out["stop"]:
            raise SystemExit(f"stop kind {out['stop']} but the first stopping pair says {kind}")
        stop = {"status": "DOMAIN_STOP_" + kind, "stop_state": k, "stop_pair": pid}
    return out, rec, stop


def _steps_list(r):
    return [r["steps"][i] for i in sorted(r["steps"])]


def main_task(args):
    from experiments.multiatom_parallel_v1 import scenarios as SC
    from experiments.multiatom_parallel_v1.run import _readout, initial_digest
    N, p, last, starts, refname = args
    t0 = time.perf_counter()
    q0, p0 = SC.initial(N)
    out, rec, stop = record(N, p, last, starts, q0, p0, make_force(p))
    if stop is not None or out["completed_steps"] != last:
        raise SystemExit(f"N{N} p{p}: main trajectory stopped: {out}")
    tie = None
    if refname:
        o = _readout({**out, "read": out["read"].get(last)}, N)
        o["initial_sha256"] = initial_digest(q0, p0)
        ref = reference(refname)
        tie = {"reference": refname, "equals_reference": all(o[k] == ref[k] for k in IDENTITY_KEYS),
               "identity": {k: o[k] for k in IDENTITY_KEYS}}
        if not tie["equals_reference"]:
            raise SystemExit(f"N{N} p{p}: replica differs from the verified reference {refname}")
    trajs = []
    for st in starts:
        r = rec[st]
        if sorted(r["steps"]) != list(range(WINDOW)) or sorted(r["full"]) != list(CHECK_T100) or \
                any(len(x) != 8 for x in r["steps"].values()):
            raise SystemExit(f"N{N} p{p} s{st}: incomplete record")
        trajs.append({"id": f"N{N}_p{p}_s{st}", "kind": "MAIN", "N": N, "p": p, "start_step": st, "T": WINDOW,
                      "replica_last_step": last, "tie": tie, "q0": r["full"][0]["q"], "p0": r["full"][0]["p_mom"],
                      "steps": _steps_list(r), "full": {str(k): v for k, v in sorted(r["full"].items())},
                      "read": {str(k): v for k, v in sorted(r["read"].items())},
                      "cpu_outcome": {"status": "OK", "stop_state": None, "stop_pair": None}})
    print(json.dumps({"N": N, "p": p, "last": last, "tie": tie and tie["equals_reference"],
                      "wall_s": round(time.perf_counter() - t0, 1)}), flush=True)
    return trajs


# ---------------------------------------------------------------------------
# probes (T = 10)
# ---------------------------------------------------------------------------
def _probe(role, N, p, q0, p0, force, m):
    out, rec, stop = record(N, p, 10, (0,), q0, p0, force, checks=CHECK_T10, reads=(10,))
    r = rec[0]
    return {"id": f"{role}_p{p}", "kind": "PROBE", "role": role, "N": N, "p": p, "start_step": 0, "T": 10,
            "search_m": m, "q0": enc([[x if hasattr(x, "_mpi_") else _lift(x) for x in row] for row in q0]),
            "p0": enc([[_lift(x) for x in row] for row in p0]), "steps": _steps_list(r),
            "full": {str(k): v for k, v in sorted(r["full"].items())},
            "read": {str(k): v for k, v in sorted(r["read"].items())},
            "cpu_outcome": stop or {"status": "OK", "stop_state": None, "stop_pair": None},
            "completed_steps": out["completed_steps"]}


def _lift(x):
    import exact_expression_gate_v0.lang_iv as LI
    return LI.c(x)


def probe_task(args):
    kind, p = args
    force = make_force(p)
    iv.prec = p
    t0 = time.perf_counter()
    out = []
    if kind == "N3":
        def n3(x1, m):
            z = Q(0)
            return [[z, z, z], [x1, z, z], [z, Q(20), z]], [[z] * 3, [Q(-m), z, z], [z] * 3]
        q, pm = n3(Q(1), 0)
        out.append(_probe("P3_F0_VIOLATED", 3, p, q, pm, force, 0))
        for role, x1 in (("P3_MULTI_VIOLATED", Q(6)), ("P3_MULTI_UNPROVEN", None)):
            want = role.split("_")[-1]
            for m in range(0, 20001, 50):
                iv.prec = p
                q, pm = n3(iv.mpf(["6", "6.5"]) if x1 is None else x1, m)
                o = _probe(role, 3, p, q, pm, force, m)
                c = o["cpu_outcome"]
                if c["status"] == "DOMAIN_STOP_" + want and 4 <= c["stop_state"] <= 7:
                    out.append(o)
                    break
            else:
                raise SystemExit(f"{role} p{p}: no momentum found")
    else:
        from experiments.multiatom_parallel_v1 import scenarios as SC
        sites = SC.fcc_sites(12)
        i = 3
        j = next(j for j in range(i + 1, 12) if sum((a - b) ** 2 for a, b in zip(sites[i], sites[j])) == 2)
        for m in range(0, 5001, 5):
            q, pm = SC.initial(12)
            pm = [list(r) for r in pm]
            pm[j] = [pm[j][k] + m * (sites[i][k] - sites[j][k]) for k in range(3)]
            o = _probe("N12_MULTI_PAIR", 12, p, q, pm, force, m)
            c = o["cpu_outcome"]
            if c["status"] != "OK" and 4 <= c["stop_state"] <= 7 and c["stop_pair"] != 0:
                o["pair_atoms"] = [i, j]
                out.append(o)
                break
        else:
            raise SystemExit(f"N12_MULTI_PAIR p{p}: no momentum found")
    for o in out:
        print(json.dumps({"probe": o["id"], "m": o["search_m"], **o["cpu_outcome"],
                          "wall_s": round(time.perf_counter() - t0, 1)}), flush=True)
    return out


def build(workers=10):
    tasks = [("main", a) for a in sorted(MAIN, key=lambda a: -a[0] * a[0] * a[1] * a[2])] + \
            [("probe", (k, p)) for k in ("N12", "N3") for p in (109, 163)]
    with ProcessPoolExecutor(workers) as pool:
        futs = [pool.submit(main_task if t == "main" else probe_task, a) for t, a in tasks]
        res = [f.result() for f in futs]
    main = [x for r, (t, _) in zip(res, tasks) if t == "main" for x in r]
    probes = [x for r, (t, _) in zip(res, tasks) if t == "probe" for x in r]
    order = [f"N{N}_p{p}_s{s}" for N, p, _, starts, _ in MAIN for s in starts]
    main.sort(key=lambda x: order.index(x["id"]))
    probes.sort(key=lambda x: (x["p"], x["role"]))
    return {"schema": "short-trajectory-bundle-v1", "evaluator": EV, "window": WINDOW, "checkpoints_T10": list(CHECK_T10),
            "checkpoints_T100": list(CHECK_T100), "main": main, "probes": probes}


def main():
    out = Path(sys.argv[1])
    b = build()
    data = json.dumps(b, sort_keys=True, separators=(",", ":")).encode()
    with gzip.GzipFile(out, "wb", mtime=0) as g:
        g.write(data)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    Path(str(out) + ".sha256").write_text(sha + "\n", encoding="utf-8")
    print("main", len(b["main"]), "probes", len(b["probes"]), "sha256", sha, "bytes", out.stat().st_size)


if __name__ == "__main__":
    main()
