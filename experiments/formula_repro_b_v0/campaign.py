"""FORMULA_REPRO_B_V0 campaign: seal, upstream tests, transformation checks, repository reference, then every
measurement in a fresh process, sequential, order rotated per repetition. Each run writes its JSON at once.

    python -m experiments.formula_repro_b_v0.campaign --out DIR
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
PKG = "experiments.formula_repro_b_v0"
SCENARIOS = ("A2_bound", "A3_low", "A3_high")
EVALUATORS = ("original", "cache", "algebra")
FIXED_PRECS = (96, 128, 192)
POLICY_STEPS = (1, 10, 100, 1000)
REPS = 3
SEALED = ["experiments/formula_repro_b_v0/" + f for f in ("protocol.json", "harness.py", "campaign.py",
                                                         "transform_checks.py")]


def lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def raw(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def log(out, msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(out / "campaign.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def other_python_load():
    try:
        import psutil
        rows = []
        me = psutil.Process().pid
        for pr in psutil.process_iter(["pid", "name", "cmdline", "cpu_times"]):
            if pr.info["name"] and "python" in pr.info["name"].lower() and pr.info["pid"] != me:
                rows.append({"pid": pr.info["pid"], "cpu_s": sum(pr.info["cpu_times"][:2]) if pr.info["cpu_times"] else None,
                             "cmd": " ".join(pr.info["cmdline"] or [])[:200]})
        return rows
    except Exception as e:
        return [{"error": str(e)}]


def job(out, args, name):
    path = out / f"{name}.json"
    if path.exists():
        log(out, f"skip existing {name}")
        return
    t = time.perf_counter()
    p = subprocess.Popen([sys.executable, "-m", f"{PKG}.harness", *args, str(path)], cwd=ROOT,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                         errors="replace")
    so, se = p.communicate()
    wall = time.perf_counter() - t
    if p.returncode != 0 or not path.exists():
        (out / f"{name}.ERROR.txt").write_text(so + "\n" + se, encoding="utf-8")
        log(out, f"ERROR {name} rc={p.returncode}")
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["parent_process_wall_s"] = wall
    doc["child_exit_code"] = p.returncode
    doc["child_pid_confirmed_exited"] = p.poll() is not None
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    log(out, f"done {name} ({wall:.1f}s)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    up = HERE / "upstream"
    sums = json.loads((up / "SHA256SUMS.json").read_text(encoding="utf-8"))
    upstream_hashes = {k: raw(up / k) for k in sums if (up / k).exists()}
    seal = {"head": git("rev-parse", "HEAD"), "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
            "source_sha256_lf": {s: lf(ROOT / s) for s in SEALED}, "upstream_sha256_raw": upstream_hashes,
            "upstream_matches_SHA256SUMS": all(sums[k] == v for k, v in upstream_hashes.items()),
            "python": sys.version, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "other_python_processes_at_start": other_python_load()}
    (out / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    if not seal["upstream_matches_SHA256SUMS"]:
        log(out, "upstream copy differs from SHA256SUMS: STOP")
        return
    ini = out / "empty_pytest.ini"
    ini.write_text("[pytest]\n", encoding="utf-8")
    t = subprocess.run([sys.executable, "-m", "pytest", "test_probe.py", "-q", "-p", "no:cacheprovider", "-c", str(ini),
                        "--rootdir", "."], cwd=up, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (out / "upstream_pytest.txt").write_text(t.stdout + "\n" + t.stderr, encoding="utf-8")
    log(out, f"upstream tests rc={t.returncode}: {t.stdout.strip().splitlines()[-1] if t.stdout.strip() else ''}")
    tc = subprocess.run([sys.executable, "-m", f"{PKG}.transform_checks", str(out / "transform_checks.json")], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    log(out, f"transform checks rc={tc.returncode}: {tc.stdout.strip()}")
    if t.returncode != 0 or tc.returncode != 0 or not json.loads((out / "transform_checks.json").read_text())["PASS"]:
        log(out, "pre-run checks failed: STOP")
        return
    job(out, ["reference"], "reference")
    for rep in range(REPS):
        order = list(EVALUATORS[rep % 3:] + EVALUATORS[:rep % 3])
        if rep % 2:
            order.reverse()
        for scen in SCENARIOS:
            for prec in FIXED_PRECS:
                for ev in order:
                    job(out, ["fixed", scen, str(prec), ev], f"fixed__{scen}__p{prec}__{ev}__t{rep}")
            for steps in POLICY_STEPS:
                for ev in order:
                    job(out, ["policy", scen, str(steps), ev], f"policy__{scen}__s{steps}__{ev}__t{rep}")
    seal["other_python_processes_at_end"] = other_python_load()
    seal["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out / "execution_seal.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")
    log(out, "campaign finished")


if __name__ == "__main__":
    main()
