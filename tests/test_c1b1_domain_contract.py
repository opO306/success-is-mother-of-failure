"""D_valid c1b1-dvalid-v2 and its new_run connection (designer verdicts on the boundary record 50cceaa and on 8ce0c0a),
plus the boundary-search logic (fake probes).

Integration: new_run -> run.validation on real initial states. Energy identity is EXACT: only the canonical lattice
states of the measurement's own constructor are identified (no energy tolerance). Fault injection: each fixture
mutation the designer named (one boundary step moved, +/- sides swapped, an unmeasured energy inserted, a corrupted
file, a side deleted) and more must make new_run's verdict "unsupported" -- through the frozen hash AND through the
structural checks alone (hash disabled). Since v2 the sides name themselves and the probes carry signed rho, so a +/-
swap is refused by the contract itself, not only by the hash. Validation never changes the dynamics (direct test)."""
from __future__ import annotations

import json
from fractions import Fraction as Q

import mpmath
import pytest

import a_reference.c1b1_domain_contract as D
import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_dt_study as S
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
    b = bo * Q(995, 1000)
    p = _v(HALF, b)["provenance"]
    assert p["dvalid_version"] == D.DVALID_VERSION == "c1b1-dvalid-v2" and p["scope"] == "initial_state"
    assert p["fixture_sha256"] == D.FROZEN_BOUNDARY_SHA256
    assert p["energy"] == "1/2" and p["verdict"] == "numerical_validated"
    s, = p["sides"]
    assert s["side"] == "delta_minus" and s["sign"] == "negative"
    assert s["largest_nonpass"] < s["smallest_pass"] <= 0.005 <= s["outermost_pass"]
    assert p["profile"] == {"position": "FX(96,48)", "momentum": "FX(96,80)", "dt": "40", "drift": "v2"}
    c = p["canonical_state"]
    assert c["energy_id"] == "1/2" and Q(c["b_nominal_bohr"][0]) <= b <= Q(c["b_nominal_bohr"][1])
    assert all(abs(x) < 2.0 ** -70 for x in c["realized_minus_nominal_rel"])      # recorded, not used as a tolerance
    assert p["e_rel_De"] == ["1/2", "1/2"]                                         # judged at the nominal energy_id


def test_unmeasured_energies_and_other_profiles_are_unsupported(bo) -> None:
    v = _v(Q(2, 5), Q(10))
    assert v["validation_status"] == "unsupported" and v["in_capture_band"] is None and "not identified" in v["reason"]
    v = _v(HALF, bo * Q(995, 1000), mom=FixedPoint(128, 112))
    assert v["validation_status"] == "unsupported" and "profile" in v["reason"]


def test_outside_capture_and_d_base() -> None:
    assert _v(Q(2), Q(5))["validation_status"] == "numerical_validated"            # above every barrier top
    assert _v(Q(1, 20), Q(5))["validation_status"] == "numerical_validated"        # b_orb > b_max
    assert D.evaluate_domain(Q(1, 10 ** 10) * DE, Q(5)).evidence == "unsupported"  # below E_LOW
    assert D.evaluate_domain(Q(11) * DE, Q(5)).evidence == "unsupported"           # above 10 De
    assert D.evaluate_domain(-DE / 2, Q(0)).evidence == "unsupported"              # bound: no bound-state D_valid yet


def _atoms(ri, rj, pj):
    return (C.Atom("Ar40", tuple(I.POS.from_exact(x) for x in ri), tuple(I.MOM.from_exact(-x) for x in pj)),
            C.Atom("Ar40", tuple(I.POS.from_exact(x) for x in rj), tuple(I.MOM.from_exact(x) for x in pj)))


def test_energy_identity_is_the_exact_canonical_state_not_a_tolerance(bo) -> None:
    """v1 matched |E - E_nom| <= 2^-80 E_nom; v2 has no energy tolerance at all: a state is at a fixture energy only if
    it IS a lattice state of the measurement's constructor. The same relative state translated was inside v1's
    tolerance and is now unsupported; a momentum 4 grid units off the constructor is not identified."""
    assert not hasattr(D, "E_MATCH_REL")
    b = bo * Q(995, 1000)
    st = I.state(HALF, b)
    assert D.canonical_member(I.POS, I.MOM, _atoms(st["r_i"], st["r_j"], st["p_j"]))[0] == "1/2"
    shift = (Q(1), Q(0), Q(0))
    ri, rj = (tuple(x + y for x, y in zip(r, shift)) for r in (st["r_i"], st["r_j"]))
    assert D.canonical_member(I.POS, I.MOM, _atoms(ri, rj, st["p_j"])) is None     # translated: not the measured state
    v = C.new_run(I.POS, 40, ri, st["p_i"], rj, st["p_j"], momentum_profile=I.MOM).validation
    assert v["validation_status"] == "unsupported" and "not identified" in v["reason"]
    assert v["provenance"]["canonical_state"] is None
    nudged = (st["p_j"][0] - 4 * D.MOM_ULP,) + st["p_j"][1:]
    assert D.canonical_b_range("1/2", nudged) is None
    assert D.evaluate_domain(HALF * DE, b).evidence == "numerical_validated"        # nominal point: exact energy_id
    assert D.evaluate_domain(HALF * DE * (1 + Q(1, 2 ** 100)), b).evidence == "unsupported"   # any other value: no


def test_every_recorded_probe_state_is_the_constructor_output() -> None:
    """The fixture's lattice states are what state(e, b_orb (1 + rho)) builds (sampled: every probe of two energies and
    the first probe of every other side); the load check verifies canonicity of ALL probes."""
    doc = json.loads(D.BOUNDARY_FIXTURE.read_text(encoding="utf-8"))
    for row in doc["energies"]:
        bo_e = Q(row["b_orb"])
        for name in ("delta_minus", "delta_plus"):
            probes = row[name]["probes"] if row["e"] in ("3/20", "99/100") else row[name]["probes"][:1]
            for p in probes:
                st = I.state(Q(row["e"]), bo_e * (1 + Q(p["rho"])))
                assert p["p_j_raw"] == [str(I.MOM.from_exact(x)) for x in st["p_j"]], (row["e"], name, p["rho"])


MEASURED = ("abs_rho", "status", "e40_sweep_rad", "pass", "reason")
SIDE_SUMMARY = ("status", "side_limit", "largest_fail", "largest_nonpass", "smallest_pass", "unknown_probes")


def test_v2_record_reproduces_the_50cceaa_measurement_probe_by_probe() -> None:
    """The v3-format record was regenerated (new fields only); every energy, b_orb, side summary and probe measurement
    (|rho|, status, sweep error, pass, order) equals the v1 record of 50cceaa, and every v2 side names itself."""
    fx = D.BOUNDARY_FIXTURE.parent
    old = json.loads((fx / "c1b1_orbit_boundary_v1.json").read_text(encoding="utf-8"))
    new = json.loads(D.BOUNDARY_FIXTURE.read_text(encoding="utf-8"))
    for k in ("status", "contract", "target_sweep_rad", "scan_abs_rho", "bisect_ratio", "b_max"):
        assert new[k] == old[k], k
    assert [r["e"] for r in new["energies"]] == [r["e"] for r in old["energies"]]
    for ro, rn in zip(old["energies"], new["energies"]):
        assert (rn["b_orb"], rn["R_star"]) == (ro["b_orb"], ro["R_star"])
        for name, label, sign in (("delta_minus", "negative", -1), ("delta_plus", "positive", 1)):
            so, sn = ro[name], rn[name]
            assert sn["side"] == label
            assert {k: sn.get(k) for k in SIDE_SUMMARY} == {k: so.get(k) for k in SIDE_SUMMARY}, (ro["e"], name)
            assert [{k: p.get(k) for k in MEASURED} for p in sn["probes"]] == \
                   [{k: p.get(k) for k in MEASURED} for p in so["probes"]], (ro["e"], name)
            assert all(float(Q(p["rho"])) == sign * p["abs_rho"] for p in sn["probes"])


def test_state_uses_local_precision_only() -> None:
    """state() used to set the global mpmath precision to 60 (and reference_task to 40), leaking it to later callers."""
    ref = None
    for dps in (15, 40, 100):
        mpmath.mp.dps = dps
        try:
            st = I.state(HALF, Q(10))
            assert mpmath.mp.dps == dps
        finally:
            mpmath.mp.dps = 40
        key = (st["p_j"], st["E_rep"], st["L_nom"])
        assert ref is None or key == ref, dps
        ref = key


def test_orbiting_does_not_depend_on_the_global_mpmath_precision() -> None:
    """Regression: b_orb used to be rounded at the caller's global precision (40, or 60 after state()). Internal work
    at ORBIT_WORK_DPS, canonical value at ORBIT_CANONICAL_DPS -- separate, both local."""
    assert (I.ORBIT_WORK_DPS, I.ORBIT_CANONICAL_DPS) == (60, 40)
    ref = str(I.orbiting(Q(3, 20))[0])
    for dps in (15, 60, 100):
        with mpmath.workdps(dps):
            assert str(I.orbiting(Q(3, 20))[0]) == ref, dps
    with mpmath.workdps(60):
        x = mpmath.sqrt(mpmath.mpf(2))
    with mpmath.workprec(136):                                                     # 40 dps = 136 bits, nearest
        want = S.mq(+x)
    assert I.canonical_b_orb(x) == want


# --- validation never changes the dynamics ---------------------------------------------------------------------

def test_validation_does_not_change_the_dynamics(bo, monkeypatch) -> None:
    """The same initial state run with run.validation read (before, and in the middle of, the run -- also with a
    fixture that fails to load) and never read: identical final state, impulse cache, step count and full run_case
    result (status, exit momentum, energy / angular momentum / momentum drift)."""
    st = I.state(HALF, bo * Q(995, 1000))

    def fresh():
        return C.new_run(I.POS, 40, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=I.MOM)

    silent, read = fresh(), fresh()
    assert silent._validation is None
    assert read.validation["validation_status"] == "numerical_validated"
    for n in range(12):
        C.step(silent)
        C.step(read)
        if n == 5:
            assert read.validation["provenance"]["scope"] == "initial_state"
    assert silent._validation is None
    assert (silent.atoms, silent.J_cache, silent.t_steps) == (read.atoms, read.J_cache, read.t_steps)
    assert silent == read                                            # the validation field is compare=False

    I._register()
    real = C.new_run

    def result(eager: bool):
        def new_run(*a, **k):
            run = real(*a, **k)
            if eager:
                assert run.validation["validation_status"] in ("numerical_validated", "unsupported")
            return run
        monkeypatch.setattr(C, "new_run", new_run)
        try:
            r = S.run_case(({"kind": "scatter", "name": "independence"}, st, 40, "cand", 40))
        finally:
            monkeypatch.setattr(C, "new_run", real)
        r.pop("seconds")
        return r
    base = result(False)
    assert base["steps"] == 40 and base == result(True)
    monkeypatch.setattr(D, "BOUNDARY_FIXTURE", D.BOUNDARY_FIXTURE.with_name("missing.json"))
    assert base == result(True)                                      # an unsupported verdict changes nothing either


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


def _swap_relabelled(doc):      # a swap that also rewrites the side labels: the probes' signed rho still refuse it
    _swap(doc)
    r = _row(doc)
    r["delta_minus"]["side"], r["delta_plus"]["side"] = "negative", "positive"


def _swap_resigned(doc):        # ... and flips every probe's sign too: the lattice states no longer match (e, rho)
    _swap_relabelled(doc)
    for name in ("delta_minus", "delta_plus"):
        for p in _row(doc)[name]["probes"]:
            p["rho"] = str(-Q(p["rho"]))


def _lattice(doc):              # a probe's recorded lattice state moved by 4 grid units
    p = _row(doc)["delta_minus"]["probes"][0]
    p["p_j_raw"][0] = str(int(p["p_j_raw"][0]) - 4)


def _no_lattice(doc):
    del _row(doc)["delta_plus"]["probes"][0]["p_j_raw"]


def _spec(doc):
    doc["canonical_state"]["R_start"] = "25"


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


MUTATIONS = {"shift": _shift, "swap": _swap, "swap_relabelled": _swap_relabelled, "swap_resigned": _swap_resigned,
             "insert": _insert, "delete_side": _delete_side, "reverse": _reverse, "duplicate": _duplicate,
             "unknown_status": _unknown_status, "certified_status": _certified, "lattice": _lattice,
             "no_lattice": _no_lattice, "canonical_spec": _spec}


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
