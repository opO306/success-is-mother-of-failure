"""D_valid c1b1-dvalid-v1 and its new_run connection (designer verdict on the boundary record 50cceaa), plus the
boundary-search logic (fake probes).

Integration: new_run -> run.validation on real initial states. Fault injection: each fixture mutation the designer
named (one boundary step moved, +/- sides swapped, an unmeasured energy inserted, a corrupted file, a side deleted) and
a few more must make new_run's verdict "unsupported" -- through the frozen hash AND, where the mutation is visible in
the data, through the structural checks alone (hash disabled). A side swap is the one mutation only the hash can see:
the fixture's sides carry |rho| only, so a swapped pair is internally consistent (recorded here, not hidden)."""
from __future__ import annotations

import json
from fractions import Fraction as Q

import mpmath
import pytest

import a_reference.c1b1_domain_contract as D
import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_orbit_boundary as B
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

DE = I.S.DE_GRID
HALF = Q(1, 2)


def _run(e, b, mom=None):
    st = I.state(e, b)
    return C.new_run(I.POS, 40, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=mom or I.MOM)


@pytest.fixture(scope="module")
def bo():
    return I.orbiting(HALF)[0]


def _v(e, b, mom=None):
    return _run(e, b, mom).validation


# --- the frozen contract on real initial states -----------------------------------------------------------------

def test_new_run_carries_the_verdict_for_every_region(bo) -> None:
    expect = {Q(5, 1000): ("numerical_validated", "validated"), Q(-5, 1000): ("numerical_validated", "validated"),
              Q(-5, 10000): ("unsupported", "inside_band"), Q(-13, 10000): ("unsupported", "uncertain_edge"),
              Q(6, 10000): ("unsupported", "uncertain_edge"), Q(-1, 5): ("unsupported", "beyond_probes")}
    for rho, (status, region) in expect.items():
        v = _v(HALF, bo * (1 + rho))
        assert v["validation_status"] == status, (rho, v["reason"])
        assert [s["region"] for s in v["provenance"]["sides"]] == [region], rho


def test_provenance_names_fixture_energy_side_interval_and_verdict(bo) -> None:
    p = _v(HALF, bo * Q(995, 1000))["provenance"]
    assert p["dvalid_version"] == D.DVALID_VERSION and p["fixture_sha256"] == D.FROZEN_BOUNDARY_SHA256
    assert p["energy"] == "1/2" and p["verdict"] == "numerical_validated"
    s, = p["sides"]
    assert s["side"] == "delta_minus" and s["largest_nonpass"] < s["smallest_pass"] <= 0.005 <= s["outermost_pass"]
    assert p["profile"] == {"position": "FX(96,48)", "momentum": "FX(96,80)", "dt": "40", "drift": "v2"}


def test_unmeasured_energies_and_other_profiles_are_unsupported(bo) -> None:
    v = _v(Q(2, 5), Q(10))
    assert v["validation_status"] == "unsupported" and v["in_capture_band"] is None and "not a measured" in v["reason"]
    v = _v(HALF, bo * Q(995, 1000), mom=FixedPoint(128, 112))
    assert v["validation_status"] == "unsupported" and "profile" in v["reason"]


def test_outside_capture_and_d_base() -> None:
    assert _v(Q(2), Q(5))["validation_status"] == "numerical_validated"            # above every barrier top
    assert _v(Q(1, 20), Q(5))["validation_status"] == "numerical_validated"        # b_orb > b_max
    assert D.evaluate_domain(Q(1, 10 ** 10) * DE, Q(5)).evidence == "unsupported"  # below E_LOW
    assert D.evaluate_domain(Q(11) * DE, Q(5)).evidence == "unsupported"           # above 10 De
    assert D.evaluate_domain(-DE / 2, Q(0)).evidence == "unsupported"              # bound: no bound-state D_valid yet


def test_energy_match_tolerance_is_derived_and_covers_the_measured_states() -> None:
    """E_MATCH_REL is the FX(96,80) momentum-rounding resolution of the measurement's own states (2^-80), not a
    neighbourhood; the states the measurement actually ran deviate by at most ~3.7e-25."""
    assert D.E_MATCH_REL == Q(1, 2 ** 80)
    for e in (Q(3, 20), HALF):
        st = I.state(e, I.orbiting(e)[0] * Q(99, 100))
        assert abs(st["E_rep"] / (e * DE) - 1) <= D.E_MATCH_REL
    assert D.evaluate_domain(HALF * DE * (1 + 4 * D.E_MATCH_REL), I.orbiting(HALF)[0] * Q(995, 1000)).evidence \
        == "unsupported"                                                               # just outside: not substituted


def test_orbiting_does_not_depend_on_the_global_mpmath_precision() -> None:
    """Regression: b_orb used to be rounded at the caller's global precision (40, or 60 after state())."""
    ref = str(I.orbiting(Q(3, 20))[0])
    for dps in (15, 60, 100):
        with mpmath.workdps(dps):
            assert str(I.orbiting(Q(3, 20))[0]) == ref, dps


# --- fault injection: every mutation must end unsupported ------------------------------------------------------

def _doc():
    return json.loads(D.BOUNDARY_FIXTURE.read_text(encoding="utf-8"))


def _row(doc, e="1/2"):
    return next(r for r in doc["energies"] if r["e"] == e)


def _shift(doc):          # one boundary step inward: the old largest non-pass becomes the smallest pass
    s = _row(doc)["delta_minus"]
    s["smallest_pass"] = s["largest_nonpass"]


def _swap(doc):
    r = _row(doc)
    r["delta_minus"], r["delta_plus"] = r["delta_plus"], r["delta_minus"]


def _insert(doc):
    r = json.loads(json.dumps(_row(doc)))
    r["e"] = "2/5"
    doc["energies"].append(r)


def _delete_side(doc):
    del _row(doc)["delta_minus"]


def _reverse(doc):
    s = _row(doc)["delta_minus"]
    s["largest_nonpass"], s["smallest_pass"] = s["smallest_pass"], s["largest_nonpass"]


def _duplicate(doc):
    doc["energies"].append(json.loads(json.dumps(_row(doc))))


def _unknown_status(doc):
    _row(doc)["delta_minus"]["status"] = "probably_fine"


def _certified(doc):
    doc["status"] = "CERTIFIED"


MUTATIONS = {"shift": _shift, "swap": _swap, "insert": _insert, "delete_side": _delete_side, "reverse": _reverse,
             "duplicate": _duplicate, "unknown_status": _unknown_status, "certified_status": _certified}
HASH_ONLY = {"swap"}


def _write(tmp_path, name, doc=None, raw=None):
    p = tmp_path / f"{name}.json"
    if raw is not None:
        p.write_bytes(raw)
    else:
        p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return p


def test_injection_control_an_unmutated_copy_validates(tmp_path, monkeypatch, bo) -> None:
    p = _write(tmp_path, "control", raw=D.BOUNDARY_FIXTURE.read_bytes())
    monkeypatch.setattr(D, "BOUNDARY_FIXTURE", p)
    assert _v(HALF, bo * Q(995, 1000))["validation_status"] == "numerical_validated"


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_every_fixture_mutation_is_refused_by_new_run(name, tmp_path, monkeypatch, bo) -> None:
    doc = _doc()
    MUTATIONS[name](doc)
    p = _write(tmp_path, name, doc)
    monkeypatch.setattr(D, "BOUNDARY_FIXTURE", p)
    for rho in (Q(-5, 1000), Q(5, 1000)):
        v = _v(HALF, bo * (1 + rho))
        assert v["validation_status"] == "unsupported" and "fixture" in v["reason"], (name, rho)
    structural = D.evaluate_domain(HALF * DE, bo * Q(995, 1000), path=p, expected_sha=None)
    if name in HASH_ONLY:
        assert structural.evidence == "numerical_validated"   # visible to the hash only (see module doc)
    else:
        assert structural.evidence == "unsupported" and "fixture rejected" in structural.reason, name


def test_corrupted_and_missing_fixture_are_refused(tmp_path, monkeypatch, bo) -> None:
    raw = D.BOUNDARY_FIXTURE.read_bytes()
    p = _write(tmp_path, "corrupt", raw=raw[: len(raw) // 2])
    assert D.evaluate_domain(HALF * DE, bo * Q(995, 1000), path=p, expected_sha=None).evidence == "unsupported"
    monkeypatch.setattr(D, "BOUNDARY_FIXTURE", p)
    assert _v(HALF, bo * Q(995, 1000))["validation_status"] == "unsupported"
    monkeypatch.setattr(D, "BOUNDARY_FIXTURE", tmp_path / "missing.json")
    v = _v(Q(2), Q(5))
    assert v["validation_status"] == "unsupported" and "unreadable" in v["reason"]     # even outside the capture range


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
    s = B.search_side(HALF, BO, -1, _probe(2.3e-4))
    assert s["status"] == "ok"
    assert s["largest_nonpass"] < 2.3e-4 <= s["smallest_pass"]
    assert s["smallest_pass"] / s["largest_nonpass"] <= B.BISECT_RATIO
    assert s["largest_fail"] == s["largest_nonpass"]


def test_unknown_probes_push_the_boundary_outward_never_inward() -> None:
    s = B.search_side(HALF, BO, 1, _probe(1e-5, unknown=[(5e-5, 4e-4)]))
    assert s["status"] == "ok" and s["unknown_probes"] > 0
    assert s["smallest_pass"] > 4e-4
    assert s["largest_fail"] < 1e-5


def test_no_pass_anywhere_on_the_side_invents_no_boundary() -> None:
    calls = []
    s = B.search_side(HALF, BO, 1, _probe(10.0, calls=calls))
    assert s["status"] == "no_pass_found" and s["smallest_pass"] is None
    assert max(abs(float(c)) for c in calls) == float(B.side_limit(BO, 1))


def test_a_pass_inside_a_fail_is_reported_as_non_monotone() -> None:
    def p(e, bo, rho):
        a = abs(float(rho))
        ok = a >= 1e-3 or 2e-5 <= a <= 5e-5
        return {"status": "ok", "e40": 1e-6 if ok else 1e-3}
    assert B.search_side(HALF, BO, -1, p)["status"] == "non_monotone"
