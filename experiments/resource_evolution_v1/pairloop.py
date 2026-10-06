"""S4 pair-force parallel prototype. The KDK loop below performs exactly the operations of
exact_expression_gate_v1.stream.run(exact=False) in the same order; only the pair-force evaluations G(R^2) are sent to
persistent pinned worker processes (algebra force at the same p) and the results are accumulated in the canonical pair
order. Bit identity with the serial algebra pass is checked by the caller.

    python -m experiments.resource_evolution_v1.pairloop SCENARIO T P NWORK CPUS(comma) OUT
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time


def _pair_worker(conn, cpu, prec):
    import psutil
    psutil.Process().cpu_affinity([cpu])
    from mpmath import iv

    from experiments.precision_pilot_a2t import evaluator_adapter as A2E
    A2E.prepare("algebra")
    P = A2E._PROBE
    iv.prec = prec
    f = P.Force(P.Backend("mp", prec), True)
    conn.send("ready")
    while True:
        m = conn.recv()
        if m is None:
            break
        conn.send(f(iv.make_mpf(m))._mpi_)
    conn.send(time.process_time())


def run_parallel(q0, p0, prec, last, conns):
    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    iv.prec = prec
    lift = LI.c
    n = len(q0)
    h, cdt = lift(K.H), lift(K.CDT)
    q = [[lift(x) for x in r] for r in q0]
    p = [[lift(x) for x in r] for r in p0]
    zero = lift(0)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    W = len(conns)

    def forces(q, step):
        F = [[zero] * 3 for _ in range(n)]
        ds = []
        for i, j in pairs:
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
            st = K.domain(r2)
            if st != K.PROVEN:
                raise K.DomainStop(st, step)
            ds.append((d, r2))
        for idx, (_, r2) in enumerate(ds):
            conns[idx % W].send(r2._mpi_)
        gs = [iv.make_mpf(conns[idx % W].recv()) for idx in range(len(ds))]
        for (i, j), (d, _), g in zip(pairs, ds, gs):
            for k in range(3):
                t = (h * g) * d[k]
                F[j][k] = F[j][k] + t
                F[i][k] = F[i][k] - t
        return F

    out = {"completed_steps": 0, "stop": None, "read": None}
    try:
        F = forces(q, 0)
        for s in range(1, last + 1):
            p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
            q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(n)]
            F = forces(q, s)
            p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
            out["completed_steps"] = s
        qv, pv = [x for r in q for x in r], [x for r in p for x in r]
        out["read"] = (K.decide(qv, pv), K.endpoints_key(qv + pv))
    except K.DomainStop as e:
        out["stop"] = e.kind
    return out


def main():
    scen, T, prec, nw, cpus, outp = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), \
        [int(x) for x in sys.argv[5].split(",")], sys.argv[6]
    import psutil
    psutil.Process().cpu_affinity([cpus[0]])
    from experiments.precision_pilot_a1 import evaluator_adapter as A1E
    from experiments.precision_pilot_a2t import evaluator_adapter as A2E
    A2E.prepare("algebra")
    res = {"scenario": scen, "T": T, "p": prec, "n_workers": nw, "cpus": cpus}
    # serial reference: the A2T algebra evaluator in this process
    t = (time.process_time(), time.perf_counter())
    ser = A2E.run_pass("algebra", scen, prec, T)
    res["serial"] = {"wall_s": time.perf_counter() - t[1], "cpu_s": time.process_time() - t[0],
                     "outcome": ser["outcome"], "cells": ser["cells"], "endpoints_scaled": ser["endpoints_scaled"]}
    # parallel
    ctx = mp.get_context("spawn")
    t_spawn = time.perf_counter()
    pipes = [ctx.Pipe() for _ in range(nw)]
    procs = [ctx.Process(target=_pair_worker, args=(b, cpus[1 + i], prec)) for i, (a, b) in enumerate(pipes)]
    for pr in procs:
        pr.start()
    conns = [a for a, b in pipes]
    for c in conns:
        assert c.recv() == "ready"
    spawn_wall = time.perf_counter() - t_spawn
    q0, p0 = A1E.initial(scen)
    t = (time.process_time(), time.perf_counter())
    par = run_parallel(q0, p0, prec, T, conns)
    wall = time.perf_counter() - t[1]
    main_cpu = time.process_time() - t[0]
    for c in conns:
        c.send(None)
    wcpu = [c.recv() for c in conns]
    for pr in procs:
        pr.join(timeout=30)
    from experiments.precision_pilot_a2t import evaluator_adapter as _  # noqa: F401
    ends = A1E._scaled_endpoints(par["read"][1]) if par["read"] else None
    res["parallel"] = {"wall_s": wall, "spawn_wall_s": spawn_wall, "main_cpu_s": main_cpu, "worker_cpu_s": wcpu,
                       "outcome": None if not par["read"] else ("DECIDED" if par["read"][0] else "UNDECIDED"),
                       "cells": par["read"][0] if par["read"] else None, "endpoints_scaled": ends,
                       "workers_exited": all(pr.exitcode is not None for pr in procs)}
    res["bit_identical"] = ends == ser["endpoints_scaled"]
    open(outp, "w", encoding="utf-8").write(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
