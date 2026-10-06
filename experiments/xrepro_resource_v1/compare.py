"""XREPRO_RESOURCE_V1 comparator. Reads JSON records only: the run-2 reference bundle and one or more machine output
directories written by xrepro.py. Imports no executor module; cells are re-derived from the exact endpoints with the
A1 checker's own half-even rounding (as the run-2 verifier/checker do).

    python -m experiments.xrepro_resource_v1.compare --ref RUN2_RESULTS_GZ --run NAME=DIR [--run NAME=DIR ...] --out OUT
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import statistics
from pathlib import Path

from experiments.precision_pilot_a1 import checker as A1C

PASS_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "effective_p", "requested_p", "evaluator", "scenario",
             "T", "cells", "endpoints_scaled")
VOLATILE = re.compile(r"(^|_)(cpu_s|wall_s)$|^(pid|python|probe_file|modules|t_wall|t_cpu)$")


def strip(x):
    """Remove timing, pid and path fields (recursively) so that only computed content is compared."""
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if not VOLATILE.search(k)}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def first_diff(a, b, path=""):
    """Path of the first difference between two JSON values (None if equal)."""
    if type(a) is not type(b):
        return f"{path}: type {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return f"{path}/{k}: missing on one side"
            d = first_diff(a[k], b[k], f"{path}/{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else f"{path}: {str(a)[:80]} != {str(b)[:80]}"


def pass_view(p):
    return {k: p.get(k) for k in PASS_KEYS}


def cells_ok(p):
    if p.get("outcome") != "DECIDED":
        return True
    return A1C.my_cells(p["endpoints_scaled"]) == p["cells"]


def load_run(d):
    d = Path(d)
    recs = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in d.glob("*.json")
            if f.name not in ("execution_seal.json",)}
    gates = {f.name: json.loads(f.read_text(encoding="utf-8")) for f in (d / "X3_e2_gates").glob("*.json")}
    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    return recs, gates, seal


def compare(ref_gz, runs):
    ref = {k: (json.loads(v) if k.endswith(".json") else v)
           for k, v in json.load(gzip.open(ref_gz))["run"].items()}
    out = {"checks": {}, "first_differences": [], "perf": {}, "env": {}}
    diffs = out["first_differences"]

    def check(name, ok, detail=None):
        out["checks"].setdefault(name, {"pass": 0, "fail": 0})
        out["checks"][name]["pass" if ok else "fail"] += 1
        if not ok:
            diffs.append({"check": name, "detail": detail})

    envs = {}
    for mname, d in runs.items():
        recs, gates, seal = load_run(d)
        env = recs["X1X2__env"]
        envs[mname] = env
        order = env["core_map"]["worker_core_order"]
        out["env"][mname] = {k: env[k] for k in ("host", "python", "platform", "cpu_name", "os_version",
                                                 "cpu_count_logical", "cpu_count_physical", "ram_bytes", "mpmath",
                                                 "mpmath_backend", "psutil", "sympy", "gmpy2_importable",
                                                 "git_head", "git_branch")}
        out["env"][mname]["git_status_clean"] = env["git_status_porcelain"] == ""
        check("X1_clean_tree", env["git_status_porcelain"] == "", f"{mname}: {env['git_status_porcelain'][:200]}")
        check("X1_seal_head_equals_env_head", seal["head"] == env["git_head"], mname)
        check("X2_no_gmpy2", env["gmpy2_importable"] is False and env["mpmath_backend"] == "python", mname)
        # X3 gates
        v, sy = gates.get("verify.json", {}), gates.get("sympy.json", {})
        check("X3_E2_S1_S6", v.get("PASS_S1_S6_except_S3b") is True, f"{mname}: {v.get('PASS_S1_S6_except_S3b')}")
        check("X3_E2_sympy", sy.get("sympy_zero") is True, f"{mname}: {sy.get('sympy_zero')}")
        for g in ("refs.json", "verify.json", "sympy.json"):
            fd = first_diff(strip(ref[f"T0_e2_gates/{g}"]), strip(gates.get(g, {})))
            check("X3_gate_output_equal_run2", fd is None, f"{mname} {g}: {fd}")
        # X4/X5 T0 representative passes
        for name, r in recs.items():
            if not name.startswith("X4__"):
                continue
            _, ev, req, pos = name.split("__")
            refrec = ref[f"T0__{ev}__{req}__cpu2.json"]
            mine = pass_view(r["workers"][0]["passes"][0])
            fd = first_diff(pass_view(refrec["workers"][0]["passes"][0]), mine)
            check("X5_T0_equal_run2", fd is None, f"{mname} {name}: {fd}")
            check("X5_cells_rederived", cells_ok(mine), f"{mname} {name}")
            check("X5_status_verified", r["status"] == "VERIFIED", f"{mname} {name}: {r['status']}")
            w = r["workers"][0]
            check("X7_affinity", w["start"]["affinity_readback"] == w["spec"]["cpus"] and len(w["spec"]["cpus"]) == 1
                  and w["spec"]["cpus"][0] in order and w["parent_pinned"] == w["spec"]["cpus"], f"{mname} {name}")
        # X6 batches
        perf = {}
        for name, r in recs.items():
            if not name.startswith("X6__"):
                continue
            _, plan, k, rep = name.split("__")
            refb = ref[f"T1__{plan}__k1__r0.json"]
            for key, e in r["results"].items():
                fd = first_diff([pass_view(p) for p in refb["results"][key]["passes"]],
                                [pass_view(p) for p in e["passes"]])
                check("X6_batch_equal_run2", fd is None, f"{mname} {name} {key}: {fd}")
                check("X6_status_verified", e["status"] == "VERIFIED", f"{mname} {name} {key}: {e['status']}")
                for p in e["passes"]:
                    check("X5_cells_rederived", cells_ok(p), f"{mname} {name} {key}")
                check("X7_affinity", e["start"]["affinity_readback"] == [e["core"]] and e["core"] in order
                      and e["parent_pinned"] == [e["core"]], f"{mname} {name} {key}")
            perf.setdefault((plan, int(k[1:])), []).append((r["wall_s"], r["total_cpu_s"]))
        rows = {}
        for (plan, k), xs in sorted(perf.items()):
            rows[f"{plan}@k{k}"] = {"n": len(xs), "wall_median_s": statistics.median(x[0] for x in xs),
                                    "cpu_median_s": statistics.median(x[1] for x in xs),
                                    "walls": [x[0] for x in xs], "cpus": [x[1] for x in xs]}
        for plan in ("BASE", "BASE_E2"):
            w1 = rows.get(f"{plan}@k1", {}).get("wall_median_s")
            for key, row in rows.items():
                if key.startswith(plan + "@") and w1:
                    k = int(key.split("@k")[1])
                    row["speedup"] = w1 / row["wall_median_s"]
                    row["efficiency"] = row["speedup"] / k
        for key in [k for k in rows if k.startswith("BASE@")]:
            e2 = rows.get(key.replace("BASE@", "BASE_E2@"))
            if e2:
                rows[key]["e2_over_e1_cpu"] = e2["cpu_median_s"] / rows[key]["cpu_median_s"]
                rows[key]["e2_over_e1_wall"] = e2["wall_median_s"] / rows[key]["wall_median_s"]
        out["perf"][mname] = rows
        # X8 pair parallel
        for s in ("A3_low", "A3_high"):
            r = recs.get(f"X8__S4__{s}_100")
            if r is None:
                check("X8_present", False, f"{mname} {s}")
                continue
            rr = ref[f"T2__S4__{s}_100__r0.json"]
            check("X8_bit_identical_local", r["bit_identical"] is True, f"{mname} {s}")
            for part in ("serial", "parallel"):
                fd = first_diff(rr[part]["endpoints_scaled"], r[part]["endpoints_scaled"])
                check("X8_equal_run2", fd is None, f"{mname} {s} {part}: {fd}")
    # cross-machine environment and source equality
    names = list(envs)
    for a in names[1:]:
        e0, e1 = envs[names[0]], envs[a]
        check("X1_same_head", e0["git_head"] == e1["git_head"], f"{names[0]} {e0['git_head']} vs {a} {e1['git_head']}")
        check("X1_same_source_hashes", e0["source_sha256_lf"] == e1["source_sha256_lf"],
              first_diff(e0["source_sha256_lf"], e1["source_sha256_lf"]))
        same_env = all(e0[k] == e1[k] for k in ("python", "mpmath", "mpmath_backend", "sympy", "psutil"))
        out["env_versions_identical"] = same_env
    failed = any(v["fail"] for v in out["checks"].values())
    if not failed:
        out["verdict"] = "REPRODUCED"
    else:
        out["verdict"] = "ENV_DIFFERENCE" if not out.get("env_versions_identical", True) else "MISMATCH"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    runs = dict(x.split("=", 1) for x in a.run)
    res = compare(a.ref, runs)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], {k: v for k, v in res["checks"].items()})
    for d in res["first_differences"][:10]:
        print("DIFF", d)


if __name__ == "__main__":
    main()
