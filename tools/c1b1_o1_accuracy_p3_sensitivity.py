"""O-1 accuracy requirement plan V0, step P3: observable sensitivity to scattering-angle error.

survey_only. Computes properties of the Lang PES and of the viscosity observable only:
  Q2(E)   = 2 pi int sin^2(chi) b db            (finite R = 20 bohr chi, b in [0, 2 Re], orbit band excluded)
  A(E)    = 2 pi int |sin 2chi| b db / Q2(E)     (first-order bound: dQ2/Q2 <= A * max|dchi| outside the band)
  B(E)    = 2 pi b_orb^2 / Q2(E)                 (near-orbit band bound scale, E < E_max only)
  energy-weight fractions of the Omega(2,2) kernel x^3 e^-x Q2 below E_max and above 10 De.
No integrator (KDK/Yoshida) is run and no dt error is used here; combining with dt errors is step P5.
chi comes from the independent continuous reference c1b1_o1.continuous.scatter (radial quadrature).
Run on the laptop (not on the main desktop):  python tools/c1b1_o1_accuracy_p3_sensitivity.py PES_F90 OUT_JSON [WORKERS]
"""
import json
import math
import sys
import time
from fractions import Fraction
from multiprocessing import Pool
from pathlib import Path

import mpmath as mm

from c1b1_o1 import continuous, model

DPS = 25
R0 = 20
RE = Fraction(71129, 10000)
B_MAX = 2 * RE
E_MAX_ORBIT = 0.9964                     # De, barrier-top orbiting limit (design record section 21 correction)
BAND = 0.01                              # |b/b_orb - 1| < BAND is excluded and bounded separately
KB_EH_PER_K = 3.1668115634564e-6         # CODATA 2022 k_B in hartree/K (as in the C1-C proposal)
# b_orb from a_reference/fixtures/c1b1_orbit_boundary_v3.json (static copy of the stored fractions' values)
B_ORB = {"3/20": 14.10268503458191, "1/5": 13.490729538770605, "3/10": 12.676953857162475,
         "1/2": 11.71900517505586, "7/10": 11.114871303100044, "9/10": 10.662936100857106,
         "99/100": 10.48346620743928}
SUPER = ["1", "2", "5", "10"]
SURVEY_ONLY = ["20", "33", "45"]         # above the production 10 De range: observable sensitivity only

_V = None


def _init(path):
    global _V
    mm.mp.dps = DPS
    _V = model.Potential(params=model.parse(Path(path)))


def chi_at(args):
    e, b = args
    with mm.workdps(DPS):
        mu = mm.mpf(Fraction(model.MASS).numerator) / Fraction(model.MASS).denominator / 2
        E = mm.mpf(e.numerator) / e.denominator * mm.mpf(model.DE)
        L = mm.mpf(b.numerator) / b.denominator * mm.sqrt(2 * mu * E)
        pt = L / R0
        pr2 = 2 * mu * (E - _V(mm.mpf(R0))) - pt * pt
        if pr2 <= 0:
            return dict(e=str(e), b=float(b), status="no_inbound")
        q, p = [R0, 0], [-mm.sqrt(pr2), pt]
        try:
            r = continuous.scatter(_V, mu, q, p, mm.mpf(R0), DPS)
        except continuous.Unresolved as exc:
            return dict(e=str(e), b=float(b), status="unresolved", reason=str(exc))
        return dict(e=str(e), b=float(b), status="ok", chi=float(mm.mpf(r["chi"])), r_min=float(mm.mpf(r["r_min"])))


def b_grid(e_key):
    pts = {Fraction(i, 10) for i in range(0, int(B_MAX * 10) + 1)} | {B_MAX}
    if e_key in B_ORB:
        bo = Fraction(B_ORB[e_key]).limit_denominator(10 ** 12)
        for k in range(0, 14):
            rho = Fraction(10 ** (-2 + k / 10)).limit_denominator(10 ** 12)   # 1e-2 ... ~2e-1, geometric
            for s in (-1, 1):
                b = bo * (1 + s * rho)
                if 0 <= b <= B_MAX:
                    pts.add(b)
        pts = {b for b in pts if abs(float(b) / B_ORB[e_key] - 1) >= BAND}
    return sorted(pts)


def trapz(xs, ys):
    return sum((xs[i + 1] - xs[i]) * (ys[i] + ys[i + 1]) / 2 for i in range(len(xs) - 1))


def integrals(points, b_orb=None):
    """Trapezoid over contiguous segments; the excluded band splits the b range into two segments."""
    pts = sorted(points)
    if b_orb is None:
        segs = [pts]
    else:
        segs = [[p for p in pts if p[0] < b_orb], [p for p in pts if p[0] > b_orb]]
    q2 = s2 = 0.0
    for seg in segs:
        if len(seg) < 2:
            continue
        bs = [p[0] for p in seg]
        q2 += trapz(bs, [math.sin(p[1]) ** 2 * p[0] for p in seg])
        s2 += trapz(bs, [abs(math.sin(2 * p[1])) * p[0] for p in seg])
    return 2 * math.pi * q2, 2 * math.pi * s2


def self_test():
    """Hard sphere chi = 2 acos(b/d): Q2 = (2/3) pi d^2 exactly. Detects wrong weights/limits."""
    d = 7.0
    bs = [i * 0.1 for i in range(0, 143)]
    pts = [(b, 2 * math.acos(b / d) if b < d else 0.0) for b in bs]
    q2, _ = integrals(pts)
    exact = 2 * math.pi * d * d / 3
    rel = abs(q2 - exact) / exact
    if rel > 2e-3:
        raise SystemExit(f"self-test failed: hard-sphere Q2 rel error {rel:.3e}")
    return rel


def weights(table, T):
    kT = KB_EH_PER_K * T / 0.000451995775          # in De
    es = sorted(table)
    def q2(e):
        if e <= es[0]: return table[es[0]]
        if e >= es[-1]: return table[es[-1]]
        for a, c in zip(es, es[1:]):
            if a <= e <= c:
                t = (math.log(e) - math.log(a)) / (math.log(c) - math.log(a))
                return table[a] * (1 - t) + table[c] * t
    n = 20000
    xs = [i * 40.0 / n for i in range(1, n + 1)]
    w = [x ** 3 * math.exp(-x) * q2(x * kT) for x in xs]
    tot = sum(w)
    below = sum(wi for x, wi in zip(xs, w) if x * kT < E_MAX_ORBIT)
    above = sum(wi for x, wi in zip(xs, w) if x * kT > 10)
    return dict(T=T, kT_over_De=kT, frac_below_Emax=below / tot, frac_above_10De=above / tot)


def main():
    pes, out = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    st = self_test()
    keys = list(B_ORB) + SUPER + SURVEY_ONLY
    jobs = [(Fraction(k), b) for k in keys for b in b_grid(k)]
    t0, c0 = time.perf_counter(), time.process_time()
    print(f"self-test hard-sphere rel {st:.2e}; {len(jobs)} chi evaluations, {workers} workers", flush=True)
    with Pool(workers, initializer=_init, initargs=(pes,)) as pool:
        rows = []
        for i, r in enumerate(pool.imap(chi_at, jobs, chunksize=4)):
            rows.append(r)
            if i % 200 == 0:
                print(f"{i}/{len(jobs)} {time.perf_counter() - t0:.0f}s", flush=True)
    per = {}
    for k in keys:
        pts = [(r["b"], r["chi"]) for r in rows if r["e"] == str(Fraction(k)) and r["status"] == "ok"]
        bad = [r for r in rows if r["e"] == str(Fraction(k)) and r["status"] != "ok"]
        bo = B_ORB.get(k)
        q2, s2 = integrals(pts, bo)
        half = integrals(pts[::2], bo)[0] if len(pts) > 4 else float("nan")
        per[k] = dict(E_over_De=float(Fraction(k)), survey_only_above_10De=k in SURVEY_ONLY, b_orb=bo,
                      n_ok=len(pts), n_not_ok=len(bad), not_ok=bad[:5], Q2=q2, Q2_half_grid=half,
                      A=s2 / q2 if q2 else None, B=(2 * math.pi * bo * bo / q2) if (bo and q2) else None)
        print(k, json.dumps({x: per[k][x] for x in ("n_ok", "n_not_ok", "Q2", "Q2_half_grid", "A", "B")}), flush=True)
    table = {per[k]["E_over_De"]: per[k]["Q2"] for k in keys if per[k]["Q2"]}
    w = [weights(table, T) for T in (200, 300, 400)]
    for x in w:
        print(json.dumps(x), flush=True)
    res = dict(format="c1b1-o1-accuracy-p3-sensitivity-v0", status="survey_only", dps=DPS, R0=R0,
               b_max=float(B_MAX), band=BAND, self_test_rel=st, per_energy=per, weights=w, rows=rows,
               wall_s=time.perf_counter() - t0, parent_cpu_s=time.process_time() - c0,
               pes_sha256=__import__("hashlib").sha256(open(pes, "rb").read()).hexdigest())
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print("done", out, f"{res['wall_s']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
