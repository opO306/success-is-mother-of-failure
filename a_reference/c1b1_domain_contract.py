"""C1-B1 D_valid: a machine-readable evidence-level contract, FROZEN as c1b1-dvalid-v1 (designer verdicts on section 22,
on 3f2f73c / eadb413, and on the boundary record 50cceaa: "new_run 연결 진행, 다만 연결하면서 계약을 넓히지는 않습니다").

It never blocks a computation: `new_run` builds the run as before and the run carries `run.validation`, the
classification of its INITIAL state (computed on first access, cached). Every result names its evidence level --
"numerical_validated" or "unsupported" ("formal_certified" exists as a level but nothing reaches it yet) -- and never the
merged word "certified". The fixture's own words stay "NUMERICALLY VALIDATED evidence (not certified)".

D_valid = D_base - D_capture, judged on an enclosure of the initial E_rel and the impact parameter b = |L| / sqrt(2 mu E):

  D_base     E_LOW <= E_rel <= E_HIGH, 0 <= b <= B_MAX, and the adopted executor profile (position FX(96,48), momentum
             FX(96,80), dt = 40, drift v2) -- the evidence was measured for that profile only.
             E_LOW = 1e-8 De (numerically validated floor, section 21), E_HIGH = 10 De (the integrator contract).
             E_rel < E_LOW includes every bound state: no bound-state D_valid exists yet -> unsupported.
  capture    orbiting exists at E (E below the barrier-top maximum E_max ~ 0.9964 De) with b_orb(E) <= B_MAX.
             Energies within E_MAX_MARGIN above the grid estimate of E_max are unsupported (existence not decided).
  measured   ONLY the energies present in the frozen boundary fixture (7: 0.15 ... 0.99 De). An energy "is" a fixture
             energy when the whole E enclosure lies within E_MATCH_REL of it: the bound on how far the measurement's
             own initial states could sit from their nominal energy (momentum rounding on the FX(96,80) grid at the
             measurement's start radius, derived below; measured worst 3.7e-25). This is the measurement's resolution,
             not a neighbourhood: no interpolation, no nearest-energy substitution, no extrapolation. Any other energy
             inside the capture range is unsupported at every b.
  per side   rho = b / b_orb - 1, sides judged independently (sign -1: b < b_orb, +1: b > b_orb). With the side's
             interval largest_nonpass <= delta_c <= smallest_pass and its outermost passing probe:
                 |rho| <  largest_nonpass                 -> "inside_band"     unsupported (measured fail or unknown)
                 largest_nonpass <= |rho| < smallest_pass  -> "uncertain_edge"  unsupported
                 smallest_pass <= |rho| <= outermost_pass  -> "validated"       numerical_validated
                 |rho| >  outermost_pass                  -> "beyond_probes"   unsupported (NOT extrapolated)
             The "validated" row relies on the monotone band model BETWEEN probes. That is a property the measurement
             protocol checks, not an accident of 14 samples: c1b1_orbit_boundary refuses (status non_monotone, fixture
             FAILED, exit 3) as soon as any measured fail lies farther out than any measured pass, and smallest_pass is
             by construction the innermost pass with no fail or unknown farther out. The load check below re-verifies
             both on the probes. Nothing beyond the outermost probe is claimed.
             Every side the (E, b) enclosure touches must be "validated"; an enclosure touching rho = 0 is inside_band.
  budgets    the fixture measures the dt = 40 DISCRETIZATION (high-precision run vs audit quadrature, < 1e-5 rad);
             rounding is the separate section 22 record (< 1e-6 rad on every near-orbiting case, the separatrix included).
             The two sources are held to separate targets, as in sections 20 / 22 -- not a combined bound.

Fail-closed: a missing fixture, a hash other than FROZEN_BOUNDARY_SHA256, bad JSON, wrong format / status, an unknown
side status, a missing side, a duplicate or unexpected energy, a b_orb that does not recompute, largest_nonpass >=
smallest_pass, probes that contradict the recorded interval -- any of these, or any exception while judging, makes
EVERY point unsupported (never numerical_validated), with the reason recorded.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
from dataclasses import dataclass, field
from fractions import Fraction as Q
from math import isqrt
from pathlib import Path

import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_two_atom as C

DVALID_VERSION = "c1b1-dvalid-v1"
BOUNDARY_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "c1b1_orbit_boundary_v1.json"
FROZEN_BOUNDARY_SHA256 = "61caa7573c6fe71457a6752b51c53cce17ec8b059bbc25d104ac85ccf34170ce"   # LF-normalized, record 50cceaa
BOUNDARY_FORMAT = "c1b1-orbit-boundary-v2"
BOUNDARY_STATUS = "NUMERICALLY VALIDATED evidence (not certified)"
EXPECTED_ENERGIES = ("3/20", "1/5", "3/10", "1/2", "7/10", "9/10", "99/100")
SIDE_STATUSES = ("ok", "no_pass_found", "non_monotone")

DE = I.S.DE_GRID
E_LOW = Q(1, 10 ** 8) * DE
E_HIGH = C.INTEGRATOR_E_MAX
B_MAX = 2 * I.S.RE_GRID
PROFILE = {"position": "FX(96,48)", "momentum": "FX(96,80)", "dt": Q(40), "drift": "v2"}
E_MAX_MARGIN = Q(1, 1000)          # relative, above the 1 %-grid estimate of the barrier-top maximum
B_ORB_MARGIN = Q(1, 10 ** 9)       # relative, around b_orb = B_MAX when deciding "capture outside the swept range"
SQRT_BITS = 256                    # outward-rounded rational square roots


def e_match_rel() -> Q:
    """Relative energy resolution of the measurement's initial states, rounded UP to a power of two.
    The states (c1b1_inner_validation.state) have exact positions (+-R_START/2 on x) and momenta rounded to the FX(96,80)
    grid: each component of p_j (= -p_i) moves by at most 2^-81, so |dP| <= sqrt(3) 2^-81 and
    |dK| <= (2 |P| |dP| + |dP|^2) / (2 mu), |P|^2 <= 2 mu (E - V(R_START)); largest relative at the lowest fixture energy."""
    mu = C.AR40_MASS_ME / 2
    e_min = min(Q(e) for e in EXPECTED_ENERGIES) * DE
    V0 = C.potential_high(I.R_START ** 2, 256)
    P = math.sqrt(float(2 * mu * (e_min - V0)))
    dP = math.sqrt(3) * 2.0 ** -81
    rel = (2 * P * dP + dP * dP) / (2 * float(mu)) / float(e_min)
    return Q(1, 2 ** math.floor(-math.log2(rel)))          # the power of two just above rel


E_MATCH_REL = e_match_rel()


class FixtureError(Exception):
    pass


# --- loading the evidence, fail-closed ---------------------------------------------------------------------------

def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


@functools.lru_cache(maxsize=None)
def _orbiting(e: str):
    return I.orbiting(Q(e))


def _check_side(e: str, name: str, s) -> dict:
    where = f"E/De={e} {name}"
    if not isinstance(s, dict) or s.get("status") not in SIDE_STATUSES:
        raise FixtureError(f"{where}: unknown or missing status")
    out = {"status": s["status"]}
    if s["status"] != "ok":
        return out
    probes = s.get("probes")
    try:
        lnp, sp = float(s["largest_nonpass"]), float(s["smallest_pass"])
    except (KeyError, TypeError, ValueError) as exc:
        raise FixtureError(f"{where}: bad interval ({exc})") from None
    if not (math.isfinite(lnp) and math.isfinite(sp) and 0 < lnp < sp):
        raise FixtureError(f"{where}: interval not 0 < largest_nonpass < smallest_pass ({lnp}, {sp})")
    if not isinstance(probes, list) or not probes:
        raise FixtureError(f"{where}: no probes")
    passes = [p["abs_rho"] for p in probes if p.get("pass") is True]
    nonpass = [p["abs_rho"] for p in probes if p.get("pass") is not True]
    fails = [p["abs_rho"] for p in probes if p.get("pass") is False]
    if sp not in passes:
        raise FixtureError(f"{where}: smallest_pass is not a passing probe")
    if any(a > sp for a in nonpass):
        raise FixtureError(f"{where}: a fail / unknown probe lies beyond smallest_pass")
    if lnp != max((a for a in nonpass if a < sp), default=None):
        raise FixtureError(f"{where}: largest_nonpass does not match the probes")
    if passes and fails and max(fails) >= min(passes):
        raise FixtureError(f"{where}: probes are non-monotone but status is ok")
    out.update(largest_nonpass=lnp, smallest_pass=sp, outermost_pass=max(passes))
    return out


@functools.lru_cache(maxsize=None)
def _load(path: str, expected_sha: str | None):
    """(table, fixture_sha) or (None, reason) -- never raises."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        return None, f"fixture unreadable: {exc}"
    sha = _sha(raw)
    if expected_sha is not None and sha != expected_sha:
        return None, f"fixture sha256 {sha[:16]}... is not the frozen {expected_sha[:16]}..."
    try:
        doc = json.loads(raw.decode("utf-8"))
        if doc.get("format") != BOUNDARY_FORMAT:
            raise FixtureError(f"format {doc.get('format')!r}")
        if doc.get("status") != BOUNDARY_STATUS:
            raise FixtureError(f"status {doc.get('status')!r}")
        table = {}
        for row in doc["energies"]:
            e = row["e"]
            if e in table:
                raise FixtureError(f"duplicate energy {e}")
            if e not in EXPECTED_ENERGIES:
                raise FixtureError(f"unexpected energy {e}")
            orb = _orbiting(e)
            if orb is None or str(orb[0]) != row["b_orb"]:
                raise FixtureError(f"E/De={e}: b_orb does not recompute")
            table[e] = {"e": Q(e), "b_orb": orb[0], "minus": _check_side(e, "delta_minus", row.get("delta_minus")),
                        "plus": _check_side(e, "delta_plus", row.get("delta_plus"))}
        if set(table) != set(EXPECTED_ENERGIES):
            raise FixtureError(f"energies {sorted(table)} are not the expected set")
    except (FixtureError, KeyError, TypeError, ValueError) as exc:
        return None, f"fixture rejected: {exc}"
    return table, sha


@functools.lru_cache(maxsize=None)
def e_max_grid() -> Q:
    """The barrier-top maximum on the same grid c1b1_inner_validation.orbiting searches (an estimate from below)."""
    grid = [I.S.RE_GRID * Q(101, 100) ** i for i in range(1, 900)]
    return max(I.barrier_energy(R)[0] for R in grid)


# --- judging -----------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class DomainVerdict:
    in_base: bool
    in_capture_band: bool | None       # None: capture exists at this energy but it was not measured (unknown)
    evidence: str                      # "numerical_validated" | "unsupported" ("formal_certified": nothing yet)
    reason: str
    provenance: dict = field(default_factory=dict, compare=False)


def _sqrt_bounds(x: Q) -> tuple[Q, Q]:
    """lo <= sqrt(x) <= hi, rationals with 2^-SQRT_BITS resolution."""
    s = 2 * SQRT_BITS
    n = x.numerator << s
    lo = isqrt(n // x.denominator)
    hi = isqrt(-(-n // x.denominator))
    if hi * hi * x.denominator < n:
        hi += 1
    return Q(lo, 1 << SQRT_BITS), Q(hi, 1 << SQRT_BITS)


def _region(a_lo: Q, a_hi: Q, side: dict) -> str:
    lnp, sp, outer = Q(side["largest_nonpass"]), Q(side["smallest_pass"]), Q(side["outermost_pass"])
    if a_lo >= sp and a_hi <= outer:
        return "validated"
    if a_hi > outer:
        return "beyond_probes"
    if a_hi < lnp:
        return "inside_band"
    return "uncertain_edge"


def classify(e_lo: Q, e_hi: Q, b_lo: Q, b_hi: Q, path: Path | None = None,
             expected_sha: str | None = FROZEN_BOUNDARY_SHA256) -> DomainVerdict:
    """Classify an enclosure E_rel in [e_lo, e_hi] (hartree), b in [b_lo, b_hi] (bohr). Never raises."""
    path = BOUNDARY_FIXTURE if path is None else path
    prov = {"dvalid_version": DVALID_VERSION, "fixture": path.name, "e_rel_De": [str(e_lo / DE), str(e_hi / DE)],
            "b_bohr": [float(b_lo), float(b_hi)]}

    def out(in_base, band, evidence, reason, **extra):
        prov.update(extra, verdict=evidence, reason=reason)
        return DomainVerdict(in_base, band, evidence, reason, prov)

    try:
        table, sha = _load(str(path), expected_sha)
        prov["fixture_sha256"] = sha if table is not None else None
        if table is None:
            return out(False, None, "unsupported", sha)
        if not (E_LOW <= e_lo and e_hi <= E_HIGH and 0 <= b_lo and b_hi <= B_MAX):
            return out(False, False, "unsupported",
                       f"outside D_base: E_rel in [{float(e_lo / DE):.6g}, {float(e_hi / DE):.6g}] De (need "
                       f"1e-8 .. 10), b in [{float(b_lo):.6g}, {float(b_hi):.6g}] bohr (need 0 .. {float(B_MAX):.6g})")
        emax = e_max_grid()
        if e_lo > emax * (1 + E_MAX_MARGIN):
            return out(True, False, "numerical_validated", "in D_base, above every barrier top: no capture band")
        if e_hi >= emax:
            return out(True, None, "unsupported", "within E_MAX_MARGIN of the barrier-top maximum: capture undecided")
        key = next((k for k, row in table.items()
                    if all(abs(x / (row["e"] * DE) - 1) <= E_MATCH_REL for x in (e_lo, e_hi))), None)
        if key is None:
            e_mid = (e_lo + e_hi) / 2
            orb = I.orbiting(e_mid / DE)
            if orb is not None and orb[0] > B_MAX * (1 + B_ORB_MARGIN):
                return out(True, False, "numerical_validated",
                           f"in D_base, capture band outside the swept range (b_orb={float(orb[0]):.6g} > b_max)")
            return out(True, None, "unsupported",
                       f"capture band exists near E/De={float(e_mid / DE):.6g} but that energy is not a measured fixture "
                       f"energy (within {float(E_MATCH_REL):.3g} relative): no interpolation, no nearest energy")
        row = table[key]
        bo = row["b_orb"]
        r_lo, r_hi = b_lo / bo - 1, b_hi / bo - 1
        prov.update(energy=key, b_orb=str(bo), rho=[float(r_lo), float(r_hi)])
        if r_lo <= 0 <= r_hi:
            return out(True, True, "unsupported", f"E/De={key}: the b enclosure touches b_orb (rho = 0)",
                       sides=[{"side": "both", "region": "inside_band"}])
        sides = []
        for name, lo, hi in (("delta_minus", -r_hi, -r_lo), ("delta_plus", r_lo, r_hi)):
            if hi <= 0:
                continue                                  # this side not touched
            side = row["minus" if name == "delta_minus" else "plus"]
            rec = {"side": name, "abs_rho": [float(max(lo, Q(0))), float(hi)], "status": side["status"]}
            if side["status"] != "ok":
                rec["region"] = side["status"]
            else:
                rec.update(largest_nonpass=side["largest_nonpass"], smallest_pass=side["smallest_pass"],
                           outermost_pass=side["outermost_pass"], region=_region(max(lo, Q(0)), hi, side))
            sides.append(rec)
        ok = bool(sides) and all(s["region"] == "validated" for s in sides)
        band = any(s["region"] in ("inside_band", "uncertain_edge") for s in sides)
        reason = f"E/De={key}: " + "; ".join(f"{s['side']} {s['region']}" for s in sides)
        return out(True, band, "numerical_validated" if ok else "unsupported", reason, sides=sides)
    except Exception as exc:                              # fail-closed: judging never raises, never validates on error
        return out(False, None, "unsupported", f"contract evaluation error: {type(exc).__name__}: {exc}")


def evaluate_domain(e_rel: Q, b: Q, path: Path | None = None,
                    expected_sha: str | None = FROZEN_BOUNDARY_SHA256) -> DomainVerdict:
    """A point (E_rel, b): the degenerate enclosure."""
    return classify(e_rel, e_rel, b, b, path, expected_sha)


def evaluate_run(run) -> dict:
    """D_valid of a run's INITIAL state (run.initial, set by new_run). Never raises."""
    try:
        prof = {"position": getattr(run.pos, "name", repr(run.pos)), "momentum": getattr(run.mom, "name", repr(run.mom)),
                "dt": run.dt, "drift": run.drift}
        if prof != PROFILE:
            v = DomainVerdict(False, None, "unsupported", f"executor profile {prof} is not the measured {PROFILE}",
                              {"dvalid_version": DVALID_VERSION, "verdict": "unsupported"})
        else:
            i, j = run.initial
            mi, mj = C.SPECIES_MASS[i.species], C.SPECIES_MASS[j.species]
            M, mu = mi + mj, mi * mj / (mi + mj)
            rel = C.relative(run.pos, i, j)
            pi, pj = C.exact(run.mom, i.p), C.exact(run.mom, j.p)
            P = tuple((mi * b - mj * a) / M for a, b in zip(pi, pj))
            L = (rel[1] * P[2] - rel[2] * P[1], rel[2] * P[0] - rel[0] * P[2], rel[0] * P[1] - rel[1] * P[0])
            L2 = sum((x * x for x in L), Q(0))
            probe = C.Run(run.pos, run.mom, run.dt, run.initial, validated_only=False, drift=run.drift)
            e_lo, e_hi = C.relative_energy_enclosure(probe, 512)
            if e_lo <= 0:
                v = classify(e_lo, e_hi, Q(0), Q(0))       # not a scattering state: D_base refuses it
            else:
                b_lo = _sqrt_bounds(L2 / (2 * mu * e_hi))[0]
                b_hi = _sqrt_bounds(L2 / (2 * mu * e_lo))[1]
                v = classify(e_lo, e_hi, b_lo, b_hi)
        p = dict(v.provenance)
        p["profile"] = {k: str(x) for k, x in prof.items()}
        return {"validation_status": v.evidence, "reason": v.reason, "in_base": v.in_base,
                "in_capture_band": v.in_capture_band, "provenance": p}
    except Exception as exc:
        return {"validation_status": "unsupported", "reason": f"contract evaluation error: {type(exc).__name__}: {exc}",
                "in_base": False, "in_capture_band": None, "provenance": {"dvalid_version": DVALID_VERSION}}


def report(e_rel: Q, b: Q) -> dict:
    v = evaluate_domain(e_rel, b)
    return {"validation_status": v.evidence, "reason": v.reason, "in_base": v.in_base,
            "in_capture_band": v.in_capture_band, "provenance": v.provenance}
