"""Build the sealed GPU_LONG_TRAJECTORY_V1 bundle (protocol 'bundle'). CPU only, before any long runner / service code.

stream.run replica (GPU_SHORT_TRAJECTORY_V1 samples.replica_run, unchanged) at T = 1000 for N12 p 64, 73, 161, 163,
N16 p 64, 78, 166, 163 and N40 p 109: per-step digests, full states at the checkpoints, the pass record (_readout), the
stop (state, kind, first pair) and the gate-P position states. The N12 / N16 runs must equal the V2 Vast references.

    python -m experiments.gpu_long_trajectory_v1.samples OUT.json.gz
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from mpmath import iv

from experiments.gpu_short_trajectory_v1 import samples as SS

T = 1000
CHECKS = (0, 1, 2, 5, 10, 20, 50, 100, 200, 250, 500, 750, 900, 950, 990, 999, 1000)
GATE_P_STATES = (0, 250, 500, 750, 1000)
RUNS = ((12, 64), (12, 73), (12, 161), (12, 163), (16, 64), (16, 78), (16, 166), (16, 163), (40, 109))
GATE_P_RUNS = {(12, 64), (12, 73), (12, 161), (12, 163), (16, 64), (16, 78), (16, 166), (16, 163)}
IDENTITY_KEYS = SS.IDENTITY_KEYS


def run_task(args):
    import exact_expression_gate_v0.lang_iv as LI
    from experiments.multiatom_parallel_v1 import scenarios as SC
    from experiments.multiatom_parallel_v1.run import _readout, initial_digest
    N, p = args
    t0 = time.perf_counter()
    force = SS.make_force(p)
    q0, p0 = SC.initial(N)
    iv.prec = p
    Lq, Lp = [[LI.c(x) for x in r] for r in q0], [[LI.c(x) for x in r] for r in p0]
    steps, full, qs = {}, {}, {}
    last = {"q": Lq, "state": 0, "prev_q": None}
    if 0 in GATE_P_STATES:
        qs[0] = SS.enc(Lq)

    def obs_a(s, q, pm, F):
        t = s - 1
        last.update(prev_q=last["q"], q=q, state=s)
        if s == 1:
            full[0] = {"q": SS.enc(Lq), "p_mom": SS.enc(Lp), "F": SS.enc(F)}
        steps[t] = {"s": t, "F_s": SS.dg("F", F), "p_half": SS.dg("P", pm), "q1": SS.dg("Q", q)}
        if s in GATE_P_STATES:
            qs[s] = SS.enc(q)

    def obs_b(s, q, pm, F):
        steps[s - 1].update(F1=SS.dg("F", F), p1=SS.dg("P", pm), state=SS.state_dg(q, pm), force=SS.dg("F", F))
        if s in CHECKS:
            full[s] = {"q": SS.enc(q), "p_mom": SS.enc(pm), "F": SS.enc(F)}
    run = SS.replica_run(force, obs_a, obs_b)
    out = run(q0, p0, p, T, {T}, exact=False)
    rec = _readout({**out, "read": out["read"].get(T)}, N)
    rec["initial_sha256"] = initial_digest(q0, p0)
    stop = None
    gate = []
    if out["stop"] in ("VIOLATED", "UNPROVEN"):
        k = out["stop_step"]
        if k != last["state"]:
            raise SystemExit(f"N{N} p{p}: stop state {k} but the last drift observer saw {last['state']}")
        kind, pid = SS.first_stop_pair(last["q"], force)
        if kind != out["stop"]:
            raise SystemExit(f"N{N} p{p}: stop kind {out['stop']} vs first pair {kind}")
        stop = {"status": "DOMAIN_STOP_" + kind, "stop_state": k, "stop_pair": pid}
        if (N, p) in GATE_P_RUNS:
            gate += [{"state": k - 1, "role": "LAST_COMPLETED", "q": SS.enc(last["prev_q"])},
                     {"state": k, "role": "STOP_STATE", "q": SS.enc(last["q"])}]
    if (N, p) in GATE_P_RUNS:
        gate += [{"state": s, "role": "TRAJECTORY", "q": q} for s, q in sorted(qs.items())]
    tie = None
    if N in (12, 16):
        ref = SS.reference(f"N{N}_T1000__p{p}")
        tie = {"reference": f"N{N}_T1000__p{p}", "equals_reference": all(rec[k] == ref[k] for k in IDENTITY_KEYS)}
        if not tie["equals_reference"]:
            raise SystemExit(f"N{N} p{p}: replica differs from the V2 reference: "
                             f"{[(k, rec[k], ref[k]) for k in IDENTITY_KEYS if rec[k] != ref[k]]}")
    n_steps = len(steps)
    if sorted(steps) != list(range(n_steps)):
        raise SystemExit(f"N{N} p{p}: step records not contiguous")
    traj = {"id": f"N{N}_p{p}", "N": N, "p": p, "T": T, "q0": full.get(0, {}).get("q") or SS.enc(Lq),
            "p0": full.get(0, {}).get("p_mom") or SS.enc(Lp), "steps": [steps[i] for i in range(n_steps)],
            "full": {str(k): v for k, v in sorted(full.items())}, "pass_record": rec, "stop": stop, "tie": tie,
            "gate_P_states": [{"id": f"N{N}_p{p}_s{g['state']}", "N": N, "p": p, **g} for g in gate]}
    print(json.dumps({"id": traj["id"], "outcome": rec["outcome"], "completed": rec["completed_steps"],
                      "stop": stop, "tie": tie and tie["equals_reference"], "steps": n_steps,
                      "gate_P_states": len(gate), "wall_s": round(time.perf_counter() - t0, 1)}), flush=True)
    return traj


def build(workers=9):
    order = sorted(RUNS, key=lambda a: -a[0])                      # N40 first (the long pole)
    with ProcessPoolExecutor(workers) as pool:
        res = dict(zip(order, pool.map(run_task, order)))
    trajs = [res[a] for a in RUNS]
    gate = [g for t in trajs for g in t.pop("gate_P_states")]
    return {"schema": "long-trajectory-bundle-v1", "evaluator": SS.EV, "T": T, "checkpoints": list(CHECKS),
            "trajectories": trajs, "gate_P_states": gate}


def main():
    out = Path(sys.argv[1])
    b = build()
    data = json.dumps(b, sort_keys=True, separators=(",", ":")).encode()
    with gzip.GzipFile(out, "wb", mtime=0) as g:
        g.write(data)
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    Path(str(out) + ".sha256").write_text(sha + "\n", encoding="utf-8")
    print("trajectories", len(b["trajectories"]), "gate_P_states", len(b["gate_P_states"]), "sha256", sha,
          "bytes", out.stat().st_size)


if __name__ == "__main__":
    main()
