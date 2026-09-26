"""Analytic obligations and real KDK checks; no fitted D_valid evidence."""
from fractions import Fraction as Q
from math import factorial
from pathlib import Path

import mpmath
import pytest

from a_numeric import FixedPoint
from a_reference import ar2_lang2024 as L
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bound as B


def norm2(v):
    return sum((x*x for x in v), Q(0))


def test_interval_arithmetic_covers_signed_extremes():
    for a, b in ((-3, -1), (-2, 5), (0, 0), (Q(-1, 3), Q(1, 7))):
        for c, d in ((-7, -1), (-3, 5), (0, 0), (Q(1, 3), Q(2, 3))):
            iv, jv = B.Iv(Q(a), Q(b)), B.Iv(Q(c), Q(d))
            for x in (a, (a+b)/Q(2), b):
                for y in (c, (c+d)/Q(2), d):
                    out = iv*jv
                    assert out.lo <= x*y <= out.hi
                    out = iv+jv
                    assert out.lo <= x+y <= out.hi
    with pytest.raises(ValueError):
        B.Iv(Q(-1), Q(1)).reciprocal()


@pytest.mark.parametrize("power", [-6, -1, 0, 1, 2, 3, 7])
def test_taylor_derivatives_have_the_right_sign_and_factorial(power):
    r = Q(21)
    x = B.Jet((B.Iv.of(r), B.Iv.of(1), B.Iv.of(0), B.Iv.of(0)))
    jet = x**power
    coef = Q(1)
    for k in range(4):
        want = coef*r**(power-k)/factorial(k)
        assert jet.c[k].lo <= want <= jet.c[k].hi
        coef *= power-k


def test_exp_derivative_sign_and_far_tail():
    x = B.Jet((B.Iv.of(-20), B.Iv.of(-1), B.Iv.of(0), B.Iv.of(0)))
    y = x.exp()
    exp = L._exp_neg(Q(20), 256)
    for k in range(4):
        candidates = [(-1)**k*exp.lo/factorial(k), (-1)**k*exp.hi/factorial(k)]
        assert y.c[k].lo <= min(candidates) <= max(candidates) <= y.c[k].hi
    tail = B.Iv(Q(-10**9), Q(-5000)).exp()
    assert (tail.lo, tail.hi) == (0, Q(1, 2**B.BITS))


@pytest.mark.parametrize("r", [Q(20), Q(21), Q(100)])
def test_derivatives_against_separately_parsed_fortran(r):
    # Numerical differentiation is a regression oracle, not the proof of the
    # derivative enclosure; that proof is the interval Taylor recurrence.
    from audit.independent_physics.ar2_lang2024 import Model, parse_fortran, _exact
    model = Model(parse_fortran())
    got = B.derivatives(r, r)
    with mpmath.workdps(90):
        rm = mpmath.mpf(r.numerator)/r.denominator
        for k in range(4):
            y = mpmath.diff(lambda t: model.V(mpmath.mp, t), rm, k)
            want = _exact(y._mpf_)
            assert got[k].lo <= want <= got[k].hi, k


def test_whole_shell_not_only_endpoints_is_enclosed():
    got = B.derivatives(Q(20), Q(21))
    for r in (Q(20), Q(81, 4), Q(41, 2), Q(83, 4), Q(21)):
        v, dv, _ = C._model(r*r, 256, True)
        for k, raw in enumerate((v, dv)):
            assert got[k].lo <= Q(raw[0], 2**256) <= Q(raw[1], 2**256) <= got[k].hi


@pytest.fixture(scope="module")
def shell():
    return B.Shell.prove(Q(20), Q(22))


def test_segment_guard_catches_an_interior_inner_crossing(shell):
    shell.check_segment((Q(20), Q(0), Q(0)), (Q(22), Q(0), Q(0)))
    # Both endpoints in shell, but the interior passes through zero.
    with pytest.raises(ValueError, match="whole chord"):
        shell.check_segment((Q(21), Q(0), Q(0)), (Q(-21), Q(0), Q(0)))
    with pytest.raises(ValueError):
        shell.check_segment((Q(21), Q(0), Q(0)), (Q(23), Q(0), Q(0)))


def modified_energy(run):
    i, j = run.atoms
    pi, pj = C.exact(run.mom, i.p), C.exact(run.mom, j.p)
    q = C.relative(run.pos, i, j)
    kinetic = norm2(tuple((y-x)/2 for x, y in zip(pi, pj)))/(2*B.MU)
    v, dv, _ = C._model(norm2(q), 256, True)
    v0, v1 = (Q(x, 2**256) for x in v)
    f0, f1 = (Q(x, 2**256) for x in dv)
    f2lo = Q(0) if f0 <= 0 <= f1 else min(f0*f0, f1*f1)
    f2hi = max(f0*f0, f1*f1)
    scale = B.H**2/(8*B.MU)
    return kinetic+v0-scale*f2hi, kinetic+v1-scale*f2lo


@pytest.mark.parametrize("pj", [(Q(0), Q(0), Q(0)), (Q(-1), Q(0), Q(0)),
                                    (Q(1), Q(1, 2), Q(0)), (Q(0), Q(1), Q(1))])
def test_real_kdk_step_is_below_separate_outer_bounds(shell, pj):
    pos, mom = FixedPoint(96, 48), FixedPoint(96, 80)
    run = C.new_run(pos, B.H, (-Q(21, 2), 0, 0), tuple(-x for x in pj),
                    (Q(21, 2), 0, 0), pj, momentum_profile=mom)
    q0 = C.relative(pos, *run.atoms)
    e0, l0 = modified_energy(run), C.angular_momentum(run)
    # First half-step momentum EXACTLY decoded, no continuous-speed assumption.
    j0 = C.impulse(q0, B.H/2, mom)
    half = C._kick(mom, run.atoms, j0)
    p_half = tuple((y-x)/2 for x, y in zip(C.exact(mom, half[0].p), C.exact(mom, half[1].p)))
    cap = B.sqrt_up(norm2(p_half))
    C.step(run)
    q1 = C.relative(pos, *run.atoms)
    shell.check_segment(q0, q1)
    b = B.step_budget(shell, cap)
    e1, l1 = modified_energy(run), C.angular_momentum(run)
    max_de = max(abs(e1[0]-e0[1]), abs(e1[1]-e0[0]))
    assert max_de <= b["energy_hartree"]["total"]
    assert norm2(tuple(y-x for x, y in zip(l0, l1))) <= b["angular_bohr_momentum"]["total"]**2
    assert b["energy_hartree"]["momentum_update"] == 0


def test_source_budget_extremes_zero_and_max_grid(shell):
    max_p = Q(2**95-1, 2**80)
    for cap in (Q(0), Q(1), B.sqrt_up(3*max_p*max_p)):
        b = B.step_budget(shell, cap)
        init = B.initial_projection_budget(shell, cap)
        for record in (b, init):
            for key in ("energy_hartree", "angular_bohr_momentum"):
                parts = record[key]
                assert all(x >= 0 for x in parts.values())
                assert parts["total"] == sum((x for k, x in parts.items() if k != "total"), Q(0))
    zero = B.step_budget(shell, Q(0))
    assert zero["energy_hartree"]["discretization"] == 0
    assert zero["angular_bohr_momentum"]["position"] == 0
    assert zero["energy_hartree"]["impulse"] > 0  # force work / quadratic error still present


def test_initial_projection_kinetic_and_torque_terms_are_independently_valid(shell):
    p = (Q(1), Q(-1), Q(1))
    eps = (B.UP/2, -B.UP/2, B.UP/2)
    rounded = tuple(x+y for x, y in zip(p, eps))
    cap = B.sqrt_up(norm2(p))
    budget = B.initial_projection_budget(shell, cap)
    dk = abs(norm2(rounded)-norm2(p))/(2*B.MU)
    assert dk <= budget["energy_hartree"]["momentum_initial"]
    # Construct an actual grid projection at three simultaneous half-even ties.
    profile = FixedPoint(96, 80)
    continuous = tuple(x+B.UP/2 for x in p)
    realized = tuple(profile.to_exact(profile.from_exact(x)) for x in continuous)
    diff = tuple(y-x for x, y in zip(continuous, realized))
    assert norm2(diff) <= 3*B.UP**2/4
    q = (Q(21), Q(0), Q(0))
    torque = (Q(0), -q[0]*diff[2], q[0]*diff[1])
    assert norm2(torque) <= budget["angular_bohr_momentum"]["momentum_initial"]**2


def test_precision_order_and_finite_sum_are_exact(shell):
    expected = B.step_budget(shell, Q(1))
    for dps in (15, 40, 60, 100):
        with mpmath.workdps(dps):
            assert B.step_budget(B.Shell.prove(Q(20), Q(22)), Q(1)) == expected
    a, b = expected, B.step_budget(shell, Q(2))
    for key in ("energy_hartree", "angular_bohr_momentum"):
        assert B.finite_sum([a, b])[key] == B.finite_sum([b, a])[key]
        assert B.finite_sum([a, b])[key]["total"] == a[key]["total"]+b[key]["total"]
    with pytest.raises(ValueError):
        B.finite_sum([B.initial_projection_budget(shell, Q(1))])


@pytest.mark.parametrize("bad", [1.0, True, "1"])
def test_approximate_and_untyped_inputs_are_refused(bad):
    with pytest.raises(TypeError):
        B.derivatives(bad, Q(22))


def test_no_dvalid_data_or_midpoint_oracle_dependency():
    source = Path(B.__file__).read_text(encoding="utf-8")
    for forbidden in ("c1b1_domain_contract", "fixtures/", "potential_high(", "force_high(", "mpmath"):
        assert forbidden not in source


def test_example_report_retains_every_source_and_derivation_provenance():
    report = B.example_report()
    assert report["kind"] == "analytic_examples_not_measurements"
    assert len(report["source_sha256"]) == 3
    for row in report["examples"]:
        b = row["step"]
        assert b["scope"] == "one_successful_outer_kdk_step"
        parts = b["energy_hartree"]
        assert Q(parts["total"]) == sum((Q(v) for k, v in parts.items() if k != "total"), Q(0))
        assert len(b["derivative_intervals"]) == 4


def test_mutation_third_derivative_sign_is_detected(monkeypatch):
    real = B.derivatives
    def broken(a, b):
        vals = real(a, b)
        return vals[:3]+(-vals[3],)
    monkeypatch.setattr(B, "derivatives", broken)
    with pytest.raises(AssertionError):
        test_derivatives_against_separately_parsed_fortran(Q(20))


def test_mutation_underestimated_relative_drift_radius_is_detected(monkeypatch, shell):
    # Two independently rounded atom displacements can differ by a FULL ulp per
    # component. Treating it as a half ulp makes the torque bound false.
    monkeypatch.setattr(B, "UX", B.UX/2)
    bad = B.step_budget(shell, Q(1))["angular_bohr_momentum"]["position"]
    delta = (Q(0), B.UX*2, B.UX*2)
    actual_torque2 = delta[1]**2+delta[2]**2  # P_h=(1,0,0)
    assert actual_torque2 > bad*bad
