"""Query policies of the five paths and their cost records.

Every path searches the SAME precision grid on its own (V1 fix: in V0 a failure of A skipped B and C, and B/C
started from A's precision). A query asks for a set of steps; the result of each step is one of
DECIDED (cells + first deciding precision), UNDECIDED_AT_CAP, REFUSED_DOMAIN (force proven undefined; final),
OUT_OF_RANGE (decided raw outside the FX(96, f) word; final).

  A, B : build the DAG to the last requested step once, then for each precision evaluate the still-undecided steps
         (ascending, memo shared inside one precision) together with their domain obligations.
  C    : every requested step is its own cold query: restart from step 0 at each precision.
  CS   : one pass per precision up to the last still-undecided step, reading every requested step on the way.
  CX   : CS with exact-rational carry (stream.py).
Costs: wall (perf_counter) and CPU (process_time) of every build and every precision attempt, kept separately.
"""

from __future__ import annotations

import hashlib
import time

from . import common as K
from . import stream
from .dag import DAG, build_kdk

PATHS = ("A", "B", "C", "CS", "CX")


def _now():
    return time.perf_counter(), time.process_time()


def _since(t):
    w, c = _now()
    return {"wall_s": w - t[0], "cpu_s": c - t[1]}


def _key(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _refuse(results, steps, from_step, status, completed, reason):
    for s in steps:
        if s >= from_step and s not in results:
            results[s] = {"status": status, "completed_steps": completed, "reason": reason}


def query_dag(opt, q0, p0, steps, grid):
    steps = sorted(steps)
    rec = {"requested_steps": steps, "attempts": []}
    t = _now()
    dag = DAG(opt)
    snaps = build_kdk(dag, q0, p0, steps[-1], set(steps))
    rec["build"] = _since(t)
    results, undecided = {}, list(steps)
    for b in grid:
        if not undecided:
            break
        t, memo, stop = _now(), {}, None
        for s in undecided:
            qi, pi, nob = snaps[s]
            obl = [g for g, _ in dag.obligations[:nob]]
            try:
                vals = dag.evaluate(qi + pi + obl, b, memo)
            except K.DomainStop as e:
                first = dag.first_step_of(e.where)
                stop = {"kind": e.kind, "force_step": first}
                if e.kind == K.VIOLATED:
                    _refuse(results, undecided, s, K.REFUSED_DOMAIN, max(first - 1, 0),
                            f"force undefined at the positions of step {first}")
                break
            try:
                d = K.decide(vals[:len(qi)], vals[len(qi):len(qi) + len(pi)])
            except K.OutOfRange as e:
                results[s] = {"status": K.OUT_OF_RANGE, "completed_steps": s, "reason": f"raw {e.args[0]}"}
                continue
            if d is not None:
                results[s] = {"status": K.DECIDED, "bits": b, "cells": d,
                              "key": _key(K.endpoints_key(vals[:len(qi) + len(pi)]))}
        a = {"bits": b, **_since(t), "stop": stop,
             "decided": sum(1 for s in undecided if s in results and results[s]["status"] == K.DECIDED)}
        rec["attempts"].append(a)
        undecided = [s for s in undecided if s not in results]
    for s in undecided:
        results[s] = {"status": K.UNDECIDED_AT_CAP}
    rec["results"] = {str(s): results[s] for s in steps}
    return rec, dag, snaps


def query_stream(exact, q0, p0, steps, grid):
    steps = sorted(steps)
    rec = {"requested_steps": steps, "attempts": [], "build": {"wall_s": 0.0, "cpu_s": 0.0}}
    results, undecided = {}, list(steps)
    for b in grid:
        if not undecided:
            break
        t = _now()
        r = stream.run(q0, p0, b, undecided[-1], set(undecided), exact)
        for s, (cells, key) in r["read"].items():
            if cells is not None:
                results[s] = {"status": K.DECIDED, "bits": b, "cells": cells, "key": _key(key)}
        if r["stop"] == K.VIOLATED:
            _refuse(results, undecided, r["stop_step"], K.REFUSED_DOMAIN, r["completed_steps"],
                    f"force undefined at the positions of step {r['stop_step']}")
        elif r["stop"] == K.OUT_OF_RANGE:
            results[r["stop_step"]] = {"status": K.OUT_OF_RANGE, "completed_steps": r["completed_steps"],
                                       "reason": "decided raw outside the FX word"}
        a = {"bits": b, **_since(t), "transitions": r["completed_steps"],
             "decided": sum(1 for s in undecided if s in results and results[s]["status"] == K.DECIDED),
             "stop": None if r["stop"] is None else {"kind": r["stop"], "force_step": r["stop_step"]}}
        if exact:
            a["exact_bits"] = r["exact_bits"]
        rec["attempts"].append(a)
        undecided = [s for s in undecided if s not in results]
    for s in undecided:
        results[s] = {"status": K.UNDECIDED_AT_CAP}
    rec["results"] = {str(s): results[s] for s in steps}
    return rec


def cost(rec):
    w = rec["build"]["wall_s"] + sum(a["wall_s"] for a in rec["attempts"])
    c = rec["build"]["cpu_s"] + sum(a["cpu_s"] for a in rec["attempts"])
    return {"wall_s": w, "cpu_s": c}


def dag_sizes(dag, snaps, at):
    out = {"created_nodes": len(dag.nodes), "index_entries": len(dag.index), "obligations": len(dag.obligations),
           "constructor_calls": dag.created_calls, "reachable": {}}
    for s in at:
        qi, pi, _ = snaps[s]
        nodes, edges = dag.reachable(qi + pi)
        out["reachable"][str(s)] = {"nodes": nodes, "edges": edges, "size": nodes + edges}
    return out


def run_workload(path, q0, p0, query_sets, grid):
    """query_sets: list of step lists (from the protocol). Each query starts from nothing (fresh DAG / fresh run)."""
    queries = []
    for steps in query_sets:
        if path in ("A", "B"):
            rec, dag, snaps = query_dag(path == "B", q0, p0, steps, grid)
            rec["cost"] = cost(rec)
            at = [s for s in (1, 10, 50, 100, 1000) if s in snaps] or steps
            rec["dag"] = dag_sizes(dag, snaps, at)        # measured after the timed part
            del dag, snaps
            queries.append(rec)
        elif path == "C":                                  # one cold query per requested step
            for s in steps:
                rec = query_stream(False, q0, p0, [s], grid)
                rec["cost"] = cost(rec)
                queries.append(rec)
        else:
            rec = query_stream(path == "CX", q0, p0, steps, grid)
            rec["cost"] = cost(rec)
            queries.append(rec)
    total = {"wall_s": sum(q["cost"]["wall_s"] for q in queries), "cpu_s": sum(q["cost"]["cpu_s"] for q in queries)}
    results = {}
    for q in queries:
        results.update(q["results"])
    return {"path": path, "queries": queries, "results": results, "total": total}
