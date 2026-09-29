"""V2 cross-check campaign (survey_only): checker V2 on the same 10,191 inputs / 14,102 decisions as the V1 campaign.

Inputs are regenerated with the same deterministic generators (c1b1_exact_impulse_crosscheck). For every nonzero
component: the unchanged executor's raw, the V2 certificate found by the untrusted V2 search and decided by checker V2,
and the V1 raw recorded by the V1 campaign (runs/c1b1_exact_impulse_crosscheck_20260929/records.jsonl), joined by
(family, dr_raw, component). Pass: V2 VALID with raw == executor raw == V1 raw.
"""
import json
import time
from fractions import Fraction
from pathlib import Path

import a_reference.c1b1_exact_impulse_crosscheck as XC
import a_reference.c1b1_exact_impulse_search_v2 as S2

ROOT = Path(__file__).resolve().parents[1]
V1_RECORDS = ROOT / "runs" / "c1b1_exact_impulse_crosscheck_20260929" / "records.jsonl"


def _one(item):
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    kind, payload = item
    t0 = time.time()
    if kind == "near":
        dr, k, e, sign = payload
        family, dr, dt, expected = XC.near_tie_item(dr, k, e, sign)
        comps = [k]
    else:
        family, dr = payload
        dt, expected = XC.DT_KICK, None
        comps = [k for k in range(3) if dr[k] != 0]
    exe = C.impulse(tuple(Fraction(v, 1 << 48) for v in dr), dt, X.MOM)
    out = []
    for k in comps:
        cert, res = S2.find_certificate(dr, k, dt, exe[k], 128, 4096)
        out.append({"component": k, "executor_raw": str(exe[k]),
                    "expected_raw": None if expected is None else str(expected),
                    "status": res.status, "reason": res.reason, "v2_raw": None if res.raw is None else str(res.raw),
                    "sqrt_bits": cert["proof"]["sqrt_bits"], "work_bits": cert["proof"]["work_bits"],
                    "seconds": res.stats["seconds"], "max_bits": res.stats["max_bits"],
                    "max_mantissa_bits": res.stats["max_mantissa_bits"]})
    return {"family": family, "dr_raw": [str(v) for v in dr], "components": out, "seconds": round(time.time() - t0, 3)}


def jobs():
    j = [("one", it) for it in (XC.family_inner(1000) + XC.family_axes(700) + XC.family_outer(700)
                                + XC.family_multi65() + XC.family_hard(18) + XC.family_hard(17) + XC.family_hard(16)
                                + XC.family_shell24_26())]
    return j + [("near", sp) for sp in XC.near_tie_specs()]


def _key(record, comp):
    return record["family"], tuple(record["dr_raw"]), comp["component"], comp.get("expected_raw")


def _v1_index():
    idx = {}
    for line in open(V1_RECORDS, encoding="utf-8"):
        r = json.loads(line)
        for c in r["components"]:
            if "status" in c:
                # expected_raw is part of the key: a near-tie dr is used twice (above / below the boundary, two dt)
                idx[_key(r, c)] = (c["status"], c["checker_raw"])
    return idx


def campaign(out_dir, workers):
    import concurrent.futures as cf
    import os
    import platform
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    js = jobs()
    t0, records = time.time(), []
    with open(out / "records.jsonl", "w", encoding="utf-8") as fh, cf.ProcessPoolExecutor(workers) as pool:
        for i, rec in enumerate(pool.map(_one, js, chunksize=16)):
            records.append(rec)
            fh.write(json.dumps(rec) + chr(10))
            if i % 1000 == 0:
                fh.flush()
                print(f"{i}/{len(js)} {time.time() - t0:.0f}s", flush=True)
    summary = summarize(records, workers, time.time() - t0)
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def summarize(records, workers=None, wall=None):
    import os
    import platform
    v1 = _v1_index()
    tot = agree_exe = agree_v1 = missing_v1 = 0
    by_status, bad, bits = {}, [], {}
    max_mant = max_bits = 0
    for r in records:
        for c in r["components"]:
            tot += 1
            by_status[c["status"]] = by_status.get(c["status"], 0) + 1
            ok_exe = c["status"] == "VALID" and c["v2_raw"] == c["executor_raw"] and (
                c["expected_raw"] is None or c["expected_raw"] == c["v2_raw"])
            agree_exe += ok_exe
            key = _key(r, c)
            if key in v1:
                agree_v1 += v1[key] == ("VALID", c["v2_raw"])
            else:
                missing_v1 += 1
            if not ok_exe or (key in v1 and v1[key] != ("VALID", c["v2_raw"])):
                bad.append({"family": r["family"], "dr_raw": r["dr_raw"], **c, "v1": v1.get(key)})
            bits[c["sqrt_bits"]] = bits.get(c["sqrt_bits"], 0) + 1
            max_mant = max(max_mant, c["max_mantissa_bits"])
            max_bits = max(max_bits, c["max_bits"])
    fam_seconds = {}
    for r in records:
        fam_seconds[r["family"]] = fam_seconds.get(r["family"], 0.0) + r["seconds"]
    summary = {"decisions": tot, "v2_valid_equal_executor": agree_exe, "v2_equal_v1": agree_v1,
               "v1_record_missing": missing_v1, "by_status": by_status, "disagreements": bad,
               "sqrt_bits_histogram": bits, "max_mantissa_bits": max_mant, "max_bits": max_bits,
               "items": len(records), "wall_seconds": None if wall is None else round(wall, 1), "workers": workers,
               "cpu_seconds_by_family": {k: round(v, 1) for k, v in sorted(fam_seconds.items())},
               "host": {"platform": platform.platform(), "cpus": os.cpu_count()}, "kind": "survey_only"}
    return summary


if __name__ == "__main__":
    import sys
    s = campaign(sys.argv[1], int(sys.argv[2]))
    print(json.dumps({k: v for k, v in s.items() if k != "disagreements"}, indent=1))
    print("disagreements:", len(s["disagreements"]))
