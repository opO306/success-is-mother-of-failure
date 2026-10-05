"""PRECISION_PILOT_A1 campaign. Sequential fresh processes; each result JSON is written at once (a partial campaign
survives and resumes by skipping existing files).

Phases: seal -> evaluator p-support audit -> training (P2 on training requests) -> freeze P1/P3 params ->
evaluation short (3 reps) -> INVESTIGATE short -> evaluation long (1 rep).

    python -m experiments.precision_pilot_a1.campaign --out DIR [--phase all|short|long]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PKG = "experiments.precision_pilot_a1"
SCEN = ("A2_bound", "A3_low", "A3_high")
TRAIN_T = (200, 2000)
SHORT_T = (100, 1000)
LONG_T = (3000, 5000, 10000)
POLICIES = ("P0", "P1", "P2", "P3")
SEALED = ["experiments/precision_pilot_a1/" + f for f in
          ("protocol.json", "evaluator_adapter.py", "policies.py", "runner.py", "campaign.py")] + \
         ["exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py", "exact_expression_gate_v0/lang_iv.py",
          "a_reference/ar2_lang2024.py"]


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def log(out, msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(out / "campaign.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def job(out, args, name):
    path = out / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    t = time.perf_counter()
    p = subprocess.Popen([sys.executable, "-m", f"{PKG}.runner", *args, str(path)], cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    so, se = p.communicate()
    wall = time.perf_counter() - t
    if p.returncode != 0 or not path.exists():
        (out / f"{name}.ERROR.txt").write_text(so + "\n" + se, encoding="utf-8")
        log(out, f"ERROR {name} rc={p.returncode}")
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.update(parent_process_wall_s=wall, child_exit_code=p.returncode, child_pid_confirmed_exited=p.poll() is not None)
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    brief = doc.get("tried_p") or doc.get("requested_p") or ""
    log(out, f"done {name} {doc.get('status') or doc.get('outcome') or ''} {brief} ({wall:.1f}s)")
    return doc


def seal(out):
    s = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
         "status_porcelain": git("status", "--porcelain"), "origin_master": git("rev-parse", "origin/master"),
         "origin_master_reflog": git("reflog", "show", "origin/master", "-n", "3"),
         "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
         "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version,
         "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out / "execution_seal.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", default="all", choices=["all", "short", "long"])
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "execution_seal.json").exists():
        s = seal(out)
        if s["sealed_sources_dirty"]:
            log(out, "sealed sources dirty: STOP")
            return
    au = job(out, ["audit"], "audit")
    if not au or not au["PASS"]:
        log(out, "evaluator p-support audit failed: STOP")
        return
    train = {}
    for scen in SCEN:
        for T in TRAIN_T:
            d = job(out, ["serve", scen, str(T), "P2", "-"], f"train__{scen}__T{T}__P2")
            if d is None:
                log(out, "training run failed: STOP")
                return
            train[f"{scen}@{T}"] = d["passes"]
    params_path = out / "policy_params.json"
    if not params_path.exists():
        sys.path.insert(0, str(ROOT))
        from experiments.precision_pilot_a1 import policies as POL
        params, h = POL.train({(k.split("@")[0], int(k.split("@")[1])): v for k, v in train.items()})
        params_path.write_text(json.dumps({**params, "policy_hash": h}, indent=1), encoding="utf-8")
        log(out, f"frozen params s1={params['s1']} lines={params['lines']} hash={h[:12]}")
    if a.phase in ("all", "short"):
        for rep in range(3):
            order = list(POLICIES[rep:] + POLICIES[:rep])
            if rep % 2:
                order.reverse()
            for scen in SCEN:
                for T in SHORT_T:
                    for pol in order:
                        job(out, ["serve", scen, str(T), pol, str(params_path)], f"eval__{scen}__T{T}__{pol}__r{rep}")
        for scen in SCEN:
            for T in SHORT_T:
                tried, low = set(), None
                for pol in POLICIES:
                    for rep in range(3):
                        f = out / f"eval__{scen}__T{T}__{pol}__r{rep}.json"
                        if f.exists():
                            d = json.loads(f.read_text(encoding="utf-8"))
                            for h in d["passes"]:
                                tried.add(h["requested_p"])
                                if h["outcome"] == "DECIDED":
                                    low = h["requested_p"] if low is None else min(low, h["requested_p"])
                if low is None:
                    continue
                for p in range(64, low):
                    if p not in tried:
                        job(out, ["pass", scen, str(T), str(p)], f"inv__{scen}__T{T}__p{p}")
                log(out, f"investigate {scen} T{T} lowest SERVE success {low}")
    if a.phase in ("all", "long"):
        for scen in SCEN:
            for T in LONG_T:
                for pol in POLICIES:
                    job(out, ["serve", scen, str(T), pol, str(params_path)], f"eval__{scen}__T{T}__{pol}__r0")
    log(out, f"phase {a.phase} finished")


if __name__ == "__main__":
    main()
