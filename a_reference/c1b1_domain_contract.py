"""C1-B1 D_valid: a machine-readable evidence-level contract (designer verdict on section 22, item 3, approved
as-is; item 1 refined to asymmetric delta_-/delta_+).

D_valid = D_base - D_capture:
    D_base    : E_rel >= E_low, 0 <= b <= b_max                              (numerically validated floor / cap)
    D_capture : E in the orbiting-capture energy range AND
                -delta_-(E) < rho(E, b) < delta_+(E), rho = b / b_orb(E) - 1  (excluded band, section 22)

This module does NOT gate `new_run` or `check_integrator_domain` (that stays a hard IntegratorDomainExceeded on
E_rel > 10 De -- a different, older contract). `evaluate_domain` only classifies a (E, b) point for reporting:
computation is never forbidden here (designer, 20th ed. item 1 and this verdict's item 3: "new_run은 계산을
금지하지 않습니다"). Every classification names the evidence level explicitly; "formal_certified" and
"numerical_validated" are never merged into one "certified" claim (designer, repeatedly).

Evidence sources feeding this module (as of 2026-09-26, section 22 + this verdict):
  * E_low = 1e-8 De        -- numerically validated floor (design doc section 21/20 item 1); NOT proven.
  * b_max = 2 R_e          -- the impact-parameter cap actually swept by every inner/orbit validation study.
  * orbiting capture range -- energies where c1b1_inner_validation.orbiting(e) is not None (E < E_max ~ 0.9964 De)
                               AND b_orb(e) <= b_max (empirically, from ~0.14 De up; below that b_orb > b_max).
  * delta_-, delta_+       -- from c1b1_orbit_boundary.py (fixtures/c1b1_orbit_boundary_v1.json), stored per side as an
                               INTERVAL largest_nonpass <= delta_c <= smallest_pass. Only |rho| >= smallest_pass on a side
                               whose status is "ok" is numerically validated; the uncertain interval, a side with
                               "no_pass_found" and a side with "non_monotone" are unsupported.
  * unmeasured energies    -- inside the capture range, an energy without its own fixture row is UNSUPPORTED at every
                               b (no interpolation, and no "far enough from b_orb, probably fine" either -- designer on
                               3f2f73c). Extending to a continuous energy range needs a conservative envelope per energy
                               interval, a separate, later step.
  * beyond the probes      -- |rho| above the largest probe on a side rests on the monotone band model (checked on the
                               probes) plus the section 22 points at 0.8 / 1.2 b_orb; it is not probed point by point.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path

import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_two_atom as C

BOUNDARY_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "c1b1_orbit_boundary_v1.json"

E_LOW = Q(1, 10 ** 8) * I.S.DE_GRID       # 1e-8 De, numerically validated floor (design doc section 21)
B_MAX = 2 * I.S.RE_GRID                    # x R_e, the cap every validation study actually swept


@dataclass(frozen=True)
class DomainVerdict:
    in_base: bool                # E_low <= E_rel and 0 <= b <= b_max
    in_capture_band: bool | None # True / False when this energy was measured; None when it was not (unknown)
    evidence: str                # "numerical_validated" | "unsupported" | "formal_certified" (unused so far)
    reason: str                  # human-readable, always filled


def _load_boundary() -> dict:
    if not BOUNDARY_FIXTURE.exists():
        return {}
    doc = json.loads(BOUNDARY_FIXTURE.read_text(encoding="utf-8"))
    return {row["e"]: row for row in doc.get("energies", [])}


def evaluate_domain(e_rel: Q, b: Q, boundary: dict | None = None) -> DomainVerdict:
    """Classify (E_rel, b) -- E_rel in hartree, b in bohr -- against D_valid. Never raises; a point outside
    every known-good region comes back "unsupported", not rejected (new_run still runs the computation)."""
    boundary = _load_boundary() if boundary is None else boundary
    e_de = e_rel / I.S.DE_GRID
    if not (e_rel >= E_LOW and 0 <= b <= B_MAX):
        return DomainVerdict(False, False, "unsupported",
                             f"outside D_base: E_rel={float(e_de):.3g} De (need >= {float(E_LOW / I.S.DE_GRID):.1g}), "
                             f"b={float(b):.3g} bohr (need 0..{float(B_MAX):.3g})")
    r = I.orbiting(e_de)
    if r is None:
        return DomainVerdict(True, False, "numerical_validated",
                             "in D_base, no orbital-capture band at this energy (above E_max ~ 0.9964 De)")
    bo, _ = r
    if bo > B_MAX:
        return DomainVerdict(True, False, "numerical_validated",
                             f"in D_base, b_orb={float(bo):.3g} > b_max: capture band outside the swept range")
    rho = b / bo - 1
    row = boundary.get(str(e_de))
    if row is None:
        return DomainVerdict(True, None, "unsupported",
                             f"capture band exists at E/De={float(e_de):.3g} (b_orb={float(bo):.3g}) but this energy was "
                             f"not measured -- unsupported at every b (no interpolation, no envelope yet)")
    side = row["delta_minus"] if rho < 0 else row["delta_plus"]
    name = "delta_-" if rho < 0 else "delta_+"
    if side["status"] != "ok":
        return DomainVerdict(True, True, "unsupported",
                             f"{name} side at E/De={float(e_de):.3g} has status {side['status']}: the whole side is "
                             f"unsupported (rho={float(rho):.3g})")
    sp = side["smallest_pass"]
    if rho != 0 and abs(float(rho)) >= sp:
        return DomainVerdict(True, False, "numerical_validated",
                             f"outside the measured capture band: |rho|={abs(float(rho)):.3g} >= smallest pass {sp:.3g} "
                             f"({name})")
    return DomainVerdict(True, True, "unsupported",
                         f"inside the capture band or its uncertain edge: |rho|={abs(float(rho)):.3g} < smallest pass "
                         f"{sp:.3g} ({name}; largest non-pass {side['largest_nonpass']})")


def report(e_rel: Q, b: Q) -> dict:
    """The machine-readable shape the designer specified: result is never blocked by this; validation_status and
    reason are attached for the caller to act on."""
    v = evaluate_domain(e_rel, b)
    return {"validation_status": v.evidence, "reason": v.reason, "in_base": v.in_base,
            "in_capture_band": v.in_capture_band}
