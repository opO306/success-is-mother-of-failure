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
    assert C.CONTRACT_VERSION == "c1b1-two-atom-v1"
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
    run = C.new_run(FX, 40, ri, tuple(-x for x in pj), rj, pj)
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
    run = C.new_run(HP, dt, (Q(-10), 0, 0), (-Px, 0, 0), (Q(10), 0, 0), (Px, 0, 0))
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
