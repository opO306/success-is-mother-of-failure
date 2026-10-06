"""Independent checker of E2_PAIR_PARALLEL_V1 (protocol.json 'checker'). Reads JSON records only; imports no executor
module (run, campaign, stream, adapters). Initial states are regenerated with the MULTIATOM checker's own generator;
cells are re-derived with the A1 checker's own half-even rounding.

    python -m experiments.e2_pair_parallel_v1.checker DIR
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time
from pathlib import Path

from experiments.multiatom_parallel_v1 import checker as MAC
from experiments.precision_pilot_a1 import checker as A1C

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
CONFIGS = ["SER_E1", "SER_E2", "PAR_E1_W3", "PAR_E2_W3", "PAR_E1_W4", "PAR_E2_W4", "PAR_E1_W6", "PAR_E2_W6"]
EV = {"E1": "algebra", "E2": "rw:R1+R2"}
FORCE_TYPE = {"algebra": "Force", "rw:R1+R2": "RwForce"}
RESULT_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells")
SUSPECT = re.compile(r"python|roblox|codex|node", re.I)
MA_EVIDENCE = ROOT / "docs/active/multiatom_parallel_v1/laptop_run/records.json.gz"


def horizons(machine):
    if machine == "desktop":
        return {"H100": (100, [3, 4, 6, 12]), "H1000": (1000, [3, 4, 6, 12])}
    return {"H100": (100, PROTO["scope"]["N_list"]), "H1000": (1000, [3, 4, 6, 12])}


def my_contaminated(rows):
    total = sum(v for _, _, v in rows)
    return total >= 100.0 or any(SUSPECT.search(n or "") and v >= 25.0 for n, _, v in rows)


def check(d):
    d = Path(d)
    t0 = time.perf_counter()
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    machine = seal["machine"]
    mm = PROTO["machines"][machine]
    ok("seal_clean", seal["status_porcelain"] == "" and not seal["sealed_sources_dirty"], seal["status_porcelain"][:200])
    ok("seal_machine_map", seal["machine_map"] == mm)
    g = d / "gates"
    v = json.loads((g / "verify.json").read_text(encoding="utf-8"))
    sy = json.loads((g / "sympy.json").read_text(encoding="utf-8"))
    dm = json.loads((g / "e2_domain.json").read_text(encoding="utf-8"))
    ok("E2_gate_S1_S6", v.get("PASS_S1_S6_except_S3b") is True)
    ok("E2_gate_sympy", sy.get("sympy_zero") is True)
    ok("E2_gate_new_domain", dm.get("PASS") is True and all(r["E1_contains_E0_1024"] and r["E2_contains_E0_1024"]
                                                             for r in dm["rows"]))
    rate = json.loads((d / "cycle_rate.json").read_text(encoding="utf-8"))["rate_hz"]
    snaps = {}
    for ln in (d / "load_snapshots.jsonl").read_text(encoding="utf-8").splitlines():
        s = json.loads(ln)
        snaps[s["tag"]] = s
        ok("contamination_rederived", my_contaminated(s["rows"]) == s["contaminated"], s["tag"])
    ma = {}
    if MA_EVIDENCE.exists():
        files = json.load(gzip.open(MA_EVIDENCE))["files"]
        ma = {k[:-5]: json.loads(v) for k, v in files.items() if k.startswith("H") and k.endswith(".json")}
    groups, contaminated_groups = {}, []
    for h, (T, ns) in horizons(machine).items():
        for n in ns:
            digest = MAC.my_digest(*MAC.my_initial(n))
            for rep in range(PROTO["scope"]["repetitions"]):
                tag = f"{h}__N{n}__r{rep}"
                ok("snapshot_present", tag in snaps, tag)
                if snaps.get(tag, {}).get("contaminated"):
                    contaminated_groups.append(tag)
                for cfg in CONFIGS:
                    name = f"{h}__N{n}__{cfg}__r{rep}"
                    f = d / f"{name}.json"
                    ok("complete", f.exists(), name)
                    if not f.exists():
                        continue
                    r = json.loads(f.read_text(encoding="utf-8"))
                    e = cfg.split("_")[1]
                    ev = EV[e]
                    ok("meta", (r["N"], r["T"], r["p"], r["effective_p"], r["config"], r["evaluator"])
                       == (n, T, 128, 128, cfg, ev), name)
                    ok("initial_state", r["initial_sha256"] == digest, name)
                    ok("group_flag", r["group_contaminated"] == snaps.get(tag, {}).get("contaminated"), name)
                    cyc = r["main_cycles"] + sum(b["cycles"] for b in r.get("worker_bye", []))
                    ok("cycle_cpu_consistent", cyc == r["total_cycles"] and r["cycle_rate_hz"] == rate and
                       abs(r["total_cpu_s"] - cyc / rate) < 1e-9, name)
                    if r["outcome"] == "DECIDED":
                        ok("cells_rederived", A1C.my_cells(r["endpoints_scaled"]) == r["cells"], name)
                    else:
                        ok("no_cells_unless_decided", r["cells"] is None, name)
                    if cfg.startswith("SER_"):
                        W = 0
                        ok("serial_swap_restored", r["force_swap_restored"] is True, name)
                        ok("affinity", r["affinity"] == [mm["serial_cpu"]], name)
                        mrec = ma.get(f"{h}__N{n}__{cfg}__r{rep}")
                        if mrec is not None and mrec["T"] == r["T"] and mrec["N"] == r["N"]:
                            ok("equal_to_MULTIATOM_evidence",
                               all(json.dumps(mrec[k]) == json.dumps(r[k]) for k in RESULT_KEYS), name)
                    else:
                        W = int(cfg.split("_W")[1])
                        cpus = mm["worker_cores"][:W]
                        ok("affinity", r["main_affinity"] == [mm["main_cpu"]] and r["worker_cpus"] == cpus and
                           [x["affinity"] for x in r["worker_hello"]] == [[c] for c in cpus] and
                           r["worker_parent_pin"] == [[c] for c in cpus] and
                           [x["affinity_end"] for x in r["worker_bye"]] == [[c] for c in cpus], name)
                        ok("worker_evaluator", all(x["evaluator"] == ev and x["force_type"] == FORCE_TYPE[ev] and
                                                   x["iv_prec"] == 128 for x in r["worker_hello"]), name)
                        ok("workers_exited", r["workers_exited"] == [0] * W, name)
                        bs = r["block_sizes"]
                        ok("blocks", sum(bs) == n * (n - 1) // 2 and max(bs) - min(bs) <= 1 and len(bs) == W, name)
                    ok("cpu_sanity", r["total_cpu_s"] <= (W + 1) * r["end_to_end_wall_s"] * 1.10 + 1.0, name)
                    groups.setdefault((h, n, e), []).append((name, tuple(json.dumps(r[k]) for k in RESULT_KEYS), r))
    for (h, n, e), rows in groups.items():
        ref = rows[0][1]
        for name, view, _ in rows:
            ok(f"bit_identical_{e}_all_W_reps", view == ref, f"{name} vs {rows[0][0]}")
    for (h, n, e), rows in groups.items():
        if e != "E1" or (h, n, "E2") not in groups:
            continue
        a, b = rows[0][2], groups[(h, n, "E2")][0][2]
        if a["outcome"] == "DECIDED" and b["outcome"] == "DECIDED":
            ok("E1_E2_cells_equal", a["cells"] == b["cells"], f"{h} N{n}")
    bad = sum(c[1] for c in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "machine": machine, "counts": counts,
            "issues": issues[:60], "n_issues": len(issues), "contaminated_groups": contaminated_groups,
            "multiatom_evidence_used": bool(ma), "checker_wall_s": time.perf_counter() - t0}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], res["machine"], {k: v for k, v in res["counts"].items()}, res["issues"][:5],
          "contaminated:", res["contaminated_groups"])


if __name__ == "__main__":
    main()
