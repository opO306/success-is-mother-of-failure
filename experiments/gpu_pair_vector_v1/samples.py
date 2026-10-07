"""Build the sealed GPU_PAIR_VECTOR_V1 state bundle (protocol 'sample_bundle'). CPU only, before any GPU code.

The four G0 trajectories are re-run with a replica of exact_expression_gate_v1.stream.run made at runtime from its own
source (inspect.getsource) with ONE inserted observer line before forces' 'return F'; the replica runs in a copy of
stream's module globals with LI = (c, E2 force) exactly as multiatom_parallel_v1.run_serial swaps it. No file changes.
Each run must end equal to its verified V2 Vast serial reference.

    python -m experiments.gpu_pair_vector_v1.samples OUT.json.gz
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
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
REF = ROOT / "docs/active/experience_start_p_v2/vast_run/records.json.gz"
EV = "rw:R1+R2"
IDENTITY_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key", "initial_sha256")
TRAJ = ((40, 100, 109), (64, 100, 109), (12, 1000, 163), (16, 1000, 163))
ANCHOR = "        return F\n"
OBSERVER = "        if step in _REC_STEPS: _REC(step, q, F)\n"


def make_force(p):
    from experiments.rewrite_pilot_a3 import adapter as AD
    from experiments.rewrite_pilot_a3 import rwforce as RW
    AD.prepare(EV)
    iv.prec = p
    return RW.RwForce(AD._PLAN)


def replica_run(force, rec_steps, rec):
    """stream.run from its own source + one observer line, executed with stream's globals and LI swapped."""
    from exact_expression_gate_v1 import stream
    import exact_expression_gate_v0.lang_iv as LI
    src = inspect.getsource(stream.run)
    if src.count(ANCHOR) != 1:
        raise SystemExit("stream.run source changed: observer anchor not unique")
    src = src.replace(ANCHOR, OBSERVER + ANCHOR)
    g = dict(vars(stream))
    g.update(LI=types.SimpleNamespace(c=LI.c, G_of_R2=force), _REC_STEPS=rec_steps, _REC=rec)
    exec(compile(src, "<stream.run replica>", "exec"), g)
    return g["run"]


def enc_state(rows):
    return [[encode_iv(x._mpi_) for x in r] for r in rows]


def reference(N, T, p):
    files = json.loads(gzip.open(REF).read())["files"]
    return json.loads(files[f"reference/N{N}_T{T}__p{p}.json"])


def cpu_forces(q, p):
    """The CPU forces loop on given position intervals (used only for the test-only states)."""
    from exact_expression_gate_v1 import common as K
    import exact_expression_gate_v0.lang_iv as LI
    force = make_force(p)
    iv.prec = p
    h, zero = LI.c(K.H), LI.c(Q(0))
    n = len(q)
    F = [[zero] * 3 for _ in range(n)]
    for pid, (i, j) in enumerate((i, j) for i in range(n) for j in range(i + 1, n)):
        d = [q[j][k] - q[i][k] for k in range(3)]
        r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
        st = K.domain(r2)
        if st != K.PROVEN:
            return {"status": st, "first_stop_pair": pid, "F": None}
        g = force(r2)
        for k in range(3):
            t = (h * g) * d[k]
            F[j][k] = F[j][k] + t
            F[i][k] = F[i][k] - t
    return {"status": "PROVEN", "first_stop_pair": None, "F": enc_state(F)}


def build():
    from experiments.multiatom_parallel_v1 import scenarios as SC
    from experiments.multiatom_parallel_v1.run import _readout, initial_digest
    import exact_expression_gate_v0.lang_iv as LI
    states, trajs = [], []
    for N, T, p in TRAJ:
        steps = (0, T // 10, T // 2, T)
        got = {}

        def rec(step, q, F):
            got[step] = (enc_state(q), enc_state(F))
        run = replica_run(make_force(p), set(steps), rec)
        q0, p0 = SC.initial(N)
        t0 = time.perf_counter()
        r = run(q0, p0, p, T, {T}, exact=False)
        out = _readout({**r, "read": r["read"].get(T)}, N)
        out["initial_sha256"] = initial_digest(q0, p0)
        ref = reference(N, T, p)
        same = all(out[k] == ref[k] for k in IDENTITY_KEYS)
        info = {"N": N, "T": T, "p": p, "steps": list(steps), "equals_reference": same,
                "identity": {k: out[k] for k in IDENTITY_KEYS}, "wall_s": round(time.perf_counter() - t0, 1)}
        print(json.dumps({k: v for k, v in info.items() if k != "identity"}), flush=True)
        if not same or sorted(got) != sorted(steps):
            raise SystemExit(f"N{N} T{T} p{p}: replica differs from the verified reference or missed a step")
        trajs.append(info)
        for s in steps:
            qe, Fe = got[s]
            states.append({"id": len(states), "role": "MAIN", "N": N, "T": T, "p": p, "step": s, "q": qe,
                           "cpu_status": "PROVEN", "cpu_first_stop_pair": None, "F_cpu": Fe})
    test = []
    mid40 = next(x for x in states if (x["N"], x["step"]) == (40, 50))
    from experiments.gpu_force_feasibility_v1.dyadic import decode_iv
    for q in (128, 192):
        rows = [[iv.make_mpf(decode_iv(e)) for e in r] for r in mid40["q"]]
        c = cpu_forces(rows, q)
        test.append({"id": len(test), "role": "TEST_ONLY_PRECISION", "N": 40, "p": q, "source_state": mid40["id"],
                     "q": mid40["q"], "cpu_status": c["status"], "cpu_first_stop_pair": c["first_stop_pair"],
                     "F_cpu": c["F"]})
    for p in (109, 163):
        iv.prec = p
        far = [Q(0), Q(0), Q(0)], [Q(5), Q(0), Q(0)], [Q(0), Q(7), Q(0)]
        probes = {"PROBE_PROVEN": far,
                  "PROBE_VIOLATED": ([Q(0)] * 3, [Q(5), Q(0), Q(0)], [Q(1), Q(0), Q(0)]),
                  "PROBE_UNPROVEN": ([Q(0)] * 3, [Q(9), Q(0), Q(0)], ["IV23", Q(0), Q(0)])}
        for role, pos in probes.items():
            rows = [[iv.mpf([2, 3]) if x == "IV23" else LI.c(x) for x in r] for r in pos]
            c = cpu_forces(rows, p)
            test.append({"id": len(test), "role": role, "N": 3, "p": p, "source_state": None, "q": enc_state(rows),
                         "cpu_status": c["status"], "cpu_first_stop_pair": c["first_stop_pair"], "F_cpu": c["F"]})
    return {"schema": "pv1-states-v1", "evaluator": EV, "trajectories": trajs, "main": states, "test_only": test}


def main():
    out = Path(sys.argv[1])
    b = build()
    data = json.dumps(b, sort_keys=True, separators=(",", ":")).encode()
    with gzip.GzipFile(out, "wb", mtime=0) as g:
        g.write(data)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    Path(str(out) + ".sha256").write_text(sha + "\n", encoding="utf-8")
    pairs = sum(x["N"] * (x["N"] - 1) // 2 for x in b["main"])
    print("main states", len(b["main"]), "pairs", pairs, "test_only",
          [(x["role"], x["p"], x["cpu_status"], x["cpu_first_stop_pair"]) for x in b["test_only"]], "sha256", sha)


if __name__ == "__main__":
    main()
