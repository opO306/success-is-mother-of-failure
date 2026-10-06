"""EXPERIENCE_START_P_V1 campaign (protocol.json). Laptop only. Part A (exact replay), Part B (unseen N), then one serial
reference pass per distinct (N, T, p). Decisions are written before their run; evaluation results go only to candidate
files that no policy reads.

    python -m experiments.experience_start_p_v1.campaign --out DIR
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

import psutil

from experiments.experience_start_p_v1 import experience as EX
from experiments.experience_start_p_v1 import policies as POLS
from experiments.experience_start_p_v1 import service as ESV
from experiments.multiatom_parallel_v1 import scenarios as SC
from experiments.multiatom_parallel_v1.run import initial_digest
from experiments.selector_service_v1 import campaign as SSC
from experiments.selector_service_v1.selector import fixed_plan

ROOT = EX.ROOT
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/experience_start_p_v1/training_bundle.json"
BUNDLE_SHA = (ROOT / "docs/active/experience_start_p_v1/training_bundle.sha256").read_text(encoding="utf-8").strip()
PART_A = [(r["N"], r["T"]) for r in PROTO["part_A_exact_replay"]["requests"]]
PART_B = [(r["N"], r["T"]) for r in PROTO["part_B_unseen_N"]["requests"]]
POL_A, POL_B = PROTO["part_A_exact_replay"]["policies"], PROTO["part_B_unseen_N"]["policies"]
REPS = PROTO["part_A_exact_replay"]["repetitions"]
CPU_CAP = 8000.0
EVALUATOR = "rw:R1+R2"
SSC.SEALED[:] = SSC.SEALED + [f"experiments/experience_start_p_v1/{f}" for f in
                              ("protocol.json", "experience.py", "build_training_bundle.py", "policies.py", "service.py",
                               "campaign.py", "checker.py", "analyze.py")] + \
    ["docs/active/experience_start_p_v1/training_bundle.json", "docs/active/experience_start_p_v1/training_bundle.sha256",
     "experiments/selector_service_v1/service.py", "experiments/selector_service_v1/selector.py"]


class Camp(SSC.Camp):
    def __init__(self, out):
        super().__init__(out)
        for sub in ("decisions", "reference", "candidate"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)

    def spent(self):
        tot = 0.0
        for f in (self.out / "service").glob("*.json"):
            tot += sum(p["record"]["total_cpu_s"] for p in json.loads(f.read_text(encoding="utf-8"))["passes"])
        for f in (self.out / "reference").glob("*.json"):
            tot += json.loads(f.read_text(encoding="utf-8"))["total_cpu_s"]
        return tot

    def execute(self, plan, N, T):
        if self.spent() > CPU_CAP:
            self.log("CPU cap reached: STOP")
            raise SystemExit(2)
        return super().execute(plan, N, T)

    def open_store(self):
        self.store = EX.ExperienceStore(BUNDLE, BUNDLE_SHA)
        self.physics, self.numeric = EX.current_contracts()
        (self.out / "store_open.json").write_text(json.dumps(
            {"bundle_sha256": self.store.sha256, "sealed_sha256": BUNDLE_SHA, "current_physics": self.physics,
             "current_numeric": self.numeric, "bundle_physics": self.store.physics, "bundle_numeric": self.store.numeric},
            indent=1), encoding="utf-8")
        self.log(f"store opened sha {self.store.sha256[:16]} contracts match "
                 f"{(self.physics, self.numeric) == (self.store.physics, self.store.numeric)}")

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
        res = ESV.run_request(N, T, d, self.topology, self.execute)
        res.update(name=name, decision=d, group_snapshot_tag=self.snap["tag"])
        f.write_text(json.dumps(res), encoding="utf-8")
        self.candidate(res)
        self.log(f"service {name}: start {d['start_p']} ({d['start_source']}) {res['status']} passes {res['p_sequence']} "
                 f"wall {res['service_wall_s']:.2f}")
        return res

    def candidate(self, res):
        """Candidate experience of this campaign: written, never read by any policy (dataset candidate after the checker)."""
        recs = [asdict(EX.record_from_pass(dict(pz["record"], requested_p=pz["p"]), self.physics, self.numeric,
                                           f"{res['name']}#pass{pz['index']}", "EXPERIENCE_START_P_V1:candidate", False))
                for pz in res["passes"]]
        succ = [pz["p"] for pz in res["passes"] if pz["record"]["outcome"] == "DECIDED"]
        fail = [pz["p"] for pz in res["passes"] if pz["record"]["outcome"] != "DECIDED"]
        sample = {"schema_version": EX.SCHEMA_VERSION, "name": res["name"],
                  "pre_run_features": {"N": res["N"], "T": res["T"], "pair_count": res["N"] * (res["N"] - 1) // 2,
                                       "evaluator": EVALUATOR, "topology_class": EX.TOPOLOGY_CLASS,
                                       "physics_contract_hash": self.physics, "numeric_contract_hash": self.numeric,
                                       "initial_state_digest": res["decision"]["initial_state_digest"]},
                  "policy": res["policy"], "start_p": res["start_p"],
                  "attempts": [{"p": pz["p"], "outcome": pz["record"]["outcome"],
                                "completed_steps": pz["record"]["completed_steps"], "backend": pz["plan"]["backend"],
                                "workers": pz["plan"]["worker_count"], "cpu_s": pz["record"]["total_cpu_s"],
                                "wall_s": pz["record"]["end_to_end_wall_s"]} for pz in res["passes"]],
                  "observed_summary": {"highest_observed_failure_p": max(fail) if fail else None,
                                       "lowest_observed_success_p": min(succ) if succ else None,
                                       "total_service_wall_s": res["service_wall_s"],
                                       "total_service_cpu_s": sum(pz["record"]["total_cpu_s"] for pz in res["passes"])},
                  "verification_status": "UNVERIFIED_UNTIL_CHECKER"}
        with open(self.out / "candidate" / "candidate_experience.jsonl", "a", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        with open(self.out / "candidate" / "candidate_samples.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(sample) + "\n")

    def reference(self, N, T, p):
        f = self.out / "reference" / f"N{N}_T{T}__p{p}.json"
        if f.exists():
            return
        rec = self.execute(fixed_plan("SERIAL", p), N, T)
        rec.update(requested_p=p, name=f.stem)
        f.write_text(json.dumps(rec), encoding="utf-8")


def part(c, label, requests, policies, extra_lookup=False):
    for rep in range(REPS):
        for N, T in requests:
            c.snapshot(f"{label}_N{N}_T{T}__r{rep}")
            if extra_lookup:
                c.decide(f"{label}_N{N}_T{T}__EXACT_MEMORY_lookup__r{rep}", "EXACT_MEMORY", N, T)
            k = rep % len(policies)
            for pol in policies[k:] + policies[:k]:
                c.run(f"{label}_N{N}_T{T}__{pol}__r{rep}", pol, N, T)
        c.log(f"{label} repetition {rep} finished; campaign CPU {c.spent():.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    psutil.Process().cpu_affinity([SSC.CAMPAIGN_CPU])
    c = Camp(a.out)
    c.setup()
    c.open_store()
    c.log(f"EXPERIENCE_START_P_V1 pid {os.getpid()} A {PART_A} B {PART_B} reps {REPS}")
    c.snapshot("start")
    part(c, "A", PART_A, POL_A)
    part(c, "B", PART_B, POL_B, extra_lookup=True)
    c.snapshot("references")
    todo = sorted({(s["N"], s["T"], p) for f in (c.out / "service").glob("*.json")
                   for s in [json.loads(f.read_text(encoding="utf-8"))] for p in s["p_sequence"]})
    for N, T, p in todo:
        c.reference(N, T, p)
    c.log(f"references done ({len(todo)}); campaign CPU {c.spent():.0f}s")
    c.snapshot("end")
    c.log("finished")


if __name__ == "__main__":
    main()
