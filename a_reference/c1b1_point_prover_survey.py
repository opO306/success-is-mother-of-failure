"""Point prover V0 survey (survey_only): the three validation stages of the design, with evidence for runs/.

Stage 1  campaign: a moderate deterministic sample (inner, axes, outer, far, 65 multi-output points, hard-case candidates,
         shell 24-26 candidates, near-tie 2^-10..2^-140 above/below). The prover gets NO raw: it finds it. Pass:
         FOUND, checker VALID, raw == the unchanged executor's raw (and the constructed raw for near-tie).
Stage 2  cap-128 rehearsal on the three whole trajectories of the witness prototype (1,640 / 5,775 / 21,056 steps): every
         impulse component the executor refused at cap 128 is settled by the prover; raw == the full-cap executor's raw.
Stage 3  2^-17000: the synthetic input on which the real executor stops at cap 16384. Both sides. Default checker limits
         give EXHAUSTED (the synthetic dt_kick has ~5,300 digits); with digits/size limits raised the prover must reach
         FOUND with raw == the mpmath-constructed raw.

No large random campaign: the same state space repeated adds no information (designer, 2026-09-29).
"""
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_exact_impulse_crosscheck as XC
import a_reference.c1b1_point_prover as P


def _row(family, dr, k, dt, r, executor_raw=None, expected=None, seconds=0.0, limits=None):
    return {"family": family, "dr_raw": [str(v) for v in dr], "component": k, "status": r.status, "reason": r.reason,
            "raw": None if r.raw is None else str(r.raw), "executor_raw": None if executor_raw is None else str(executor_raw),
            "expected_raw": None if expected is None else str(expected),
            "agree": bool(r.found and (executor_raw is None or r.raw == executor_raw)
                          and (expected is None or r.raw == expected) and P.verify_found(r, limits)),   # same limits as the run
            "attempts": [(a["sqrt_bits"], a["verdict"]) for a in r.attempts], "seconds": round(seconds, 3),
            "dist_bits": None if r.estimate is None else r.estimate["dist_bits"]}


def _stage1_job(job):
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    kind, payload = job
    if kind == "near":
        dr, k, e, sign = payload
        family, dr, dt, expected = XC.near_tie_item(dr, k, e, sign)
        comps = [k]
    else:
        family, dr = payload
        dt, expected, comps = XC.DT_KICK, None, [k for k in range(3) if dr[k] != 0]
    exe = C.impulse(tuple(Fraction(v, 1 << 48) for v in dr), dt, X.MOM)
    rows = []
    for k in comps:
        t0 = time.time()
        r = P.prove(dr, k, dt)
        rows.append(_row(family, dr, k, dt, r, exe[k], expected, time.time() - t0))
    return rows


def stage1(workers, sizes):
    import concurrent.futures as cf
    hard = XC.family_hard(18)[::max(1, 109 // sizes["hard"] or 1)] + XC.family_hard(17)[::max(1, 827 // sizes["hard"])] \
        + XC.family_hard(16)[::max(1, 6581 // sizes["hard"])]
    jobs = [("one", it) for it in (XC.family_inner(sizes["inner"]) + XC.family_axes(sizes["axes"])
                                    + XC.family_outer(sizes["outer"]) + XC.family_multi65() + hard
                                    + XC.family_shell24_26())]
    jobs += [("near", sp) for sp in XC.near_tie_specs()]
    rows = []
    with cf.ProcessPoolExecutor(workers) as pool:
        for part in pool.map(_stage1_job, jobs, chunksize=8):
            rows.extend(part)
    return rows


def _refused_components(e, bf, steps):
    import a_reference.c1b1_runtime_local_witness as W
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    st = X.canonical(e, bf * X.RE)
    run = C.new_run(X.POS, X.DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=X.MOM)
    _, witnesses, refusals = W.run_with_local_witnesses(run, steps)
    out = []
    for w in witnesses:
        dr = [int(Fraction(x) * (1 << 48)) for x in w["input"]["dr"]]
        for comp in w["components"]:
            if not comp.get("zero_input"):
                out.append((dr, comp["axis"], comp["raw"], comp["bits"] > 128))
    return out, len(refusals)


def _stage2_job(case):
    e, bf, steps = case
    comps, refusals = _refused_components(e, bf, steps)
    rows = []
    for dr, k, raw, above in comps:
        t0 = time.time()
        r = P.prove(dr, k, Fraction(20))
        row = _row(f"rehearsal_e{e}_b{bf}", dr, k, Fraction(20), r, raw, None, time.time() - t0)
        row["above_exec_cap_128"] = above
        rows.append(row)
    return {"case": [str(e), str(bf), steps], "refusals": refusals, "rows": rows}


def stage2(workers):
    import concurrent.futures as cf
    cases = ((Fraction(9), Fraction(1, 2), 1640), (Fraction(1, 2), Fraction(1, 2), 5775),
             (Fraction(1, 10), Fraction(2), 21056))
    with cf.ProcessPoolExecutor(min(workers, 3)) as pool:
        return list(pool.map(_stage2_job, cases))


def _stage3_job(sign):
    sys.set_int_max_str_digits(0)
    dr = XC._dr(4.4, (0.6, 0.6, 0.5))
    _, dr_, dt, expected = XC.near_tie_item(dr, 0, 17000, sign, dps=5700, dt_bits=17600)
    out = {"sign": sign}
    t0 = time.time()
    r0 = P.prove(dr_, 0, dt, limits=None)                              # default checker limits
    out["default_limits"] = {"status": r0.status, "reason": r0.reason, "seconds": round(time.time() - t0, 1)}
    lim = K2.Limits(digits_max=10 ** 5, bits_max=10 ** 8, seconds_max=3000)
    t0 = time.time()
    r = P.prove(dr_, 0, dt, limits=lim)
    row = _row("2^-17000", dr_, 0, dt, r, None, expected, time.time() - t0, limits=lim)
    row["attempts_seconds"] = [round(a["seconds"], 1) for a in r.attempts]
    out["raised_limits"] = row
    return out


def stage3(workers):
    import concurrent.futures as cf
    with cf.ProcessPoolExecutor(min(workers, 2)) as pool:
        return list(pool.map(_stage3_job, (1, -1)))


def summarize(rows):
    by_status, by_family, first_try, secs, maxN, bad = {}, {}, 0, 0.0, 0, []
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        f = by_family.setdefault(r["family"], [0, 0])
        f[0] += 1
        f[1] += r["agree"]
        if r["agree"] and len(r["attempts"]) == 1:
            first_try += 1
        secs += r["seconds"]
        if r["attempts"]:
            maxN = max(maxN, max(a[0] for a in r["attempts"]))
        if not r["agree"]:
            bad.append(r)
    n = len(rows)
    return {"decisions": n, "agree": sum(v[1] for v in by_family.values()), "by_status": by_status,
            "first_attempt_valid": first_try, "cpu_seconds": round(secs, 1), "max_sqrt_bits": maxN,
            "by_family": {k: {"decisions": v[0], "agree": v[1]} for k, v in sorted(by_family.items())},
            "disagreements": bad}


def main(out_dir, workers, sizes=None):
    import os
    import platform
    sizes = sizes or {"inner": 300, "axes": 200, "outer": 300, "hard": 60}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows1 = stage1(workers, sizes)
    s1 = summarize(rows1)
    (out / "stage1_records.jsonl").write_text("\n".join(json.dumps(r) for r in rows1) + "\n", encoding="utf-8")
    print("stage1", {k: v for k, v in s1.items() if k not in ("by_family", "disagreements")}, flush=True)
    s2 = stage2(workers)
    for c in s2:
        c["summary"] = summarize(c["rows"])
        c["settled_above_cap128"] = sum(1 for r in c["rows"] if r["above_exec_cap_128"] and r["agree"])
        print("stage2", c["case"], "refusals", c["refusals"], {k: v for k, v in c["summary"].items() if k not in ("by_family", "disagreements")}, flush=True)
    (out / "stage2_rehearsal.json").write_text(json.dumps(s2), encoding="utf-8")
    s3 = stage3(workers)
    print("stage3", json.dumps(s3), flush=True)
    summary = {"stage1": s1, "stage2": [{"case": c["case"], "refusals": c["refusals"], "settled_above_cap128": c["settled_above_cap128"],
                                          "summary": {k: v for k, v in c["summary"].items() if k != "disagreements"},
                                          "disagreements": c["summary"]["disagreements"]} for c in s2],
               "stage3": s3, "sizes": sizes, "workers": workers, "wall_seconds": round(time.time() - t0, 1),
               "host": {"platform": platform.platform(), "cpus": os.cpu_count()}, "kind": "survey_only"}
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


if __name__ == "__main__":
    if sys.argv[1] == "--stage3":                    # python -m ... --stage3 OUT_DIR: only the 2^-17000 stage
        out3 = stage3(2)
        Path(sys.argv[2], "stage3_rerun.json").write_text(json.dumps(out3, indent=1), encoding="utf-8")
        print(json.dumps(out3))
        raise SystemExit(0)
    s = main(sys.argv[1], int(sys.argv[2]))
    print("stage1 disagreements:", len(s["stage1"]["disagreements"]),
          "stage2 disagreements:", sum(len(c["disagreements"]) for c in s["stage2"]))
