"""Orchestrator of RESOURCE_EVOLUTION_PILOT_V1: launches pinned workers, enforces CPU / wall / RAM budgets by polling,
accepts only verifier-approved results, kills the rest, and keeps the resource ledger.

The orchestrator itself runs pinned to logical CPU 1 (sibling of logical 0, the last physical core in the order).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

from experiments.precision_pilot_a1 import policies as POL

from . import selector as SEL
from . import verifier as VF

ROOT = SEL.ROOT
POLL = 0.05


def pin_self():
    psutil.Process().cpu_affinity([SEL.ORCH_CPU])


class Worker:
    def __init__(self, wdir, name, spec):
        self.name, self.spec = name, spec
        self.spec_path = wdir / f"{name}.spec.json"
        self.out_path = wdir / f"{name}.jsonl"
        self.spec_path.write_text(json.dumps(spec), encoding="utf-8")
        if self.out_path.exists():
            self.out_path.unlink()
        self.t_launch = time.perf_counter()
        self.proc = subprocess.Popen([sys.executable, "-m", "experiments.resource_evolution_v1.worker",
                                      str(self.spec_path), str(self.out_path)], cwd=ROOT,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            self.ps = psutil.Process(self.proc.pid)
            self.ps.cpu_affinity(spec["cpus"])
            self.parent_pinned = self.ps.cpu_affinity()
        except psutil.Error:
            self.ps, self.parent_pinned = None, None
        self.pos, self.lines, self.cpu, self.rss_mb, self.killed = 0, [], 0.0, 0.0, False

    def poll(self):
        if self.ps is not None and self.proc.poll() is None:
            try:
                t = self.ps.cpu_times()
                self.cpu = max(self.cpu, t.user + t.system)
                self.rss_mb = max(self.rss_mb, self.ps.memory_info().rss / 2 ** 20)
            except psutil.Error:
                pass

    def alive(self):
        return self.proc.poll() is None

    def kill(self):
        if self.alive():
            self.proc.kill()
            self.killed = True
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    def end(self):
        return next((x for x in self.lines if x["kind"] == "end"), None)

    def passes(self):
        return [x for x in self.lines if x["kind"] == "pass"]

    def cpu_final(self):
        """One consistent figure: the larger of the OS-polled CPU and the worker's own report (the report misses the
        interpreter start before its T0; the poll may miss the last <50 ms)."""
        e = self.end()
        return max(self.cpu, e["child_cpu_s"]) if e else self.cpu


def _read_all(w):
    """Read the worker's whole file (small) and keep every line; robust to partial last lines."""
    if not w.out_path.exists():
        return []
    text = w.out_path.read_text(encoding="utf-8")
    done = text.rfind("\n") + 1
    rows = [json.loads(ln) for ln in text[:done].splitlines() if ln.strip()]
    new = rows[len(w.lines):]
    w.lines = rows
    return new


def run_workers(wdir, tag, specs, env, scenario, T, fallback=None):
    """Run concurrent workers for one request under env budgets. specs: list of worker specs (cpus filled here).
    fallback: callable(history) -> spec or None, used when every worker ended without a verified result."""
    t0, c0 = time.perf_counter(), time.process_time()
    rec = {"tag": tag, "scenario": scenario, "T": T, "env": env, "workers": [], "events": []}
    if len(specs) * SEL.RAM_PER_WORKER_MB > env["ram_mb"]:
        rec.update(status="RESOURCE_REFUSED", refusal="RAM admission", wall_s=0.0, total_cpu_s=0.0,
                   orch_cpu_s=time.process_time() - c0)
        return rec
    cores = env["core_set"]
    ws, accepted, budget_hit, verify_cpu = [], None, None, 0.0
    for i, s in enumerate(specs):
        s = dict(s, cpus=[cores[i % len(cores)]])
        ws.append(Worker(wdir, f"{tag}__w{i}", s))
    stage = 0

    def consume():
        nonlocal accepted, verify_cpu
        for w in ws:
            w.poll()
            for row in _read_all(w):
                if row["kind"] == "pass" and row["outcome"] == "DECIDED" and accepted is None:
                    v = VF.verify(row, scenario, T)
                    verify_cpu += v["verify_cpu_s"]
                    rec["events"].append({"t": time.perf_counter() - t0, "worker": w.name, "verify": v,
                                          "p": row["requested_p"]})
                    if v["verified"]:
                        accepted = (w, row, time.perf_counter() - t0)
    while True:
        time.sleep(POLL)
        all_dead = not any(w.alive() for w in ws)
        consume()
        total_cpu = sum(w.cpu_final() if not w.alive() else w.cpu for w in ws)
        wall = time.perf_counter() - t0
        if accepted is not None:
            for w in ws:
                if w is not accepted[0]:
                    w.kill()
            if accepted[0].alive():
                accepted[0].proc.wait(timeout=60)
            break
        if total_cpu >= env["cpu_s"] or wall >= env["wall_s"]:
            budget_hit = "cpu" if total_cpu >= env["cpu_s"] else "wall"
            rec["cpu_at_trigger"], rec["kill_t"] = total_cpu, wall
            for w in ws:
                w.kill()
            break
        if all_dead:                                   # every line of every dead worker has been consumed
            spec = fallback([r for w in ws for r in w.passes()]) if fallback and stage == 0 else None
            if spec is None:
                break
            stage = 1
            ws.append(Worker(wdir, f"{tag}__fallback", dict(spec, cpus=[cores[0]])))
            rec["events"].append({"t": wall, "fallback_start_p": spec["start_p"]})
    late = []
    for w in ws:
        for row in _read_all(w):                         # lines first read after the stop decision
            if budget_hit and row["kind"] == "pass" and row["outcome"] == "DECIDED":
                v = VF.verify(row, scenario, T)
                verify_cpu += v["verify_cpu_s"]
                late.append({"worker": w.name, "p": row["requested_p"], "verified": v["verified"],
                             "worker_t_cpu": row.get("t_cpu")})
        w.poll()
    rec["late_results_discarded"] = late
    rec["wall_s"] = accepted[2] if accepted else time.perf_counter() - t0
    rec["wall_all_ended_s"] = time.perf_counter() - t0
    for w in ws:
        rec["workers"].append({"name": w.name, "spec": w.spec, "parent_pinned": w.parent_pinned,
                               "start": next((x for x in w.lines if x["kind"] == "start"), None),
                               "prepared": next((x for x in w.lines if x["kind"] == "prepared"), None),
                               "passes": w.passes(), "end": w.end(), "cpu_s": w.cpu_final(),
                               "cpu_source": "self-report" if w.end() else "poll", "rss_poll_mb": w.rss_mb,
                               "killed": w.killed, "exit_code": w.proc.poll(),
                               "exited_confirmed": w.proc.poll() is not None,
                               "accepted": accepted is not None and w is accepted[0]})
    rec["total_cpu_s"] = sum(x["cpu_s"] for x in rec["workers"])
    rec["verify_cpu_s"] = verify_cpu
    rec["peak_mb"] = max([(x["end"] or {}).get("peak_wset_mb", x["rss_poll_mb"]) for x in rec["workers"]], default=0)
    rec["ram_budget_exceeded"] = rec["peak_mb"] * len(ws) > env["ram_mb"]
    if accepted:
        w, row, _ = accepted
        rec.update(status="VERIFIED", result={k: row[k] for k in ("evaluator", "requested_p", "cells",
                                                                     "endpoints_scaled", "completed_steps")})
        acc = next(x for x in rec["workers"] if x["accepted"])
        rec["waste_cpu_s"] = rec["total_cpu_s"] - acc["cpu_s"]
        rec["retry_cpu_s"] = sum(p["cpu_s"] for p in acc["passes"][:-1])
    else:
        failed = any(p["outcome"] != "DECIDED" for x in rec["workers"] for p in x["passes"])
        rec["status"] = ("BUDGET_STARVATION" if failed else "RESOURCE_REFUSED") if budget_hit else "NO_VERIFIED_RESULT"
        rec["budget_hit"] = budget_hit
        rec["waste_cpu_s"] = rec["total_cpu_s"]
        rec["retry_cpu_s"] = sum(p["cpu_s"] for x in rec["workers"] for p in x["passes"])
    rec["orch_cpu_s"] = time.process_time() - c0
    rec["all_workers_exited"] = all(x["exited_confirmed"] for x in rec["workers"])
    return rec


def specs_for(plan, s, T):
    mode = "policy" if not SEL.PLANS[plan]["spec"] else "single"
    return [{"evaluator": ev, "scenario": s, "T": T, "mode": mode, "start_p": p, "max_passes": 24}
            for ev, p in SEL.start_ps(plan, s, T)]


def fallback_for(plan, s, T):
    if not SEL.PLANS[plan]["spec"]:
        return None
    ev = SEL.PLANS[plan]["workers"][0][0]

    def fb(history):
        if not history:
            return None
        top = max(history, key=lambda r: r["requested_p"])
        nxt = POL.p2_next(top, T)
        if top["requested_p"] >= 1024:
            return None
        return {"evaluator": ev, "scenario": s, "T": T, "mode": "policy", "start_p": min(nxt, 1024), "max_passes": 24}
    return fb


def run_plan(wdir, tag, plan, env, s, T):
    rec = run_workers(wdir, tag, specs_for(plan, s, T), env, s, T, fallback_for(plan, s, T))
    rec["plan"] = plan
    return rec


def run_batch(wdir, tag, plan, requests, k, verify_mode="inline", us=None):
    """S1 batch: requests (LPT order by predicted u) on k physical cores, one worker per request, no CPU cap.
    verify_mode: inline (orchestrator verifies on arrival), after (all at the end), pipeline (verifier subprocess)."""
    t0, c0 = time.perf_counter(), time.process_time()
    order = sorted(requests, key=lambda r: -(us or {}).get(f"{r[0]}@{r[1]}", 0))
    cores = SEL.PHYS_ORDER[:k]
    free, running, results, pending = list(cores), {}, {}, list(order)
    vproc = None
    if verify_mode == "pipeline":
        vproc = subprocess.Popen([sys.executable, "-m", "experiments.resource_evolution_v1.vserver"], cwd=ROOT,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
        psutil.Process(vproc.pid).cpu_affinity([SEL.ORCH_CPU])
    deferred, verify_cpu = [], 0.0
    while pending or running:
        while pending and free:
            s, T = pending.pop(0)
            c = free.pop(0)
            spec = dict(specs_for(plan, s, T)[0], cpus=[c])
            running[(s, T)] = (Worker(wdir, f"{tag}__{s}_{T}", spec), c)
        time.sleep(POLL)
        for key, (w, c) in list(running.items()):
            w.poll()
            _read_all(w)
            if not w.alive():
                _read_all(w)
                row = next((p for p in w.passes() if p["outcome"] == "DECIDED"), None)
                entry = {"worker": w.name, "core": c, "passes": w.passes(), "end": w.end(), "cpu_s": w.cpu_final(),
                         "start": next((x for x in w.lines if x["kind"] == "start"), None),
                         "parent_pinned": w.parent_pinned, "exited_confirmed": True,
                         "finish_t": time.perf_counter() - t0, "decided": row}
                if row is not None:
                    if verify_mode == "inline":
                        v = VF.verify(row, *key)
                        verify_cpu += v["verify_cpu_s"]
                        entry["verify"] = v
                    elif verify_mode == "after":
                        deferred.append(key)
                    else:
                        vproc.stdin.write(json.dumps({"key": list(key), "rec": row}) + "\n")
                        vproc.stdin.flush()
                results[f"{key[0]}@{key[1]}"] = entry
                del running[key]
                free.append(c)
    if verify_mode == "after":
        for key in deferred:
            e = results[f"{key[0]}@{key[1]}"]
            v = VF.verify(e["decided"], *key)
            verify_cpu += v["verify_cpu_s"]
            e["verify"] = v
    if vproc is not None:
        vproc.stdin.close()
        for ln in vproc.stdout:
            d = json.loads(ln)
            results[f"{d['key'][0]}@{d['key'][1]}"]["verify"] = d["v"]
            verify_cpu += d["v"]["verify_cpu_s"]
        vproc.wait(timeout=60)
    wall = time.perf_counter() - t0
    for e in results.values():
        e["status"] = "VERIFIED" if e.get("verify", {}).get("verified") else "NOT_VERIFIED"
    return {"tag": tag, "plan": plan, "k": k, "cores": cores, "verify_mode": verify_mode, "wall_s": wall,
            "total_cpu_s": sum(e["cpu_s"] for e in results.values()), "orch_cpu_s": time.process_time() - c0,
            "verify_cpu_s": verify_cpu, "results": results,
            "peak_mb": max((e["end"] or {}).get("peak_wset_mb", 0) for e in results.values())}
