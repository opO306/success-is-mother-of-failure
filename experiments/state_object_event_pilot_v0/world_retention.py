"""PART A: production C1-B1 with the world keeping only its current state (WORLD_ONLY) vs an observer that keeps a
history (OBSERVER_HISTORY). Same REF executor (a_reference.c1b1_two_atom.step), unchanged.

The observer receives a snapshot made of immutable tuples built by the loop; it never gets the Run, so nothing can
flow from observer data back into the physics. The trajectory identity is a streaming SHA-256 over the canonical
record of every step (no history array in WORLD_ONLY).

Worker (one fresh process per run):
    python -m experiments.state_object_event_pilot_v0.world_retention --case CASE --mode MODE [--memory] --out FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import tracemalloc
from fractions import Fraction as Q
from pathlib import Path

from a_numeric import FixedPoint
from a_numeric.profiles import VMHalt
from a_reference import c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[2]
DT = Q(40)
CHECKPOINTS = (1, 10, 100, 1000, 10000)
MAX_STEPS = 10000
ORIGINS = ("e0.5_rho-0.005", "e1_b10", "e10_b0")
CASES = ORIGINS + ("A2_sym",)
MODES = ("WORLD_ONLY", "OBSERVER_HISTORY", "PORT", "PAIR")
STOPS = (C.PhysicsDomainExceeded, C.IntegratorDomainExceeded, C.ExecutorLimitExceeded, C.ContractViolation, VMHalt)


def profiles():
    return FixedPoint(96, 48), FixedPoint(96, 80)


def origin(case):
    path = ROOT / "docs/active/c1b1_trusted_test_origins_v1" / f"{case}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc["case"] != case or doc["approval_status"] != "APPROVED":
        raise ValueError(f"{case}: not an approved trusted origin")
    return doc, hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def new_case(case):
    """A fresh canonical Run for the case (stored raws after the initial rounding)."""
    pos, mom = profiles()
    if case == "A2_sym":
        return C.new_run(pos, DT, (Q(-71, 20), 0, 0), (1, -3, 0), (Q(71, 20), 0, 0), (-1, 3, 0),
                         momentum_profile=mom, validated_only=True)
    doc, _ = origin(case)
    raw = [int(x) for x in doc["initial_raw"]]
    ri, pi, rj, pj = raw[0:3], raw[3:6], raw[6:9], raw[9:12]
    run = C.new_run(pos, DT, tuple(Q(v, 1 << 48) for v in ri), tuple(Q(v, 1 << 80) for v in pi),
                    tuple(Q(v, 1 << 48) for v in rj), tuple(Q(v, 1 << 80) for v in pj),
                    momentum_profile=mom, validated_only=False)
    a, b = run.atoms
    if list(a.r) + list(a.p) + list(b.r) + list(b.p) != raw:
        raise ValueError(f"{case}: stored raws differ from initial_raw")
    return run


def _raws(t):
    return ",".join(str(v) for v in t)


def record(run, t, status):
    """Canonical record of one state (version tag v1)."""
    a, b = run.atoms
    J = "None" if run.J_cache is None else _raws(run.J_cache)
    return f"v1|{t}|{a.species}|{_raws(a.r)}|{_raws(a.p)}|{b.species}|{_raws(b.r)}|{_raws(b.p)}|{J}|{status}"


def snapshot(run):
    """Observer view: immutable tuples only (ints, strs). The observer never receives the Run."""
    a, b = run.atoms
    return (run.t_steps, (a.species, tuple(a.r), tuple(a.p)), (b.species, tuple(b.r), tuple(b.p)),
            None if run.J_cache is None else tuple(run.J_cache), "OK")


class Observer:
    def __init__(self):
        self.history = []

    def observe(self, snap):
        self.history.append(snap)


def deep_size(obj):
    """Deep getsizeof (shared objects counted once). Python object bytes, not RSS."""
    seen, stack, total = set(), [obj], 0
    while stack:
        o = stack.pop()
        if id(o) in seen or o is None:
            continue
        seen.add(id(o))
        total += sys.getsizeof(o)
        if isinstance(o, (tuple, list, set, frozenset)):
            stack.extend(o)
        elif isinstance(o, dict):
            stack.extend(o.keys())
            stack.extend(o.values())
        elif hasattr(o, "__dict__"):
            stack.append(vars(o))
        elif hasattr(o, "__slots__"):
            stack.extend(getattr(o, s) for s in o.__slots__ if hasattr(o, s))
    return total


def peak_rss():
    import psutil
    mi = psutil.Process().memory_info()
    return getattr(mi, "peak_wset", None) or getattr(mi, "rss")


def rss():
    import psutil
    return psutil.Process().memory_info().rss


def run_loop(run, stepper, observer=None, max_steps=MAX_STEPS, checkpoints=CHECKPOINTS, on_checkpoint=None):
    """Advance until max_steps or a canonical refusal. Returns identity fields (no history)."""
    h = hashlib.sha256()
    h.update(record(run, run.t_steps, "OK").encode() + b"\n")
    cps, status = {}, "OK"
    for _ in range(max_steps):
        try:
            stepper(run)
        except STOPS as e:
            status = type(e).__name__
            break
        rec = record(run, run.t_steps, "OK")
        h.update(rec.encode() + b"\n")
        if observer is not None:
            observer.observe(snapshot(run))
        if run.t_steps in checkpoints:
            cps[str(run.t_steps)] = rec
            if on_checkpoint is not None:
                on_checkpoint(run.t_steps)
    final = record(run, run.t_steps, status)
    h.update(b"END|" + final.encode())
    return {"completed_steps": run.t_steps, "status": status, "final_record": final, "checkpoint_records": cps,
            "stream_sha256": h.hexdigest()}


def live_state(run):
    """The world's current physical state plus the J cache (what the next step reads)."""
    core = getattr(run, "state_core", None)
    return core() if core else (run.atoms, run.J_cache, run.t_steps)


def make(case, mode):
    """(state object, stepper, observer or None, extra report callable)."""
    run = new_case(case)
    if mode == "WORLD_ONLY":
        return run, C.step, None, (lambda: {})
    if mode == "OBSERVER_HISTORY":
        return run, C.step, Observer(), (lambda: {})
    if mode == "PORT":
        from . import object_port as P
        world = P.PortRun.from_run(run)
        return world, P.step, None, world.report
    if mode == "PAIR":
        if case != "A2_sym":
            raise ValueError("PAIR is defined for A2_sym only")
        from . import pair_state as S
        world = S.PairRun.from_run(run)
        return world, S.step, None, world.report
    raise ValueError(mode)


def execute(case, mode, memory=False, max_steps=MAX_STEPS):
    if memory:
        tracemalloc.start()
    world, stepper, observer, extra = make(case, mode)
    mem = {"checkpoint_rss": {}}
    if memory:
        mem.update(tracemalloc={}, live_state_bytes={}, history_bytes={})

    def on_cp(t):
        mem["checkpoint_rss"][str(t)] = rss()
        if memory:
            cur, peak = tracemalloc.get_traced_memory()
            mem["tracemalloc"][str(t)] = [cur, peak]
            mem["live_state_bytes"][str(t)] = deep_size(live_state(world))
            if observer is not None:
                mem["history_bytes"][str(t)] = deep_size(observer.history)
    c0, w0 = time.process_time(), time.perf_counter()
    out = run_loop(world, stepper, observer, max_steps=max_steps, on_checkpoint=on_cp)
    out["cpu_s"], out["wall_s"] = time.process_time() - c0, time.perf_counter() - w0
    out.update(mem)
    out["peak_rss"] = peak_rss()
    out["observer_entries"] = None if observer is None else len(observer.history)
    out["extra"] = extra()
    if memory:
        tracemalloc.stop()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, choices=CASES)
    ap.add_argument("--mode", required=True, choices=MODES)
    ap.add_argument("--memory", action="store_true")
    ap.add_argument("--max-steps", type=int, default=MAX_STEPS)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = {"case": a.case, "mode": a.mode, "memory_run": a.memory, "python": sys.version}
    out.update(execute(a.case, a.mode, a.memory, a.max_steps))
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
