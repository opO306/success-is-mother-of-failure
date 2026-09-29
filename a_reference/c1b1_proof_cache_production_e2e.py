"""Proof Cache V0 -- ONE end-to-end admission at the real production cap 16384 (survey_only evidence, not in the suite).

Designer instruction 2026-09-30: use the existing synthetic near-tie 2^-17000 STOP (sign +1, one case only). The executor's
real MAX_PRECISION_BITS = 16384 is never touched (no precision_cap). Three runs of the SAME step from the SAME initial state:

  X1  production shelf (new temporary directory), empty: plain executor raises ReferenceUndecided; PC.step: STOP, prover
      FOUND, wrapper bytes re-verification, step advances, new_certificates, production admission -> object / index / admit event
  X2  same shelf, fresh identical run: cache source, 0 prover calls, the V2 checker called again, same raw, same state
  Y   cache OFF (RW.step without a cache): the reference for raw and state

Prover and checker calls are counted in-process. Everything is recorded (times, counts, admission metadata, shelf files);
the verdict is the list of assertions at the end, and a failed assertion is reported, not hidden.
"""
import concurrent.futures as cf
import hashlib
import json
import shutil
import sys
import tempfile
import time
from fractions import Fraction as Q
from pathlib import Path

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_exact_impulse_crosscheck as XC
import a_reference.c1b1_point_prover as P
import a_reference.c1b1_proof_cache as PC
import a_reference.c1b1_runtime_wrapper as RW

SIGN = 1


def _setup():
    sys.set_int_max_str_digits(0)                                       # the synthetic dt_kick has ~5,300 digits
    import a_reference.c1b1_runtime_local_witness as W
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    dr0 = XC._dr(4.4, (0.6, 0.6, 0.5))
    _, dr, dt_kick, expected = XC.near_tie_item(dr0, 0, 17000, SIGN, dps=5700, dt_bits=17600)
    z = (Q(0),) * 3
    p = (Q(3), Q(-1), Q(2))

    def mk():
        return C.new_run(X.POS, 2 * dt_kick, z, tuple(-x for x in p), tuple(Q(v, 1 << 48) for v in dr), p,
                         momentum_profile=X.MOM, validated_only=False)
    return W, C, mk, expected


def _counters():
    n = {"prove": 0, "check": 0}
    real_prove, real_check = P.prove, K2.check_certificate

    def prove(*a, **k):
        n["prove"] += 1
        return real_prove(*a, **k)

    def check(*a, **k):
        n["check"] += 1
        return real_check(*a, **k)
    P.prove, K2.check_certificate = prove, check
    return n


def _state(W, run):
    return json.dumps(W._raw(run), default=str)


def _cfg():
    return RW.Config(limits=K2.Limits(digits_max=10 ** 5, bits_max=10 ** 8, seconds_max=3000))


def _record(o, n, seconds, W, run):
    return {"status": o.status, "reason": o.reason, "seconds": round(seconds, 1), "stops": len(o.stops),
            "prover_calls": n["prove"], "checker_calls": n["check"],
            "new_certificates": len(o.new_certificates),
            "witnesses": [{"source": w["source"], "raw": w["raw"], "component": w["key"][1],
                           "certificate_sha256": w["certificate_sha256"], "certificate_bytes": w["certificate_bytes"]}
                          for w in o.witnesses],
            "t_steps": run.t_steps, "state_sha256": hashlib.sha256(_state(W, run).encode()).hexdigest()}


def with_cache(shelf_dir):
    """X1 then X2 on one production shelf."""
    W, C, mk, expected = _setup()
    out = {"expected_raw": str(expected)}
    t0 = time.time()
    try:
        C.step(mk())
        out["plain_executor"] = "decided (unexpected)"
    except C.ReferenceUndecided:
        out["plain_executor"] = "ReferenceUndecided at cap %d (%.1fs)" % (C.MAX_PRECISION_BITS, time.time() - t0)
    out["cap_at_start"] = C.MAX_PRECISION_BITS
    n = _counters()
    cache = PC.ProofCache(shelf_dir, PC.PRODUCTION, run_id="e2e-x1")
    run = mk()
    t0 = time.time()
    o = PC.step(run, cache, _cfg())
    out["X1"] = _record(o, n, time.time() - t0, W, run)
    out["shelf_after_X1"] = {"index": len(cache.index.records), "events": [e["event"] for e in cache.events.records]}
    n["prove"] = n["check"] = 0
    cache = PC.ProofCache(shelf_dir, PC.PRODUCTION, run_id="e2e-x2")    # reopened from disk
    run = mk()
    t0 = time.time()
    o = PC.step(run, cache, _cfg())
    out["X2"] = _record(o, n, time.time() - t0, W, run)
    out["X2"]["use_events"] = [{k: e[k] for k in ("index_seq", "result", "reason")}
                               for e in cache.events.records if e["event"] == "use"]
    out["cap_at_end"] = C.MAX_PRECISION_BITS
    return out


def cache_off():
    """Y: the reference, no cache."""
    W, C, mk, expected = _setup()
    n = _counters()
    run = mk()
    t0 = time.time()
    o = RW.step(run, _cfg())
    out = _record(o, n, time.time() - t0, W, run)
    out["cap"] = C.MAX_PRECISION_BITS
    return out


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    shelf = Path(tempfile.mkdtemp(prefix="proof_cache_e2e_"))
    t0 = time.time()
    with cf.ProcessPoolExecutor(2) as pool:
        fx, fy = pool.submit(with_cache, shelf), pool.submit(cache_off)
        x, y = fx.result(), fy.result()
    res = {"kind": "survey_only", "sign": SIGN, "wall_seconds": round(time.time() - t0, 1), "X": x, "Y_cache_off": y}
    admits = [json.loads(line) for line in (shelf / "events.jsonl").read_bytes().split(b"\n") if line]
    res["admission_events"] = [e for e in admits if e["event"] == "admit"]
    res["index"] = [json.loads(line) for line in (shelf / "index.jsonl").read_bytes().split(b"\n") if line]
    res["objects"] = {p.name: p.stat().st_size for p in (shelf / "objects").iterdir()}
    shutil.copytree(shelf, out / "shelf_copy", dirs_exist_ok=True)      # evidence copy; the temp shelf itself is discarded

    res["checks"] = checks = evaluate(res)
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"wall_seconds": res["wall_seconds"], "X1_seconds": res["X"]["X1"]["seconds"],
                      "X2_seconds": res["X"]["X2"]["seconds"], "off_seconds": res["Y_cache_off"]["seconds"],
                      "checks": checks}, indent=1), flush=True)
    return 0 if all(checks.values()) else 1


def evaluate(res):
    """The verdict: every condition of the designer's list, computed from the recorded values only."""
    x, y = res["X"], res["Y_cache_off"]
    X1, X2 = x["X1"], x["X2"]
    checks = {
        "executor_stops_at_cap_16384": x["plain_executor"].startswith("ReferenceUndecided at cap 16384"),
        "cap_untouched": x["cap_at_start"] == x["cap_at_end"] == y["cap"] == 16384,
        "X1_advanced_with_witnesses": X1["status"] == RW.WITNESS_RESOLVED and X1["stops"] >= 1
                                      and all(w["source"] == "prover" for w in X1["witnesses"]),
        "X1_new_certificates_and_prover": X1["new_certificates"] == len(X1["witnesses"]) >= 1 and X1["prover_calls"] >= 1,
        "X1_admitted_to_production_shelf": len(res["admission_events"]) == X1["new_certificates"] >= 1
                                           and len(res["index"]) == X1["new_certificates"]
                                           and len(res["objects"]) == len({w["certificate_sha256"] for w in X1["witnesses"]}),
        "admission_metadata": all(e["admission"]["kind"] == "production" and e["admission"]["cap_before"] == 16384
                                  and e["admission"]["cap_after"] == 16384 and e["admission"]["production_stop"] is True
                                  for e in res["admission_events"]),
        "X2_cache_source_only": X2["status"] == RW.WITNESS_RESOLVED and X2["witnesses"]
                                and all(w["source"] == "cache" for w in X2["witnesses"]),
        "X2_prover_zero": X2["prover_calls"] == 0,
        "X2_checker_called_again": X2["checker_calls"] >= len(X2["witnesses"]) >= 1,
        "X2_all_hits": [u["result"] for u in X2["use_events"]] == [PC.HIT] * len(X2["witnesses"]),
        "raw_equal_X1_X2_off": [w["raw"] for w in X1["witnesses"]] == [w["raw"] for w in X2["witnesses"]]
                               == [w["raw"] for w in y["witnesses"]],
        "raw_equals_mpmath_expected": bool(X1["witnesses"]) and all(int(w["raw"]) == int(x["expected_raw"])
                                                                   for w in X1["witnesses"]),   # both components: same exact impulse
        "state_bit_identical": X1["state_sha256"] == X2["state_sha256"] == y["state_sha256"],
        "off_did_not_use_cache": all(w["source"] == "prover" for w in y["witnesses"]),
    }
    return checks


if __name__ == "__main__":
    if sys.argv[1] == "--recheck":                      # re-evaluate a finished run from its recorded summary; runs nothing
        rec = json.loads(Path(sys.argv[2], "summary.json").read_text(encoding="utf-8"))
        chk = evaluate(rec)
        print(json.dumps(chk, indent=1))
        sys.exit(0 if all(chk.values()) else 1)
    sys.exit(main(sys.argv[1]))
