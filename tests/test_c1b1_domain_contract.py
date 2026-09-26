"""D_valid machine-readable contract (designer verdict on section 22, item 3; item 1 asymmetric delta refinement).

Pure-logic tests only: `evaluate_domain`/`report` never raise and never block computation (designer: "new_run은
계산을 금지하지 않습니다"). The boundary fixture (c1b1_orbit_boundary_v1.json, from a_reference.c1b1_orbit_boundary
run on the Vast remote node) is NOT required to exist for these tests -- absence just means every capture-range
point classifies "unsupported" rather than "numerical_validated" (never invented, never interpolated)."""
from __future__ import annotations

from fractions import Fraction as Q

import a_reference.c1b1_domain_contract as D
import a_reference.c1b1_inner_validation as I


def test_below_e_low_is_unsupported_not_rejected() -> None:
    v = D.evaluate_domain(Q(1, 10 ** 10) * I.S.DE_GRID, Q(5))
    assert v.in_base is False and v.evidence == "unsupported"
    r = D.report(Q(1, 10 ** 10) * I.S.DE_GRID, Q(5))
    assert r["validation_status"] == "unsupported" and "E_low" not in r  # never raises, always a dict


def test_beyond_b_max_is_unsupported() -> None:
    v = D.evaluate_domain(I.S.DE_GRID, D.B_MAX * 2)
    assert v.in_base is False and v.evidence == "unsupported"


def test_above_e_max_has_no_capture_band_and_is_validated() -> None:
    # E = 2 De is above the potential's orbiting maximum (~0.9964 De): no capture band exists at all.
    v = D.evaluate_domain(Q(2) * I.S.DE_GRID, Q(5))
    assert v.in_base and v.in_capture_band is False and v.evidence == "numerical_validated"


def test_capture_exists_but_energy_unmeasured_never_interpolates() -> None:
    """Without a boundary-fixture row for this exact energy, the point must not be silently declared validated
    just because it lies far from b_orb by a coarse margin, nor silently declared invalid -- it must say why."""
    bo, _ = I.orbiting(Q(1, 2))
    v = D.evaluate_domain(Q(1, 2) * I.S.DE_GRID, bo, boundary={})   # exactly at b_orb, no fixture row
    assert v.in_base and v.in_capture_band is None
    assert "not measured" in v.reason


def test_measured_boundary_row_classifies_inside_and_outside_the_band() -> None:
    bo, _ = I.orbiting(Q(15, 100))
    e_de = "3/20"
    fake_boundary = {e_de: {"delta_minus": {"delta": 1e-4}, "delta_plus": {"delta": 2e-4}}}
    inside = D.evaluate_domain(Q(15, 100) * I.S.DE_GRID, bo, boundary=fake_boundary)
    assert inside.in_capture_band is True and inside.evidence == "unsupported"
    outside = D.evaluate_domain(Q(15, 100) * I.S.DE_GRID, bo * Q(99, 100), boundary=fake_boundary)
    assert outside.in_capture_band is False and outside.evidence == "numerical_validated"


def test_evidence_levels_are_never_merged_into_a_bare_certified_string() -> None:
    for e_de, b in [(Q(1, 10 ** 10), Q(5)), (Q(2), Q(5))]:
        v = D.evaluate_domain(e_de * I.S.DE_GRID, b)
        assert v.evidence in ("formal_certified", "numerical_validated", "unsupported")
        assert v.evidence != "certified"        # the merged word the designer explicitly forbade
