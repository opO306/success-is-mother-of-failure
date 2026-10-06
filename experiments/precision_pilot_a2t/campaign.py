"""PRECISION_PILOT_A2T campaign. Sequential fresh processes; each result JSON is written at once (a partial campaign
survives and resumes by skipping existing files).

Order: seal -> audit (+ upstream tests) -> short evaluation (3 reps, 7 combinations interleaved) -> algebra
INVESTIGATE (short) -> long evaluation (1 rep).

    python -m experiments.precision_pilot_a2t.campaign --out DIR [--phase all|short|long]
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
PKG = "experiments.precision_pilot_a2t"
UP = ROOT / "experiments/formula_repro_b_v0/upstream"
SCEN = ("A2_bound", "A3_low", "A3_high")
SHORT_T = (100, 1000)
LONG_T = (3000, 5000, 10000)
COMBOS = (("original", "P0"), ("original", "P2"), ("original", "P3"),
          ("algebra", "P0"), ("algebra", "P1"), ("algebra", "P2"), ("algebra", "P3"))
CAMPAIGN_CPU_CAP = 18000.0
PARAMS = HERE / "frozen_policy_params_a1.json"
SEALED = ["experiments/precision_pilot_a2t/" + f for f in
          ("protocol.json", "frozen_policy_params_a1.json", "evaluator_adapter.py", "runner.py", "campaign.py")] + \
         ["experiments/precision_pilot_a1/" + f for f in ("policies.py", "evaluator_adapter.py", "protocol.json")] + \
         ["experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/transform_checks.py",
          "experiments/formula_repro_b_v0/upstream/probe.py", "exact_expression_gate_v1/stream.py",
          "exact_expression_gate_v1/common.py", "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py"]


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


_SPENT = []


def spent(out):
    if not _SPENT:
        _SPENT.append(sum(json.loads(f.read_text(encoding="utf-8")).get("child_cpu_s", 0) for f in out.glob("*.json")
                          if f.name.startswith(("eval__", "inv__", "audit"))))
    return _SPENT[0]


def job(out, args, name):
    path = out / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if spent(out) >= CAMPAIGN_CPU_CAP:
        log(out, f"CAMPAIGN_CPU_CAP reached before {name}: STOP")
        raise SystemExit(2)
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
    _SPENT[0] += doc.get("child_cpu_s", 0)
    brief = doc.get("tried_p") or doc.get("requested_p") or ""
    log(out, f"done {name} {doc.get('status') or doc.get('outcome') or doc.get('PASS')} {brief} ({wall:.1f}s)")
    return doc


def seal(out):
    s = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
         "status_porcelain": git("status", "--porcelain"), "origin_master": git("rev-parse", "origin/master"),
         "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
         "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version,
         "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out / "execution_seal.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
    return s


def upstream_tests(out):
    f = out / "upstream_pytest.txt"
    if f.exists():
        return
    ini = out / "empty_pytest.ini"
    ini.write_text("[pytest]\n", encoding="utf-8")
    t = time.perf_counter()
    r = subprocess.run([sys.executable, "-m", "pytest", "test_probe.py", "-q", "-p", "no:cacheprovider", "-c", str(ini),
                        "--rootdir", "."], cwd=UP, capture_output=True, text=True, encoding="utf-8", errors="replace")
    f.write_text(r.stdout + "\n" + r.stderr + f"\nexit_code={r.returncode}\n", encoding="utf-8")
    log(out, f"upstream tests rc={r.returncode} ({time.perf_counter() - t:.1f}s)")


def order(rep):
    k = (2 * rep) % len(COMBOS)
    o = list(COMBOS[k:] + COMBOS[:k])
    return o[::-1] if rep % 2 else o


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", default="all", choices=["all", "short", "long"])
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "execution_seal.json").exists():
        if seal(out)["sealed_sources_dirty"]:
            log(out, "sealed sources dirty: STOP")
            return
    upstream_tests(out)
    au = job(out, ["audit"], "audit")
    if not au or not au["PASS"]:
        log(out, "algebra audit failed: STOP")
        return
    if a.phase in ("all", "short"):
        for rep in range(3):
            for scen in SCEN:
                for T in SHORT_T:
                    for ev, pol in order(rep):
                        job(out, ["serve", ev, scen, str(T), pol, str(PARAMS)], f"eval__{scen}__T{T}__{ev}__{pol}__r{rep}")
        for scen in SCEN:
            for T in SHORT_T:
                tried, low = set(), None
                for f in out.glob(f"eval__{scen}__T{T}__algebra__*.json"):
                    for h in json.loads(f.read_text(encoding="utf-8"))["passes"]:
                        tried.add(h["requested_p"])
                        if h["outcome"] == "DECIDED":
                            low = h["requested_p"] if low is None else min(low, h["requested_p"])
                if low is None:
                    continue
                for p in range(64, low):
                    if p not in tried:
                        job(out, ["pass", "algebra", scen, str(T), str(p)], f"inv__{scen}__T{T}__algebra__p{p}")
                log(out, f"investigate algebra {scen} T{T} lowest SERVE success {low}")
    if a.phase in ("all", "long"):
        for scen in SCEN:
            for T in LONG_T:
                for ev, pol in order(0):
                    job(out, ["serve", ev, scen, str(T), pol, str(PARAMS)], f"eval__{scen}__T{T}__{ev}__{pol}__r0")
    log(out, f"phase {a.phase} finished; campaign child CPU so far {spent(out):.0f}s")


if __name__ == "__main__":
    main()
