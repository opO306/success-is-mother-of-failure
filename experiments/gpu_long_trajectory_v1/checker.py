"""Independent checker of GPU_LONG_TRAJECTORY_V1 (protocol 'checker').

Imports none of the long runner, service, campaign, support (precision layer), traj, one_step, pv_host or GPU code.
It reuses only the earlier INDEPENDENT checkers' primitives (GPU_SHORT_TRAJECTORY_V1 checker: digests, literal forces;
GPU_PAIR_VECTOR_V1 checker: per-pair literal loop and record decoding) and implements here its own literal T = 1000
KDK pass, its own pass readout (outcome, scaled endpoints), its own P2 rule (from the protocol text, not policies.py)
and its own service restart semantics (every pass from its own FCC initial state).

    python -m experiments.gpu_long_trajectory_v1.checker DIR --phase gateP|fixed|service [--workers W]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from pathlib import Path

from mpmath import iv

from experiments.gpu_pair_vector_v1 import checker as PVC
from experiments.gpu_short_trajectory_v1 import checker as SC_

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/active/gpu_long_trajectory_v1/bundle.json.gz"
BUNDLE_SHA_FILE = ROOT / "docs/active/gpu_long_trajectory_v1/bundle.json.gz.sha256"
V2 = ROOT / "docs/active/experience_start_p_v2/vast_run/records.json.gz"
T = 1000
CHECKS = (0, 1, 2, 5, 10, 20, 50, 100, 200, 250, 500, 750, 900, 950, 990, 999, 1000)
STAGES = ("F_s", "p_half", "q1", "F1", "p1")
EARLIER_STAGE_P = (64, 109, 128, 163, 192)
BASELINE_P = (64, 163)
NEW_P = (73, 78, 161, 166)
START_P = {"BASE64": 64, "FAMILY_MAX": 163}
FINAL = ("DECIDED", "DOMAIN_VIOLATED_PROVEN", "OUT_OF_RANGE", "INVALID_EVIDENCE")
P_MIN, P_MAX, GUARD, MAX_PASSES = 64, 1024, 8, 24
WF, WA = 114, 26
_OWN = {}

vdig, sdig, _rows, _raw, my_forces = SC_.vdig, SC_.sdig, SC_._rows, SC_._raw, SC_.my_forces


# ---------------------------------------------------------------------------
# own P2 (rule text of the protocol / PRECISION_PILOT_A1; independent code)
# ---------------------------------------------------------------------------
def _round_half_even(x):
    fl = x.numerator // x.denominator
    rem = x - fl
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and fl % 2 == 1):
        return fl + 1
    return fl


def _ceil_log2(x):
    e = 0
    while Fraction(2) ** e < x:
        e += 1
    while Fraction(2) ** (e - 1) >= x:
        e -= 1
    return e


def my_p2(last):
    p, out = last["requested_p"], last["outcome"]
    if out == "UNDECIDED_AT_PRECISION" and last.get("endpoints_scaled"):
        extra = None
        for lo, hi in last["endpoints_scaled"]:
            lo, hi = Fraction(lo), Fraction(hi)
            if _round_half_even(lo) == _round_half_even(hi):
                continue
            mid = (lo + hi) / 2
            margin = Fraction(1, 2) - abs(mid - _round_half_even(mid))
            e = 32 if margin <= 0 else _ceil_log2((hi - lo) / margin)
            extra = e if extra is None else max(extra, e)
        nxt = p + max(extra or 0, 1) + GUARD
    elif out == "DOMAIN_UNPROVEN":
        k = last["completed_steps"]
        nxt = 2 * p if k <= 0 else -((-p * T) // k) + GUARD
    else:
        nxt = 2 * p
    return max(nxt, p + 1)


# ---------------------------------------------------------------------------
# own pass
# ---------------------------------------------------------------------------
def _scaled(vals_q, vals_p):
    out = []
    for vals, sh in ((vals_q, 48), (vals_p, 80)):
        for v in vals:
            pair = []
            for end in v._mpi_:
                s, m, e, bc = end
                x = Fraction(m) * (Fraction(2) ** e) if m else Fraction(0)
                pair.append(str((-x if s else x) * (1 << sh)))
            out.append(pair)
    return out


def own_initial(N, p):
    import exact_expression_gate_v0.lang_iv as LI
    from experiments.multiatom_parallel_v1 import scenarios as SC
    iv.prec = p
    q0, p0 = SC.initial(N)
    return [[LI.c(x) for x in r] for r in q0], [[LI.c(x) for x in r] for r in p0]


def own_pass(N, p, keep=()):
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    q, pm = own_initial(N, p)
    iv.prec = p
    cdt = LI.c(K.CDT)
    o = {"N": N, "p": p, "initial": {"q": _raw(q), "p_mom": _raw(pm)}, "steps": [], "full": {}, "kept": {},
         "stop": None, "completed_steps": 0, "record": None}
    st, pid, F = my_forces(q, p)
    if st != "OK":
        o["stop"] = {"status": st, "stop_state": 0, "stop_pair": pid}
    else:
        o["full"][0] = {"q": _raw(q), "p_mom": _raw(pm), "F": _raw(F)}
        for s in range(T):
            ph = [[pm[a][k] + F[a][k] for k in range(3)] for a in range(N)]
            q1 = [[q[a][k] + ph[a][k] * cdt for k in range(3)] for a in range(N)]
            rec = {"s": s, "F_s": vdig("F", _raw(F)), "p_half": vdig("P", _raw(ph)), "q1": vdig("Q", _raw(q1))}
            st, pid, F1 = my_forces(q1, p)
            if st != "OK":
                o["steps"].append(rec)
                o["stop"] = {"status": st, "stop_state": s + 1, "stop_pair": pid}
                if s in keep:
                    o["kept"][s] = {"F_s": _raw(F), "p_half": _raw(ph), "q1": _raw(q1)}
                break
            p1 = [[ph[a][k] + F1[a][k] for k in range(3)] for a in range(N)]
            rq, rp, rf = _raw(q1), _raw(p1), _raw(F1)
            rec.update(F1=vdig("F", rf), p1=vdig("P", rp), state=sdig(rq, rp), force=vdig("F", rf))
            o["steps"].append(rec)
            if s in keep:
                o["kept"][s] = {"F_s": _raw(F), "p_half": _raw(ph), "q1": rq, "F1": rf, "p1": rp}
            if s + 1 in CHECKS:
                o["full"][s + 1] = {"q": rq, "p_mom": rp, "F": rf}
            q, pm, F = q1, p1, F1
            o["completed_steps"] = s + 1
    rec = {"completed_steps": o["completed_steps"], "stop": None, "stop_step": None, "cells": None,
           "endpoints_key": None, "endpoints_scaled": None}
    if o["stop"]:
        kind = o["stop"]["status"].replace("DOMAIN_STOP_", "")
        rec.update(stop=kind, stop_step=o["stop"]["stop_state"])
        rec["outcome"] = {"VIOLATED": "DOMAIN_VIOLATED_PROVEN", "UNPROVEN": "DOMAIN_UNPROVEN"}[kind]
        rec["completed_steps"] = max(o["stop"]["stop_state"] - 1, 0)
    else:
        qv, pv = [x for r in q for x in r], [x for r in pm for x in r]
        try:
            cells = K.decide(qv, pv)
            rec.update(cells=cells, endpoints_key=K.endpoints_key(qv + pv), endpoints_scaled=_scaled(qv, pv))
            rec["outcome"] = "DECIDED" if cells is not None else "UNDECIDED_AT_PRECISION"
        except K.OutOfRange:
            rec.update(stop="OUT_OF_RANGE", stop_step=o["completed_steps"], outcome="OUT_OF_RANGE")
    o["record"] = rec
    return o


def _own_task(args):
    N, p, keep = args
    key = (N, p, tuple(keep))
    hit = next((v for k, v in _OWN.items() if k[:2] == (N, p) and set(keep) <= set(k[2])), None)
    if hit is None:
        hit = _OWN[key] = own_pass(N, p, set(keep))
    return (N, p), hit


def own_service(N, policy, get):
    """The expected p sequence: P2 on the checker's own pass records, every pass from its own initial state.
    get(N, p) -> the checker's own pass."""
    hist, seq = [], []
    p = START_P[policy]
    while True:
        if p == "CAP":
            return seq, "REFUSED_AT_CAP"
        if len(seq) >= MAX_PASSES:
            return seq, "REFUSED_PASS_LIMIT"
        r = get(N, p)["record"]
        seq.append(p)
        hist.append({"requested_p": p, **r})
        if r["outcome"] in FINAL:
            return seq, r["outcome"]
        nxt = my_p2(hist[-1])
        p = nxt if nxt <= P_MAX else ("CAP" if max(seq) >= P_MAX else P_MAX)


def v2_reference(N, p):
    files = json.loads(gzip.open(V2).read())["files"]
    k = f"reference/N{N}_T1000__p{p}.json"
    return json.loads(files[k]) if k in files else None


# ---------------------------------------------------------------------------
# gate P (per pair)
# ---------------------------------------------------------------------------
def check_gate_p(d, b, ok):
    states = {g["id"]: g for g in b["gate_P_states"]}
    per_p, layouts = {}, {}
    for mf in sorted((d / "gateP").glob("*.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        g = states.get(m["state_id"])
        ok("gateP_state_known", g is not None, mf.name)
        if g is None:
            continue
        p, N = m["requested_p"], g["N"]
        clean = m["fault"] is None
        st = per_p.setdefault(p, {"bad": 0, "pairs_exact": 0, "unsound": 0, "domain_mismatch": 0, "echo_bad": 0,
                                  "atoms_exact": 0, "refused": 0, "states": 0})

        def bad(name, cond, detail=""):
            ok(name, cond, detail)
            if not cond:
                st["bad"] += 1
        bad("gateP_requested_p_equals_state_p", p == g["p"], mf.name)
        bad("gateP_settings_clean", clean, mf.name)
        stem = mf.name[:-5]
        rf = gzip.decompress((d / "gateP" / f"{stem}.full.gz").read_bytes())
        ra = gzip.decompress((d / "gateP" / f"{stem}.atoms.gz").read_bytes())
        if m["status"].startswith("REFUSED"):
            st["refused"] += 1
            st["bad"] += 1
            continue
        st["states"] += 1
        bad("gateP_device_p_equals_requested", m["device_p"] == p, f"{mf.name}: device {m['device_p']} requested {p}")
        q = [[PVC._dec_iv(e) for e in r] for r in g["q"]]
        pairs, first, F = PVC.own_forces(q, p)
        fw, aw = PVC._words(rf), PVC._words(ra)
        P = N * (N - 1) // 2
        bad("gateP_pair_count", len(fw) == P * WF, mf.name)
        gfirst = None
        for pid in range(min(P, len(fw) // WF)):
            o = fw[pid * WF:(pid + 1) * WF]
            gst = PVC.ST.get(o[0], f"S{o[0]}")
            if o[3] != p:
                st["echo_bad"] += 1
            bad("gateP_precision_echo", o[3] == p, f"{mf.name}#{pid}: {o[3]}")
            bad("gateP_pair_id", o[1] == pid, f"{mf.name}#{pid}")
            cst, cr2, cg, cJ = pairs[pid]
            if gst != "PROVEN" and gfirst is None:
                gfirst = pid
            if gst != cst:
                st["domain_mismatch"] += 1
                bad("gateP_domain_status", False, f"{mf.name}#{pid}: gpu {gst} cpu {cst}")
                continue
            bad("gateP_r2_equal", PVC._iv(o[4:26]) == cr2, f"{mf.name}#{pid}")
            if cst != "PROVEN":
                continue
            bad("gateP_obligations_complete", o[2] == 0b11, f"{mf.name}#{pid}")
            bad("gateP_G_equal", PVC._iv(o[26:48]) == cg, f"{mf.name}#{pid}")
            gJ = tuple(PVC._iv(o[48 + 22 * k:70 + 22 * k]) for k in range(3))
            cls = PVC.classify(gJ, cJ)
            if cls == "PAIR_UNSOUND":
                st["unsound"] += 1
            if cls == "PAIR_EXACT":
                st["pairs_exact"] += 1
            bad("gateP_J_exact", cls == "PAIR_EXACT", f"{mf.name}#{pid}: {cls}")
        bad("gateP_first_stop_pair", gfirst == first, f"{mf.name}: gpu {gfirst} cpu {first}")
        if F is not None:
            gF = [[PVC._iv(aw[(3 * a + k) * WA + 4:(3 * a + k + 1) * WA]) for k in range(3)] for a in range(N)]
            echo = {aw[t * WA + 2] for t in range(3 * N)}
            bad("gateP_atom_precision_echo", echo == {p}, f"{mf.name}: {echo}")
            same = gF == F
            st["atoms_exact"] += same
            bad("gateP_atom_F_equal", same, mf.name)
        layouts.setdefault(m["state_id"], []).append(hashlib.sha256(rf + ra).hexdigest())
    for sid, hs in layouts.items():
        ok("gateP_layouts_identical", len(set(hs)) == 1 and len(hs) >= 2, sid)
    verified = sorted(p for p, s in per_p.items() if s["bad"] == 0 and s["states"] > 0)
    failed = sorted(p for p, s in per_p.items() if p not in verified)
    for p in BASELINE_P:
        ok("gateP_baseline_p_exact", p in verified, str(p))
    support = {"verified_in_gate_P": verified, "failed_in_gate_P": failed,
               "earlier_stage_p": list(EARLIER_STAGE_P),
               "GPU_SUPPORTED_P": sorted(set(verified) | (set(EARLIER_STAGE_P) - set(failed))),
               "GPU_UNSUPPORTED_P": sorted(set(NEW_P) - set(verified)), "per_p": {str(k): v for k, v in per_p.items()}}
    return support


# ---------------------------------------------------------------------------
# passes and services
# ---------------------------------------------------------------------------
def _first_diff(X, Y):
    return SC_._first_diff(X, Y)


def check_pass(r, o, ok, support, label):
    """One pass record (fixed run or service pass) against the checker's own pass at (N, p)."""
    f = label
    rec = r["pass_record"]
    want = o["record"]
    N, p = o["N"], o["p"]
    ok("C0_pass_starts_from_original_state", (_rows(r["echo_q0"]), _rows(r["echo_p0"])) ==
       (o["initial"]["q"], o["initial"]["p_mom"]), f)
    for k in ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key", "endpoints_scaled"):
        ok(f"pass_{k}_equal", rec.get(k) == want.get(k), f"{f}: {str(rec.get(k))[:60]} vs {str(want.get(k))[:60]}")
    fd = None
    if r["backend"] == "CPU_E2_FALLBACK":
        ok("fallback_only_for_unsupported_p", p not in support["GPU_SUPPORTED_P_USED"], f"{f}: p {p}")
        ok("fallback_p_unchanged", r["requested_p"] == p and r.get("effective_p") == p, f)
        return all(rec.get(k) == want.get(k) for k in ("outcome", "completed_steps", "stop_step", "cells",
                                                         "endpoints_key")), None
    ok("gpu_only_for_supported_p", p in support["GPU_SUPPORTED_P_USED"], f"{f}: p {p}")
    ok("device_p_equals_requested", r["device_p"] == p == r["requested_p"], f"{f}: device {r['device_p']}")
    ok("device_precision_echo", r["device_p_echo"] == [p], f"{f}: {r['device_p_echo']}")
    want_stop = o["stop"] or {"status": "OK", "stop_state": None, "stop_pair": None}
    got_stop = {"status": r["status"], "stop_state": r["stop_state"], "stop_pair": r["stop_pair"]}
    ok("stop_equal", got_stop == want_stop, f"{f}: gpu {got_stop} cpu {want_stop}")
    idx = [x["s"] for x in r["steps"]]
    ok("step_indices_contiguous", idx == list(range(len(idx))), f)
    ok("step_count_equal", len(r["steps"]) == len(o["steps"]), f"{f}: {len(r['steps'])} vs {len(o['steps'])}")
    mism = None
    for a, (x, y) in enumerate(zip(o["steps"], r["steps"])):
        badk = [st for st in STAGES + ("state", "force") if x.get(st) != y.get(st)]
        if badk and mism is None:
            mism = (a, [st for st in STAGES if st in badk] or badk)
    ok("per_step_digests_equal", mism is None and len(r["steps"]) == len(o["steps"]), f"{f}: first {mism}")
    ev = (want_stop["stop_state"] + 1) if want_stop["status"] != "OK" else T + 1
    ok("force_evaluations_reuse", r["force_evals"] == ev, f"{f}: {r['force_evals']} vs {ev}")
    ok("executor_persistent_in_pass", r["uploads_in_pass"] == 0 and r["allocs_in_pass"] == 0, f)
    for rel in CHECKS:
        if want_stop["status"] != "OK" and rel >= want_stop["stop_state"]:
            continue
        g = r["full"].get(str(rel))
        ok("checkpoint_present", g is not None, f"{f} rel {rel}")
        if g is None:
            continue
        gq, gp, gF = _rows(g["q"]), _rows(g["p_mom"]), _rows(g["F"])
        c = o["full"].get(rel)
        ok("checkpoint_endpoints_equal", c is not None and (gq, gp, gF) == (c["q"], c["p_mom"], c["F"]), f"{f} rel {rel}")
        if rel == 0:
            ok("digest_self_consistent", bool(r["steps"]) and vdig("F", gF) == r["steps"][0]["F_s"], f"{f} rel 0")
        elif rel - 1 < len(r["steps"]):
            y = r["steps"][rel - 1]
            ok("digest_self_consistent", (vdig("Q", gq), vdig("P", gp), vdig("F", gF), sdig(gq, gp)) ==
               (y["q1"], y["p1"], y["F1"], y["state"]), f"{f} rel {rel}")
    if mism is not None:
        fd = {"run": f, "N": N, "precision": p, "first_divergence_state": mism[0] + 1, "first_divergence_step": mism[0],
              "first_divergence_stage": mism[1][0]}
        dump, kept = r.get("dump"), o["kept"].get(mism[0])
        if dump and dump["s"] == mism[0] and kept and dump.get(mism[1][0]) is not None and mism[1][0] in kept:
            fd.update(_first_diff(kept[mism[1][0]], _rows(dump[mism[1][0]])) or
                      {"note": "endpoints equal - digest serialization differs"})
    good = mism is None and got_stop == want_stop and r["force_evals"] == ev and \
        all(rec.get(k) == want.get(k) for k in ("outcome", "completed_steps", "stop_step", "cells", "endpoints_key"))
    return good, fd


def check(d, bundle_path=BUNDLE, bundle_sha_file=BUNDLE_SHA_FILE, phase="service", expect_complete=True, workers=1,
          support_override=None):
    d = Path(d)
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    raw = Path(bundle_path).read_bytes()
    sealed = Path(bundle_sha_file).read_text(encoding="utf-8").strip()
    ok("bundle_hash_matches_sealed_file", hashlib.sha256(raw).hexdigest() == sealed)
    b = json.loads(gzip.decompress(raw))
    envf = d / "env.json"
    if envf.exists():
        env = json.loads(envf.read_text(encoding="utf-8"))
        ok("seal_clean", env["status_porcelain"] == "" and not env["sealed_sources_dirty"], env["status_porcelain"][:200])
        ok("env_bundle_sha", env["bundle_sha256"] == sealed)
    out = {"phase": phase}
    # ---- gate P
    if (d / "gateP").exists():
        support = check_gate_p(d, b, ok)
        out["support"] = support
    else:
        support = None
    if phase == "gateP":
        if expect_complete:
            for g in b["gate_P_states"]:
                ok("gateP_state_present", any((d / "gateP").glob(f"{g['id']}__*.json")), g["id"])
        bad = sum(v[1] for v in counts.values())
        out.update(verdict="EVIDENCE OK" if bad == 0 else "NOT_OK", counts=counts, issues=issues[:80])
        return out
    # ---- trajectory passes
    runs = [json.loads(gzip.decompress(f.read_bytes())) | {"_file": f.name} for f in sorted((d / "runs").glob("*.json.gz"))]
    services = [json.loads(gzip.decompress(f.read_bytes())) | {"_file": f.name}
                for f in sorted((d / "services").glob("*.json.gz"))] if (d / "services").exists() else []
    passes = [(r["_file"], r) for r in runs] + [(f"{s['_file']}#{i}", x) for s in services for i, x in enumerate(s["passes"])]
    need, keep = set(), {}
    for _, r in passes:
        need.add((r["N"], r["requested_p"]))
        if r.get("dump"):
            keep.setdefault((r["N"], r["requested_p"]), set()).add(r["dump"]["s"])
    tasks = [(N, p, sorted(keep.get((N, p), ()))) for N, p in sorted(need)]
    if workers > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(min(workers, len(tasks))) as pool:
            res = list(pool.map(_own_task, tasks))
    else:
        res = [_own_task(t) for t in tasks]
    own = dict(res)

    def get(N, p):
        if (N, p) not in own:
            own[(N, p)] = _own_task((N, p, []))[1]
        return own[(N, p)]
    # own vs bundle (the stream.run replica) and vs the V2 references
    trajs = {(t["N"], t["p"]): t for t in b["trajectories"]}
    for (N, p), o in own.items():
        t = trajs.get((N, p))
        if t is not None:
            ok("own_initial_equals_bundle", (o["initial"]["q"], o["initial"]["p_mom"]) == (_rows(t["q0"]), _rows(t["p0"])),
               f"N{N} p{p}")
            ok("own_steps_equal_bundle_replica", o["steps"] == t["steps"], f"N{N} p{p}")
            ok("own_stop_equals_bundle", o["stop"] == t["stop"], f"N{N} p{p}: {o['stop']} vs {t['stop']}")
            for rel, full in o["full"].items():
                if str(rel) in t["full"]:
                    ok("own_full_equals_bundle", full == {k: _rows(t["full"][str(rel)][k]) for k in ("q", "p_mom", "F")},
                       f"N{N} p{p} rel {rel}")
            for k in ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key", "endpoints_scaled"):
                ok("own_record_equals_bundle", o["record"].get(k) == t["pass_record"].get(k), f"N{N} p{p} {k}")
        ref = v2_reference(N, p)
        if ref is not None:
            for k in ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key"):
                ok("own_record_equals_V2_reference", o["record"].get(k) == ref.get(k), f"N{N} p{p} {k}")
    sup_used = support_override or (support and support["GPU_SUPPORTED_P"]) or list(EARLIER_STAGE_P)
    stats = {"passes": 0, "passes_exact": 0, "passes_mismatch": 0, "stops_exact": 0, "steps_compared": 0,
             "gpu_passes": 0, "cpu_fallback_passes": 0, "services": 0, "services_exact": 0}
    first_div, layouts = [], {}
    for label, r in passes:
        o = own[(r["N"], r["requested_p"])]
        ok("run_settings_clean", r["fault"] == 0 and r["work_limbs"] == 16, label)
        sup = {"GPU_SUPPORTED_P_USED": r.get("support_used", sup_used)}
        good, fd = check_pass(r, o, ok, sup, label)
        stats["passes"] += 1
        stats["passes_exact" if good else "passes_mismatch"] += 1
        stats["gpu_passes" if r["backend"] == "GPU" else "cpu_fallback_passes"] += 1
        if r["backend"] == "GPU":
            stats["steps_compared"] += len(r["steps"])
            if o["stop"] and good:
                stats["stops_exact"] += 1
        if fd:
            first_div.append(fd)
        if r.get("kind") == "FIXED":
            view = json.dumps({k: r[k] for k in ("steps", "full", "pass_record", "status", "stop_state", "stop_pair")},
                              sort_keys=True)
            layouts.setdefault((r["N"], r["requested_p"]), []).append((r["block"], view))
    for key, v in layouts.items():
        ok("layouts_identical", len({x for _, x in v}) == 1, f"{key}: {len(v)}")
    # services: start p, P2 sequence (own), restart, labels, final result
    final_cells = {}
    for s in services:
        f = s["_file"]
        stats["services"] += 1
        ok("service_settings_clean", s.get("fault", 0) == 0, f)
        exp_seq, exp_final = own_service(s["N"], s["policy"], get)
        seq = [x["requested_p"] for x in s["passes"]]
        ok("service_start_p", bool(seq) and seq[0] == START_P[s["policy"]], f"{f}: {seq[:1]}")
        ok("service_p2_sequence", exp_seq is not None and seq == exp_seq, f"{f}: {seq} vs own {exp_seq}")
        ok("service_p_source", [x["p_source"] for x in s["passes"]] == ["decision"] + ["P2"] * (len(seq) - 1), f)
        ok("service_every_pass_from_original_state", all(x["start"] == "ORIGINAL_Q0_P0" for x in s["passes"]), f)
        last = s["passes"][-1]["pass_record"] if s["passes"] else {}
        ok("service_final_status", s["status"] == ("DECIDED" if exp_final == "DECIDED" else f"FINAL_{exp_final}"),
           f"{f}: {s['status']} vs {exp_final}")
        ok("service_final_p", s["final_p"] == (seq[-1] if seq else None), f)
        own_last = get(s["N"], seq[-1])["record"] if seq else None
        ok("service_final_cells_equal_cpu", own_last is not None and last.get("cells") == own_last["cells"], f)
        backends = {x["backend"] for x in s["passes"]}
        label = "GPU_FULL_RETRY" if backends == {"GPU"} else "GPU_WITH_CPU_PRECISION_FALLBACK"
        ok("service_backend_label", s["execution_label"] == label, f"{f}: {s['execution_label']} vs {label}")
        ok("service_support_set_recorded", "support_used" in s, f)
        if support is not None:
            ok("service_support_subset_of_checker_verified", set(s.get("support_used", [])) <=
               set(support["GPU_SUPPORTED_P"]), f"{f}: {s.get('support_used')}")
        good = seq == exp_seq and own_last is not None and last.get("cells") == own_last["cells"]
        stats["services_exact"] += good
        if s["status"] == "DECIDED":
            final_cells.setdefault(s["N"], {})[f"{s['policy']}@{s['final_p']}"] = last.get("cells")
    out["final_cells_across_policies_equal"] = {str(N): len({json.dumps(c) for c in v.values()}) == 1
                                                for N, v in final_cells.items()}
    if expect_complete:
        for N in (12, 16):
            ok("fixed_p163_layouts_complete", sorted(b for b, _ in layouts.get((N, 163), [])) == [32, 64, 128, 256], str(N))
            ok("fixed_p64_long_stop_present", (N, 64) in layouts, str(N))
        ok("fixed_N40_present", (40, 109) in layouts)
        if phase == "service":
            for N in (12, 16):
                for pol in START_P:
                    ok("service_present", any(s["N"] == N and s["policy"] == pol and not s.get("demonstration")
                                              for s in services), f"N{N} {pol}")
            ok("fallback_demonstration_present", any(s.get("demonstration") for s in services))
    bad = sum(v[1] for v in counts.values())
    out.update(verdict="EVIDENCE OK" if bad == 0 else "NOT_OK", counts=counts, issues=issues[:80], stats=stats,
               first_divergence=first_div[:40])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--phase", default="service", choices=("gateP", "fixed", "service"))
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    res = check(a.dir, phase=a.phase, workers=a.workers)
    Path(a.dir, f"checker_verdict_{a.phase}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    if a.phase == "gateP" and "support" in res:
        Path(a.dir, "gpu_support.json").write_text(json.dumps({**res["support"], "gate_verdict": res["verdict"]}, indent=1),
                                                   encoding="utf-8")
    print(res["verdict"], {k: v for k, v in res["counts"].items() if v[1]}, res["issues"][:6], res.get("stats"),
          res.get("support", {}).get("GPU_SUPPORTED_P"))
    sys.exit(0 if res["verdict"] == "EVIDENCE OK" else 1)


if __name__ == "__main__":
    main()
