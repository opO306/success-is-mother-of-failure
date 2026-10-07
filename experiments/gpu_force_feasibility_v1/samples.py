"""Build the sealed G0 sample bundle from real E2 trajectories (protocol 'sample_bundle'). CPU only, before any GPU code.

    python -m experiments.gpu_force_feasibility_v1.samples OUT.json.gz
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
import time
import types
from pathlib import Path

from mpmath import iv

from experiments.gpu_force_feasibility_v1.dyadic import decode_iv, encode_iv

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
REF = ROOT / "docs/active/experience_start_p_v2/vast_run/records.json.gz"
EV = "rw:R1+R2"
IDENTITY_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key", "initial_sha256")
TEST_P = (64, 128, 192)
# [-1, 4], [0, 4], [0, 0] as raw tuples
DOMAIN_PROBES = (((1, 1, 0, 1), (0, 1, 2, 1)), ((0, 0, 0, 0), (0, 1, 2, 1)), ((0, 0, 0, 0), (0, 0, 0, 0)))


def make_force(p):
    from experiments.rewrite_pilot_a3 import adapter as AD
    from experiments.rewrite_pilot_a3 import rwforce as RW
    AD.prepare(EV)
    iv.prec = p
    return RW.RwForce(AD._PLAN)


def cpu_g(force, r2_raw):
    """The frozen E2 G at the current iv.prec: ('OK', raw interval) or ('DOMAIN_UNPROVEN', None)."""
    from exact_expression_gate_v1 import common as K
    try:
        return "OK", force(iv.make_mpf(r2_raw))._mpi_          # exact endpoints, as the E2 worker builds values
    except K.DomainStop as e:
        if e.kind != K.UNPROVEN:
            raise
        return "DOMAIN_UNPROVEN", None


def record_run(N, T, p, steps):
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import stream
    from experiments.multiatom_parallel_v1 import scenarios as SC
    from experiments.multiatom_parallel_v1.run import _readout, initial_digest
    force = make_force(p)
    pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
    P = len(pairs)
    calls, got = [0], []

    def recorder(r2):                       # observes only: same argument, same return value
        c = calls[0]
        calls[0] += 1
        g = force(r2)
        s, k = divmod(c, P)
        if s in steps:
            got.append((s, k, r2._mpi_, g._mpi_))
        return g
    q0, p0 = SC.initial(N)
    saved = stream.LI
    stream.LI = types.SimpleNamespace(c=LI.c, G_of_R2=recorder)
    try:
        r = stream.run(q0, p0, p, T, {T}, exact=False)
    finally:
        stream.LI = saved
    rec = _readout({**r, "read": r["read"].get(T)}, N)
    rec["initial_sha256"] = initial_digest(q0, p0)
    return rec, got, calls[0], pairs


def reference(N, T, p):
    files = json.loads(gzip.open(REF).read())["files"]
    return json.loads(files[f"reference/N{N}_T{T}__p{p}.json"])


def build():
    main, trajs, test = [], [], []
    for tr in PROTO["sample_bundle"]["trajectories"]:
        N, T, p = tr["N"], tr["T"], tr["p"]
        steps = (0, T // 10, T // 2, T)
        t0 = time.perf_counter()
        rec, got, ncalls, pairs = record_run(N, T, p, set(steps))
        ref = reference(N, T, p)
        same = all(rec[k] == ref[k] for k in IDENTITY_KEYS)
        P = len(pairs)
        info = {"N": N, "T": T, "p": p, "steps": list(steps), "pairs": P, "force_calls": ncalls,
                "expected_calls": P * (T + 1), "identity": {k: rec[k] for k in IDENTITY_KEYS},
                "reference": f"docs/active/experience_start_p_v2/vast_run reference/N{N}_T{T}__p{p}.json",
                "equals_reference": same, "wall_s": round(time.perf_counter() - t0, 1)}
        print(json.dumps({k: v for k, v in info.items() if k != "identity"}), flush=True)
        if not same or ncalls != P * (T + 1) or len(got) != 4 * P:
            raise SystemExit(f"trajectory N{N} T{T} p{p} does not match its verified reference / call count")
        trajs.append(info)
        for s, k, r2, g in got:
            main.append({"id": len(main), "N": N, "T": T, "p": p, "step": s, "pair_index": k, "pair": list(pairs[k]),
                         "r2": encode_iv(r2), "cpu_status": "OK", "g_cpu": encode_iv(g)})
        mid = [x for x in main if (x["N"], x["T"], x["step"]) == (N, T, T // 2)][:64]
        for q in TEST_P:
            f = make_force(q)
            for x in mid:
                st, g = cpu_g(f, decode_iv(x["r2"]))
                test.append({"id": len(test), "role": "TEST_ONLY_PRECISION", "p": q, "source_id": x["id"],
                             "r2": x["r2"], "cpu_status": st, "g_cpu": encode_iv(g) if g else None})
    for q in (109, 163):
        f = make_force(q)
        for r2 in DOMAIN_PROBES:
            st, g = cpu_g(f, r2)
            test.append({"id": len(test), "role": "TEST_ONLY_DOMAIN_PROBE", "p": q, "source_id": None,
                         "r2": encode_iv(r2), "cpu_status": st, "g_cpu": encode_iv(g) if g else None})
    for x in main + test:                               # exact round trip of every endpoint
        for key in ("r2", "g_cpu"):
            if x.get(key) and encode_iv(decode_iv(x[key])) != x[key]:
                raise SystemExit(f"encoding round trip failed at {x['id']}")
    return {"schema": "g0-samples-v1", "evaluator": EV, "encoding": PROTO["sample_bundle"]["encoding"],
            "trajectories": trajs, "main": main, "test_only": test}


def main():
    out = Path(sys.argv[1])
    b = build()
    data = json.dumps(b, sort_keys=True, separators=(",", ":")).encode()
    with gzip.GzipFile(out, "wb", mtime=0) as g:
        g.write(data)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    Path(str(out) + ".sha256").write_text(sha + "\n", encoding="utf-8")
    print("main", len(b["main"]), "test_only", len(b["test_only"]),
          "statuses", sorted({(x["role"], x["p"], x["cpu_status"]) for x in b["test_only"]}), "sha256", sha)


if __name__ == "__main__":
    main()
