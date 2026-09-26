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

import a_reference.c1b1_boundary_compare as X
import a_reference.c1b1_canonical_state as G
import a_reference.c1b1_domain_contract as D
import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_dt_study as S
import a_reference.c1b1_orbit_boundary as B
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

DE = I.S.DE_GRID
HALF = Q(1, 2)


def _run(e, b, mom=None):
    st = D.canonical_initial_state(str(e), b)          # a state D_valid identifies: state(E, b_current) of its own b
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
    assert c["energy_id"] == c["nominal_energy_De"] == "1/2" and "b_current" in c["rule"]
    b_lo, b_hi = Q(c["b_current_bohr"][0]), Q(c["b_current_bohr"][1])
    assert b_hi - b_lo < Q(1, 2 ** 250) and abs(b_lo / b - 1) < Q(1, 2 ** 70)   # one b: the state's own, not a range
    assert Q(c["rho_current"][0]) == b_lo / bo - 1
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
    it IS state(E_nominal, b_current) of its own b. The same relative state translated was inside v1's tolerance and is
    now unsupported; a momentum 4 grid units off the generator is not identified."""
    assert not hasattr(D, "E_MATCH_REL")
    b = bo * Q(995, 1000)
    st = D.canonical_initial_state("1/2", b)
    assert D.canonical_member(I.POS, I.MOM, _atoms(st["r_i"], st["r_j"], st["p_j"]))[0] == "1/2"
    shift = (Q(1), Q(0), Q(0))
    ri, rj = (tuple(x + y for x, y in zip(r, shift)) for r in (st["r_i"], st["r_j"]))
    assert D.canonical_member(I.POS, I.MOM, _atoms(ri, rj, st["p_j"])) is None     # translated: not the measured state
    v = C.new_run(I.POS, 40, ri, st["p_i"], rj, st["p_j"], momentum_profile=I.MOM).validation
    assert v["validation_status"] == "unsupported" and "not identified" in v["reason"]
    assert v["provenance"]["canonical_state"] is None
    nudged = (st["p_j"][0] - 4 * D.MOM_ULP,) + st["p_j"][1:]
    assert D.canonical_member(I.POS, I.MOM, _atoms(st["r_i"], st["r_j"], nudged)) is None
    assert D.evaluate_domain(HALF * DE, b).evidence == "numerical_validated"        # nominal point: exact energy_id
    assert D.evaluate_domain(HALF * DE * (1 + Q(1, 2 ** 100)), b).evidence == "unsupported"   # any other value: no


def _state_atoms(pj):
    half = I.R_START / 2
    return _atoms((-half, Q(0), Q(0)), (half, Q(0), Q(0)), pj)


def _history(name):
    return json.loads((D.BOUNDARY_FIXTURE.parent / name).read_text(encoding="utf-8"))


def test_a_momentum_from_another_b_is_refused() -> None:
    """Designer's fault test: a state whose momentum another b produced but which is not
    canonical_initial_state(E, b_current) of the b it represents must be unsupported.
    (a) real cases: the retired constructor (Pr from the UNROUNDED Pt) made 32 of the 181 states of the historical v2
        record; each was built at its recorded b2 but regenerates to another Pr at its own b_current -- all refused,
        among them the E = 0.15 De negative-side smallest_pass probe of that record;
    (b) splice: the stored Pt of a state at b1 with the Pr the generator makes at b2 (another Pt cell) -- refused."""
    old = _history("c1b1_orbit_boundary_v2.json")
    refused, identified = [], 0
    for row in old["energies"]:
        for name in ("delta_minus", "delta_plus"):
            for p in row[name]["probes"]:
                pj = tuple(Q(int(x)) * D.MOM_ULP for x in p["p_j_raw"])
                m = D.canonical_member(I.POS, I.MOM, _state_atoms(pj))
                if m is None:
                    refused.append((row["e"], name, p["rho"], row[name]["smallest_pass"] == p["abs_rho"]))
                    assert G.radial_momentum(row["e"], pj[1]) != pj[0]      # its own b_current regenerates another Pr
                else:
                    identified += 1
    assert (identified, len(refused)) == (149, 32)
    assert ("3/20", "delta_minus", "-12207620611/50000000000000", True) in refused
    e, name, rho, _ = refused[0]
    row = next(r for r in old["energies"] if r["e"] == e)
    pj = tuple(Q(int(x)) * D.MOM_ULP for x in next(p for p in row[name]["probes"] if p["rho"] == rho)["p_j_raw"])
    v = C.new_run(I.POS, 40, (-10, 0, 0), tuple(-x for x in pj), (10, 0, 0), pj, momentum_profile=I.MOM).validation
    assert v["validation_status"] == "unsupported" and "not identified" in v["reason"]

    bo = I.orbiting(HALF)[0]
    s1 = D.canonical_initial_state("1/2", bo * Q(995, 1000))
    spliced = 0
    for k in range(1, 40):
        s2 = D.canonical_initial_state("1/2", bo * Q(995, 1000) * (1 + k * Q(1, 10 ** 24)))
        if s2["p_j"][1] != s1["p_j"][1] and s2["p_j"][0] != s1["p_j"][0]:
            pj = (s2["p_j"][0], s1["p_j"][1], Q(0))                   # b1's Pt, b2's Pr
            assert D.canonical_member(I.POS, I.MOM, _state_atoms(pj)) is None
            spliced += 1
    assert spliced > 0


def test_different_b_collapsing_to_one_quantized_state_is_one_state(bo) -> None:
    """Two different input b that quantize to the SAME state are the same state: same verdict, same b_current / rho in
    the provenance (the b recorded is the state's own, never the input that happened to build it)."""
    b1 = bo * Q(995, 1000)
    b2 = b1 * (1 + Q(1, 10 ** 26))                        # far below one grid unit of Pt
    s1, s2 = D.canonical_initial_state("1/2", b1), D.canonical_initial_state("1/2", b2)
    assert b1 != b2 and s1 == s2
    v1, v2 = _v(HALF, b1), _v(HALF, b2)
    assert v1["validation_status"] == v2["validation_status"] == "numerical_validated"
    c1, c2 = v1["provenance"]["canonical_state"], v2["provenance"]["canonical_state"]
    assert c1["b_current_bohr"] == c2["b_current_bohr"] and c1["rho_current"] == c2["rho_current"]


def test_measured_states_are_exactly_the_identified_states() -> None:
    """"측정한 상태 = 인정하는 상태": every probe of the frozen record is the generator's output at its recorded b AND is
    identified by canonical_member at its own b_current (the energy it was measured at) -- all of them, no exception."""
    doc = json.loads(D.BOUNDARY_FIXTURE.read_text(encoding="utf-8"))
    assert doc["canonical_state"] == G.SPEC and doc["format"] == "c1b1-orbit-boundary-v4"
    n = 0
    for row in doc["energies"]:
        bo_e = Q(row["b_orb"])
        for name in ("delta_minus", "delta_plus"):
            for p in row[name]["probes"]:
                st = G.canonical_initial_state(row["e"], bo_e * (1 + Q(p["rho"])))
                assert p["p_j_raw"] == [str(I.MOM.from_exact(x)) for x in st["p_j"]], (row["e"], name, p["rho"])
                m = D.canonical_member(I.POS, I.MOM, _state_atoms(st["p_j"]))
                assert m is not None and m[0] == row["e"], (row["e"], name, p["rho"])
                n += 1
    assert n == sum(len(r[k]["probes"]) for r in doc["energies"] for k in ("delta_minus", "delta_plus"))


def test_historical_records_are_refused_by_the_contract(bo) -> None:
    """The v1 (50cceaa) and v2 (30c14b7) records stay as history; the contract accepts neither (format and generator)."""
    for name in ("c1b1_orbit_boundary_v1.json", "c1b1_orbit_boundary_v2.json"):
        v = D.evaluate_domain(HALF * DE, bo * Q(995, 1000), path=D.BOUNDARY_FIXTURE.parent / name, expected_sha=None)
        assert v.evidence == "unsupported" and "fixture rejected" in v.reason and "format" in v.reason, name


def test_boundary_change_against_50cceaa_is_recorded() -> None:
    """The re-measured boundaries against the 50cceaa record, per side: largest_nonpass, smallest_pass, outermost pass,
    monotonicity -- the recorded comparison must equal the one recomputed from the two records."""
    got = X.compare_records(_history("c1b1_orbit_boundary_v1.json"),
                            json.loads(D.BOUNDARY_FIXTURE.read_text(encoding="utf-8")))
    assert got == _history("c1b1_orbit_boundary_v3_vs_v1.json")["sides"]


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
    st = D.canonical_initial_state("1/2", bo * Q(995, 1000))

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


def _old_generator(doc):        # one probe's state replaced by the retired constructor's (one Pr grid unit off)
    hist = _history("c1b1_orbit_boundary_v2.json")
    for rn, ro in zip(doc["energies"], hist["energies"]):
        for name in ("delta_minus", "delta_plus"):
            for pn, po in zip(rn[name]["probes"], ro[name]["probes"]):
                if pn["p_j_raw"] != po["p_j_raw"]:
                    pn["p_j_raw"] = po["p_j_raw"]
                    return
    raise AssertionError("no probe differs between the two generators")


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
             "no_lattice": _no_lattice, "canonical_spec": _spec, "old_generator_state": _old_generator}


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
