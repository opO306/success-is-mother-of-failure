"""RESOURCE_EVOLUTION_PILOT_V1 worker: one fresh process, pinned FIRST, then passes appended line by line.

    python -m experiments.resource_evolution_v1.worker SPEC_JSON OUT_JSONL

spec: {"cpus": [..], "evaluator", "scenario", "T", "mode": "policy"|"single"|"smt_burn", "start_p", "max_passes"}
policy: first pass at start_p, then the frozen P2 rule (A1 policies.p2_next), cap 1024, until DECIDED.
Every completed pass is one JSON line (flushed), so a worker killed by its budget still leaves its completed attempts.
"""

from __future__ import annotations

import json
import os
import sys
import time

T0 = (time.process_time(), time.perf_counter())


def main():
    spec = json.loads(open(sys.argv[1], encoding="utf-8").read())
    out = open(sys.argv[2], "a", encoding="utf-8")
    import psutil
    me = psutil.Process()
    me.cpu_affinity(spec["cpus"])
    readback = me.cpu_affinity()

    def emit(d):
        out.write(json.dumps(d) + "\n")
        out.flush()
    emit({"kind": "start", "pid": os.getpid(), "affinity_requested": spec["cpus"], "affinity_readback": readback,
          "t_wall": time.perf_counter() - T0[1]})
    if spec["mode"] == "smt_burn":
        t = time.perf_counter()
        x = 0
        for i in range(spec.get("n", 12_000_000)):
            x += i * i
        emit({"kind": "burn", "wall_s": time.perf_counter() - t})
    else:
        from experiments.precision_pilot_a1 import policies as POL
        from experiments.rewrite_pilot_a3 import adapter as AD
        prep = AD.prepare(spec["evaluator"])
        emit({"kind": "prepared", "modules": prep.get("modules"), "prepare_cpu_s": prep.get("prepare_cpu_s"),
              "t_wall": time.perf_counter() - T0[1]})
        hist, p = [], spec["start_p"]
        while True:
            rec = AD.run_pass(spec["evaluator"], spec["scenario"], p, spec["T"])
            hist.append(rec)
            emit({"kind": "pass", **rec, "t_wall": time.perf_counter() - T0[1],
                  "t_cpu": time.process_time() - T0[0]})
            if spec["mode"] == "single" or rec["outcome"] != "UNDECIDED_AT_PRECISION" and \
                    rec["outcome"] != "DOMAIN_UNPROVEN" or len(hist) >= spec.get("max_passes", 24):
                break
            nxt = POL.p2_next(rec, spec["T"])
            if nxt > 1024:
                if p >= 1024:
                    break
                nxt = 1024
            p = nxt
    mi = me.memory_info()
    emit({"kind": "end", "child_cpu_s": time.process_time() - T0[0], "child_wall_s": time.perf_counter() - T0[1],
          "peak_wset_mb": getattr(mi, "peak_wset", mi.rss) / 2 ** 20, "affinity_end": me.cpu_affinity()})
    out.close()


if __name__ == "__main__":
    main()
