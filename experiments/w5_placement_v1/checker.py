"""Independent checker of W5_PLACEMENT_V1. Reads JSON records only; imports no executor module (plan, run, campaign,
stream, adapters). Initial states: the MULTIATOM checker's own generator; cells: the A1 checker's rounding.

    python -m experiments.w5_placement_v1.checker DIR
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

from experiments.multiatom_parallel_v1 import checker as MAC
from experiments.precision_pilot_a1 import checker as A1C

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
CONFIGS = ["SER_E2", "W4_DEDICATED", "W5_DEDICATED", "W6_SHARED"]
RESULT_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells", "initial_sha256")
SUSPECT = re.compile(r"python|roblox|codex|node", re.I)
E2P_EVIDENCE = ROOT / "docs/active/e2_pair_parallel_v1/laptop_run/records.json.gz"


def my_contaminated(rows):
    return sum(v for _, _, v in rows) >= 100.0 or any(SUSPECT.search(n or "") and v >= 25.0 for n, _, v in rows)


def check(d):
    d = Path(d)
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    ok("seal_clean", seal["status_porcelain"] == "" and not seal["sealed_sources_dirty"], seal["status_porcelain"][:200])
    topo = json.loads((d / "topology.json").read_text(encoding="utf-8"))
    ok("topology_as_sealed", topo["logical"] == 6 and topo["physical"] == 6 and
       [c["group_cpus"] for c in topo["cores"]] == [[[0, [k]]] for k in range(6)] and
       not any(c["smt"] for c in topo["cores"]))
    rate = json.loads((d / "cycle_rate.json").read_text(encoding="utf-8"))["rate_hz"]
    snaps = {}
    for ln in (d / "load_snapshots.jsonl").read_text(encoding="utf-8").splitlines():
        s = json.loads(ln)
        snaps[s["tag"]] = s
        ok("contamination_rederived", my_contaminated(s["rows"]) == s["contaminated"], s["tag"])
    prior = {}
    if E2P_EVIDENCE.exists():
        files = json.load(gzip.open(E2P_EVIDENCE))["files"]
        prior = {json.loads(v)["N"]: json.loads(v) for k, v in files.items() if k.startswith("H100__") and
                 "__SER_E2__r0" in k}
    groups, contaminated = {}, []
    T, P = PROTO["scope"]["T"], PROTO["scope"]["p"]
    for n in PROTO["scope"]["N"]:
        digest = MAC.my_digest(*MAC.my_initial(n))
        for rep in range(PROTO["scope"]["repetitions"]):
            tag = f"N{n}__r{rep}"
            ok("snapshot_present", tag in snaps, tag)
            if snaps.get(tag, {}).get("contaminated"):
                contaminated.append(tag)
            for cfg in CONFIGS:
                name = f"N{n}__{cfg}__r{rep}"
                f = d / f"{name}.json"
                ok("complete", f.exists(), name)
                if not f.exists():
                    continue
                r = json.loads(f.read_text(encoding="utf-8"))
                c = PROTO["configurations"][cfg]
                plan = r["plan"]
                ok("plan_as_sealed", plan == {"evaluator": "rw:R1+R2", "precision": P, "backend": c["backend"],
                                              "worker_count": c["worker_count"], "main_cpu": c["main_cpu"],
                                              "worker_cpus": c["worker_cpus"]}, name)
                ok("meta", (r["N"], r["T"], r["p"], r["effective_p"], r["evaluator"]) == (n, T, P, P, "rw:R1+R2"), name)
                ok("initial_state", r["initial_sha256"] == digest, name)
                ok("group_flag", r["group_contaminated"] == snaps.get(tag, {}).get("contaminated"), name)
                wcyc = [b["cycles"] for b in r.get("worker_bye", [])]
                ok("cycle_cpu_consistent", r["main_cycles"] + sum(wcyc) == r["total_cycles"] and
                   r["cycle_rate_hz"] == rate and abs(r["total_cpu_s"] - r["total_cycles"] / rate) < 1e-9, name)
                if r["outcome"] == "DECIDED":
                    ok("cells_rederived", A1C.my_cells(r["endpoints_scaled"]) == r["cells"], name)
                if c["backend"] == "CPU_SERIAL":
                    W = 0
                    ok("affinity", r["affinity"] == [c["main_cpu"]], name)
                    ok("serial_swap_restored", r["force_swap_restored"] is True, name)
                    if n in prior and prior[n]["T"] == r["T"] and prior[n]["p"] == r["p"]:
                        ok("SER_E2_equal_to_E2_PAIR_PARALLEL_evidence",
                           all(json.dumps(prior[n][k]) == json.dumps(r[k]) for k in RESULT_KEYS), name)
                else:
                    W = c["worker_count"]
                    cpus = c["worker_cpus"]
                    ok("affinity", r["main_affinity"] == [c["main_cpu"]] and r["worker_cpus"] == cpus and
                       [x["affinity"] for x in r["worker_hello"]] == [[k] for k in cpus] and
                       r["worker_parent_pin"] == [[k] for k in cpus] and
                       [x["affinity_end"] for x in r["worker_bye"]] == [[k] for k in cpus], name)
                    ok("worker_evaluator", all(x["evaluator"] == "rw:R1+R2" and x["force_type"] == "RwForce" and
                                               x["iv_prec"] == P for x in r["worker_hello"]), name)
                    ok("workers_exited", r["workers_exited"] == [0] * W, name)
                    bs = r["block_sizes"]
                    ok("blocks", sum(bs) == n * (n - 1) // 2 and max(bs) - min(bs) <= 1 and len(bs) == W, name)
                ok("cpu_sanity", r["total_cpu_s"] <= (W + 1) * r["end_to_end_wall_s"] * 1.10 + 1.0, name)
                groups.setdefault(n, []).append((name, tuple(json.dumps(r[k]) for k in RESULT_KEYS)))
    for n, rows in groups.items():
        for name, view in rows:
            ok("bit_identical_all_configs_reps", view == rows[0][1], f"{name} vs {rows[0][0]}")
    bad = sum(v[1] for v in counts.values())
    mismatch = counts.get("bit_identical_all_configs_reps", [0, 0])[1] + \
        counts.get("SER_E2_equal_to_E2_PAIR_PARALLEL_evidence", [0, 0])[1]
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "bit_mismatches": mismatch, "counts": counts,
            "issues": issues[:60], "contaminated_groups": contaminated, "prior_evidence_used": bool(prior)}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], "bit mismatches", res["bit_mismatches"], {k: v for k, v in res["counts"].items()},
          res["issues"][:5], "contaminated:", res["contaminated_groups"])


if __name__ == "__main__":
    main()
