"""C1-B1 reference layer (designer 11th ed.): two 40Ar atoms, exact pair geometry, direct impulse, KDK.

docs/current/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md (contract section). The reference DEFINES the
dynamics; these tests check it against the frozen C1-A fixture, the independent audit (needs D:\\reference),
the symmetry requirements of D10 and the refusal rules. Tests needing the published files skip without them.
"""
from __future__ import annotations

import hashlib
from fractions import Fraction as Q

import mpmath
import pytest

import a_reference.ar2_lang2024 as L
import a_reference.ar2_lang2024_fixture as X
import a_reference.c1b1_two_atom as C
from a_numeric import Binary64Finite, FixedPoint

B64, FX, HP = Binary64Finite(), FixedPoint(64, 32), FixedPoint(256, 192)
HAVE_DATA = all((X.DATA / f).exists() for f in X.SOURCE_FILES)
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="published Lang 2024 files not on D:\\reference")


def G(x) -> Q:
    return FX.to_exact(FX.from_exact(Q(x)))


RI, RJ = (G(-4.1), G(-0.7), G(0.3)), (G(4.3), G(0.9), G(-0.2))
PJ = (G(-3.1), G(0.8), G(0.25))
PI = tuple(-x for x in PJ)


def trajectory(prof, ri, pi, rj, pj, n=120, dt=40):
    run = C.new_run(prof, dt, ri, pi, rj, pj)
    out = []
    for _ in range(n):
        C.step(run)
        out.append((run.atoms[0].r, run.atoms[0].p, run.atoms[1].r, run.atoms[1].p))
    return run, out


# --- contract ------------------------------------------------------------------------------------------------

def test_species_and_contract_constants() -> None:
    assert C.CONTRACT_VERSION == "c1b1-two-atom-v2"
    assert C.AR40_MASS_U == Q("39.9623831237") and C.ELECTRON_MASS_U == Q("5.485799090441e-4")
    assert C.AR40_MASS_ME == Q("39.9623831237") / Q("5.485799090441e-4")          # nominal values only
    assert "(24)" in C.AR40_MASS_U_UNCERTAINTY and "(97)" in C.ELECTRON_MASS_U_UNCERTAINTY
    assert "NIST" in C.MASS_SOURCES and "CODATA 2022" in C.MASS_SOURCES
    assert C.FROZEN_C1A_FINGERPRINT == L.parameter_fingerprint()
    assert C.R_MIN2 == (Q("1.2") / Q("0.529177210903")) ** 2
    assert L.WORLD_RETARDATION is True


def test_algebraic_input_extension_reproduces_the_frozen_c1a_bits() -> None:
    """With R^2 a perfect square the new sqrt(R^2) evaluator must give exactly the frozen fixture bits."""
    n = 0
    for c in X.load()["cases"]:
        p, R = c["profile"], Q(c["R"])
        for name, (q, ret) in (("V", ("V", True)), ("V_ret_off", ("V", False)), ("F", ("F", True)),
                               ("F_ret_off", ("F", False))):
            want = c["results"][name]
            try:
                v = (C.potential if q == "V" else C.radial_force)(R * R, X.PROFILES[p], ret)
                got = {"raw": X.raw_str(p, v)}
            except C.PhysicsDomainExceeded as e:
                got = {"domain": e.reason}
            assert got == want, (p, c["R_bohr_approx"], name)
            n += 1
    assert n == 1328


# --- the impulse -----------------------------------------------------------------------------------------------

def _audit_F(model, R2: Q, dps=80):
    mpmath.mp.dps = dps
    r = mpmath.sqrt(mpmath.mpf(R2.numerator) / R2.denominator)
    return -mpmath.diff(lambda x: model.V(mpmath.mp, x, True), r), r


@needs_data
def test_impulse_is_the_exact_value_rounded_once_at_irrational_R() -> None:
    """J_k against the audit: 80-digit numerical derivative of the audit's own model at R = sqrt(R^2)."""
    from audit.independent_numeric.oracle import SIGN, _interval
    from audit.independent_physics.ar2_lang2024 import Model, parse_fortran
    model = Model(parse_fortran())
    dt_kick = Q(20)
    for k in range(40):
        dr = (G(2.4 + 0.37 * k), G(0.13 * k - 1), G(0.05 * (k % 7)))
        R2 = sum((x * x for x in dr), Q(0))
        F, r = _audit_F(model, R2)
        for prof in (B64, FX):
            J = C.impulse(dr, dt_kick, prof)
            for x, j in zip(dr, J):
                exact = F * (mpmath.mpf(x.numerator) / x.denominator) / r * 20
                man, e = mpmath.mpf(exact).man_exp
                ex = Q(abs(man)) * Q(2) ** e * (-1 if exact < 0 else 1)
                if prof is FX:
                    assert abs(ex - FX.to_exact(j)) <= Q(1, 2 ** 33), (k, x)
                else:
                    lo, hi = _interval(j & ~SIGN)
                    assert lo <= (-ex if j >> 63 else ex) <= hi, (k, x)


def test_double_rounding_of_the_impulse_would_give_different_bits() -> None:
    """The forbidden path round(round(F_k) * dt/2) differs from the contract on some inputs -- so a later
    executor that takes it is detectable by comparing J bits."""
    differ = 0
    for k in range(60):
        dr = (G(2.4 + 0.29 * k), G(0.11 * k - 1), G(0))
        J = C.impulse(dr, Q(20), B64)
        F_rounded = C.impulse(dr, Q(1), B64)                  # round(F dr_k / R): the force component, rounded
        twice = tuple(B64.from_exact(B64.to_exact(f) * 20) for f in F_rounded)
        differ += twice != J
    assert differ > 0


# --- stepping, guard, refusal ----------------------------------------------------------------------------------

def test_run_is_deterministic_and_momentum_exact() -> None:
    for prof in (B64, FX):
        run1, a = trajectory(prof, RI, PI, RJ, PJ, 60)
        run2, b = trajectory(prof, RI, PI, RJ, PJ, 60)
        assert a == b
        assert C.total_momentum(run1) == (0, 0, 0)       # p_i = -p_j, the same J applied with both signs


def test_angular_momentum_is_conserved_up_to_rounding_only() -> None:
    run = C.new_run(HP, 40, RI, PI, RJ, PJ)
    L0 = C.angular_momentum(run)
    for _ in range(200):
        C.step(run)
    assert all(abs(a - b) < Q(1, 10 ** 40) for a, b in zip(C.angular_momentum(run), L0))


def test_segment_minimum_is_exact() -> None:
    a, d = (Q(-3), Q(2), Q(0)), (Q(6), Q(0), Q(0))
    assert C.segment_min_R2(a, d) == 4                    # passes (0, 2): R = 2 between endpoints of R^2 = 13
    assert C.segment_min_R2(a, (Q(-1), Q(0), Q(0))) == 13
    assert C.segment_min_R2(a, (Q(0),) * 3) == 13


def test_drift_segment_guard_stops_a_step_whose_endpoints_are_both_allowed() -> None:
    """A fast pass at impact parameter 2 bohr (< r_min = 2.27): with a step long enough the stored positions
    skip over the forbidden core, but the drift segment does not -- physics_domain_exceeded."""
    ri, rj = (Q(0), Q(-1), Q(0)), (Q(-3), Q(1), Q(0))
    pj = (Q(6000), Q(0), Q(0))                           # relative speed 12000 / m ~ 0.16 bohr / a.u.
    run = C.new_run(FX, 40, ri, tuple(-x for x in pj), rj, pj, validated_only=False)   # ~1000 De: guard test only
    q0 = C.relative(FX, *run.atoms)
    with pytest.raises(C.PhysicsDomainExceeded) as info:
        C.step(run)
    assert "drift segment" in str(info.value) and info.value.reason == "physics_domain_exceeded"
    assert sum((x * x for x in q0), Q(0)) > C.R_MIN2
    with pytest.raises(C.PhysicsDomainExceeded):
        C.new_run(FX, 40, (Q(0),) * 3, (Q(0),) * 3, (Q(2), Q(0), Q(0)), (Q(0),) * 3)


def test_reference_refuses_instead_of_guessing(monkeypatch) -> None:
    monkeypatch.setattr(C, "START_PRECISION_BITS", 8)
    monkeypatch.setattr(C, "MAX_PRECISION_BITS", 8)
    with pytest.raises(C.ReferenceUndecided):
        C.impulse((G(4.3), G(0.9), G(0.1)), Q(20), B64)


# --- D10 invariances ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("prof", [B64, FX], ids=["B64", "FX64_32"])
def test_exchange_and_90_degree_rotation_are_bit_identical(prof) -> None:
    _, A = trajectory(prof, RI, PI, RJ, PJ)
    _, S = trajectory(prof, RJ, PJ, RI, PI)
    assert all(a[0] == s[2] and a[1] == s[3] and a[2] == s[0] and a[3] == s[1] for a, s in zip(A, S))
    rot = lambda v: (v[1], -v[0], v[2])
    _, R = trajectory(prof, rot(RI), rot(PI), rot(RJ), rot(PJ))
    rraw = lambda v: (v[1], prof.neg(v[0]), v[2])
    assert all(rraw(a[k]) == r[k] for a, r in zip(A, R) for k in range(4))


def _relative_trajectory(prof, shift, n=120):
    tr = lambda v: tuple(x + shift for x in v)
    _, T = trajectory(prof, tr(RI), PI, tr(RJ), PJ, n)
    return [(tuple(b - a for a, b in zip(C.exact(prof, s[0]), C.exact(prof, s[2]))), s[1], s[3]) for s in T]


@pytest.mark.parametrize("wf", [(64, 32), (64, 40), (64, 48), (96, 64), (128, 96)], ids=lambda x: f"FX{x[0]}_{x[1]}")
def test_fixed_point_candidates_keep_all_three_invariances(wf) -> None:
    """D10 for every fixed-point candidate (12th ed. item 4): exchange, 90-degree rotation and a grid-aligned
    representation-preserving translation give bit-identical (relative) trajectories."""
    prof = FixedPoint(*wf)
    _, A = trajectory(prof, RI, PI, RJ, PJ, 40)
    _, S = trajectory(prof, RJ, PJ, RI, PI, 40)
    assert all(a[0] == s[2] and a[1] == s[3] and a[2] == s[0] and a[3] == s[1] for a, s in zip(A, S))
    rot = lambda v: (v[1], -v[0], v[2])
    _, R = trajectory(prof, rot(RI), rot(PI), rot(RJ), rot(PJ), 40)
    rraw = lambda v: (v[1], prof.neg(v[0]), v[2])
    assert all(rraw(a[k]) == r[k] for a, r in zip(A, R) for k in range(4))
    shift = Q(1024) + Q(3, 1 << wf[1])
    assert _relative_trajectory(prof, Q(0), 40) == _relative_trajectory(prof, shift, 40)


@pytest.mark.xfail(strict=True, reason="DISQUALIFICATION RECORD (designer 12th ed. item 2): binary64 absolute "
                   "positions are excluded as A's position state -- the shift keeps the initial Delta r exactly, but "
                   "every drift r + p dt/m is rounded at the ulp of the ABSOLUTE position, so the relative trajectory "
                   "depends on the origin from the first step on. Kept as a regression test of the reason, not as an "
                   "allowed failure")
def test_representation_preserving_translation_b64() -> None:
    base = _relative_trajectory(B64, Q(0))
    shifted = _relative_trajectory(B64, Q(1024))
    tr = lambda v: tuple(x + 1024 for x in v)
    assert all(B64.to_exact(B64.from_exact(x)) == x for v in (tr(RI), tr(RJ)) for x in v)   # representable: A-type
    assert base == shifted


# --- audit: conserved quantities recomputed independently -------------------------------------------------------

@needs_data
def test_audit_recomputes_the_conserved_quantities() -> None:
    from audit.independent_physics.c1b1_two_atom import AR40_MASS_ME, Reference
    assert AR40_MASS_ME == C.AR40_MASS_ME
    ref = Reference()
    run = C.new_run(FX, 40, RI, PI, RJ, PJ)
    for _ in range(50):
        C.step(run)
    pos = [C.exact(FX, a.r) for a in run.atoms]
    mom = [C.exact(FX, a.p) for a in run.atoms]
    P, Lv, E = ref.conserved(pos, mom)
    assert tuple(P) == C.total_momentum(run) and tuple(Lv) == C.angular_momentum(run)
    E_ref = C.kinetic(run) + C.potential_high(sum((x * x for x in C.relative(FX, *run.atoms)), Q(0)))
    assert abs(E - (mpmath.mpf(E_ref.numerator) / E_ref.denominator)) < mpmath.mpf(10) ** -25


# --- domain-guard stress (12th ed. item 6; not an accuracy claim) -----------------------------------------------

def _head_on(f: Q, dt):
    """Head-on from 20 bohr with total energy f * V(r_min), FX(256,192); returns (run, exception or None)."""
    import mpmath as mp
    V0 = C.potential_high(Q(400))
    E = f * C.potential_high(C.R_MIN2)
    mu = C.AR40_MASS_ME / 2
    P = -mp.sqrt(2 * (mp.mpf(mu.numerator) / mu.denominator) * (mp.mpf((E - V0).numerator) / (E - V0).denominator))
    man, e = P.man_exp
    Px = FX.to_exact(FX.from_exact(-Q(abs(man)) * Q(2) ** e))
    run = C.new_run(HP, dt, (Q(-10), 0, 0), (-Px, 0, 0), (Q(10), 0, 0), (Px, 0, 0), validated_only=False)
    try:
        for _ in range(5000):
            q0 = C.relative(HP, *run.atoms)
            C.step(run)
            q = C.relative(HP, *run.atoms)
            if q[0] > q0[0] and q[0] >= 20:
                return run, None
    except C.PhysicsDomainExceeded as exc:
        return run, exc
    raise AssertionError("did not come back")


def test_domain_guard_stress_at_small_dt() -> None:
    """At dt = 10 a.u. the discrete path follows the continuous one closely enough: 0.99 V(r_min) turns back
    above r_min, 1.01 V(r_min) is stopped by the drift-segment guard."""
    assert _head_on(Q(99, 100), 10)[1] is None
    exc = _head_on(Q(101, 100), 10)[1]
    assert exc is not None and "drift segment" in str(exc)


def test_domain_guard_stress_at_dt_40_is_not_resolved() -> None:
    """MEASURED (reported to the designer): at dt = 40 a.u., far outside the validated E <= 10 De range, the
    discrete trajectory turns back ABOVE r_min at 1.01 V(r_min) -- the integrator's energy error at this speed is
    larger than 1 %, so the guard never sees a crossing. This is a fact about dt = 40 at this energy, not a guard
    defect; if it changes, the report must be revisited."""
    run, exc = _head_on(Q(101, 100), 40)
    assert exc is None


# --- relative kinetic energy: hand-computable states (13th ed. item 12) -----------------------------------------

def test_relative_kinetic_energy_by_hand() -> None:
    """K_rel = |P|^2 / (2 mu). Guards against the factor-2 error found in the stress script (P^2 / mu)."""
    m = C.AR40_MASS_ME
    # equal masses, opposite momenta: P = p_j, mu = m/2 -> K_rel = 9/m, and all kinetic energy is relative
    assert C.relative_kinetic((Q(-3), Q(0), Q(0)), (Q(3), Q(0), Q(0)), m, m) == Q(9) / m
    # one atom at rest: P = (4/2, 0, 0) -> K_rel = 4/m; total 16/(2m) = 8/m = K_cm 4/m + K_rel 4/m
    assert C.relative_kinetic((Q(0),) * 3, (Q(4), Q(0), Q(0)), m, m) == Q(4) / m
    # unequal masses 1 and 3: P = (1*0 - 3*1)/4 = -3/4, mu = 3/4 -> K_rel = (9/16)/(3/2) = 3/8 (total 1/2 = 1/8 + 3/8)
    assert C.relative_kinetic((Q(1), Q(0), Q(0)), (Q(0),) * 3, Q(1), Q(3)) == Q(3, 8)
    # the run-level enclosure agrees with the hand value on an equal-mass state
    run = C.new_run(FX, 40, (Q(-5), 0, 0), (Q(-3), 0, 0), (Q(5), 0, 0), (Q(3), 0, 0), validated_only=False)
    lo, hi = C.relative_energy_enclosure(run, 256)
    V = C.potential_high(Q(100))
    assert lo <= Q(9) / m + V <= hi and hi - lo < Q(1, 2 ** 200)


# --- three kinds of refusal (13th ed. items 2-3) ------------------------------------------------------------------

def test_refusal_kinds_are_distinct() -> None:
    kinds = {C.PhysicsDomainExceeded.reason, C.IntegratorDomainExceeded.reason, C.ExecutorLimitExceeded.reason}
    assert kinds == {"physics_domain_exceeded", "integrator_domain_exceeded", "executor_limit_exceeded"}
    assert issubclass(C.ReferenceUndecided, C.ExecutorLimitExceeded)
    assert not issubclass(C.IntegratorDomainExceeded, C.PhysicsDomainExceeded)
    assert not issubclass(C.PhysicsDomainExceeded, C.IntegratorDomainExceeded)


def test_unvalidated_energies_are_refused_before_any_step() -> None:
    """A world run never computes E_rel > 10 De: the 1.01 V(r_min) collision that dt = 40 would reflect is refused."""
    for f in (Q(1, 4), Q(101, 100)):
        with pytest.raises(C.IntegratorDomainExceeded) as info:
            _head_on_state(f, validated_only=True)
        assert info.value.reason == "integrator_domain_exceeded"


def _grid_state_with_energy(E: Q):
    """Head-on at 20 bohr, momentum on the FX(64,32) grid nearest to relative energy E (from above and below)."""
    import mpmath as mp
    mp.mp.dps = 50
    V0 = C.potential_high(Q(400))
    mu = C.AR40_MASS_ME / 2
    P = mp.sqrt(2 * (mp.mpf(mu.numerator) / mu.denominator) * (mp.mpf((E - V0).numerator) / (E - V0).denominator))
    raw = int(mp.floor(P * 2 ** 32))
    return [Q(r, 1 << 32) for r in (raw - 1, raw + 2)]


def test_integrator_domain_boundary_is_decided_exactly() -> None:
    """Just below 10 De runs, just above is refused -- decided on exact enclosures, never by a float."""
    below, above = _grid_state_with_energy(C.INTEGRATOR_E_MAX)
    ok = C.new_run(FX, 40, (Q(-10), 0, 0), (below, 0, 0), (Q(10), 0, 0), (-below, 0, 0))
    lo, hi = C.relative_energy_enclosure(ok, 256)
    assert hi <= C.INTEGRATOR_E_MAX
    with pytest.raises(C.IntegratorDomainExceeded):
        C.new_run(FX, 40, (Q(-10), 0, 0), (above, 0, 0), (Q(10), 0, 0), (-above, 0, 0))


def _head_on_state(f: Q, validated_only: bool):
    import mpmath as mp
    V0 = C.potential_high(Q(400))
    E = f * C.potential_high(C.R_MIN2)
    mu = C.AR40_MASS_ME / 2
    P = mp.sqrt(2 * (mp.mpf(mu.numerator) / mu.denominator) * (mp.mpf((E - V0).numerator) / (E - V0).denominator))
    man, e = P.man_exp
    Px = FX.to_exact(FX.from_exact(Q(abs(man)) * Q(2) ** e))
    return C.new_run(HP, 40, (Q(-10), 0, 0), (Px, 0, 0), (Q(10), 0, 0), (-Px, 0, 0), validated_only=validated_only)


def test_stress_state_energy_is_what_the_stress_asks_for() -> None:
    """The stress runs' relative energy really is f * V(r_min) (the script once had it doubled)."""
    for f in (Q(1, 4), Q(99, 100)):
        run = _head_on_state(f, validated_only=False)
        lo, hi = C.relative_energy_enclosure(run, 256)
        target = f * C.potential_high(C.R_MIN2)
        assert abs((lo + hi) / 2 / target - 1) < Q(1, 10 ** 6)


# --- typed profiles (13th ed. items 7-8) ---------------------------------------------------------------------------

POS96, MOM64 = FixedPoint(96, 48), FixedPoint(64, 48)


def _typed_relative(shift, n=60):
    tr = lambda v: tuple(x + shift for x in v)
    run = C.new_run(POS96, 40, tr(RI), PI, tr(RJ), PJ, momentum_profile=MOM64)
    out = []
    for _ in range(n):
        C.step(run)
        out.append((C.relative(POS96, *run.atoms), run.atoms[0].p, run.atoms[1].p))
    return run, out


def test_typed_run_keeps_position_and_momentum_apart() -> None:
    run, _ = _typed_relative(Q(0), 5)
    with pytest.raises(AttributeError):
        run.profile                                              # a typed run has no single profile
    assert run.pos is POS96 and run.mom is MOM64
    assert all(-(1 << 63) <= v < (1 << 63) for a in run.atoms for v in a.p)


def test_typed_positions_reach_far_beyond_the_fx64_48_range() -> None:
    """A representation-preserving shift of 10^6 bohr: impossible in FX(64,48) (range +-32768 bohr), and in
    FX(96,48) the relative trajectory is bit-identical to the unshifted one (D10-A)."""
    from a_numeric.profiles import VMHalt
    with pytest.raises(VMHalt):
        C.new_run(MOM64, 40, tuple(x + 10 ** 6 for x in RI), PI, tuple(x + 10 ** 6 for x in RJ), PJ)
    assert _typed_relative(Q(0))[1] == _typed_relative(Q(10 ** 6) + Q(5, 1 << 48))[1]


# --- exact drift ties (found 2026-09-26; designer 14th ed.: the drift rounds the displacement) --------------------

P_TIE = Q(4995297890462500, 1 << 48)     # dt = 40, 48 fraction bits: p dt / m is exactly half a raw unit
RAW = Q(1, 1 << 48)


def _legacy_drift(pos, mom, a, dt, rule=None):
    """The v1 drift round(r + p dt / m): kept here only to show what the contract tests catch."""
    m = C.SPECIES_MASS[a.species]
    exact_new = tuple(r + p * dt / m for r, p in zip(C.exact(pos, a.r), C.exact(mom, a.p)))
    return C.Atom(a.species, tuple(pos.from_exact(x) for x in exact_new), a.p), exact_new


def _tie_run(shift=Q(0), rot=False):
    """A VALIDATED state (E_rel <= 10 De checked by new_run) whose first drift is an exact tie for both atoms:
    after the first half kick p_j = T and p_i = -T exactly (J is added exactly on the momentum grid)."""
    ri, rj = (Q(-4), Q(0), Q(0)), (Q(4), Q(1), Q(0))
    J = tuple(MOM64.to_exact(j) for j in C.impulse(tuple(b - a for a, b in zip(ri, rj)), Q(20), MOM64))
    pj = tuple(t - j for t, j in zip((P_TIE, Q(0), Q(0)), J))
    pi = tuple(-x for x in pj)
    f = (lambda v: (v[1], -v[0], v[2])) if rot else (lambda v: v)
    tr = lambda v: tuple(x + shift for x in f(v))
    return C.new_run(POS96, 40, tr(ri), f(pi), tr(rj), f(pj), momentum_profile=MOM64)


def _rel_steps(run, n):
    out = []
    for _ in range(n):
        C.step(run)
        out.append((C.relative(POS96, *run.atoms), run.atoms[0].p, run.atoms[1].p))
    return out


def test_drift_ties_are_reachable_and_no_longer_follow_the_parity_of_r() -> None:
    """p = 4995297890462500 * 2^-48 ~ 17.747 a.u. (inside |p| <= ~18 a.u. of E <= 10 De) makes p dt / m land exactly
    halfway between two FX(., 48) positions. The v2 displacement is the same for every r; the v1 one followed the
    parity of r (the defect, shown with the legacy drift)."""
    assert (P_TIE * 40 / C.AR40_MASS_ME * (1 << 48)).denominator == 2

    def disp(drift):
        out = []
        for shift in range(4):
            r = Q(3) + Q(5 + shift, 1 << 48)
            a = C.Atom("Ar40", (POS96.from_exact(r), 0, 0), (MOM64.from_exact(P_TIE), 0, 0))
            out.append(drift(POS96, MOM64, a, Q(40))[0].r[0] - POS96.from_exact(r))
        return out
    assert len(set(disp(C._drift))) == 1
    old = disp(_legacy_drift)
    assert old[0] == old[2] and old[1] == old[3] and old[0] != old[1]


def test_tie_state_is_inside_the_validated_contract() -> None:
    run = _tie_run()                                          # validated_only=True: new_run checked E_rel <= 10 De
    assert run.validated_only
    lo, hi = C.relative_energy_enclosure(run, 256)
    assert hi <= C.INTEGRATOR_E_MAX and lo > 8 * C.DE_CONTRACT
    J = C.impulse(C.relative(POS96, *run.atoms), Q(20), MOM64)
    kicked = C._kick(MOM64, run.atoms, J)
    assert C.exact(MOM64, kicked[1].p) == (P_TIE, 0, 0) and C.exact(MOM64, kicked[0].p) == (-P_TIE, 0, 0)
    for a in kicked:                                          # the x drift of both atoms is an exact half-unit tie
        assert (C.exact(MOM64, a.p)[0] * 40 / C.AR40_MASS_ME * (1 << 48)).denominator == 2


@pytest.mark.parametrize("shift", [RAW, 3 * RAW, Q(10 ** 6) + RAW], ids=["1raw", "3raw", "1e6+1raw"])
def test_translation_invariance_survives_exact_drift_ties(shift, monkeypatch) -> None:
    """D10-A at a tie, on a validated state: an odd raw shift leaves the relative trajectory bit-identical."""
    assert _rel_steps(_tie_run(), 20) == _rel_steps(_tie_run(shift), 20)
    monkeypatch.setattr(C, "_drift", _legacy_drift)          # the v1 drift fails this very test
    assert _rel_steps(_tie_run(), 1) != _rel_steps(_tie_run(shift), 1)


def test_tie_drift_and_the_whole_kdk_step_are_exactly_reversible(monkeypatch) -> None:
    """+dt then -dt returns a tie drift exactly (round(-x) = -round(x)); with it the whole KDK step is exactly
    time-reversible: step, flip momenta, step, flip -> the starting state bit for bit."""
    for k in range(4):
        r = POS96.from_exact(Q(3) + Q(5 + k, 1 << 48))
        a = C.Atom("Ar40", (r, 0, 0), (MOM64.from_exact(P_TIE), 0, 0))
        fwd = C._drift(POS96, MOM64, a, Q(40))[0]
        assert C._drift(POS96, MOM64, fwd, Q(-40))[0].r == a.r
    flip = lambda atoms: tuple(C.Atom(x.species, x.r, tuple(MOM64.neg(v) for v in x.p)) for x in atoms)

    def there_and_back(n, shift=Q(0)):
        run = _tie_run(shift)
        start = run.atoms
        for _ in range(n):
            C.step(run)
        run.atoms = flip(run.atoms)                          # J_cache stays valid: the positions did not move
        for _ in range(n):
            C.step(run)
        return flip(run.atoms) == start
    assert all(there_and_back(n, sh) for n in (1, 15) for sh in (Q(0), RAW))
    monkeypatch.setattr(C, "_drift", _legacy_drift)
    assert there_and_back(1) and not there_and_back(1, RAW)  # v1: from an odd raw position the tie is not undone


def test_exchange_and_rotation_hold_at_exact_ties() -> None:
    A = _rel_steps(_tie_run(), 20)
    ri, rj = (Q(-4), Q(0), Q(0)), (Q(4), Q(1), Q(0))
    J = tuple(MOM64.to_exact(j) for j in C.impulse(tuple(b - a for a, b in zip(ri, rj)), Q(20), MOM64))
    pj = tuple(t - j for t, j in zip((P_TIE, Q(0), Q(0)), J))
    ex = C.new_run(POS96, 40, rj, pj, ri, tuple(-x for x in pj), momentum_profile=MOM64)
    S = _rel_steps(ex, 20)
    assert all(a[0] == tuple(-x for x in s[0]) and a[1] == s[2] and a[2] == s[1] for a, s in zip(A, S))
    R = _rel_steps(_tie_run(rot=True), 20)
    rr = lambda v: (v[1], -v[0], v[2])
    rraw = lambda v: (v[1], MOM64.neg(v[0]), v[2])
    assert all(rr(a[0]) == r[0] and rraw(a[1]) == r[1] and rraw(a[2]) == r[2] for a, r in zip(A, R))


@pytest.mark.parametrize("pair", [(FixedPoint(64, 32), None), (FixedPoint(64, 48), None), (POS96, MOM64)],
                         ids=["FX64_32", "FX64_48", "POS96+MOM64"])
def test_v2_drift_is_bit_identical_to_v1_away_from_ties(pair, monkeypatch) -> None:
    """Off ties round(r + x) = r + round(x) on an integer grid, so the change must not move a single bit."""
    pos, mom = pair
    mom = mom or pos
    ties = []

    def run(drift):
        monkeypatch.setattr(C, "_drift", drift)
        r = C.new_run(pos, 40, RI, PI, RJ, PJ, momentum_profile=mom)
        out = []
        for _ in range(120):
            C.step(r)
            out.append(r.atoms)
        return out

    def counting(p, m, a, dt, rule=None):
        ties.extend(x * dt / C.SPECIES_MASS[a.species] * (1 << p.frac_bits) for x in C.exact(m, a.p))
        return _legacy_drift(p, m, a, dt)
    new = run(C._drift)
    assert new == run(counting)
    assert len(ties) == 120 * 2 * 3 and all(t.denominator != 2 for t in ties)


def test_position_overflow_is_an_executor_limit_never_a_wrap() -> None:
    """FX(64,48) as the position profile (range +-32768 bohr): an atom drifting past the edge stops the step."""
    edge = Q(32768) - Q(3, 1 << 48)
    fx = FixedPoint(64, 48)
    run = C.new_run(fx, 40, (edge - 8, Q(0), Q(0)), (Q(-2), Q(0), Q(0)), (edge, Q(0), Q(0)), (Q(2), Q(0), Q(0)))
    before = run.atoms
    with pytest.raises(C.ExecutorLimitExceeded) as info:
        C.step(run)
    assert info.value.reason == "executor_limit_exceeded" and "overflow" in str(info.value)
    assert not isinstance(info.value, (C.PhysicsDomainExceeded, C.IntegratorDomainExceeded))
    assert run.atoms == before and run.t_steps == 0            # nothing stored: no wrap, no saturation


def test_the_built_in_v1_rule_is_the_legacy_drift() -> None:
    """The comparison rule drift="v1" is exactly the retired round(r + p dt/m) (checked at a tie and off ties)."""
    for k in range(4):
        r = POS96.from_exact(Q(3) + Q(5 + k, 1 << 48))
        for p in (P_TIE, Q(12345, 1 << 20)):
            a = C.Atom("Ar40", (r, 0, 0), (MOM64.from_exact(p), 0, 0))
            assert C._drift(POS96, MOM64, a, Q(40), rule="v1") == _legacy_drift(POS96, MOM64, a, Q(40))


def test_exact_positions_never_round_the_drift() -> None:
    E = C.ExactPosition()
    run = C.new_run(E, 40, RI, PI, RJ, PJ, momentum_profile=MOM64)
    start = [C.exact(E, a.r) for a in run.atoms]
    moved = [[Q(0)] * 3, [Q(0)] * 3]
    for _ in range(30):
        J = run.J_cache if run.J_cache is not None else C.impulse(C.relative(E, *run.atoms), Q(20), MOM64)
        kicked = C._kick(MOM64, run.atoms, J)
        for n, a in enumerate(kicked):
            moved[n] = [x + p * 40 / C.AR40_MASS_ME for x, p in zip(moved[n], C.exact(MOM64, a.p))]
        C.step(run)
    for n, a in enumerate(run.atoms):
        assert tuple(s + d for s, d in zip(start[n], moved[n])) == a.r


def test_carry_momentum_keeps_impulses_below_the_coarse_grid() -> None:
    """Designer 15th ed. candidate: at 1000 bohr J rounds to 0 on FX(64,48) -- with the carry profile the same
    impulses accumulate on the 2^-111 grid, and the pair starts moving once they add up to a coarse unit."""
    K = C.CarryMomentum()
    rest = ((Q(-500), Q(0), Q(0)), (Q(0),) * 3, (Q(500), Q(0), Q(0)), (Q(0),) * 3)
    plain = C.new_run(POS96, 40, *rest, momentum_profile=MOM64)
    carry = C.new_run(POS96, 40, *rest, momentum_profile=K)
    for _ in range(50):
        C.step(plain)
        C.step(carry)
    assert plain.atoms[1].p == (0, 0, 0)                                   # the implicit cutoff: nothing, ever
    J = C.impulse((Q(1000), Q(0), Q(0)), Q(20), K)
    assert J[0][0] == 0 and J[0][1] != 0                                    # below the coarse grid, kept in fine
    assert C.exact(K, carry.atoms[1].p)[0] < 0 and C.total_momentum(carry) == (0, 0, 0)
    assert carry.atoms[0].p == tuple(K.neg(v) for v in carry.atoms[1].p)  # action = reaction, exactly


def test_carry_split_is_odd_symmetric_and_bounded() -> None:
    K = C.CarryMomentum()
    for x in (Q(1, 2 ** 49), Q(3, 2 ** 49), Q(-5, 2 ** 49), Q(12345, 2 ** 70), P_TIE, -P_TIE + Q(7, 2 ** 111)):
        v = K.from_exact(x)
        assert K.to_exact(v) == x and K.from_exact(-x) == K.neg(v)
        assert abs(v[1]) <= K.unit // 2 and K.drift_exact(v) == MOM64.to_exact(MOM64.from_exact(x))
