"""E2_PAIR_PARALLEL_V1 parallel run (protocol.json). One fresh main process + W persistent pinned pair workers.

    python -m experiments.e2_pair_parallel_v1.run EV N T P W MAIN_CPU CPUS OUT     (EV: algebra | rw:R1+R2)

Same algorithm as experiments/multiatom_parallel_v1/run.run_parallel (MULTIATOM PAR_W); the only difference is the
force each worker evaluates: E1 = probe Force(compiled=True) at p, E2 = A3 RwForce(plan) built after iv.prec = p,
exactly as the serial paths of experiments/multiatom_parallel_v1/run.run_serial construct them. Serial runs use that
unchanged module directly.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import pickle
import sys
import time

from experiments.multiatom_parallel_v1.run import _mem, _readout, cycles, initial_digest

T0 = (time.process_time(), time.perf_counter())


def _now():
    return time.process_time(), time.perf_counter()


def make_force(ev, prec):
    """The force object of evaluator ev at precision prec, constructed as the serial path does."""
    from mpmath import iv

    from experiments.precision_pilot_a2t import evaluator_adapter as A2E
    from experiments.rewrite_pilot_a3 import adapter as AD
    AD.prepare(ev)
    if ev == "algebra":
        return A2E._PROBE.Force(A2E._PROBE.Backend("mp", prec), True)     # sets iv.prec = prec
    if ev == "rw:R1+R2":
        from experiments.rewrite_pilot_a3 import rwforce as RW
        iv.prec = prec
        return RW.RwForce(AD._PLAN)
    raise ValueError(ev)


def _pair_worker(conn, cpu, prec, block, ev):
    w0 = time.perf_counter()
    import psutil
    me = psutil.Process()
    me.cpu_affinity([cpu])
    from mpmath import iv

    from exact_expression_gate_v1 import common as K
    force = make_force(ev, prec)
    iv.prec = prec
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    h = LI.c(K.H)
    conn.send({"ready": True, "pid": me.pid, "affinity": me.cpu_affinity(), "ready_wall_s": time.perf_counter() - w0,
               "iv_prec": iv.prec, "evaluator": ev, "force_type": type(force).__name__})
    busy, busy_wall = 0.0, 0.0
    make = iv.make_mpf
    while True:
        m = conn.recv()
        if m is None:
            break
        c0, b0 = time.process_time(), time.perf_counter()
        q = [[make(x) for x in row] for row in m]
        out = []
        for i, j in block:
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
            st = K.domain(r2)
            if st != K.PROVEN:
                out.append((st, None))
                continue
            g = force(r2)
            out.append((st, tuple(((h * g) * d[k])._mpi_ for k in range(3))))
        busy += time.process_time() - c0
        busy_wall += time.perf_counter() - b0
        conn.send(out)
    conn.send({"busy_cpu_s": busy, "busy_wall_s": busy_wall, "cpu_s": time.process_time(), "cycles": cycles(),
               "peak_wset_mb": _mem(), "affinity_end": me.cpu_affinity()})


def run_parallel(ev, n, T, prec, W, main_cpu, cpus):
    import psutil
    me = psutil.Process()
    me.cpu_affinity([main_cpu])
    from fractions import Fraction as Q

    from mpmath import iv

    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    from experiments.multiatom_parallel_v1 import scenarios as SC
    blocks = SC.pair_blocks(n, W)
    ctx = mp.get_context("spawn")
    ts = time.perf_counter()
    pipes = [ctx.Pipe() for _ in range(W)]
    procs = [ctx.Process(target=_pair_worker, args=(b, cpus[w], prec, blocks[w], ev))
             for w, (a, b) in enumerate(pipes)]
    for pr in procs:
        pr.start()
    parent_pin = []
    for w, pr in enumerate(procs):
        try:
            ps = psutil.Process(pr.pid)
            ps.cpu_affinity([cpus[w]])
            parent_pin.append(ps.cpu_affinity())
        except psutil.Error:
            parent_pin.append(None)
    conns = [a for a, b in pipes]
    hello = [c.recv() for c in conns]
    ready = _now()
    spawn_wall = ready[1] - ts

    iv.prec = prec
    lift = LI.c
    q0, p0 = SC.initial(n)
    h, cdt = lift(K.H), lift(K.CDT)
    q = [[lift(x) for x in r] for r in q0]
    p = [[lift(x) for x in r] for r in p0]
    zero = lift(Q(0))
    make = iv.make_mpf
    tm = {"send_s": 0.0, "wait_s": 0.0, "reduce_s": 0.0}
    keep = {}

    def forces(q, step):
        a = time.perf_counter()
        msg = [[x._mpi_ for x in r] for r in q]
        for c in conns:
            c.send(msg)
        tm["send_s"] += time.perf_counter() - a
        F = [[zero] * 3 for _ in range(n)]
        got = 0
        try:
            for b, c in enumerate(conns):
                a = time.perf_counter()
                res = c.recv()
                got += 1
                tm["wait_s"] += time.perf_counter() - a
                if step == 0:
                    keep.setdefault("msg", msg)
                    keep.setdefault("res", []).append(res)
                a = time.perf_counter()
                for (i, j), (st, tt) in zip(blocks[b], res):
                    if st != K.PROVEN:
                        raise K.DomainStop(st, step)
                    for k in range(3):
                        t = make(tt[k])
                        F[j][k] = F[j][k] + t
                        F[i][k] = F[i][k] - t
                tm["reduce_s"] += time.perf_counter() - a
        except K.DomainStop:
            for c in conns[got:]:
                c.recv()
            raise
        return F

    out = {"completed_steps": 0, "stop": None, "stop_step": None, "read": None}
    t = _now()
    try:
        F = forces(q, 0)
        for s in range(1, T + 1):
            p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
            q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(n)]
            F = forces(q, s)
            p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(n)]
            out["completed_steps"] = s
            if s == T:
                qv, pv = [x for r in q for x in r], [x for r in p for x in r]
                out["read"] = (K.decide(qv, pv), K.endpoints_key(qv + pv))
    except K.DomainStop as e:
        out["stop"], out["stop_step"] = e.kind, e.where
    except K.OutOfRange:
        out["stop"], out["stop_step"] = K.OUT_OF_RANGE, out["completed_steps"]
    t1 = _now()
    wcpu_poll = []
    for pr in procs:
        try:
            ct = psutil.Process(pr.pid).cpu_times()
            wcpu_poll.append(ct.user + ct.system)
        except psutil.Error:
            wcpu_poll.append(None)
    for c in conns:
        c.send(None)
    bye = [c.recv() for c in conns]
    for pr in procs:
        pr.join(timeout=30)
    rec = _readout(out, n)
    rec.update(mode="parallel", evaluator=ev, W=W, initial_sha256=initial_digest(q0, p0), effective_p=iv.prec,
               main_cpu=main_cpu, worker_cpus=cpus, main_affinity=me.cpu_affinity(), worker_hello=hello,
               worker_parent_pin=parent_pin, worker_bye=bye, worker_cpu_poll_s=wcpu_poll,
               worker_cpu_s=[max(x["cpu_s"], y or 0.0) for x, y in zip(bye, wcpu_poll)],
               workers_exited=[pr.exitcode for pr in procs], block_sizes=[len(b) for b in blocks],
               spawn_wall_s=spawn_wall, ready_wall_s=ready[1] - T0[1], loop_wall_s=t1[1] - t[1],
               loop_main_cpu_s=t1[0] - t[0], main_breakdown=dict(tm),
               ipc_bytes_out_step=len(pickle.dumps(keep.get("msg"))) * W if keep else None,
               ipc_bytes_in_step=sum(len(pickle.dumps(r)) for r in keep.get("res", [])) if keep else None)
    rec["main_breakdown"]["kdk_and_other_s"] = rec["loop_wall_s"] - sum(tm.values())
    return rec


def main():
    ev = sys.argv[1]
    n, T, prec, W, mcpu = (int(x) for x in sys.argv[2:7])
    cpus, outp = [int(x) for x in sys.argv[7].split(",")], sys.argv[8]
    rec = run_parallel(ev, n, T, prec, W, mcpu, cpus)
    rec.update(N=n, T=T, p=prec, main_cpu_s=time.process_time(), main_cycles=cycles(), main_peak_wset_mb=_mem(),
               main_wall_s=time.perf_counter() - T0[1], python=sys.version)
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(rec, f)


if __name__ == "__main__":
    main()
