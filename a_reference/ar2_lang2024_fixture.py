"""C1-A fixture and hard inputs for the Ar-Ar reference evaluator (designer 9th ed., items 2-3).

The fixture freezes, INSIDE Git, the reference's result bits at every chosen input so the core physics
regression runs without the published files on D:\\reference. It was generated once with those files present:
every stored bit pattern was re-judged by the independent audit (audit/independent_physics) before writing,
and the provenance (SHA-256 of the published files, of the audit code, the git commit) is stored with it.

Inputs (`build_cases`):
  * the 94-point grid of the C1-A tests;
  * hard inputs by region -- r_min and just above, the sign change of V, F ~ 0 at the minimum, the strongest
    cancellation, the onset of retardation, 20 A, 250 bohr and beyond, tiny V / F up to 10^4 bohr (and the
    B0 range end 2^20 bohr), the FX underflow-to-zero edge;
  * boundary-search inputs: R where the exact value lies unusually close to a binary64 or FX(64,32) rounding
    boundary, found by scanning 2^18 consecutive inputs with a degree-6 interpolant of high-precision values.

The search only PICKS inputs; nothing it computes is trusted -- the stored bits come from the reference and are
judged by the audit, and each case records how close it actually is (log2 of the distance, in units of the
result spacing, from the exact value to the nearest rounding boundary).

Run `python -m a_reference.ar2_lang2024_fixture` to regenerate (needs D:\\reference). Slow (minutes).
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import subprocess
from fractions import Fraction as Q
from pathlib import Path

import a_reference.ar2_lang2024 as L
from a_numeric import Binary64Finite, FixedPoint, VMHalt

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ar2_lang2024_c1a_v1.json"
DATA = Path(r"D:\reference\ar2_lang2024")
SOURCE_FILES = ("S2_ar2_pot.f90", "S1_abinitio.txt", "lang2024_v2.pdf")
FIXTURE_FORMAT = "c1a-ar2-fixture-v1"

B64 = Binary64Finite()
FX = FixedPoint(64, 32)
PROFILES = {"B64": B64, "FX64_32": FX}
# name -> (reference quantity, retardation)
QUANTITIES = {"V": ("V", True), "V_ret_off": ("V", False), "F": ("F", True), "F_ret_off": ("F", False),
              "sigma": ("sigma", True), "V+sigma": ("V+sigma", True), "V-sigma": ("V-sigma", True)}
SCAN_N = 1 << 20
SCAN_DEGREE = 6
B0_R_MAX = Q(1 << 20)          # the B0 executor's declared range end (a capability limit, not physics)


# --- raw inputs ------------------------------------------------------------------------------------

def bits(x: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def R_of(profile: str, raw: int) -> Q:
    return PROFILES[profile].to_exact(raw)


def raw_ceil(profile: str, R: Q) -> int:
    """The smallest input >= R."""
    if profile == "FX64_32":
        return -((-R.numerator << 32) // R.denominator)
    x = float(R)
    return bits(x) if Q(x) >= R else bits(math.nextafter(x, math.inf))


def raw_near(profile: str, R: Q) -> int:
    return PROFILES[profile].from_exact(R)


def raw_str(profile: str, raw: int) -> str:
    return f"{raw:016x}" if profile == "B64" else str(raw)


def raw_parse(profile: str, s: str) -> int:
    return int(s, 16) if profile == "B64" else int(s)


# --- the reference, as stored outcomes ------------------------------------------------------------

def outcome(profile: str, name: str, raw: int) -> dict:
    q, ret = QUANTITIES[name]
    try:
        v = L.evaluate(q, R_of(profile, raw), PROFILES[profile], ret)
    except L.PhysicsDomainExceeded as e:
        return {"domain": e.reason}
    except VMHalt as h:
        return {"halt": h.reason}
    return {"raw": raw_str(profile, v)}


def _enclosure(name: str, R: Q, M: int):
    q, ret = QUANTITIES[name]
    iv = L.enclose("dVdR" if q == "F" else q, R, M, ret)
    return (-iv.hi, -iv.lo) if q == "F" else (iv.lo, iv.hi)


def high(name: str, R: Q, M: int = 640) -> Q:
    a, b = _enclosure(name, R, M)
    return (a + b) / 2


def _boundaries(profile: str, raw_result: int):
    """(lower boundary, upper boundary, spacing) of the rounding interval of a result."""
    p = PROFILES[profile]
    if profile == "FX64_32":
        h = Q(1, 1 << 33)
        v = p.to_exact(raw_result)
        return v - h, v + h, 2 * h
    m = raw_result & ~(1 << 63)
    neg = raw_result >> 63
    here = p.to_exact(m)
    lo = Q(0) if m == 0 else (here + p.to_exact(m - 1)) / 2
    hi = (here + p.to_exact(m + 1)) / 2
    spacing = p.to_exact(m + 1) - here
    return (-hi, -lo, spacing) if neg else (lo, hi, spacing)


def boundary_distance_log2(profile: str, name: str, raw: int, M: int = 1024) -> float | None:
    """log2(distance from the exact value to the nearest rounding boundary / result spacing)."""
    o = outcome(profile, name, raw)
    if "raw" not in o:
        return None
    y = high(name, R_of(profile, raw), M)
    lo, hi, sp = _boundaries(profile, raw_parse(profile, o["raw"]))
    d = min(y - lo, hi - y) / sp
    return round(math.log2(d), 2) if d > 0 else float("-inf")


# --- search helpers (they only choose inputs) ------------------------------------------------------

def _sign(profile: str, name: str, raw: int) -> int:
    o = outcome(profile, name, raw)
    v = PROFILES[profile].to_exact(raw_parse(profile, o["raw"]))
    return (v > 0) - (v < 0)


def root_raw(profile: str, name: str, lo_R: Q, hi_R: Q, offset: Q = Q(0)) -> int:
    """The last input below the sign change of (quantity - offset) in [lo_R, hi_R] (monotone there)."""
    def s(raw):
        return (high(name, R_of(profile, raw), 256) - offset) > 0
    lo, hi = raw_ceil(profile, lo_R), raw_ceil(profile, hi_R)
    slo = s(lo)
    assert slo != s(hi), (name, float(lo_R), float(hi_R))
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if s(mid) == slo:
            lo = mid
        else:
            hi = mid
    return lo


def _cancellation(R: Q) -> float:
    """sum of |parts| / |V| (retardation on), parts = every exponential term and both halves of every
    damping factor -- how much the formula cancels at R."""
    import mpmath as mp
    mp.mp.dps = 40
    r = mp.mpf(R.numerator) / R.denominator
    total, parts = mp.mpf(0), mp.mpf(0)
    for name in ("BO", "REL", "QED"):
        short, (eta, C, kadd) = L.COMPONENTS[name]
        for alpha, coefs in short.values():
            e = mp.exp(-mp.mpf(alpha.numerator) / alpha.denominator * r)
            for i, c in coefs.items():
                t = e * mp.mpf(c.numerator) / c.denominator * r ** i
                total += t
                parts += abs(t)
        x = mp.mpf(eta.numerator) / eta.denominator * r
        kmin = min(C)
        for k, c in C.items():
            n = 2 * k + kadd
            tail = mp.exp(-x) * sum(x ** i / mp.factorial(i) for i in range(n + 1))
            cc = mp.mpf(c.numerator) / c.denominator / r ** (2 * k)
            if k == kmin and name == "BO":
                num = 1 + sum(mp.mpf(a.numerator) / a.denominator * r ** (m + 1) for m, a in enumerate(L.RET_A))
                den = 1 + sum(mp.mpf(b.numerator) / b.denominator * r ** (m + 1) for m, b in enumerate(L.RET_B))
                g = num / den
                total -= cc * (g - tail)
                parts += abs(cc) * (abs(g) + tail)
            elif k == kmin and name == "REL":
                total -= cc * (-tail)
                parts += abs(cc) * tail
            else:
                total -= cc * (1 - tail)
                parts += abs(cc) * (1 + tail)
    return float(parts / abs(total))


def _retardation_ratio(R: Q) -> Q:
    on, off = high("V", R, 256), high("V_ret_off", R, 256)
    return abs(on - off) / abs(on)


def _ratio_crossing(target: Q, lo: float, hi: float) -> Q:
    """R (bohr) where the retardation ratio crosses `target` (log-bisection; the ratio grows with R there)."""
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        if _retardation_ratio(Q(mid)) < target:
            lo = mid
        else:
            hi = mid
    return Q(lo)


def _forward_differences(ys, h):
    """Power-free forward differences of step 1 at k = 0 of the interpolant through (j h, ys[j])."""
    n = len(ys) - 1
    # Newton form on nodes 0, h, 2h, ...: divided differences
    dd = list(ys)
    coef = [dd[0]]
    for order in range(1, n + 1):
        dd = [(dd[i + 1] - dd[i]) / (order * h) for i in range(len(dd) - 1)]
        coef.append(dd[0])

    def p(k):
        out, basis = Q(0), Q(1)
        for order, c in enumerate(coef):
            out += c * basis
            basis *= (k - order * h)
        return out
    vals = [p(k) for k in range(n + 1)]
    diffs = []
    for order in range(n + 1):
        diffs.append(vals[0])
        vals = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    return diffs


def scan_hard(profile: str, name: str, R0: Q, keep: int = 2, N: int = SCAN_N) -> list[int]:
    """Inputs among N consecutive ones from R0 whose exact value lies closest to a rounding boundary."""
    raw0 = raw_ceil(profile, R0)
    h = N // SCAN_DEGREE
    ys = [high(name, R_of(profile, raw0 + j * h), 512) for j in range(SCAN_DEGREE + 1)]
    if profile == "B64":
        # the input spacing and the result spacing must be constant over the scan
        assert (raw0 >> 52) == ((raw0 + N) >> 52), "input binade changes inside the scan"
        exps = {math.frexp(float(y))[1] for y in ys}
        if len(exps) != 1:
            return []
        spacing = Q(2) ** (exps.pop() - 53)
    else:
        spacing = Q(1, 1 << 32)
    G = 200
    diffs = [int(d / spacing * (1 << G)) for d in _forward_differences(ys, h)]
    half, mask = 1 << (G - 1), (1 << G) - 1
    best = []
    s = diffs
    for k in range(N + 1):
        frac = s[0] & mask
        dist = abs(frac - half)            # distance of value / spacing to the nearest half-integer
        if len(best) < keep or dist < best[-1][0]:
            best.append((dist, k))
            best.sort()
            best = best[:keep]
        for i in range(SCAN_DEGREE):
            s[i] += s[i + 1]
    return [raw0 + k for _, k in best]


# --- the case list ----------------------------------------------------------------------------------

GRID_A = ([1.2, 1.25, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2, 3.4, 3.5, 3.6, 3.7, 3.76, 3.8, 3.9, 4.0, 4.2, 4.5,
           5.0, 5.5, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0, 50.0]
          + [1.2 + 0.137 * i for i in range(1, 60)])


def grid_R() -> list[Q]:
    """The 94 distances of the C1-A tests (binary64 nearest to angstrom / a0, then 250, 1000, 10^4 bohr)."""
    return [Q(float(Q(str(a)) / L.BOHR_ANGSTROM)) for a in GRID_A] + [Q(250), Q(1000), Q(10000)]


def build_cases(log=print) -> list[tuple[str, int, list[str]]]:
    cases: dict[tuple[str, int], list[str]] = {}

    def add(profile, raw, tag):
        cases.setdefault((profile, raw), [])
        if tag not in cases[(profile, raw)]:
            cases[(profile, raw)].append(tag)

    def around(profile, raw, tag, below=2, above=2):
        for d in range(-below, above + 1):
            add(profile, raw + d, tag)

    for R in grid_R():
        add("B64", bits(float(R)), "grid")
    for R in grid_R()[::3]:
        add("FX64_32", raw_near("FX64_32", R), "grid")

    for p in PROFILES:
        # r_min = 1.2 A: the last input below it (domain exceeded) and the first ones at or above it
        r0 = raw_ceil(p, L.R_MIN_BOHR)
        around(p, r0, "r_min", below=1, above=4)
        # V changes sign between 3.3 and 3.4 A; F = 0 at the minimum (R_e ~ 3.764 A)
        around(p, root_raw(p, "V", Q(62, 10), Q(65, 10)), "V_sign_change", 3, 4)
        around(p, root_raw(p, "V_ret_off", Q(62, 10), Q(65, 10)), "V_sign_change", 1, 2)
        around(p, root_raw(p, "F", Q(7), Q(73, 10)), "F_zero_minimum", 3, 4)
        around(p, root_raw(p, "V+sigma", Q(62, 10), Q(65, 10)), "V+sigma_sign_change", 1, 2)
        around(p, root_raw(p, "V-sigma", Q(62, 10), Q(65, 10)), "V-sigma_sign_change", 1, 2)
        # 20 A: the upper end of the rel / QED ab initio data
        around(p, raw_near(p, Q(20) / L.BOHR_ANGSTROM), "20_angstrom", 2, 2)
        # 250 bohr and beyond
        for R in (Q(250), Q(300), Q(500), Q(2000), Q(5000), Q(10000)):
            around(p, raw_near(p, R), "long_range_250_bohr_plus" if R <= 500 else "tiny_V_F_to_1e4_bohr", 1, 1)
    log("roots and fixed regions done")

    # FX(64,32): where V and F round to zero (the tail below 2^-33 hartree vanishes in this profile)
    for name, lo, hi in (("V", Q(20), Q(400)), ("F", Q(20), Q(400))):
        around("FX64_32", root_raw("FX64_32", name, lo, hi, offset=-Q(1, 1 << 33)), f"FX_{name}_underflow_edge", 2, 2)

    # the B0 range end (capability limit, not physics): 2^20 bohr and one input beyond
    add("B64", bits(float(B0_R_MAX)), "b0_range_end")
    add("B64", bits(math.nextafter(float(B0_R_MAX), math.inf)), "b0_range_end")
    add("B64", bits(1e5), "tiny_V_F_to_1e4_bohr")

    # strongest cancellation (away from the roots) on a log grid
    cand = [Q(float(L.R_MIN_BOHR * Q(1.03) ** i)) for i in range(0, 260)]
    kap = [(c, _cancellation(c)) for c in cand]
    rv = R_of("B64", root_raw("B64", "V", Q(62, 10), Q(65, 10)))
    far = [(c, k) for c, k in kap if abs(c / rv - 1) > Q(1, 20)]
    peak = max(far, key=lambda t: t[1])
    log(f"cancellation peak (away from the V root): R = {float(peak[0]):.4g} bohr, kappa = {peak[1]:.3g}")
    for p in PROFILES:
        around(p, raw_near(p, peak[0]), "strong_cancellation", 1, 1)
    short_peak = max((t for t in far if t[0] < rv), key=lambda t: t[1])
    for p in PROFILES:
        around(p, raw_near(p, short_peak[0]), "strong_cancellation", 1, 1)

    # onset of retardation: |V_on - V_off| / |V_on| is already ~1.5e-6 at r_min (far above 2^-53, so
    # retardation is visible in the last bits everywhere); it passes 1e-5 before the V root and grows past it
    onset = {}
    for label, t, lo, hi in (("1e-5", Q(1, 10 ** 5), 3.0, 6.0), ("1e-3", Q(1, 1000), 7.5, 5e4),
                             ("1e-2", Q(1, 100), 7.5, 5e4), ("1e-1", Q(1, 10), 7.5, 5e4)):
        onset[label] = _ratio_crossing(t, lo, hi)
        log(f"retardation ratio {label} at R = {float(onset[label]):.5g} bohr")
        for p in PROFILES:
            around(p, raw_near(p, onset[label]), f"retardation_onset_{label}", 1, 1)

    # boundary search: values closest to a rounding boundary among 2^18 consecutive inputs
    regions = {"r_min": L.R_MIN_BOHR, "short": Q(3), "cancellation": short_peak[0],
               "V_sign_change": rv * Q(99, 100), "well": Q(15, 2), "mid": Q(12), "20_angstrom": Q(20) / L.BOHR_ANGSTROM,
               "retardation_onset": onset["1e-3"], "250_bohr": Q(250), "1e4_bohr": Q(10000)}
    for p in PROFILES:
        for region, R0 in regions.items():
            if p == "FX64_32" and R0 > 100:
                continue            # FX(64,32) V and F are 0 or a few units there -- no fractional search
            for name in ("V", "F"):
                for raw in scan_hard(p, name, R0):
                    add(p, raw, f"boundary_search_{name}_{region}")
        log(f"boundary search {p} done")
    return [(p, raw, tags) for (p, raw), tags in sorted(cases.items(), key=lambda t: (t[0][0], R_of(*t[0])))]


# --- generation (needs D:\reference) and loading ----------------------------------------------------

def _sha256(path: Path) -> str:
    """Raw bytes (the published Lang files, kept outside Git)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_sha256(path: Path) -> str:
    """Code files: CRLF normalised to LF, i.e. the Git blob content, so a Windows checkout gives the same hash."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    return r.stdout.strip()


# every code file that decides a stored bit or its verdict; the fixture is generated only when all of them are
# committed unchanged at HEAD, so git_head_at_generation contains exactly the code that produced it
REFERENCE_FILES = ("a_reference/ar2_lang2024.py", "a_numeric/exp.py", "a_numeric/profiles.py")
GENERATOR_FILE = "a_reference/ar2_lang2024_fixture.py"


def code_files() -> tuple[str, ...]:
    from audit.independent_physics.ar2_lang2024 import AUDIT_FILES
    return REFERENCE_FILES + (GENERATOR_FILE,) + tuple(AUDIT_FILES)


def dirty_code_files() -> list[str]:
    r = subprocess.run(["git", "status", "--porcelain", "--", *code_files()], capture_output=True, text=True,
                       cwd=ROOT)
    return [l for l in r.stdout.splitlines() if l.strip()]


def verify_with_audit(profile: str, raw: int, name: str, stored: dict, model) -> str | None:
    """The audit's verdict on one stored outcome (None = confirmed)."""
    from audit.independent_physics import ar2_lang2024 as A
    R = R_of(profile, raw)
    if not A.in_domain(R):
        return None if "domain" in stored else "audit: outside the domain but a value was stored"
    if "raw" not in stored:
        return f"audit: in the domain but stored {stored}"
    q, ret = QUANTITIES[name]
    v = raw_parse(profile, stored["raw"])
    if q == "F":
        x = A.dVdR_numeric(model, R, 80, ret)
        ok = (A.force_in_fx_interval(x, v, 32) if profile == "FX64_32" else
              _b64_contains(x, v))
        return None if ok else "audit: numerical derivative outside the rounding interval"
    if profile == "FX64_32":
        return A.judge_fx(model, q, R, v, 32, ret)
    return A.judge_b64(model, q, R, v, ret)


def _b64_contains(x: Q, result: int) -> bool:
    from audit.independent_numeric.oracle import SIGN, _interval
    lo, hi = _interval(result & ~SIGN)
    return lo <= (-x if result >> 63 else x) <= hi


def generate(path: Path = FIXTURE, log=print) -> dict:
    from audit.independent_physics.ar2_lang2024 import AUDIT_FILES, Model, parse_fortran
    dirty = dirty_code_files()
    if dirty:
        raise RuntimeError(f"commit these first -- the fixture must name the commit that generated it: {dirty}")
    model = Model(parse_fortran())
    cases = build_cases(log)
    log(f"{len(cases)} cases; evaluating and auditing")
    out_cases = []
    for i, (p, raw, tags) in enumerate(cases):
        res = {name: outcome(p, name, raw) for name in QUANTITIES}
        for name, o in res.items():
            verdict = verify_with_audit(p, raw, name, o, model)
            if verdict is not None:
                raise AssertionError(f"{p} {raw_str(p, raw)} {name}: {verdict}")
        hard = {name: boundary_distance_log2(p, name, raw) for name in ("V", "F")} if "raw" in res["V"] else {}
        R = R_of(p, raw)
        out_cases.append({"profile": p, "R_raw": raw_str(p, raw), "R": f"{R.numerator}/{R.denominator}",
                          "R_bohr_approx": float(R), "tags": tags, "results": res,
                          "boundary_distance_log2": hard})
        if i % 50 == 0:
            log(f"  {i}/{len(cases)}")
    doc = {
        "format": FIXTURE_FORMAT,
        "contract": {
            "version": L.CONTRACT_VERSION,
            "parameter_fingerprint": L.parameter_fingerprint(),
            "meaning": "A value = round_profile(exact Lang 2024 model value), rounded once; F = -dV/dR analytic; "
                       "R < 1.2 A -> physics_domain_exceeded",
            "units": "R bohr, V and sigma hartree, F hartree/bohr",
            "bohr_angstrom": str(L.BOHR_ANGSTROM),
            "bohr_angstrom_source": L.BOHR_ANGSTROM_SOURCE,
            "profiles": {"B64": "A-Binary64-Finite (raw = 16 hex digits)",
                         "FX64_32": "FX(64, 32) (raw = integer, value raw / 2^32)"},
            "quantities": {k: {"quantity": q, "retardation": r} for k, (q, r) in QUANTITIES.items()},
        },
        "provenance": {
            "lang2024_files_sha256": {f: _sha256(DATA / f) for f in SOURCE_FILES},
            "code_hash_rule": "SHA-256 of the file with CRLF normalised to LF (= the Git blob)",
            "audit_code_sha256": {f: code_sha256(ROOT / f) for f in AUDIT_FILES},
            "reference_code_sha256": code_sha256(ROOT / "a_reference" / "ar2_lang2024.py"),
            "reference_dependencies_sha256": {f: code_sha256(ROOT / f) for f in REFERENCE_FILES[1:]},
            "generator_code_sha256": code_sha256(Path(__file__)),
            "git_head_at_generation": _git_head(),
            "code_files_committed_at_head": True,
            "audit_checks": "V, V_ret_off, sigma, V+-sigma: mpmath interval enclosure strictly inside the rounding "
                            "interval; F, F_ret_off: 80-digit numerical derivative inside the rounding interval "
                            "(strong independent check, not a proof); domain: the audit's own 1.2 A / a0",
        },
        "cases": out_cases,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    log(f"wrote {path} ({len(out_cases)} cases)")
    return doc


def load(path: Path = FIXTURE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    generate()
