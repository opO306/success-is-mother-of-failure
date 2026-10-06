"""Independent checker of MULTIATOM_PARALLEL_V1 (protocol.json 'checker'). Reads JSON records only. Imports no
executor module (run, scenarios, campaign, stream, adapters); regenerates every FCC_N initial state with its own code;
re-derives cells with the A1 checker's own half-even rounding.

    python -m experiments.multiatom_parallel_v1.checker DIR
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from fractions import Fraction as F
from pathlib import Path

from experiments.precision_pilot_a1 import checker as A1C

PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
N_LIST = PROTO["scenario_family"]["N_list"]
HORIZONS = {"H100": (100, N_LIST), "H1000": (1000, [2, 3, 4, 6, 8, 12])}
CONFIGS = ["SER_E1", "SER_E2", "PAR_1", "PAR_2", "PAR_3", "PAR_4", "PAR_6"]
WORKER_CORES, MAIN_CPU, SERIAL_CPU = [2, 4, 6, 8, 10, 0], 1, 2
P = 128
RESULT_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells")


def my_initial(n):
    """Own FCC_N generator: walk shells of increasing |v|^2, inside a shell take (x, y, z) ascending."""
    sites, r2 = [], 0
    while len(sites) < n:
        lim = int(r2 ** 0.5) + 1
        shell = sorted((x, y, z) for x in range(-lim, lim + 1) for y in range(-lim, lim + 1)
                       for z in range(-lim, lim + 1) if x * x + y * y + z * z == r2 and (x + y + z) % 2 == 0)
        sites.extend(shell)
        r2 += 1
    sites = sites[:n]
    q = [[F(5) * c for c in s] for s in sites]
    raw = [[F((7 * i + 3 * k + 1) % 5 - 2) for k in range(3)] for i in range(n)]
    p = [[raw[i][k] - sum(raw[a][k] for a in range(n)) / n for k in range(3)] for i in range(n)]
    return q, p


def my_digest(q, p):
    txt = json.dumps({"q": [[str(x) for x in r] for r in q], "p": [[str(x) for x in r] for r in p]})
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def check(d):
    d = Path(d)
    t_verify = time.perf_counter()
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    ok("seal_clean", seal["status_porcelain"] == "" and not seal["sealed_sources_dirty"], seal["status_porcelain"][:200])
    g = d / "gates"
    v = json.loads((g / "verify.json").read_text(encoding="utf-8"))
    sy = json.loads((g / "sympy.json").read_text(encoding="utf-8"))
    dm = json.loads((g / "e2_domain.json").read_text(encoding="utf-8"))
    ok("E2_gate_S1_S6", v.get("PASS_S1_S6_except_S3b") is True)
    ok("E2_gate_sympy", sy.get("sympy_zero") is True)
    ok("E2_gate_new_domain", dm.get("PASS") is True and dm.get("p") == P and
       all(r["E1_contains_E0_1024"] and r["E2_contains_E0_1024"] for r in dm["rows"]))
    digests = {n: my_digest(*my_initial(n)) for n in N_LIST}
    reps = 3
    groups, e2groups, verify_cells, vcost = {}, {}, 0, {}
    for h, (T, ns) in HORIZONS.items():
        for n in ns:
            for rep in range(reps):
                for cfg in CONFIGS:
                    name = f"{h}__N{n}__{cfg}__r{rep}"
                    f = d / f"{name}.json"
                    ok("complete", f.exists(), name)
                    if not f.exists():
                        continue
                    r = json.loads(f.read_text(encoding="utf-8"))
                    ok("meta", (r["N"], r["T"], r["p"], r["effective_p"], r["config"]) == (n, T, P, P, cfg), name)
                    ok("initial_state", r["initial_sha256"] == digests[n], name)
                    if r["outcome"] == "DECIDED":
                        verify_cells += 1
                        tv = time.perf_counter()
                        same = A1C.my_cells(r["endpoints_scaled"]) == r["cells"]
                        vcost.setdefault(f"{h}__N{n}", []).append(time.perf_counter() - tv)
                        ok("cells_rederived", same, name)
                    else:
                        ok("no_cells_unless_decided", r["cells"] is None, name)
                    view = tuple(json.dumps(r[k]) for k in RESULT_KEYS)
                    if cfg == "SER_E2":
                        e2groups.setdefault((h, n), []).append((name, view, r))
                        ok("serial_swap_restored", r["force_swap_restored"] is True, name)
                        ok("affinity", r["affinity"] == [SERIAL_CPU], name)
                    else:
                        groups.setdefault((h, n), []).append((name, view, r))
                    if cfg == "SER_E1":
                        ok("serial_swap_restored", r["force_swap_restored"] is True, name)
                        ok("affinity", r["affinity"] == [SERIAL_CPU], name)
                        W = 0
                    elif cfg.startswith("PAR_"):
                        W = int(cfg[4:])
                        cpus = WORKER_CORES[:W]
                        ok("affinity", r["main_affinity"] == [MAIN_CPU] and r["worker_cpus"] == cpus and
                           [x["affinity"] for x in r["worker_hello"]] == [[c] for c in cpus] and
                           r["worker_parent_pin"] == [[c] for c in cpus] and
                           [x["affinity_end"] for x in r["worker_bye"]] == [[c] for c in cpus], name)
                        ok("workers_exited", r["workers_exited"] == [0] * W, name)
                        ok("worker_precision", all(x["iv_prec"] == P for x in r["worker_hello"]), name)
                        npairs = n * (n - 1) // 2
                        bs = r["block_sizes"]
                        ok("blocks", sum(bs) == npairs and max(bs) - min(bs) <= 1 and len(bs) == W, name)
                    else:
                        W = 0
                    ok("cpu_sanity", r["total_cpu_s"] <= (W + 1) * r["end_to_end_wall_s"] * 1.10 + 1.0, name)
    for key, rows in groups.items():
        ref = rows[0][1]
        for name, view, _ in rows:
            ok("result_equal_serial_parallel_reps", view == ref, f"{name} vs {rows[0][0]}")
    for key, rows in e2groups.items():
        ref = rows[0][1]
        for name, view, _ in rows:
            ok("E2_reps_equal", view == ref, name)
        e1 = groups[key][0][2]
        e2 = rows[0][2]
        if e1["outcome"] == "DECIDED" and e2["outcome"] == "DECIDED":
            ok("E2_cells_equal_E1", e1["cells"] == e2["cells"], str(key))
    t_verify = time.perf_counter() - t_verify
    bad = sum(c[1] for c in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "counts": counts, "issues": issues[:50],
            "n_issues": len(issues), "checker_wall_s": t_verify,
            "verify_cost_cells_s_median": {k: sorted(v)[len(v) // 2] for k, v in vcost.items()}, "decided_readouts_rederived": verify_cells}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], {k: v for k, v in res["counts"].items()}, res["issues"][:5])


if __name__ == "__main__":
    main()
