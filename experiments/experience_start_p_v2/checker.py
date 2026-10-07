"""Independent checker of EXPERIENCE_START_P_V2. Imports none of experience.py / policies.py / service.py / campaign.py /
analyze.py or the V1 experience / P2 / selector executor code. With its own code it rebuilds the training records and
summaries from the two source evidence archives, checks the sealed bundle, re-derives every decision, first p, P2 chain,
the fixed W6 plan, the cells, bit identity to serial references, the cross-platform anchor and the cost verdicts.

    python -m experiments.experience_start_p_v2.checker DIR
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

from experiments.multiatom_parallel_v1 import checker as MAC
from experiments.precision_pilot_a1 import checker as A1C
from experiments.selector_service_v1 import checker as SSCK        # checker-side code only (own P2)

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/experience_start_p_v2/training_bundle.json"
BUNDLE_SHA_FILE = ROOT / "docs/active/experience_start_p_v2/training_bundle.sha256"
SOURCES = {"SELECTOR_SERVICE_V1@0e6953b:docs/active/selector_service_v1/laptop_run":
           ("docs/active/selector_service_v1/laptop_run", ("service", "shadow")),
           "EXPERIENCE_START_P_V1@abf5ac7:docs/active/experience_start_p_v1/laptop_run":
           ("docs/active/experience_start_p_v1/laptop_run", ("service",))}
PHYS = ["a_reference/ar2_lang2024.py", "exact_expression_gate_v0/lang_iv.py", "exact_expression_gate_v1/common.py",
        "exact_expression_gate_v1/stream.py"]
NUM = ["experiments/formula_repro_b_v0/harness.py", "experiments/formula_repro_b_v0/upstream/probe.py",
       "experiments/precision_pilot_a1/evaluator_adapter.py", "experiments/precision_pilot_a2t/evaluator_adapter.py",
       "experiments/rewrite_pilot_a3/adapter.py", "experiments/rewrite_pilot_a3/rules.py",
       "experiments/rewrite_pilot_a3/rwforce.py"]
EV = "rw:R1+R2"
POLICIES = ("BASE64", "FAMILY_MIN", "FAMILY_MAX")
W6 = {"evaluator": EV, "backend": "CPU_PARALLEL", "worker_count": 6, "main_cpu": 0, "worker_cpus": [1, 2, 3, 4, 5, 0]}
SERIAL = {"evaluator": EV, "backend": "CPU_SERIAL", "worker_count": 0, "main_cpu": 1, "worker_cpus": []}
ANCHOR = (8, 100, 107)
RESULT_KEYS = ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells", "initial_sha256")
FORBIDDEN_LABELS = re.compile(r"true_minimum|minimum_required", re.I)


def _chash(table, files):
    return hashlib.sha256("\n".join(f"{f}:{table[f]}" for f in sorted(files)).encode()).hexdigest()


def _sha_lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _fp(phys, num, ev, init, T):
    return hashlib.sha256(json.dumps([phys, num, ev, init, T]).encode()).hexdigest()


def _rsha(r):
    x = {k: v for k, v in r.items() if k != "record_sha256"}
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def own_training():
    """From the source evidence only: the expected record identities, per-key bounds and family min / max."""
    rows, contracts, ok_all = [], set(), True
    for sid, (rel, kinds) in SOURCES.items():
        d = ROOT / rel
        files = json.load(gzip.open(d / "records.json.gz"))["files"]
        verdict = json.loads((d / "checker_verdict.json").read_text(encoding="utf-8"))
        seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
        ok_all &= verdict["verdict"] == "EVIDENCE OK" and verdict["bit_mismatches"] == 0
        phys, num = _chash(seal["source_sha256_lf"], PHYS), _chash(seal["source_sha256_lf"], NUM)
        contracts.add((phys, num))
        for name, txt in files.items():
            kind = name.split("/")[0]
            if not name.endswith(".json") or kind not in kinds:
                continue
            x = json.loads(txt)
            recs = ([(f"{name}#pass{pz['index']}", dict(pz["record"], requested_p=pz["p"])) for pz in x["passes"]]
                    if kind == "service" else [(name, x)])
            for run_id, r in recs:
                rows.append((sid, run_id, _fp(phys, num, r["evaluator"], r["initial_sha256"], r["T"]), r["N"], r["T"],
                             r["requested_p"], r["outcome"], r["evaluator"]))
    phys, num = next(iter(contracts))
    exact = {}
    for sid, run_id, fp, N, T, p, outcome, ev in rows:
        a = exact.setdefault(fp, {"N": N, "T": T, "s": set(), "f": set()})
        (a["s"] if outcome == "DECIDED" else a["f"]).add(p)
    exact = {k: {"N": a["N"], "T": a["T"], "low": min(a["s"]) if a["s"] else None,
                 "high_fail": max(a["f"]) if a["f"] else None} for k, a in exact.items()} if ok_all else {}
    fam = {}
    for e in exact.values():
        if e["low"] is not None:
            fam.setdefault(e["T"], []).append(e["low"])
    fam = {T: (min(v), max(v)) for T, v in fam.items()}
    return {"physics": phys, "numeric": num, "single_contract": len(contracts) == 1, "sources_ok": ok_all,
            "identities": {(r[0], r[1], r[2], r[5], r[6]) for r in rows}, "n_records": len(rows),
            "exact": exact, "family": fam}


def own_cost_verdicts(per_req):
    """The sealed cost rules re-implemented: per_req = {key: {policy: (median wall, median cpu)}}."""
    tot = {p: (sum(v[p][0] for v in per_req.values()), sum(v[p][1] for v in per_req.values())) for p in POLICIES}
    out = {}
    for p in ("FAMILY_MIN", "FAMILY_MAX"):
        out[f"{p}_cost_policy"] = ("USEFUL_COST_POLICY_CANDIDATE" if tot[p][0] <= 0.8 * tot["BASE64"][0] and
                                   tot[p][1] <= 0.8 * tot["BASE64"][1] else "INFO_ONLY")
    sw, sc = tot["FAMILY_MAX"][0] / tot["FAMILY_MIN"][0], tot["FAMILY_MAX"][1] / tot["FAMILY_MIN"][1]
    ew = statistics.mean(v["FAMILY_MAX"][0] / v["FAMILY_MIN"][0] for v in per_req.values())
    ec = statistics.mean(v["FAMILY_MAX"][1] / v["FAMILY_MIN"][1] for v in per_req.values())
    fw = statistics.mean(v["FAMILY_MIN"][0] / v["FAMILY_MAX"][0] for v in per_req.values())
    fc = statistics.mean(v["FAMILY_MIN"][1] / v["FAMILY_MAX"][1] for v in per_req.values())
    max_total = [m for m, s, e in (("w", sw, ew), ("c", sc, ec)) if s <= 0.95]
    min_total = [m for m, s, e in (("w", sw, fw), ("c", sc, fc)) if 1 / s <= 0.95]
    if sw <= 0.95 and sc <= 0.95 and ew <= 1.02 and ec <= 1.02:
        v = "MAX_WIN"
    elif 1 / sw <= 0.95 and 1 / sc <= 0.95 and fw <= 1.02 and fc <= 1.02:
        v = "MIN_WIN"
    elif any({"w": ew, "c": ec}[m] > 1.02 for m in max_total) or any({"w": fw, "c": fc}[m] > 1.02 for m in min_total):
        v = "DISTRIBUTION_SENSITIVE"
    elif max(abs(sw - 1), abs(sc - 1), abs(ew - 1), abs(ec - 1)) < 0.05:
        v = "TIE"
    else:
        v = "MIXED"
    out["MIN_vs_MAX"] = v
    return out, tot


def check(d, requests=None, reps=None, bundle_path=BUNDLE, bundle_sha_file=BUNDLE_SHA_FILE, require_anchor=True):
    d = Path(d)
    requests = requests or [(r["N"], r["T"]) for r in PROTO["evaluation_requests"]["requests"]]
    reps = PROTO["evaluation_requests"]["repetitions"] if reps is None else reps
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    seal = json.loads((d / "execution_seal.json").read_text(encoding="utf-8"))
    ok("seal_clean", seal["status_porcelain"] == "" and not seal["sealed_sources_dirty"], seal["status_porcelain"][:200])
    ok("mpmath_python_backend", seal.get("mpmath_backend") == "python" and seal.get("mpmath") == "1.3.0",
       f"{seal.get('mpmath')} {seal.get('mpmath_backend')}")
    # ---- the sealed V2 bundle ----
    own = own_training()
    ok("sources_verified_single_contract", own["sources_ok"] and own["single_contract"])
    sealed_sha = Path(bundle_sha_file).read_text(encoding="utf-8").strip()
    bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    canon = hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    ok("bundle_hash_matches_sealed_file", canon == sealed_sha, f"{canon[:16]} vs {sealed_sha[:16]}")
    ok("bundle_contracts_equal_source", (bundle["physics_contract_hash"], bundle["numeric_contract_hash"]) ==
       (own["physics"], own["numeric"]))
    recs = bundle["records"]
    ok("bundle_sources_allowed", {r["source_evidence_id"] for r in recs} <= set(SOURCES) and
       {m["id"] for m in bundle["sources"]} == set(SOURCES))
    ok("bundle_records_single_contract", all((r["physics_contract_hash"], r["numeric_contract_hash"], r["evaluator"]) ==
                                             (own["physics"], own["numeric"], EV) for r in recs))
    ok("bundle_records_all_verified", all(r["verification_status"] == "VERIFIED" for r in recs))
    keys = [(r["source_evidence_id"], r["run_id"]) for r in recs]
    ok("bundle_no_duplicates", len(keys) == len(set(keys)) and len({r["record_sha256"] for r in recs}) == len(recs))
    ok("bundle_record_hashes_intact", all(r["record_sha256"] == _rsha(r) for r in recs))
    ident = {(r["source_evidence_id"], r["run_id"], r["request_fingerprint"], r["attempt_p"], r["outcome"]) for r in recs}
    ok("bundle_records_equal_rebuilt_from_sources", ident == own["identities"] and len(recs) == own["n_records"] ==
       bundle["n_records"], f"{len(recs)} vs {own['n_records']}")
    eval_fps = {_fp(own["physics"], own["numeric"], EV, MAC.my_digest(*MAC.my_initial(N)), T) for N, T in requests}
    ok("bundle_contains_no_evaluation_request", not any(r["request_fingerprint"] in eval_fps for r in recs) and
       not (set(bundle["exact"]) & eval_fps))
    for k, e in bundle["exact"].items():
        o = own["exact"].get(k)
        ok("bundle_exact_equals_source", o is not None and (e["lowest_observed_success_p"], e["highest_observed_failure_p"])
           == (o["low"], o["high_fail"]), f"N{e.get('N')} T{e.get('T')}")
    ok("bundle_exact_keys_equal_source", set(bundle["exact"]) == set(own["exact"]))
    for fk, f in bundle["family"].items():
        o = own["family"].get(f["T"])
        ok("bundle_family_equals_source", o is not None and (f["FAMILY_MIN"], f["FAMILY_MAX"]) == o, fk[:40])
    ok("bundle_family_keys_equal_source", {f["T"] for f in bundle["family"].values()} == set(own["family"]))
    so = json.loads((d / "store_open.json").read_text(encoding="utf-8"))
    cur_phys = _chash({f: _sha_lf(ROOT / f) for f in PHYS}, PHYS)
    cur_num = _chash({f: _sha_lf(ROOT / f) for f in NUM}, NUM)
    ok("store_opened_with_sealed_bundle", so["bundle_sha256"] == sealed_sha == so["sealed_sha256"])
    ok("campaign_contracts_equal_current_and_training", (so["current_physics"], so["current_numeric"]) ==
       (cur_phys, cur_num) == (own["physics"], own["numeric"]))

    # ---- decisions and service runs ----
    def expected(policy, N, T):
        init = MAC.my_digest(*MAC.my_initial(N))
        fp = _fp(own["physics"], own["numeric"], EV, init, T)
        e = own["exact"].get(fp)
        fam = own["family"].get(T)
        start = fam[0] if policy == "FAMILY_MIN" and fam else fam[1] if policy == "FAMILY_MAX" and fam else 64
        return {"start_p": start, "request_fingerprint": fp, "initial_state_digest": init, "exact_hit": e is not None,
                "exact_low": e["low"] if e else None, "family": fam}

    def check_decision(where, dec, policy, N, T):
        x = expected(policy, N, T)
        ok("decision_bundle_sha", dec["bundle_sha256"] == sealed_sha, where)
        ok("decision_rederived", dec["policy"] == policy and dec["start_p"] == x["start_p"] and
           dec["request_fingerprint"] == x["request_fingerprint"] and dec["initial_state_digest"] == x["initial_state_digest"]
           and dec["exact_hit"] == x["exact_hit"] and dec["exact_lowest_observed_success_p"] == x["exact_low"]
           and (dec["FAMILY_MIN"], dec["FAMILY_MAX"]) == (x["family"] if x["family"] else (None, None)),
           f"{where}: start {dec['start_p']} vs {x['start_p']}")
        return x

    passes_by_ntp, per_req = {}, {}
    snaps = {}
    if (d / "load_snapshots.jsonl").exists():
        for ln in (d / "load_snapshots.jsonl").read_text(encoding="utf-8").splitlines():
            s = json.loads(ln)
            snaps[s["tag"]] = s["contaminated"]
    for N, T in requests:
        key = f"N{N}_T{T}"
        clean_vals = {p: [] for p in POLICIES}
        for rep in range(reps):
            f = d / "decisions" / f"{key}__EXACT_LOOKUP__r{rep}.json"
            ok("exact_lookup_present", f.exists(), f.name)
            if f.exists():
                dec = json.loads(f.read_text(encoding="utf-8"))
                x = check_decision(f.name, dec, "EXACT_LOOKUP", N, T)
                ok("exact_lookup_is_miss", dec["exact_hit"] is False and x["exact_hit"] is False and
                   dec["exact_lowest_observed_success_p"] is None, f.name)
            for pol in POLICIES:
                name = f"{key}__{pol}__r{rep}"
                f = d / "service" / f"{name}.json"
                ok("service_complete", f.exists(), name)
                if not f.exists():
                    continue
                s = json.loads(f.read_text(encoding="utf-8"))
                dec = s["decision"]
                fd = json.loads((d / "decisions" / f"{name}.json").read_text(encoding="utf-8"))
                ok("decision_file_equals_run_decision", fd == dec, name)
                x = check_decision(name, dec, pol, N, T)
                ok("decision_exact_miss", dec["exact_hit"] is False, name)
                ok("service_meta", (s["N"], s["T"], s["policy"], s["plan_kind"]) == (N, T, pol, "W6"), name)
                ok("first_p_is_decision", bool(s["passes"]) and s["passes"][0]["p"] == x["start_p"] == s["start_p"],
                   f"{name}: first {s['passes'][0]['p'] if s['passes'] else None} decision {x['start_p']}")
                hist, cpu = [], 0.0
                for i, pz in enumerate(s["passes"]):
                    where = f"{name} pass {i}"
                    ok("pass_index", pz["index"] == i and pz["p_source"] == ("decision" if i == 0 else "P2"), where)
                    if i > 0:
                        ok("p2_rederived", SSCK.my_next_p(hist, T) == pz["p"], f"{where}: {pz['p']} own {SSCK.my_next_p(hist, T)}")
                    ok("plan_is_fixed_W6", pz["plan"] == dict(W6, precision=pz["p"]), where)
                    r = pz["record"]
                    ok("pass_meta", (r["N"], r["T"], r["p"], r["effective_p"], r["requested_p"], r["evaluator"]) ==
                       (N, T, pz["p"], pz["p"], pz["p"], EV) and r["initial_sha256"] == x["initial_state_digest"], where)
                    ok("pass_executed_as_planned", r.get("mode") != "serial" and r["W"] == 6 and
                       r["worker_cpus"] == W6["worker_cpus"] and r["main_cpu"] == 0 and r["workers_exited"] == [0] * 6
                       and r["plan"] == dict(W6, precision=pz["p"]), where)
                    if r["outcome"] == "DECIDED":
                        ok("cells_rederived", A1C.my_cells(r["endpoints_scaled"]) == r["cells"], where)
                    passes_by_ntp.setdefault((N, T, pz["p"]), []).append((where, tuple(json.dumps(r[k]) for k in RESULT_KEYS)))
                    hist.append((pz["p"], r["outcome"], r["completed_steps"], r.get("endpoints_scaled")))
                    cpu += r["total_cpu_s"]
                nxt = SSCK.my_next_p(hist, T)
                if nxt is None and hist:
                    want = {"DECIDED": "DECIDED", "DOMAIN_VIOLATED_PROVEN": "STOP_DOMAIN_VIOLATED_PROVEN",
                            "OUT_OF_RANGE": "STOP_OUT_OF_RANGE"}.get(hist[-1][1], f"FINAL_{hist[-1][1]}")
                    ok("final_status", s["status"] == want and s["final_p"] == hist[-1][0], f"{name}: {s['status']}")
                elif nxt == "CAP":
                    ok("final_status", s["status"] == "REFUSED_AT_CAP", name)
                else:
                    ok("final_status", False, f"{name}: P2 still wants p {nxt} (missing pass?)")
                ok("p_sequence_recorded", s["p_sequence"] == [pz["p"] for pz in s["passes"]] and
                   s["n_passes"] == len(s["passes"]), name)
                if not snaps.get(f"{key}__r{rep}", False):
                    clean_vals[pol].append((s["service_wall_s"], cpu))
        if all(clean_vals[p] for p in POLICIES):
            per_req[key] = {p: (statistics.median(w for w, _ in clean_vals[p]), statistics.median(c for _, c in clean_vals[p]))
                            for p in POLICIES}
    # ---- serial references, bit identity, cross-platform anchor ----
    for key, rows in passes_by_ntp.items():
        N, T, p = key
        f = d / "reference" / f"N{N}_T{T}__p{p}.json"
        ok("reference_present", f.exists(), str(key))
        if not f.exists():
            continue
        ref = json.loads(f.read_text(encoding="utf-8"))
        ok("reference_is_serial", ref["plan"] == dict(SERIAL, precision=p) and ref["mode"] == "serial" and ref["p"] == p,
           str(key))
        rv = tuple(json.dumps(ref[k]) for k in RESULT_KEYS)
        if ref["outcome"] == "DECIDED":
            ok("cells_rederived", A1C.my_cells(ref["endpoints_scaled"]) == ref["cells"], f"reference {key}")
        for where, view in rows:
            ok("bit_identical_to_serial_reference", view == rv, where)
    if require_anchor:
        N, T, p = ANCHOR
        f = d / "anchor" / f"N{N}_T{T}__p{p}.json"
        ok("anchor_present", f.exists())
        if f.exists():
            a = json.loads(f.read_text(encoding="utf-8"))
            lap = None
            files = json.load(gzip.open(ROOT / "docs/active/selector_service_v1/laptop_run/records.json.gz"))["files"]
            for name, txt in files.items():
                if name.startswith("service/") and "__SEL_CPU__" in name:
                    sx = json.loads(txt)
                    for pz in sx["passes"]:
                        if (sx["N"], sx["T"], pz["p"]) == ANCHOR:
                            lap = tuple(json.dumps(pz["record"][k]) for k in RESULT_KEYS)
            ok("anchor_bit_identical_to_laptop_serial", lap is not None and lap == tuple(json.dumps(a[k]) for k in RESULT_KEYS))
            ok("anchor_is_serial", a["plan"] == dict(SERIAL, precision=p))
    # ---- candidate experience ----
    for fname in ("candidate_samples.jsonl", "candidate_experience.jsonl"):
        cand = d / "candidate_v2" / fname
        ok("candidate_present", cand.exists(), fname)
        if cand.exists():
            ok("no_true_minimum_label", not FORBIDDEN_LABELS.search(cand.read_text(encoding="utf-8")), fname)
    cand = d / "candidate_v2" / "candidate_samples.jsonl"
    if cand.exists():
        for ln in cand.read_text(encoding="utf-8").splitlines():
            smp = json.loads(ln)
            ok("sample_pre_run_features_only", set(smp["pre_run_features"]) == {
                "N", "T", "pair_count", "evaluator", "topology_class", "physics_contract_hash", "numeric_contract_hash",
                "initial_state_digest"}, smp["name"])
            ok("sample_unverified_until_checker", smp["verification_status"] == "UNVERIFIED_UNTIL_CHECKER", smp["name"])
    cand = d / "candidate_v2" / "candidate_experience.jsonl"
    if cand.exists():
        for ln in cand.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            ok("candidate_record_unverified", r["verification_status"] == "UNVERIFIED" and
               r["source_evidence_id"] == "EXPERIENCE_START_P_V2:candidate", r["run_id"])
    # ---- cost verdicts: own computation, and the analysis file if present ----
    own_rules, own_tot = (own_cost_verdicts(per_req) if len(per_req) == len(requests) else ({}, {}))
    fa = d / "analysis.json"
    if fa.exists() and own_rules:
        an = json.loads(fa.read_text(encoding="utf-8"))
        for k, v in own_rules.items():
            ok("analysis_verdict_rederived", an["rules"].get(k) == v, f"{k}: {an['rules'].get(k)} vs own {v}")
        for p in POLICIES:
            ok("analysis_totals_rederived", abs(an["totals"][p]["wall"] - own_tot[p][0]) < 1e-9 and
               abs(an["totals"][p]["cpu"] - own_tot[p][1]) < 1e-9, p)
    bad = sum(v[1] for v in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "counts": counts, "issues": issues[:80],
            "bit_mismatches": counts.get("bit_identical_to_serial_reference", [0, 0])[1],
            "own_training_family": {str(k): v for k, v in own["family"].items()}, "own_cost_rules": own_rules,
            "own_totals": {p: list(v) for p, v in own_tot.items()}, "analysis_checked": fa.exists() and bool(own_rules)}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], "bit mismatches", res["bit_mismatches"], {k: v for k, v in res["counts"].items() if v[1]},
          res["issues"][:6], "own family", res["own_training_family"], "own rules", res["own_cost_rules"],
          "analysis checked", res["analysis_checked"])


if __name__ == "__main__":
    main()
