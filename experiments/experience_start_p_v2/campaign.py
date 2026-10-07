"""EXPERIENCE_START_P_V2 campaign (protocol.json). Vast node (Linux) for the evidence; the desktop only for the test
fixture. Cross-platform anchor, then 4 holdout requests x 3 policies x 3 repetitions on the fixed W6 plan, then one serial
reference pass per distinct (N, T, p). Decisions are written before their run; results go only to candidate_v2/.

    ESP2_LINUX_CLOCK=1 PYTHONPATH=<repo>/experiments/experience_start_p_v2/linux_shim:<repo> \
        python -m experiments.experience_start_p_v2.campaign --out DIR
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import psutil

from experiments.e2_pair_parallel_v1.campaign import contamination, git, lf
from experiments.experience_start_p_v2 import experience as EX
from experiments.experience_start_p_v2 import policies as POLS
from experiments.experience_start_p_v2 import service as ESV
from experiments.multiatom_parallel_v1 import scenarios as SC
from experiments.multiatom_parallel_v1.run import initial_digest
from experiments.selector_service_v1.selector import fixed_plan

ROOT = EX.ROOT
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/experience_start_p_v2/training_bundle.json"
BUNDLE_SHA = (ROOT / "docs/active/experience_start_p_v2/training_bundle.sha256").read_text(encoding="utf-8").strip()
REQUESTS = [(r["N"], r["T"]) for r in PROTO["evaluation_requests"]["requests"]]
REPS = PROTO["evaluation_requests"]["repetitions"]
POLICIES = list(POLS.POLICIES)
CPU_CAP = 20000.0
CAMPAIGN_CPU = 0
PLACEMENT_CPUS = (0, 1, 2, 3, 4, 5)
ANCHOR = (8, 100, 107)
ANCHOR_SRC = ROOT / "docs/active/selector_service_v1/laptop_run/records.json.gz"
RESULT_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells", "initial_sha256")
EVALUATOR = EX.EVALUATOR
SEALED = [f"experiments/experience_start_p_v2/{f}" for f in
          ("protocol.json", "experience.py", "build_training_bundle.py", "policies.py", "service.py", "campaign.py",
           "checker.py", "analyze.py", "linux_shim/sitecustomize.py", "vast_job.sh")] + \
         ["docs/active/experience_start_p_v2/training_bundle.json", "docs/active/experience_start_p_v2/training_bundle.sha256",
          "experiments/experience_start_p_v1/experience.py", "experiments/selector_service_v1/service.py",
          "experiments/selector_service_v1/selector.py", "experiments/precision_pilot_a1/policies.py",
          "experiments/w5_placement_v1/plan.py", "experiments/w5_placement_v1/run.py",
          "experiments/e2_pair_parallel_v1/run.py", "experiments/multiatom_parallel_v1/run.py",
          "experiments/multiatom_parallel_v1/scenarios.py", "exact_expression_gate_v1/stream.py",
          "exact_expression_gate_v1/common.py", "exact_expression_gate_v0/lang_iv.py", "a_reference/ar2_lang2024.py",
          "experiments/precision_pilot_a2t/evaluator_adapter.py", "experiments/precision_pilot_a1/evaluator_adapter.py",
          "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
          "experiments/rewrite_pilot_a3/rwforce.py", "experiments/formula_repro_b_v0/harness.py",
          "experiments/formula_repro_b_v0/upstream/probe.py"]
LINUX = sys.platform.startswith("linux")


def allowed_cpus():
    """CPUs the container may use (the cgroup cpuset; this process itself is already pinned to CAMPAIGN_CPU)."""
    f = Path("/sys/fs/cgroup/cpuset.cpus.effective")
    txt = f.read_text().strip() if f.exists() else ""
    if not txt:
        return list(range(os.cpu_count()))
    out = []
    for part in txt.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def linux_topology():
    cpus = allowed_cpus()
    rows = {}
    for c in PLACEMENT_CPUS:
        base = Path(f"/sys/devices/system/cpu/cpu{c}/topology")
        rows[c] = {"core_id": int((base / "core_id").read_text()), "package": int((base / "physical_package_id").read_text()),
                   "siblings": (base / "thread_siblings_list").read_text().strip()}
    model = next((ln.split(":", 1)[1].strip() for ln in Path("/proc/cpuinfo").read_text().splitlines()
                  if ln.startswith("model name")), "?")
    cores = {(r["package"], r["core_id"]) for r in rows.values()}
    ok = len(cores) == len(PLACEMENT_CPUS) and all(c in cpus for c in PLACEMENT_CPUS)
    return {"platform": "linux", "model": model, "logical": psutil.cpu_count(True), "physical": psutil.cpu_count(False),
            "affinity_mask": cpus, "placement_cpus": rows, "placement_distinct_physical_cores": ok, "nice": os.nice(0),
            "topology_class": f"{model} | W6 on cores 0-5 (distinct physical cores, SMT siblings unused)"}


def windows_topology():
    from experiments.w5_placement_v1 import topology as TOPO
    t = TOPO.summary()
    t.update(platform="windows", topology_class="desktop-fixture (scratch, not evidence)")
    return t


def host_counters():
    if not LINUX:
        return {}
    la = Path("/proc/loadavg").read_text().split()
    cpu = Path("/proc/stat").read_text().splitlines()[0].split()
    return {"loadavg_1m": float(la[0]), "loadavg_5m": float(la[1]), "proc_stat_steal_ticks": int(cpu[8])}


class Camp:
    def __init__(self, out):
        self.out = Path(out).resolve()
        for sub in ("work", "service", "decisions", "reference", "candidate_v2", "anchor"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)
        self.rate, self.snap, self.k, self.clock = None, None, 0, None

    def log(self, msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with open(self.out / "campaign.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def spent(self):
        tot = 0.0
        for f in (self.out / "service").glob("*.json"):
            tot += sum(p["record"]["total_cpu_s"] for p in json.loads(f.read_text(encoding="utf-8"))["passes"])
        for sub in ("reference", "anchor"):
            for f in (self.out / sub).glob("*.json"):
                tot += json.loads(f.read_text(encoding="utf-8"))["total_cpu_s"]
        return tot

    def snapshot(self, tag):
        me = psutil.Process()
        own = {me.pid} | {c.pid for c in me.children(recursive=True)}
        procs = [pr for pr in psutil.process_iter(["pid", "name"]) if pr.pid not in own and pr.pid != 0]
        for pr in procs:
            try:
                pr.cpu_percent(None)
            except psutil.Error:
                pass
        h0 = host_counters()
        time.sleep(1.0)
        rows = []
        for pr in procs:
            try:
                v = pr.cpu_percent(None)
                if v > 0:
                    rows.append((pr.info["name"], pr.pid, round(v, 1)))
            except psutil.Error:
                pass
        h1 = host_counters()
        rows.sort(key=lambda x: -x[2])
        c = contamination(rows)
        info = dict(h1, steal_ticks_in_1s=h1["proc_stat_steal_ticks"] - h0["proc_stat_steal_ticks"]) if h1 else {}
        snap = {"tag": tag, "time": time.strftime("%H:%M:%S"), "rows": rows[:40], **c, "info_only": info}
        with open(self.out / "load_snapshots.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(snap) + "\n")
        self.log(f"load {tag}: others {c['other_total_pct']}% suspects {c['suspects']} "
                 f"{'CONTAMINATED' if c['contaminated'] else 'clean'} info {info} top {rows[:3]}")
        self.snap = snap
        return snap

    def setup(self, check_topology=True):
        t = linux_topology() if LINUX else windows_topology()
        (self.out / "topology.json").write_text(json.dumps(t, indent=1), encoding="utf-8")
        self.topology = t
        if check_topology and not (LINUX and t["placement_distinct_physical_cores"]):
            self.log(f"PLACEMENT CHECK FAILED: {t}")
            raise SystemExit(4)
        f = self.out / "execution_seal.json"
        if not f.exists():
            import mpmath
            import mpmath.libmp
            s = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
                 "status_porcelain": git("status", "--porcelain", "--untracked-files=no"),
                 "untracked": git("status", "--porcelain", "--untracked-files=all"),
                 "sealed_sources_dirty": bool(git("status", "--porcelain", "--", *SEALED)),
                 "source_sha256_lf": {x: lf(ROOT / x) for x in SEALED}, "python": sys.version,
                 "mpmath": mpmath.__version__, "mpmath_backend": mpmath.libmp.BACKEND, "psutil": psutil.__version__,
                 "started": time.strftime("%Y-%m-%d %H:%M:%S"), "host": platform.node(), "platform": sys.platform,
                 "campaign_cpu": CAMPAIGN_CPU}
            f.write_text(json.dumps(s, indent=1), encoding="utf-8")
        self.clock = self.check_clock()
        self.rate = self.clock["rate_hz"]
        self.log(f"clock {self.clock['method']} rate {self.rate / 1e9:.4f} GHz-equivalent")

    def check_clock(self):
        f = self.out / "cpu_clock.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        if LINUX:
            from experiments.multiatom_parallel_v1 import run as M
            r = subprocess.run([sys.executable, "-c", "import experiments.multiatom_parallel_v1.run as M; "
                                "print(getattr(M, 'CPU_CLOCK', 'NONE'))"], cwd=ROOT, capture_output=True, text=True)
            child = r.stdout.strip()
            here = getattr(M, "CPU_CLOCK", "NONE")
            if here != "linux:CLOCK_PROCESS_CPUTIME_ID_ns" or child != here:
                self.log(f"LINUX CLOCK SHIM NOT ACTIVE (here {here}, child {child}): STOP")
                raise SystemExit(6)
            c = {"method": here, "rate_hz": 1e9, "child_process_check": child,
                 "pythonpath": os.environ.get("PYTHONPATH"), "flag": os.environ.get("ESP2_LINUX_CLOCK")}
        else:
            from experiments.multiatom_parallel_v1.run import cycle_rate
            rates = [cycle_rate() for _ in range(3)]
            c = {"method": "windows:QueryProcessCycleTime", "rates_hz": rates, "rate_hz": max(rates)}
        f.write_text(json.dumps(c, indent=1), encoding="utf-8")
        return c

    def execute(self, plan, N, T):
        """One fresh pass through the unchanged W5_PLACEMENT_V1 runner; returns the enriched record."""
        if self.spent() > CPU_CAP:
            self.log("CPU cap reached: STOP")
            raise SystemExit(2)
        self.k += 1
        pf = self.out / "work" / f"pass_{os.getpid()}_{self.k}.plan.json"
        pf.write_text(plan.to_json(), encoding="utf-8")
        tmp = pf.with_suffix(".out.json")
        cmd = [sys.executable, "-m", "experiments.w5_placement_v1.run", str(pf), str(N), str(T), str(tmp)]
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        e2e = time.perf_counter() - t0
        if r.returncode != 0:
            self.log(f"ERROR pass {plan}: rc {r.returncode} {r.stderr[-600:]}")
            raise SystemExit(3)
        d = json.loads(tmp.read_text(encoding="utf-8"))
        tmp.unlink()
        pf.unlink()
        wcyc = [b["cycles"] for b in d.get("worker_bye", [])]
        cyc = d["main_cycles"] + sum(wcyc)
        d.update(end_to_end_wall_s=e2e, total_cycles=cyc, cycle_rate_hz=self.rate, total_cpu_s=cyc / self.rate,
                 main_cpu_cycle_s=d["main_cycles"] / self.rate, worker_cpu_cycle_s=[c / self.rate for c in wcyc],
                 cpu_clock=self.clock["method"], group_contaminated=self.snap["contaminated"] if self.snap else None,
                 group_snapshot_tag=self.snap["tag"] if self.snap else None)
        d.setdefault("endpoints_scaled", None)
        self.log(f"  pass N{N} T{T} p{plan.precision} {plan.backend} W{plan.worker_count} {d['outcome']} "
                 f"e2e {e2e:.2f} cpu {d['total_cpu_s']:.2f}")
        return d

    def open_store(self):
        self.store = EX.ExperienceStore(BUNDLE, BUNDLE_SHA)
        self.physics, self.numeric = EX.current_contracts()
        (self.out / "store_open.json").write_text(json.dumps(
            {"bundle_sha256": self.store.sha256, "sealed_sha256": BUNDLE_SHA, "current_physics": self.physics,
             "current_numeric": self.numeric, "bundle_physics": self.store.physics, "bundle_numeric": self.store.numeric},
            indent=1), encoding="utf-8")
        match = (self.physics, self.numeric) == (self.store.physics, self.store.numeric)
        self.log(f"store opened sha {self.store.sha256[:16]} contracts match {match}")
        if not match:
            raise SystemExit(7)

    def anchor(self):
        """Cross-platform anchor: serial N=8 T=100 p=107 must equal the laptop SELECTOR_SERVICE_V1 serial pass."""
        N, T, p = ANCHOR
        f = self.out / "anchor" / f"N{N}_T{T}__p{p}.json"
        if not f.exists():
            rec = self.execute(fixed_plan("SERIAL", p), N, T)
            rec.update(requested_p=p, name=f.stem)
            f.write_text(json.dumps(rec), encoding="utf-8")
        rec = json.loads(f.read_text(encoding="utf-8"))
        files = json.load(gzip.open(ANCHOR_SRC))["files"]
        ref = None
        for name, txt in sorted(files.items()):
            if name.startswith("service/") and "__SEL_CPU__" in name:
                s = json.loads(txt)
                for pz in s["passes"]:
                    if (s["N"], s["T"], pz["p"]) == ANCHOR:
                        ref = pz["record"]
                        break
            if ref:
                break
        same = ref is not None and all(rec[k] == ref[k] for k in RESULT_KEYS)
        self.log(f"cross-platform anchor N{N} T{T} p{p}: {'IDENTICAL' if same else 'MISMATCH'} to laptop serial")
        if not same:
            raise SystemExit(5)

    def decide(self, name, policy, N, T):
        f = self.out / "decisions" / f"{name}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        q0, p0 = SC.initial(N)
        d = POLS.decide(policy, N, T, EVALUATOR, initial_digest(q0, p0), self.store, self.physics, self.numeric)
        d["name"] = name
        f.write_text(json.dumps(d, indent=1), encoding="utf-8")
        return d

    def run(self, name, policy, N, T):
        f = self.out / "service" / f"{name}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        d = self.decide(name, policy, N, T)
        res = ESV.run_request(N, T, d, self.execute)
        res.update(name=name, decision=d, group_snapshot_tag=self.snap["tag"])
        f.write_text(json.dumps(res), encoding="utf-8")
        self.candidate(res)
        self.log(f"service {name}: start {d['start_p']} ({d['start_source']}) {res['status']} passes {res['p_sequence']} "
                 f"wall {res['service_wall_s']:.2f}")
        return res

    def candidate(self, res):
        """Candidate experience of this campaign: written, never read by any policy (dataset candidate after the checker)."""
        tc = self.topology["topology_class"]
        recs = [EX.candidate_record(dict(pz["record"], requested_p=pz["p"]), self.physics, self.numeric,
                                    f"{res['name']}#pass{pz['index']}", tc) for pz in res["passes"]]
        succ = [pz["p"] for pz in res["passes"] if pz["record"]["outcome"] == "DECIDED"]
        fail = [pz["p"] for pz in res["passes"] if pz["record"]["outcome"] != "DECIDED"]
        sample = {"schema_version": EX.SCHEMA_VERSION, "name": res["name"],
                  "pre_run_features": {"N": res["N"], "T": res["T"], "pair_count": res["N"] * (res["N"] - 1) // 2,
                                       "evaluator": EVALUATOR, "topology_class": tc,
                                       "physics_contract_hash": self.physics, "numeric_contract_hash": self.numeric,
                                       "initial_state_digest": res["decision"]["initial_state_digest"]},
                  "policy": res["policy"], "starting_p": res["start_p"],
                  "attempts": [{"p": pz["p"], "outcome": pz["record"]["outcome"],
                                "completed_steps": pz["record"]["completed_steps"], "backend": pz["plan"]["backend"],
                                "workers": pz["plan"]["worker_count"], "cpu_s": pz["record"]["total_cpu_s"],
                                "wall_s": pz["record"]["end_to_end_wall_s"]} for pz in res["passes"]],
                  "observed_summary": {"highest_observed_failure_p": max(fail) if fail else None,
                                       "lowest_observed_success_p": min(succ) if succ else None,
                                       "total_service_wall_s": res["service_wall_s"],
                                       "total_service_cpu_s": sum(pz["record"]["total_cpu_s"] for pz in res["passes"])},
                  "verification_status": "UNVERIFIED_UNTIL_CHECKER"}
        with open(self.out / "candidate_v2" / "candidate_experience.jsonl", "a", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        with open(self.out / "candidate_v2" / "candidate_samples.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(sample) + "\n")

    def reference(self, N, T, p):
        f = self.out / "reference" / f"N{N}_T{T}__p{p}.json"
        if f.exists():
            return
        rec = self.execute(fixed_plan("SERIAL", p), N, T)
        rec.update(requested_p=p, name=f.stem)
        f.write_text(json.dumps(rec), encoding="utf-8")


def evaluate(c, requests, reps):
    for rep in range(reps):
        for N, T in requests:
            c.snapshot(f"N{N}_T{T}__r{rep}")
            c.decide(f"N{N}_T{T}__EXACT_LOOKUP__r{rep}", POLS.LOOKUP, N, T)
            k = rep % len(POLICIES)
            for pol in POLICIES[k:] + POLICIES[:k]:
                c.run(f"N{N}_T{T}__{pol}__r{rep}", pol, N, T)
        c.log(f"repetition {rep} finished; campaign CPU {c.spent():.0f}s")


def references(c):
    todo = sorted({(s["N"], s["T"], p) for f in (c.out / "service").glob("*.json")
                   for s in [json.loads(f.read_text(encoding="utf-8"))] for p in s["p_sequence"]})
    for N, T, p in todo:
        c.reference(N, T, p)
    c.log(f"references done ({len(todo)}); campaign CPU {c.spent():.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    psutil.Process().cpu_affinity([CAMPAIGN_CPU])
    c = Camp(a.out)
    c.setup()
    c.open_store()
    c.log(f"EXPERIENCE_START_P_V2 pid {os.getpid()} requests {REQUESTS} reps {REPS} policies {POLICIES}")
    c.snapshot("anchor")
    c.anchor()
    evaluate(c, REQUESTS, REPS)
    c.snapshot("references")
    references(c)
    c.snapshot("end")
    c.log("finished")


if __name__ == "__main__":
    main()
