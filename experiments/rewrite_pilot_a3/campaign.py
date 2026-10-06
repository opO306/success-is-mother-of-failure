"""REWRITE_PILOT_A3 campaign. Sequential fresh processes; results written at once; resumes by skipping existing files.

screen: seal -> upstream tests -> refs -> verify (S1-S6 minus S3b) and sympy (S3b, 300 s timeout) per candidate ->
        screening cost passes (T 1000, p 128, 3 reps) and width passes (T 3000, p 192) for passing candidates ->
        selection (FAST, NARROW) by the sealed rule.
serve : short (3 reps) and long (1 rep) SERVE runs with frozen P0/P2/P3, then rewrite INVESTIGATE (short).

    python -m experiments.rewrite_pilot_a3.campaign --out DIR --phase screen|serve
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PKG = "experiments.rewrite_pilot_a3"
UP = ROOT / "experiments/formula_repro_b_v0/upstream"
sys.path.insert(0, str(ROOT))
from experiments.rewrite_pilot_a3 import rules as RU  # noqa: E402

SCEN = ("A2_bound", "A3_low", "A3_high")
SHORT_T, LONG_T = (100, 1000), (3000, 5000, 10000)
SCREEN_COST = (1000, 128, 3)
SCREEN_WIDTH = (3000, 192)
SCREEN_CAP, SERVE_CAP = 3600.0, 10800.0
SYMPY_TIMEOUT = 300
SEALED = ["experiments/rewrite_pilot_a3/" + f for f in
          ("protocol.json", "rules.py", "rwforce.py", "symbolic.py", "adapter.py", "runner.py", "campaign.py")] + \
         ["experiments/precision_pilot_a2t/evaluator_adapter.py", "experiments/precision_pilot_a2t/frozen_policy_params_a1.json",
          "experiments/precision_pilot_a1/policies.py", "experiments/precision_pilot_a1/evaluator_adapter.py",
          "experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/upstream/probe.py",
          "exact_expression_gate_v1/stream.py", "exact_expression_gate_v1/common.py",
          "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py"]


def safe(ev):
    return ev.replace(":", "-").replace("+", "_")


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


_SPENT = {}


def spent(out, prefixes):
    key = prefixes
    if key not in _SPENT:
        _SPENT[key] = sum(json.loads(f.read_text(encoding="utf-8")).get("child_cpu_s", 0) for f in out.glob("*.json")
                          if f.name.startswith(prefixes))
    return _SPENT[key]


def job(out, args, name, cap=None, prefixes=None, timeout=None):
    path = out / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if cap is not None and spent(out, prefixes) >= cap:
        log(out, f"CPU cap {cap:.0f}s reached before {name}: STOP")
        raise SystemExit(2)
    t = time.perf_counter()
    p = subprocess.Popen([sys.executable, "-m", f"{PKG}.runner", *args, str(path)], cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    try:
        so, se = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        so, se = p.communicate()
        doc = {"mode": args[0], "evaluator": args[1], "status": "REFUSED_TIMEOUT", "timeout_s": timeout,
               "child_exit_code": None, "child_pid_confirmed_exited": p.poll() is not None,
               "parent_process_wall_s": time.perf_counter() - t}
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        log(out, f"TIMEOUT {name} after {timeout}s: REFUSED")
        return doc
    wall = time.perf_counter() - t
    if p.returncode != 0 or not path.exists():
        (out / f"{name}.ERROR.txt").write_text(so + "\n" + se, encoding="utf-8")
        log(out, f"ERROR {name} rc={p.returncode}")
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.update(parent_process_wall_s=wall, child_exit_code=p.returncode, child_pid_confirmed_exited=p.poll() is not None)
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    for k in list(_SPENT):
        if name.startswith(k):
            _SPENT[k] += doc.get("child_cpu_s", 0)
    brief = doc.get("tried_p") or doc.get("requested_p") or doc.get("PASS_S1_S6_except_S3b", doc.get("sympy_zero", ""))
    log(out, f"done {name} {doc.get('status') or doc.get('outcome') or ''} {brief} ({wall:.1f}s)")
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
    r = subprocess.run([sys.executable, "-m", "pytest", "test_probe.py", "-q", "-p", "no:cacheprovider", "-c", str(ini),
                        "--rootdir", "."], cwd=UP, capture_output=True, text=True, encoding="utf-8", errors="replace")
    f.write_text(r.stdout + "\n" + r.stderr + f"\nexit_code={r.returncode}\n", encoding="utf-8")
    log(out, f"upstream tests rc={r.returncode}")


def rotate(seq, rep):
    seq = list(seq)
    k = (2 * rep) % len(seq)
    o = seq[k:] + seq[:k]
    return o[::-1] if rep % 2 else o


def passing(out):
    ok = []
    for c in RU.candidates():
        ev = RU.ev_id(c)
        v = out / f"verify__{safe(ev)}.json"
        s = out / f"sympy__{safe(ev)}.json"
        if v.exists() and s.exists():
            dv, ds = json.loads(v.read_text(encoding="utf-8")), json.loads(s.read_text(encoding="utf-8"))
            if dv.get("PASS_S1_S6_except_S3b") and ds.get("sympy_zero") is True:
                ok.append(ev)
    return ok


def select(out, cands):
    """The sealed selection rule. Controls (rw:R0) are not eligible."""
    elig = [ev for ev in cands if ev != "rw:R0"]
    cost, width = {}, {}
    for ev in elig + ["algebra"]:
        reps = []
        for rep in range(SCREEN_COST[2]):
            vals = [json.loads((out / f"scr__{safe(ev)}__{s}__r{rep}.json").read_text(encoding="utf-8"))["cpu_s"]
                    for s in SCEN]
            reps.append(sum(vals))
        cost[ev] = statistics.median(reps)
    from fractions import Fraction as Q
    import math

    def w(ev, s):
        h = json.loads((out / f"wid__{safe(ev)}__{s}.json").read_text(encoding="utf-8"))
        return max(Q(b) - Q(a) for a, b in h["endpoints_scaled"]) if h.get("endpoints_scaled") else None
    for ev in elig:
        width[ev] = statistics.median(math.log2(w("algebra", s) / w(ev, s)) if w(ev, s) else -math.inf for s in SCEN)
    fast = min(elig, key=lambda e: (cost[e], e))
    narrow = max(elig, key=lambda e: (width[e], e))
    sel = {"FAST": fast, "NARROW": narrow if narrow != fast and width[narrow] > 0.5 else None,
           "screen_cost_median_sum_s": cost, "width_gain_median_log2": width}
    (out / "selection.json").write_text(json.dumps(sel, indent=1), encoding="utf-8")
    return sel


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase", required=True, choices=["screen", "serve"])
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not (out / "execution_seal.json").exists():
        if seal(out)["sealed_sources_dirty"]:
            log(out, "sealed sources dirty: STOP")
            return
    SP = ("refs", "verify__", "sympy__", "scr__", "wid__")
    if a.phase == "screen":
        upstream_tests(out)
        if not job(out, ["refs"], "refs", SCREEN_CAP, SP):
            log(out, "refs failed: STOP")
            return
        for c in RU.candidates():
            ev = RU.ev_id(c)
            job(out, ["verify", ev, str(out / "refs.json")], f"verify__{safe(ev)}", SCREEN_CAP, SP)
            job(out, ["sympy", ev], f"sympy__{safe(ev)}", SCREEN_CAP, SP, timeout=SYMPY_TIMEOUT)
        cands = passing(out)
        log(out, f"passing S1-S6: {len(cands)} of {len(RU.candidates())}")
        T, p, reps = SCREEN_COST
        for rep in range(reps):
            for s in SCEN:
                for ev in rotate(["algebra"] + cands, rep):
                    job(out, ["pass", ev, s, str(T), str(p)], f"scr__{safe(ev)}__{s}__r{rep}", SCREEN_CAP, SP)
        for s in SCEN:
            job(out, ["pass", "original", s, str(T), str(p)], f"scr__original__{s}__r0", SCREEN_CAP, SP)
        T, p = SCREEN_WIDTH
        for s in SCEN:
            for ev in ["algebra"] + cands:
                job(out, ["pass", ev, s, str(T), str(p)], f"wid__{safe(ev)}__{s}", SCREEN_CAP, SP)
        sel = select(out, cands)
        log(out, f"selection FAST={sel['FAST']} NARROW={sel['NARROW']}; screening child CPU {spent(out, SP):.0f}s")
        return
    sel = json.loads((out / "selection.json").read_text(encoding="utf-8"))
    rws = [x for x in (sel["FAST"], sel["NARROW"]) if x]
    VP = ("eval__", "inv__")
    short = [(ev, pol) for ev in ["original", "algebra"] + rws for pol in ("P0", "P2", "P3")]
    for rep in range(3):
        for s in SCEN:
            for T in SHORT_T:
                for ev, pol in rotate(short, rep):
                    job(out, ["serve", ev, s, str(T), pol], f"eval__{s}__T{T}__{safe(ev)}__{pol}__r{rep}", SERVE_CAP, VP)
    for ev in rws:
        for s in SCEN:
            for T in SHORT_T:
                tried, low = set(), None
                for f in out.glob(f"eval__{s}__T{T}__{safe(ev)}__*.json"):
                    for h in json.loads(f.read_text(encoding="utf-8"))["passes"]:
                        tried.add(h["requested_p"])
                        if h["outcome"] == "DECIDED":
                            low = h["requested_p"] if low is None else min(low, h["requested_p"])
                for p in range(64, low or 64):
                    if p not in tried:
                        job(out, ["pass", ev, s, str(T), str(p)], f"inv__{s}__T{T}__{safe(ev)}__p{p}", SERVE_CAP, VP)
                log(out, f"investigate {ev} {s} T{T} lowest SERVE success {low}")
    long = [("original", "P3")] + [(ev, pol) for ev in ["algebra"] + rws for pol in ("P0", "P2", "P3")]
    for s in SCEN:
        for T in LONG_T:
            for ev, pol in long:
                job(out, ["serve", ev, s, str(T), pol], f"eval__{s}__T{T}__{safe(ev)}__{pol}__r0", SERVE_CAP, VP)
    log(out, f"phase serve finished; serve child CPU {spent(out, VP):.0f}s")


if __name__ == "__main__":
    main()
