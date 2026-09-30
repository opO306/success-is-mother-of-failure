"""C1-B1 inbound V1 (a_reference/c1b1_inbound_outer.py): the mirror shell induction and the exact R >= R_J line.

What these tests are: (1) every inequality the certificate claims is re-checked from its own record by a separate small
checker below; (2) the claims are compared with the REAL executor on a few states -- a consistency check that can
catch a wrong derivation, never a substitute for it (designer, IN verdicts: a sampled trajectory is not evidence);
(3) the refusals; (4) fault injection into the module's source text (a dropped w gain, an exit radius without the
overshoot, a missing momentum-cap check must each be caught). Nothing here is about inner, shadowing, the scattering
angle, E_min or rounding liveness.
"""
import types
from fractions import Fraction as Q
from pathlib import Path

import pytest

import a_reference.c1b1_inbound_outer as IB
import a_reference.c1b1_outer_bootstrap as O
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

POS, MOM = FixedPoint(96, 48), FixedPoint(96, 80)
H = Q(40)
SRC = Path(IB.__file__).read_text(encoding="utf-8")


def _run(q, P, cache=None):
    run = C.new_run(POS, H, tuple(-x / 2 for x in q), tuple(-x for x in P), tuple(x / 2 for x in q), P,
                    momentum_profile=MOM, validated_only=False)
    run.J_cache = cache
    return run


def _rel(atoms):
    q = C.relative(POS, *atoms)
    pi, pj = (C.exact(MOM, a.p) for a in atoms)
    return q, tuple((y - x) / 2 for x, y in zip(pi, pj))


def _dot(a, b):
    return sum((x * y for x, y in zip(a, b)), Q(0))


def _cross(u, v):
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


NEAR = ((Q(28), Q(5), Q(0)), (Q(-12), Q(0), Q(0)))          # R ~ 28.44 inbound, E ~ 4.4 De, b = 5
FAR = ((Q(10245), Q(5), Q(0)), (Q(-12), Q(0), Q(0)))        # beyond R_J = 10240: the exact zero-impulse line first
CAP = Q(13)


def _check_record(cert):
    """An independent re-check of every closing inequality from the certificate's own numbers."""
    cap, g = cert["p_cap"], cert["handoff_width_g"]
    assert g == O.ALPHA * cap + O.D
    for s in cert["shells"]:
        a, b, k, n, count = s["a"], s["b"], s["half_kick_cap"], s["induction_budget"], s["max_steps"]
        assert s["guard_low"] == a - g >= 20 and s["chord_region"] == (a - g, b)
        assert count <= n
        assert s["entry_enclosure"]["p_norm"][1] + 2 * n * k <= cap
        assert s["w_gain_per_step"] == 2 * b * k + O.ALPHA * cap ** 2 + O.D * cap
        assert s["w_ceiling"] + s["w_gain_per_step"] < 0
        assert s["half_step_w_ceiling"] == s["w_ceiling"] + b * k
        c0 = 2 * b * O.D + (O.ALPHA * cap + O.D) ** 2
        assert s["g_in"] == -(2 * O.ALPHA * s["half_step_w_ceiling"] + c0) > 0
        r_hi = s["entry_enclosure"]["radius_upper"]
        assert r_hi * r_hi - count * s["g_in"] < a * a <= r_hi * r_hi - (count - 1) * s["g_in"]
        assert s["exit_enclosure"]["radius"] == (a - g, a)
    for s, t in zip(cert["shells"], cert["shells"][1:]):
        assert t["b"] == s["a"] and t["entry_enclosure"]["radius_upper"] == s["a"]
        assert t["entry_enclosure"]["q_dot_p_upper"] == s["exit_enclosure"]["q_dot_p_upper"]
    hp = cert["handoff_packet"]
    assert hp["radius"][0] >= 20 and hp["q_dot_p_upper"] < 0
    if cert["shells"]:
        assert hp["radius"] == (Q(20), 20 + g)


@pytest.fixture(scope="module")
def near():
    return IB.certify_inbound_outer(_run(*NEAR), CAP)


def test_a_near_outer_inbound_state_is_certified_and_every_inequality_rechecks(near):
    _check_record(near)
    assert near["zero_impulse_leg"] is None and len(near["shells"]) == 2
    assert near["reference_decision_within_precision_cap"] == "not_proved_for_future_steps"
    assert near["inner"] == near["global_trajectory_shadowing"] == near["incoming_asymptote"] == "not_claimed"


def test_the_executor_stays_inside_every_claim_consistency_only(near):
    """Run the real executor to the handoff. Every stored chord is at R >= 20, every step lowers R^2 by at least the
    shell's g_in, q.P stays under the shell's ceiling, and the handoff state is in the packet. NOT a proof."""
    run = _run(*NEAR)
    A = 20 + near["handoff_width_g"]
    shells, steps = near["shells"], 0
    q, P = _rel(run.atoms)
    while _dot(q, q) >= A * A:
        shell = next(s for s in shells if _dot(q, q) >= s["a"] ** 2)
        C.step(run)
        steps += 1
        q1, P1 = _rel(run.atoms)
        assert C.segment_min_R2(q, tuple(y - x for x, y in zip(q, q1))) >= 400
        assert _dot(q1, q1) - _dot(q, q) <= -shell["g_in"]
        assert _dot(q1, P1) <= shell["w_ceiling"] + shell["w_gain_per_step"]
        q, P = q1, P1
    hp = near["handoff_packet"]
    assert steps <= near["max_shell_steps"]
    assert hp["radius"][0] ** 2 <= _dot(q, q) < hp["radius"][1] ** 2
    assert hp["p_norm"][0] ** 2 <= _dot(P, P) <= hp["p_norm"][1] ** 2
    assert _dot(q, P) <= hp["q_dot_p_upper"] < 0
    assert _dot(_cross(q, P), _cross(q, P)) <= hp["L_norm_upper"] ** 2


def test_the_zero_impulse_line_is_exact_and_the_far_chain_closes():
    run = _run(*FAR)
    cert = IB.certify_inbound_outer(run, CAP)
    _check_record(cert)
    z = cert["zero_impulse_leg"]
    assert z["R_J"] == O.zero_impulse_radius() == 10240 and len(cert["shells"]) >= 20
    q0, P0 = _rel(run.atoms)
    for n in range(z["steps_exact"]):                        # the executor: no kick, the exact straight lattice line
        C.step(run)
        q, P = _rel(run.atoms)
        if n + 1 < z["steps_exact"]:
            assert P == P0 and _dot(q, q) >= 10240 ** 2
    assert q == z["exit_q_exact"] and _dot(q, q) < 10240 ** 2
    L0 = _cross(*_rel(_run(*FAR).atoms))                     # before the last (nonzero) kick L moved exactly n delta x P
    assert len(z["relative_L_change_before_last_kick_exact"]) == 3    # (a V1 bug stored n copies of the tuple)
    assert tuple(a + b for a, b in zip(L0, z["relative_L_change_before_last_kick_exact"])) == _cross(q, P0)
    assert _dot(P, P) <= (abs(P0[0]) + z["last_kick_cap"]) ** 2


def test_a_state_already_in_the_handoff_band_is_handed_off_with_zero_steps():
    cert = IB.certify_inbound_outer(_run((Q(20005, 1000), Q(0), Q(0)), (Q(-12), Q(0), Q(0))), CAP)
    assert cert["shells"] == [] and cert["max_shell_steps"] == 0 and cert["handoff_packet"]["q_dot_p_upper"] < 0


@pytest.mark.parametrize("q,P,cap,cache,reason", [
    ((Q(28), Q(5), Q(0)), (Q(12), Q(0), Q(0)), CAP, None, "not inbound"),
    ((Q(19), Q(1), Q(0)), (Q(-12), Q(0), Q(0)), CAP, None, "inner"),
    ((Q(28), Q(5), Q(0)), (Q(-12), Q(0), Q(0)), Q(12), None, "momentum"),
    ((Q(28), Q(5), Q(0)), (Q(-12), Q(0), Q(0)), Q(11), None, "below the current momentum"),
    ((Q(5), Q(24), Q(0)), (Q(-12), Q(0), Q(0)), CAP, None, "ceiling"),           # b = 24 > 20: turns outside
    ((Q(20000), Q(12000), Q(0)), (Q(-12), Q(0), Q(0)), CAP, None, "never enters R_J"),
    ((Q(28), Q(5), Q(0)), (Q(-12), Q(0), Q(0)), CAP, (1, 0, 0), "cache mismatch"),
    ((Q(10245), Q(5), Q(0)), (Q(-12), Q(0), Q(0)), CAP, (1, 0, 0), "cache beyond"),
], ids=["outbound", "inner", "cap_equal", "cap_below", "grazing", "misses_R_J", "cache", "cache_far"])
def test_refusals_are_not_certified(q, P, cap, cache, reason):
    with pytest.raises(IB.NotCertified, match=reason):
        IB.certify_inbound_outer(_run(q, P, cache), cap)


def _mutant(old, new):
    assert SRC.count(old) == 1, old
    mod = types.ModuleType("mutant_inbound")
    exec(compile(SRC.replace(old, new), "mutant_inbound.py", "exec"), mod.__dict__)
    return mod


def test_fault_injection_a_dropped_w_gain_is_caught_by_the_executor_check():
    """Mutant: gain without alpha P_cap^2 (the drift's own q.P increase). The ceiling becomes the entry w and the real
    trajectory rises above it."""
    mod = _mutant("    gain = 2 * b * k + O.ALPHA * p_cap ** 2 + O.D * p_cap\n", "    gain = 2 * b * k + O.D * p_cap\n")
    cert = mod.certify_inbound_outer(_run(*NEAR), CAP)
    run, worst = _run(*NEAR), Q(-10 ** 9)
    s = cert["shells"][0]
    for _ in range(s["max_steps"] // 2):
        C.step(run)
        q, P = _rel(run.atoms)
        worst = max(worst, _dot(q, P))
    assert worst > s["w_ceiling"] + s["w_gain_per_step"]


def test_fault_injection_an_exit_radius_without_the_overshoot_is_caught():
    mod = _mutant('"exit_enclosure": {"radius": (lower, a),', '"exit_enclosure": {"radius": (a, a),')
    cert = mod.certify_inbound_outer(_run(*NEAR), CAP)
    with pytest.raises(AssertionError):
        _check_record(cert)


def test_fault_injection_a_missing_momentum_cap_check_is_caught():
    mod = _mutant('''        if half_cap > p_cap:
            raise NotCertified("momentum induction budget did not close")
''', "")
    cert = mod.certify_inbound_outer(_run(*NEAR), Q(12))                    # the honest module refuses this cap
    with pytest.raises(AssertionError):
        _check_record(cert)


def test_the_module_never_runs_the_trajectory_or_reads_d_valid():
    assert "C.step(" not in SRC and "c1b1_domain_contract" not in SRC and "validation" not in SRC


# --- energy mode (Energy Bound v0, docs/active/C1B1_ENERGY_BOUND_V0.md) --------------------------------------------

import math                                                                   # noqa: E402

import a_reference.c1b1_energy_bound as EB                                    # noqa: E402

LOW = None


def _low_state():
    """E = 1e-2 De, b = 7, R0 = 25 inbound: the kick-accumulated V1 mode cannot certify it (survey)."""
    V = float(C.potential_high(Q(625)))
    p = math.sqrt(2 * float(IB.B.MU) * (0.01 * float(C.DE_CONTRACT) - V))
    return _run((Q(math.sqrt(625 - 49)), Q(7), Q(0)), (Q(-p), Q(0), Q(0)))


def _low_cap(run):
    _, P = _rel(run.atoms)
    return IB.B.sqrt_up(_dot(P, P) + 2 * IB.B.MU * abs(C.potential_high(Q(400)))) * (1 + Q(1, 128))


@pytest.fixture(scope="module")
def low():
    run = _low_state()
    return IB.certify_inbound_outer(run, _low_cap(run), energy=True)


def _check_energy_record(cert):
    cap = cert["p_cap"]
    for s in cert["shells"]:
        n, k = s["induction_budget"], s["half_kick_cap"]
        domain = O._covered_shell(s["guard_low"], s["b"])
        pe = EB.momentum_range(EB.EnergyRange(*s["energy_entry"]).widen(n * s["energy_step_budget"]),
                               domain.radial[0], domain.force)
        assert pe == s["energy_momentum_range"]
        assert min(s["entry_enclosure"]["p_norm"][1] + 2 * n * k, pe[1] + k) <= cap
        assert s["w_ceiling"] + s["w_gain_per_step"] < 0 and s["g_in"] > 0 and s["guard_low"] >= 20
    for s, t in zip(cert["shells"], cert["shells"][1:]):
        assert EB.EnergyRange(*t["energy_entry"]) == EB.EnergyRange(*s["energy_entry"]).widen(
            s["max_steps"] * s["energy_step_budget"])


def test_energy_mode_certifies_a_low_energy_state_that_v1_cannot(low):
    run = _low_state()
    with pytest.raises(IB.NotCertified):
        IB.certify_inbound_outer(run, _low_cap(run))
    assert low["momentum_bounds"] == "energy_and_kick"
    _check_energy_record(low)


def test_energy_mode_the_executor_stays_inside_every_claim_consistency_only(low):
    run = _low_state()
    A = 20 + low["handoff_width_g"]
    q, P = _rel(run.atoms)
    steps = 0
    while _dot(q, q) >= A * A:
        s = next(x for x in low["shells"] if _dot(q, q) >= x["a"] ** 2)
        C.step(run)
        steps += 1
        q1, P1 = _rel(run.atoms)
        assert _dot(q1, q1) - _dot(q, q) <= -s["g_in"]
        assert _dot(q1, P1) <= s["w_ceiling"] + s["w_gain_per_step"]
        lo, hi = s["energy_momentum_range"]
        assert lo * lo <= _dot(P1, P1) <= hi * hi
        q, P = q1, P1
    hp = low["handoff_packet"]
    assert steps <= low["max_shell_steps"]
    assert hp["p_norm"][0] ** 2 <= _dot(P, P) <= hp["p_norm"][1] ** 2 and _dot(q, P) <= hp["q_dot_p_upper"]


def test_fault_injection_energy_mode_taking_the_momentum_ceiling_as_the_floor_is_caught():
    mod = _mutant("            half_cap, pl = min(half_cap, pe[1] + k), max(pl, pe[0])\n",
                  "            half_cap, pl = min(half_cap, pe[1] + k), max(pl, pe[1])\n")
    run = _low_state()
    cert = mod.certify_inbound_outer(run, _low_cap(run), energy=True)
    s = cert["shells"][0]
    run, worst = _low_state(), None
    for _ in range(s["max_steps"]):
        C.step(run)
        q, P = _rel(run.atoms)
        worst = _dot(q, P) if worst is None else max(worst, _dot(q, P))
        if _dot(q, q) < s["a"] ** 2:
            break
    assert worst > s["w_ceiling"] + s["w_gain_per_step"]
