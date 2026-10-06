"""Independent checker of EXPERIENCE_START_P_V1. Imports none of experience.py / policies.py / service.py / campaign.py
or the selector/P2 executor code. It rebuilds the training summaries from the source evidence with its own code, checks
the sealed bundle, re-derives every decision, first p, P2 chain, worker plan and bit identity.

    python -m experiments.experience_start_p_v1.checker DIR
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

from experiments.multiatom_parallel_v1 import checker as MAC
from experiments.precision_pilot_a1 import checker as A1C
from experiments.selector_service_v1 import checker as SSCK        # checker-side code only (own P2, own plan table)

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
SRC = ROOT / "docs/active/selector_service_v1/laptop_run"
BUNDLE = ROOT / "docs/active/experience_start_p_v1/training_bundle.json"
BUNDLE_SHA_FILE = ROOT / "docs/active/experience_start_p_v1/training_bundle.sha256"
PHYS = ["a_reference/ar2_lang2024.py", "exact_expression_gate_v0/lang_iv.py", "exact_expression_gate_v1/common.py",
        "exact_expression_gate_v1/stream.py"]
NUM = ["experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/upstream/probe.py",
       "experiments/precision_pilot_a1/evaluator_adapter.py", "experiments/precision_pilot_a2t/evaluator_adapter.py",
       "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
       "experiments/rewrite_pilot_a3/rwforce.py"]
EV = "rw:R1+R2"
RESULT_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells", "initial_sha256")
FORBIDDEN_LABELS = re.compile(r"true_minimum|minimum_required", re.I)


def _chash(table, files):
    return hashlib.sha256("\n".join(f"{f}:{table[f]}" for f in sorted(files)).encode()).hexdigest()


def _sha_lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _fp(phys, num, ev, init, T):
    return hashlib.sha256(json.dumps([phys, num, ev, init, T]).encode()).hexdigest()


def own_training_summary():
    """From the source evidence only: per exact key (lowest success, highest failure) and per family (min, max)."""
    files = json.load(gzip.open(SRC / "records.json.gz"))["files"]
    verdict = json.loads((SRC / "checker_verdict.json").read_text(encoding="utf-8"))
    seal = json.loads((SRC / "execution_seal.json").read_text(encoding="utf-8"))
    ok_src = verdict["verdict"] == "EVIDENCE OK" and verdict["bit_mismatches"] == 0
    phys, num = _chash(seal["source_sha256_lf"], PHYS), _chash(seal["source_sha256_lf"], NUM)
    att, n_records = {}, 0
    for name, txt in files.items():
        if not name.endswith(".json") or not (name.startswith("service/") or name.startswith("shadow/")):
            continue
        d = json.loads(txt)
        recs = [dict(pz["record"], requested_p=pz["p"]) for pz in d["passes"]] if name.startswith("service/") else [d]
        for r in recs:
            n_records += 1
            key = _fp(phys, num, r["evaluator"], r["initial_sha256"], r["T"])
            a = att.setdefault(key, {"N": r["N"], "T": r["T"], "s": set(), "f": set()})
            (a["s"] if r["outcome"] == "DECIDED" else a["f"]).add(r["requested_p"])
    exact = {k: {"N": a["N"], "T": a["T"], "low": min(a["s"]) if a["s"] else None, "high_fail": max(a["f"]) if a["f"] else None}
             for k, a in att.items()} if ok_src else {}
    fam = {}
    for k, e in exact.items():
        if e["low"] is not None:
            fam.setdefault(e["T"], []).append(e["low"])
    fam = {T: (min(v), max(v)) for T, v in fam.items()}
    return {"physics": phys, "numeric": num, "exact": exact, "family": fam, "n_records": n_records}


def check(d, part_a=None, part_b=None, reps=None, bundle_path=BUNDLE, bundle_sha_file=BUNDLE_SHA_FILE):
    d = Path(d)
    part_a = part_a or [(r["N"], r["T"]) for r in PROTO["part_A_exact_replay"]["requests"]]
    part_b = part_b or [(r["N"], r["T"]) for r in PROTO["part_B_unseen_N"]["requests"]]
    reps = PROTO["part_A_exact_replay"]["repetitions"] if reps is None else reps
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    ok("seal_clean", seal["status_porcelain"] == "" and not seal["sealed_sources_dirty"], seal["status_porcelain"][:200])
    # ---- the sealed bundle ----
    own = own_training_summary()
    sealed_sha = Path(bundle_sha_file).read_text(encoding="utf-8").strip()
    bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    canon = hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    ok("bundle_hash_matches_sealed_file", canon == sealed_sha, f"{canon[:16]} vs {sealed_sha[:16]}")
    ok("bundle_contracts_equal_source", (bundle["physics_contract_hash"], bundle["numeric_contract_hash"]) ==
       (own["physics"], own["numeric"]))
    ok("bundle_records_single_contract", all((r["physics_contract_hash"], r["numeric_contract_hash"], r["evaluator"]) ==
                                             (own["physics"], own["numeric"], EV) for r in bundle["records"]))
    ok("bundle_records_all_verified", all(r["verification_status"] == "VERIFIED" for r in bundle["records"]) and
       len(bundle["records"]) == own["n_records"])
    for k, e in bundle["exact"].items():
        o = own["exact"].get(k)
        ok("bundle_exact_equals_source", o is not None and (e["lowest_observed_success_p"], e["highest_observed_failure_p"])
           == (o["low"], o["high_fail"]), f"N{e.get('N')} T{e.get('T')}")
    ok("bundle_exact_keys_equal_source", set(bundle["exact"]) == set(own["exact"]))
    vs = {}
    for r in bundle["records"]:
        if r["verification_status"] == "VERIFIED":
            v = vs.setdefault(r["request_fingerprint"], {"s": set(), "f": set()})
            (v["s"] if r["outcome"] == "DECIDED" else v["f"]).add(r["attempt_p"])
    for k, e in bundle["exact"].items():
        v = vs.get(k, {"s": set(), "f": set()})
        ok("bundle_summary_from_verified_records_only", e["lowest_observed_success_p"] == (min(v["s"]) if v["s"] else None),
           k[:12])
    for fk, f in bundle["family"].items():
        o = own["family"].get(f["T"])
        ok("bundle_family_equals_source", o is not None and (f["FAMILY_MIN"], f["FAMILY_MAX"]) == o, fk[:40])
    so = json.loads((d / "store_open.json").read_text(encoding="utf-8"))
    cur_phys = _chash({f: _sha_lf(ROOT / f) for f in PHYS}, PHYS)
    cur_num = _chash({f: _sha_lf(ROOT / f) for f in NUM}, NUM)
    ok("store_opened_with_sealed_bundle", so["bundle_sha256"] == sealed_sha == so["sealed_sha256"])
    ok("campaign_contracts_equal_current_and_training", (so["current_physics"], so["current_numeric"]) ==
       (cur_phys, cur_num) == (own["physics"], own["numeric"]))

    # ---- decisions, service runs ----
    def expected(policy, N, T):
        init = MAC.my_digest(*MAC.my_initial(N))
        fp = _fp(own["physics"], own["numeric"], EV, init, T)
        e = own["exact"].get(fp)
        fam = own["family"].get(T)
        if policy == "EXACT_MEMORY" and e and e["low"] is not None:
            start = e["low"]
        elif policy == "FAMILY_MIN" and fam:
            start = fam[0]
        elif policy == "FAMILY_MAX" and fam:
            start = fam[1]
        else:
            start = 64
        return {"start_p": start, "request_fingerprint": fp, "initial_state_digest": init, "exact_hit": e is not None,
                "exact_low": e["low"] if e else None, "family": fam}

    passes_by_ntp = {}

    def check_decision(where, dec, policy, N, T):
        x = expected(policy, N, T)
        ok("decision_bundle_sha", dec["bundle_sha256"] == sealed_sha, where)
        ok("decision_rederived", dec["start_p"] == x["start_p"] and dec["request_fingerprint"] == x["request_fingerprint"]
           and dec["initial_state_digest"] == x["initial_state_digest"] and dec["exact_hit"] == x["exact_hit"]
           and dec["exact_lowest_observed_success_p"] == x["exact_low"]
           and (dec["FAMILY_MIN"], dec["FAMILY_MAX"]) == (x["family"] if x["family"] else (None, None)),
           f"{where}: start {dec['start_p']} vs {x['start_p']}")
        return x

    for label, reqs, pols in (("A", part_a, PROTO["part_A_exact_replay"]["policies"]),
                              ("B", part_b, PROTO["part_B_unseen_N"]["policies"])):
        for N, T in reqs:
            for rep in range(reps):
                if label == "B":
                    f = d / "decisions" / f"B_N{N}_T{T}__EXACT_MEMORY_lookup__r{rep}.json"
                    ok("partB_exact_lookup_present", f.exists(), f.name)
                    if f.exists():
                        dec = json.loads(f.read_text(encoding="utf-8"))
                        check_decision(f.name, dec, "EXACT_MEMORY", N, T)
                        ok("partB_exact_memory_is_miss", dec["exact_hit"] is False and dec["start_p"] == 64, f.name)
                for pol in pols:
                    name = f"{label}_N{N}_T{T}__{pol}__r{rep}"
                    f = d / "service" / f"{name}.json"
                    ok("service_complete", f.exists(), name)
                    if not f.exists():
                        continue
                    s = json.loads(f.read_text(encoding="utf-8"))
                    dec = s["decision"]
                    fd = json.loads((d / "decisions" / f"{name}.json").read_text(encoding="utf-8"))
                    ok("decision_file_equals_run_decision", fd == dec, name)
                    x = check_decision(name, dec, pol, N, T)
                    ok("service_meta", (s["N"], s["T"], s["policy"], s["goal"]) == (N, T, pol, "WALL_MIN"), name)
                    ok("first_p_is_decision", bool(s["passes"]) and s["passes"][0]["p"] == x["start_p"] == s["start_p"],
                       f"{name}: first {s['passes'][0]['p'] if s['passes'] else None} decision {x['start_p']}")
                    hist = []
                    for i, pz in enumerate(s["passes"]):
                        where = f"{name} pass {i}"
                        ok("pass_index", pz["index"] == i, where)
                        if i > 0:
                            ok("p2_rederived", SSCK.my_next_p(hist, T) == pz["p"], f"{where}: {pz['p']} own {SSCK.my_next_p(hist, T)}")
                        si = pz["selector_input"]
                        ok("selector_input_allowed_keys_only", set(si) == SSCK.ALLOWED_SELECTOR_KEYS and
                           (si["N"], si["T"], si["p"], si["goal"], si["topology"]) == (N, T, pz["p"], "WALL_MIN", SSCK.LAPTOP_TOPO), where)
                        exp_plan = SSCK.my_plan(N, T, pz["p"], "WALL_MIN")
                        ok("plan_rederived", pz["plan"] == exp_plan, where)
                        r = pz["record"]
                        ok("pass_meta", (r["N"], r["T"], r["p"], r["effective_p"], r["requested_p"], r["evaluator"]) ==
                           (N, T, pz["p"], pz["p"], pz["p"], EV) and r["initial_sha256"] == x["initial_state_digest"], where)
                        ok("pass_executed_as_planned", (r.get("mode") == "serial") == (exp_plan["backend"] == "CPU_SERIAL")
                           and (exp_plan["backend"] == "CPU_SERIAL" or (r["W"] == exp_plan["worker_count"] and
                                r["worker_cpus"] == exp_plan["worker_cpus"] and r["workers_exited"] == [0] * r["W"])), where)
                        if r["outcome"] == "DECIDED":
                            ok("cells_rederived", A1C.my_cells(r["endpoints_scaled"]) == r["cells"], where)
                        passes_by_ntp.setdefault((N, T, pz["p"]), []).append((where, tuple(json.dumps(r[k]) for k in RESULT_KEYS)))
                        hist.append((pz["p"], r["outcome"], r["completed_steps"], r.get("endpoints_scaled")))
                    nxt = SSCK.my_next_p(hist, T)
                    if nxt is None and hist:
                        want = {"DECIDED": "DECIDED", "DOMAIN_VIOLATED_PROVEN": "STOP_DOMAIN_VIOLATED_PROVEN",
                                "OUT_OF_RANGE": "STOP_OUT_OF_RANGE"}.get(hist[-1][1], f"FINAL_{hist[-1][1]}")
                        ok("final_status", s["status"] == want and s["final_p"] == hist[-1][0], f"{name}: {s['status']}")
                    elif nxt == "CAP":
                        ok("final_status", s["status"] == "REFUSED_AT_CAP", name)
                    else:
                        ok("final_status", False, f"{name}: P2 still wants p {nxt} (missing pass?)")
                    ok("p_sequence_recorded", s["p_sequence"] == [pz["p"] for pz in s["passes"]], name)
    # ---- serial references and bit identity ----
    old = {}
    files = json.load(gzip.open(SRC / "records.json.gz"))["files"]
    for name, txt in files.items():
        if name.startswith("service/") and "__SEL_CPU__" in name:
            sx = json.loads(txt)
            for pz in sx["passes"]:
                old[(sx["N"], sx["T"], pz["p"])] = tuple(json.dumps(pz["record"][k]) for k in RESULT_KEYS)
    for key, rows in passes_by_ntp.items():
        N, T, p = key
        f = d / "reference" / f"N{N}_T{T}__p{p}.json"
        ok("reference_present", f.exists(), str(key))
        if not f.exists():
            continue
        ref = json.loads(f.read_text(encoding="utf-8"))
        ok("reference_is_serial", ref["plan"]["backend"] == "CPU_SERIAL" and ref["mode"] == "serial" and ref["p"] == p, str(key))
        rv = tuple(json.dumps(ref[k]) for k in RESULT_KEYS)
        for where, view in rows:
            ok("bit_identical_to_serial_reference", view == rv, where)
        if key in old:
            ok("reference_equals_SELECTOR_SERVICE_V1_serial", old[key] == rv, str(key))
    # ---- candidate experience: written, labelled, never a true-minimum label ----
    cand = d / "candidate" / "candidate_samples.jsonl"
    if cand.exists():
        txt = cand.read_text(encoding="utf-8")
        ok("no_true_minimum_label", not FORBIDDEN_LABELS.search(txt))
        for ln in txt.splitlines():
            smp = json.loads(ln)
            ok("sample_pre_run_features_only", set(smp["pre_run_features"]) == {
                "N", "T", "pair_count", "evaluator", "topology_class", "physics_contract_hash", "numeric_contract_hash",
                "initial_state_digest"}, smp["name"])
            ok("sample_unverified_until_checker", smp["verification_status"] == "UNVERIFIED_UNTIL_CHECKER", smp["name"])
    bad = sum(v[1] for v in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "counts": counts, "issues": issues[:80],
            "bit_mismatches": counts.get("bit_identical_to_serial_reference", [0, 0])[1],
            "own_training_family": {str(k): v for k, v in own["family"].items()}}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], "bit mismatches", res["bit_mismatches"], {k: v for k, v in res["counts"].items() if v[1]},
          res["issues"][:6], "own family", res["own_training_family"])


if __name__ == "__main__":
    main()
