"""Build the sealed GPU_ONE_STEP_V1 (q, p) bundle (protocol 'bundle'). CPU only, before any one-step runner code.

Real states: a runtime replica of exact_expression_gate_v1.stream.run (its own source + ONE observer line after the
second kick, i.e. at the end of step s, where q = q_s, p = p_s, F = F_s) records steps s and s + 1. Each run must end
equal to its verified V2 Vast serial reference. Probes: N = 3 states found by a small search over one atom's momentum.

    python -m experiments.gpu_one_step_v1.samples OUT.json.gz
"""

from __future__ import annotations

import gzip
import hashlib
import inspect
import json
import sys
import time
import types
from fractions import Fraction as Q
from pathlib import Path

from mpmath import iv

from experiments.gpu_force_feasibility_v1.dyadic import encode_iv

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "docs/active/experience_start_p_v2/vast_run/records.json.gz"
EV = "rw:R1+R2"
IDENTITY_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key", "initial_sha256")
TRAJ = ((40, 100, 109), (64, 100, 109), (12, 1000, 163), (16, 1000, 163))
ANCHOR = '            out["completed_steps"] = s\n'
OBSERVER = '            if s in _REC_STEPS: _REC(s, q, p, F)\n'


def make_force(p):
    from experiments.rewrite_pilot_a3 import adapter as AD
    from experiments.rewrite_pilot_a3 import rwforce as RW
    AD.prepare(EV)
    iv.prec = p
    return RW.RwForce(AD._PLAN)


def enc(rows):
    return [[encode_iv(x._mpi_) for x in r] for r in rows]


def replica_run(force, rec_steps, rec):
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import stream
    src = inspect.getsource(stream.run)
    if src.count(ANCHOR) != 1:
        raise SystemExit("stream.run source changed: observer anchor not unique")
    src = src.replace(ANCHOR, OBSERVER + ANCHOR)
    g = dict(vars(stream))
    g.update(LI=types.SimpleNamespace(c=LI.c, G_of_R2=force), _REC_STEPS=rec_steps, _REC=rec)
    exec(compile(src, "<stream.run replica>", "exec"), g)
    return g["run"]


def reference(N, T, p):
    files = json.loads(gzip.open(REF).read())["files"]
    return json.loads(files[f"reference/N{N}_T{T}__p{p}.json"])


def _forces(q, p, force):
    """Sampler-side forces (for the probe search only)."""
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    h, zero = LI.c(K.H), LI.c(Q(0))
    n = len(q)
    F = [[zero] * 3 for _ in range(n)]
    pid = 0
    for i in range(n):
        for j in range(i + 1, n):
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
            st = K.domain(r2)
            if st != K.PROVEN:
                return st, pid, None
            g = force(r2)
            for k in range(3):
                t = (h * g) * d[k]
                F[j][k] = F[j][k] + t
                F[i][k] = F[i][k] - t
            pid += 1
    return "PROVEN", None, F


def _probe_outcome(q, pm, p, force):
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    iv.prec = p
    cdt = LI.c(K.CDT)
    st, pid, F0 = _forces(q, p, force)
    if F0 is None:
        return ("F0", st, pid)
    ph = [[pm[a][k] + F0[a][k] for k in range(3)] for a in range(3)]
    q1 = [[q[a][k] + ph[a][k] * cdt for k in range(3)] for a in range(3)]
    st, pid, F1 = _forces(q1, p, force)
    return ("F1", st, pid) if F1 is None else ("OK", "PROVEN", None)


def probes(p):
    import exact_expression_gate_v0.lang_iv as LI
    force = make_force(p)
    iv.prec = p
    L = LI.c
    out = []

    def state(x1, mom):
        q = [[L(Q(0)), L(Q(0)), L(Q(0))], [x1, L(Q(0)), L(Q(0))], [L(Q(0)), L(Q(20)), L(Q(0))]]
        pm = [[L(Q(0))] * 3, [L(Q(-mom)), L(Q(0)), L(Q(0))], [L(Q(0))] * 3]
        return q, pm
    q, pm = state(L(Q(5)), 0)
    out.append(("PROBE_NORMAL", q, pm, _probe_outcome(q, pm, p, force)))
    q, pm = state(L(Q(1)), 0)
    out.append(("PROBE_F0_VIOLATED", q, pm, _probe_outcome(q, pm, p, force)))
    found = {}
    for mom in range(0, 20001, 250):                     # deterministic search, first hit kept
        if "PROBE_F1_VIOLATED" not in found:
            q, pm = state(L(Q(6)), mom)
            o = _probe_outcome(q, pm, p, force)
            if o[:2] == ("F1", "VIOLATED"):
                found["PROBE_F1_VIOLATED"] = (q, pm, o, mom)
        if "PROBE_F1_UNPROVEN" not in found:
            q, pm = state(iv.mpf(["6", "6.5"]), mom)
            o = _probe_outcome(q, pm, p, force)
            if o[:2] == ("F1", "UNPROVEN"):
                found["PROBE_F1_UNPROVEN"] = (q, pm, o, mom)
        if len(found) == 2:
            break
    for role, (q, pm, o, mom) in sorted(found.items()):
        out.append((role, q, pm, o, mom))
    return [{"role": r[0], "q": enc(r[1]), "p_mom": enc(r[2]), "cpu_outcome": list(r[3]),
             "search_momentum": r[4] if len(r) > 4 else None} for r in out]


def build():
    from experiments.multiatom_parallel_v1 import scenarios as SC
    from experiments.multiatom_parallel_v1.run import _readout, initial_digest
    states, trajs = [], []
    for N, T, p in TRAJ:
        picks = (T // 10, T // 2, 9 * T // 10)
        want = set(picks) | {s + 1 for s in picks}
        got = {}

        def rec(s, q, pm, F):
            got[s] = (enc(q), enc(pm), enc(F))
        run = replica_run(make_force(p), want, rec)
        q0, p0 = SC.initial(N)
        t0 = time.perf_counter()
        r = run(q0, p0, p, T, {T}, exact=False)
        out = _readout({**r, "read": r["read"].get(T)}, N)
        out["initial_sha256"] = initial_digest(q0, p0)
        same = all(out[k] == reference(N, T, p)[k] for k in IDENTITY_KEYS)
        info = {"N": N, "T": T, "p": p, "picks": list(picks), "equals_reference": same,
                "identity": {k: out[k] for k in IDENTITY_KEYS}, "wall_s": round(time.perf_counter() - t0, 1)}
        print(json.dumps({k: v for k, v in info.items() if k != "identity"}), flush=True)
        if not same or sorted(got) != sorted(want):
            raise SystemExit(f"N{N} T{T} p{p}: replica differs from the verified reference or missed a step")
        trajs.append(info)
        for s in picks:
            q, pm, F = got[s]
            qn, pn, Fn = got[s + 1]
            states.append({"id": len(states), "role": "MAIN", "N": N, "T": T, "p": p, "step": s, "q": q, "p_mom": pm,
                           "F": F, "next_q": qn, "next_p_mom": pn, "next_F": Fn})
    test = []
    for p in (109, 163):
        for x in probes(p):
            x.update(id=len(test), N=3, p=p)
            test.append(x)
            print("probe", p, x["role"], x["cpu_outcome"], x["search_momentum"], flush=True)
    return {"schema": "one-step-states-v1", "evaluator": EV, "trajectories": trajs, "main": states, "test_only": test}


def main():
    out = Path(sys.argv[1])
    b = build()
    data = json.dumps(b, sort_keys=True, separators=(",", ":")).encode()
    with gzip.GzipFile(out, "wb", mtime=0) as g:
        g.write(data)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    Path(str(out) + ".sha256").write_text(sha + "\n", encoding="utf-8")
    print("main", len(b["main"]), "test_only", len(b["test_only"]), "sha256", sha)


if __name__ == "__main__":
    main()
