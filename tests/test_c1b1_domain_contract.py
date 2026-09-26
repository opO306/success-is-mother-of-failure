"""D_valid machine-readable contract and the orbital-capture boundary search logic (designer verdicts on section 22
and on 3f2f73c / eadb413).

Pure-logic tests: `evaluate_domain` never raises and never blocks computation; the boundary search is driven by an
injected fake probe, so its bookkeeping (interval, unknowns, expansion, monotonicity) is checked without running a
trajectory. The real fixture is not needed."""
from __future__ import annotations

from fractions import Fraction as Q

import a_reference.c1b1_domain_contract as D
import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_orbit_boundary as B

DE = I.S.DE_GRID


def _side(status="ok", nonpass=1e-4, sp=1.2e-4):
    return {"status": status, "largest_nonpass": nonpass, "smallest_pass": sp}


def _row(minus, plus):
    return {"delta_minus": minus, "delta_plus": plus}


# --- the contract --------------------------------------------------------------------------------------------

def test_below_e_low_and_beyond_b_max_are_unsupported_not_rejected() -> None:
    assert D.evaluate_domain(Q(1, 10 ** 10) * DE, Q(5)).evidence == "unsupported"
    assert D.evaluate_domain(DE, D.B_MAX * 2).evidence == "unsupported"
    r = D.report(Q(1, 10 ** 10) * DE, Q(5))
    assert r["validation_status"] == "unsupported" and r["in_base"] is False


def test_above_e_max_has_no_capture_band_and_is_validated() -> None:
    v = D.evaluate_domain(Q(2) * DE, Q(5))
    assert v.in_base and v.in_capture_band is False and v.evidence == "numerical_validated"


def test_unmeasured_energy_in_the_capture_range_is_unsupported_at_every_b() -> None:
    """Designer on 3f2f73c: no 'far enough from b_orb, probably fine' -- an energy without its own row is unknown."""
    bo, _ = I.orbiting(Q(1, 2))
    for b in (bo, bo * Q(4, 5), bo * Q(1, 2), Q(0)):
        v = D.evaluate_domain(Q(1, 2) * DE, b, boundary={})
        assert v.evidence == "unsupported" and v.in_capture_band is None, b


def test_measured_row_validates_only_at_or_beyond_the_smallest_pass() -> None:
    e = Q(15, 100)
    bo, _ = I.orbiting(e)
    fx = {"3/20": _row(_side(nonpass=1e-4, sp=1.2e-4), _side(nonpass=2e-4, sp=2.5e-4))}
    at = D.evaluate_domain(e * DE, bo, boundary=fx)
    assert at.in_capture_band is True and at.evidence == "unsupported"
    edge = D.evaluate_domain(e * DE, bo * (1 - Q(11, 100000)), boundary=fx)       # between nonpass and pass
    assert edge.evidence == "unsupported"
    out = D.evaluate_domain(e * DE, bo * Q(99, 100), boundary=fx)
    assert out.in_capture_band is False and out.evidence == "numerical_validated"
    plus_edge = D.evaluate_domain(e * DE, bo * (1 + Q(22, 100000)), boundary=fx)  # asymmetric: + side wider
    assert plus_edge.evidence == "unsupported"


def test_a_side_without_pass_or_non_monotone_is_unsupported_everywhere() -> None:
    e = Q(15, 100)
    bo, _ = I.orbiting(e)
    for status in ("no_pass_found", "non_monotone"):
        fx = {"3/20": _row(_side(status=status), _side())}
        assert D.evaluate_domain(e * DE, bo * Q(1, 2), boundary=fx).evidence == "unsupported", status


def test_evidence_levels_are_never_merged_into_a_bare_certified_string() -> None:
    for e_de, b in [(Q(1, 10 ** 10), Q(5)), (Q(2), Q(5)), (Q(1, 2), Q(5))]:
        assert D.evaluate_domain(e_de * DE, b, boundary={}).evidence in (
            "formal_certified", "numerical_validated", "unsupported")


# --- the boundary search logic (fake probes) ------------------------------------------------------------------

BO = Q(10)          # side limits: minus 0.99, plus b_max / 10 - 1 ~ 0.42


def _probe(fail_below, unknown=(), calls=None):
    def p(e, bo, rho):
        if calls is not None:
            calls.append(rho)
        a = abs(float(rho))
        if any(lo <= a <= hi for lo, hi in unknown):
            return {"status": "audit_fail", "reason": "fake"}
        return {"status": "ok", "e40": 1e-3 if a < fail_below else 1e-6}
    return p


def test_search_brackets_a_monotone_boundary_as_an_interval() -> None:
    s = B.search_side(Q(1, 2), BO, -1, _probe(2.3e-4))
    assert s["status"] == "ok"
    assert s["largest_nonpass"] < 2.3e-4 <= s["smallest_pass"]
    assert s["smallest_pass"] / s["largest_nonpass"] <= B.BISECT_RATIO
    assert s["largest_fail"] == s["largest_nonpass"]


def test_unknown_probes_push_the_boundary_outward_never_inward() -> None:
    s = B.search_side(Q(1, 2), BO, 1, _probe(1e-5, unknown=[(5e-5, 4e-4)]))
    assert s["status"] == "ok" and s["unknown_probes"] > 0
    assert s["smallest_pass"] > 4e-4                 # the unknown stretch stays on the unsupported side
    assert s["largest_fail"] < 1e-5


def test_no_pass_anywhere_on_the_side_invents_no_boundary() -> None:
    calls = []
    s = B.search_side(Q(1, 2), BO, 1, _probe(10.0, calls=calls), )
    assert s["status"] == "no_pass_found" and s["smallest_pass"] is None
    assert max(abs(float(c)) for c in calls) == float(B.side_limit(BO, 1))   # expanded to the physical limit


def test_a_pass_inside_a_fail_is_reported_as_non_monotone() -> None:
    def p(e, bo, rho):
        a = abs(float(rho))
        ok = a >= 1e-3 or 2e-5 <= a <= 5e-5          # an island of passes inside the failing band
        return {"status": "ok", "e40": 1e-6 if ok else 1e-3}
    s = B.search_side(Q(1, 2), BO, -1, p)
    assert s["status"] == "non_monotone"
