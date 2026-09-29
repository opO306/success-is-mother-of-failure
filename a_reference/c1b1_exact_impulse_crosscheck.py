"""T3 cross-check driver (survey_only): the executor's RESOLVED raw vs the independent exact checker's VALID raw.

For each input the plain executor (C.impulse, unchanged, cap 16384) decides the three impulse components; for every
nonzero component a certificate is searched (c1b1_exact_impulse_search, untrusted) and decided by the independent
checker. The cross-check passes when the checker says VALID with exactly the executor's raw. A checker that says
INVALID / REFUSED is recorded, not hidden. This measures agreement of two implementations of the frozen formula; it is
not a proof of the formula transcription (see the fault-injection tests) and not an A-EV proof.

Inputs are deterministic (radical-inverse sequences, exact integers): no random numbers.
"""
import json
import math
import time
from fractions import Fraction
from pathlib import Path

import mpmath as mp

import a_reference.c1b1_exact_impulse_checker as K
import a_reference.c1b1_exact_impulse_search as S

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "a_reference" / "fixtures"
DT_KICK = Fraction(20)             # h/2 of the C1-B1 candidate (dt = 40)
R_MIN = 1.2 / 0.529177210903


def radical_inverse(i, base):
    x, f = 0.0, 1.0 / base
    while i:
        i, d = divmod(i, base)
        x += d * f
        f /= base
    return x


def _direction(i):
    v = [radical_inverse(i, b) - 0.5 for b in (2, 3, 5)]
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / n for c in v]


def _dr(R, d):
    return tuple(int(round(R * c * 2.0 ** 48)) for c in d)


def _log_R(i, n, lo, hi):
    return lo * (hi / lo) ** ((i + 0.5) / n)


def family_inner(n):
    """R in [r_min, 20] bohr, 3D directions (the region every D_valid trajectory passes through)."""
    return [("inner", _dr(_log_R(i, n, R_MIN * 1.0001, 20.0), _direction(i + 1))) for i in range(n)]


def family_axes(n):
    """Single-axis and two-axis positions, R from r_min to 10^4."""
    out = []
    for i in range(n):
        R = _log_R(i, n, R_MIN * 1.0001, 1.0e4)
        d = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (0, 1, 1), (1, 0, 1), (1, 1, 1)][i % 7]
        s = math.sqrt(sum(c * c for c in d))
        out.append(("axes", _dr(R, [c / s * (1 if (i // 7) % 2 == 0 else -1) for c in d])))
    return out


def family_outer(n):
    """R in [20, 10240] (shells 0..26) with 3D directions, plus a few far points up to 2^40 bohr."""
    out = [("outer", _dr(_log_R(i, n, 20.0, 10240.0), _direction(i + 101))) for i in range(n)]
    out += [("far", _dr(2.0 ** e, _direction(200 + e))) for e in range(15, 41, 5)]
    return out


def family_multi65():
    d = json.load(open(FIX / "c1b1_rounding_regions_v1.json", encoding="utf-8"))
    return [("multi65", tuple(p)) for p in d["finite_acceptance"]["domain"]["points"]]


def family_hard(shell):
    """The hard-case candidate points found by the shell searches (16, 17, 18): exact-boundary neighbours."""
    name = {18: "c1b1_hard_case_certificate_v1.json", 17: "c1b1_hard_case_certificate_shell17_v1.json",
            16: "c1b1_hard_case_certificate_shell16_v1.json"}[shell]
    d = json.load(open(FIX / name, encoding="utf-8"))
    pts = []
    for sb in d["certificate"]["superblocks"]:
        for lo, hi in sb["candidate_intervals"]:
            pts.extend(range(lo, hi + 1))
    return [(f"hard{shell}", (n, 0, 0)) for n in pts]


def family_shell24_26():
    d = json.load(open(FIX / "c1b1_half_ulp_boundaries_v1.json", encoding="utf-8"))
    out = []
    for g in d["groups"]:
        for rec in g["certificate"].get("records", []):
            for n in rec.get("candidate_integers", []):
                out.append((f"shell{g['shell_index']}", (n, 0, 0)))
    return out


def run_one(item, start_bits=128, max_bits=4096, limits=None):
    """One input: executor raws vs checker verdicts. Imports the executor here (worker processes)."""
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    family, dr = item
    t0 = time.time()
    exe = C.impulse(tuple(Fraction(v, 1 << 48) for v in dr), DT_KICK, X.MOM)
    comps = []
    for k in range(3):
        if dr[k] == 0:
            comps.append({"component": k, "skipped": "dr_k = 0 (executor returns exact 0 without deciding)",
                          "executor_raw": str(exe[k])})
            continue
        cert, res = S.find_certificate(dr, k, DT_KICK, exe[k], start_bits, max_bits, limits)
        comps.append({"component": k, "executor_raw": str(exe[k]), "status": res.status, "reason": res.reason,
                      "checker_raw": None if res.raw is None else str(res.raw),
                      "agree": bool(res.valid and res.raw == exe[k]),
                      "sqrt_bits": cert["proof"]["sqrt_bits"], "max_bits": res.stats["max_bits"],
                      "seconds": res.stats["seconds"]})
    return {"family": family, "dr_raw": [str(v) for v in dr], "components": comps, "seconds": round(time.time() - t0, 3)}


def summarize(records):
    tot = agree = 0
    by_status, by_family, bad = {}, {}, []
    for r in records:
        for c in r["components"]:
            if "status" not in c:
                continue
            tot += 1
            by_status[c["status"]] = by_status.get(c["status"], 0) + 1
            f = by_family.setdefault(r["family"], [0, 0])
            f[0] += 1
            if c["agree"]:
                agree += 1
                f[1] += 1
            else:
                bad.append({"family": r["family"], "dr_raw": r["dr_raw"], **c})
    return {"decisions": tot, "agree": agree, "by_status": by_status,
            "by_family": {k: {"decisions": v[0], "agree": v[1]} for k, v in sorted(by_family.items())},
            "disagreements": bad}


# --- a third, high-precision reference (mpmath) -------------------------------------------------------------------
# Used only to BUILD test inputs (near-tie constructions) and to sanity-check the executor and the checker. It reads
# the constant tables of the checker (which the fingerprint test ties to the frozen source), and evaluates the same
# published formula independently with mpmath floats. Not part of any proof.

def reference_dv(R2, dps=160):
    """dV/dR (retardation ON) at R = sqrt(R2), R2 an exact Fraction, as an mpmath number."""
    with mp.workdps(dps):
        R = mp.sqrt(mp.mpf(R2.numerator) / R2.denominator)
        F = lambda t: mp.mpf(Fraction(t).numerator) / Fraction(t).denominator
        Nr = 1 + sum(F(a) * R ** (m + 1) for m, a in enumerate(K.RET_A))
        Dn = 1 + sum(F(b) * R ** (m + 1) for m, b in enumerate(K.RET_B))
        dNr = sum(F(a) * (m + 1) * R ** m for m, a in enumerate(K.RET_A))
        dDn = sum(F(b) * (m + 1) * R ** m for m, b in enumerate(K.RET_B))
        g, dg = Nr / Dn, (dNr * Dn - Nr * dDn) / (Dn * Dn)
        total = mp.mpf(0)
        for name in ("BO", "REL", "QED"):
            for alpha, coefs in K.SHORT[name]:
                al = F(alpha)
                P = sum(F(c) * R ** i for i, c in coefs.items())
                dP = sum(F(c) * i * R ** (i - 1) for i, c in coefs.items() if i)
                total += mp.exp(-al * R) * (dP - al * P)
            eta, kadd, cs = K.LONG[name]
            eta = F(eta)
            x, ex = eta * R, mp.exp(-eta * R)
            kmin = min(cs)
            for k, c in cs.items():
                n = 2 * k + kadd
                partial = sum(x ** i / mp.factorial(i) for i in range(n + 1))
                T = ex * partial
                base = eta * ex * x ** n / mp.factorial(n)
                if name == "BO" and k == kmin:
                    D, dD = g - T, base + dg
                elif name == "REL" and k == kmin:
                    D, dD = -T, base
                else:
                    D, dD = 1 - T, base
                total += -F(c) * (dD * R ** (-2 * k) - 2 * k * D * R ** (-2 * k - 1))
        return total


def reference_J_unit(dr, k, dps=160):
    """J_k for dt_kick = 1: -dV/dR * dr_k / R (positions in bohr). J for a kick interval dt is dt times this."""
    R2 = Fraction(sum(v * v for v in dr), 1 << 96)
    with mp.workdps(dps):
        R = mp.sqrt(mp.mpf(R2.numerator) / R2.denominator)
        return -reference_dv(R2, dps) * (mp.mpf(dr[k]) / 2 ** 48) / R


def near_tie_item(dr, k, e_bits, sign, dps=200, dt_bits=400):
    """An input whose exact impulse is 2^-e_bits ulps above (sign>0) / below (sign<0) a half-ulp boundary.

    dt_kick is chosen (a rational with dt_bits fractional bits) so that J = boundary + sign * 2^-e_bits ulp. The
    quantization of dt shifts J by about 2^(70 - dt_bits) ulp, so dt_bits must exceed e_bits by a margin (default 400:
    good for e_bits up to about 300). The expected raw is m+1 (above) or m (below), m the cell below the boundary.
    Returns (family, dr, dt_kick, expected_raw)."""
    with mp.workdps(dps):
        Ju = reference_J_unit(dr, k, dps)
        ulp = mp.mpf(2) ** -80
        m = int(mp.floor(Ju * 20 / ulp))
        target = (m + mp.mpf(1) / 2) * ulp + sign * ulp * mp.mpf(2) ** -e_bits
        dt = target / Ju
        dt_q = Fraction(int(mp.floor(dt * mp.mpf(2) ** dt_bits)), 1 << dt_bits)
    return f"near_tie_2^-{e_bits}", tuple(dr), dt_q, m + 1 if sign > 0 else m


def run_near_tie(spec, start_bits=128, max_bits=2048):
    """spec = (dr, k, e_bits, sign). Executor and checker on an input 2^-e ulps from a half-ulp boundary."""
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    dr, k, e, sign = spec
    t0 = time.time()
    _, dr, dt, expected = near_tie_item(dr, k, e, sign)
    exe = C.impulse(tuple(Fraction(v, 1 << 48) for v in dr), dt, X.MOM)[k]
    cert, res = S.find_certificate(dr, k, dt, expected, start_bits, max_bits)
    return {"family": f"near_tie_2^-{e}", "dr_raw": [str(v) for v in dr], "components": [
        {"component": k, "executor_raw": str(exe), "expected_raw": str(expected), "status": res.status,
         "reason": res.reason, "checker_raw": None if res.raw is None else str(res.raw),
         "agree": bool(res.valid and res.raw == exe == expected), "sqrt_bits": cert["proof"]["sqrt_bits"],
         "max_bits": res.stats["max_bits"], "seconds": res.stats["seconds"]}],
        "seconds": round(time.time() - t0, 3)}


def near_tie_specs(n_points=20, e_ladder=(10, 30, 60, 100, 140)):
    specs = []
    for i in range(n_points):
        R = _log_R(i, n_points, R_MIN * 1.001, 3000.0)
        dr = _dr(R, _direction(i + 7))
        k = max(range(3), key=lambda j: abs(dr[j]))
        for e in e_ladder:
            for sign in (1, -1):
                specs.append((dr, k, e, sign))
    return specs


def _work(job):
    kind, payload = job
    return run_near_tie(payload) if kind == "near" else run_one(payload)


def campaign(out_dir, workers, sizes=None):
    """Run all families; write records.jsonl and summary.json into out_dir. survey_only evidence."""
    import concurrent.futures as cf
    import os
    import platform
    sizes = sizes or {"inner": 1000, "axes": 700, "outer": 700}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [("one", it) for it in (family_inner(sizes["inner"]) + family_axes(sizes["axes"])
                                    + family_outer(sizes["outer"]) + family_multi65()
                                    + family_hard(18) + family_hard(17) + family_hard(16) + family_shell24_26())]
    jobs += [("near", sp) for sp in near_tie_specs()]
    t0, records = time.time(), []
    with open(out / "records.jsonl", "w", encoding="utf-8") as fh, cf.ProcessPoolExecutor(workers) as pool:
        for i, rec in enumerate(pool.map(_work, jobs, chunksize=8)):
            records.append(rec)
            fh.write(json.dumps(rec) + chr(10))
            if i % 200 == 0:
                fh.flush()
                print(f"{i}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    summary = summarize(records)
    bits = {}
    for r in records:
        for c in r["components"]:
            if "sqrt_bits" in c:
                bits[c["sqrt_bits"]] = bits.get(c["sqrt_bits"], 0) + 1
    fam_seconds = {}
    for r in records:
        fam_seconds[r["family"]] = fam_seconds.get(r["family"], 0.0) + r["seconds"]
    summary.update({"items": len(records), "wall_seconds": round(time.time() - t0, 1), "workers": workers,
                    "sqrt_bits_histogram": bits, "max_number_bits": max(
                        (c.get("max_bits", 0) for r in records for c in r["components"]), default=0),
                    "cpu_seconds_by_family": {k: round(v, 1) for k, v in sorted(fam_seconds.items())},
                    "host": {"platform": platform.platform(), "cpus": os.cpu_count()},
                    "sizes": sizes, "kind": "survey_only"})
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import sys
    print(json.dumps({k: v for k, v in campaign(sys.argv[1], int(sys.argv[2])).items() if k != "disagreements"}, indent=1))
