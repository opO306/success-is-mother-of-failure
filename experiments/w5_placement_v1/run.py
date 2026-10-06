"""W5_PLACEMENT_V1 single run: execute one ExecutionPlan in a fresh process.

    python -m experiments.w5_placement_v1.run PLAN_JSON_FILE N T OUT
"""

from __future__ import annotations

import json
import sys
import time

from experiments.multiatom_parallel_v1.run import _mem, cycles

from experiments.w5_placement_v1.plan import ExecutionPlan, execute

T0 = time.perf_counter()


def main():
    plan = ExecutionPlan.from_json(open(sys.argv[1], encoding="utf-8").read())
    n, T, outp = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    rec = execute(plan, n, T)
    rec.update(plan=json.loads(plan.to_json()), N=n, T=T, p=plan.precision, main_cpu_s=time.process_time(),
               main_cycles=cycles(), main_peak_wset_mb=_mem(), main_wall_s=time.perf_counter() - T0,
               python=sys.version)
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(rec, f)


if __name__ == "__main__":
    main()
