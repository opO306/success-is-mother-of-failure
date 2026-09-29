"""C1-B1 inbound V0: lemma TR, the exact time reversal of the executor step (a_reference/c1b1_time_reversal.py).

Fixed here: (i) a whole D_valid scattering event that starts in the OUTER region inbound (R ~ 28.4 bohr, E ~ 4.4 De,
b = 5 bohr, H part of D_valid), goes through the inner wall and back out past R = 20, is retraced bit for bit by the
reversed run, state by state; (ii) the reverse run asks no rounding question the forward run did not decide; (iii) the
ONLY way a reverse step can fail is the drift-segment guard, whose segment is the forward one moved by the drift
residual d (|d_k| <= 2^-48), predicted exactly, with a real counterexample one grid unit above r_min; (iv) D_valid is
not closed under T; (v) premises refused; fault injection (a rounding that is not odd-symmetric breaks the lemma).
These say nothing about inbound infall, inner scattering, shadowing or rounding liveness (docs/active/C1B1_INBOUND_V0.md).
"""
from fractions import Fraction as Q

import pytest

import a_reference.c1b1_domain_contract as D
import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_time_reversal as TR
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

POS, MOM = FixedPoint(96, 48), FixedPoint(96, 80)
H = Q(40)
UNIT = Q(1, 1 << 48)


def _run(q, P, validated_only=True):
    """Relative position q and relative momentum P = p_j = -p_i, atoms symmetric about the origin."""
    return C.new_run(POS, H, tuple(-x / 2 for x in q), tuple(-x for x in P), tuple(x / 2 for x in q), P,
                     momentum_profile=MOM, validated_only=validated_only)


def _R2(atoms):
    return sum((x * x for x in C.relative(POS, *atoms)), Q(0))


def _w(atoms):
    q = C.relative(POS, *atoms)
    return sum((a * b for a, b in zip(q, C.exact(MOM, atoms[1].p))), Q(0))


def _T(atoms):
    return tuple(C.Atom(a.species, a.r, tuple(MOM.neg(v) for v in a.p)) for a in atoms)


OUTER_INBOUND = ((Q(28), Q(5), Q(0)), (Q(-12), Q(0), Q(0)))    # R ~ 28.44, inbound, b = 5, E ~ 4.4 De
EVENT_STEPS = 3600


@pytest.fixture(scope="module")
def event():
    run = _run(*OUTER_INBOUND)
    states = [run.atoms]
    for _ in range(EVENT_STEPS):
        C.step(run)
        states.append(run.atoms)
    return run, states


def test_a_d_valid_scattering_event_from_outer_inbound_is_retraced_bit_for_bit(event):
    run, states = event
    assert _run(*OUTER_INBOUND).validation["validation_status"] == "numerical_validated"
    assert _R2(states[0]) > 400 and _w(states[0]) < 0                      # starts OUTER and INBOUND
    assert min(_R2(s) for s in states) < 7 ** 2                             # reaches the inner repulsive wall
    assert _R2(states[-1]) > 400 and _w(states[-1]) > 0                     # back out past R = 20, outbound
    back = TR.time_reverse(run)
    for k in range(EVENT_STEPS):
        C.step(back)
        assert back.atoms == _T(states[EVENT_STEPS - 1 - k]), k            # every intermediate state, not just the end
    assert back.J_cache == C.impulse(C.relative(POS, *states[0]), H / 2, MOM)
    assert TR.time_reverse(back).atoms == states[0]


def test_the_reverse_run_asks_no_rounding_question_the_forward_run_did_not_decide(monkeypatch):
    asked = []
    real = C.impulse

    def recording(dr, dt_kick, profile):
        asked.append((tuple(dr), dt_kick))
        return real(dr, dt_kick, profile)
    monkeypatch.setattr(C, "impulse", recording)
    run = _run((Q(49, 5), Q(2), Q(0)), (Q(-12), Q(0), Q(0)))                # R ~ 10: through the inner wall
    assert run.validation["validation_status"] == "numerical_validated"     # D_valid H part: no start-radius limit
    for _ in range(700):
        C.step(run)
    forward = set(asked)
    for keep_cache in (True, False):
        asked.clear()
        back = TR.time_reverse(run)
        if not keep_cache:
            back.J_cache = None
        for _ in range(700):
            C.step(back)
        assert asked and set(asked) <= forward, keep_cache


def test_the_reverse_segment_is_the_forward_segment_moved_by_the_drift_residual(monkeypatch):
    seen = []
    real = C.segment_min_R2
    monkeypatch.setattr(C, "segment_min_R2", lambda a, d: seen.append((a, d)) or real(a, d))
    run = _run(*OUTER_INBOUND)
    f = TR.forward_drift(run)
    C.step(run)
    back = TR.time_reverse(run)
    C.step(back)
    (a0, v), (a1, v1) = seen
    assert a0 == f["q0"] and v == f["vh"] and v1 == tuple(-x for x in v)
    assert a1 == tuple(x + m for x, m in zip(a0, f["moved"]))               # the reverse starts at the stored q1
    assert tuple(x - y for x, y in zip(a1, v)) == tuple(x + e for x, e in zip(a0, f["d"]))   # and ends at q0 + d
    assert all(abs(e) <= UNIT for e in f["d"]) and any(e != 0 for e in f["d"])


def _near_r_min(frac):
    """q0 on +x at the first position grid point above r_min, moving outward; P h/m = (k + frac) grid units per atom,
    so each atom's displacement is rounded down by frac units and the relative residual is d_x = -2 frac units."""
    x0raw = -((-C.L.R_MIN_BOHR.numerator << 48) // C.L.R_MIN_BOHR.denominator)
    q0 = (Q(x0raw, 1 << 48), Q(0), Q(0))
    J0 = C.impulse(q0, H / 2, MOM)
    Praw = MOM.from_exact((2000 + frac) * UNIT * C.AR40_MASS_ME / H)
    atoms = (C.Atom("Ar40", (0, 0, 0), (J0[0] - Praw, 0, 0)), C.Atom("Ar40", (x0raw, 0, 0), (Praw - J0[0], 0, 0)))
    return C.Run(POS, MOM, H, atoms, validated_only=False, initial=atoms), q0[0] - C.L.R_MIN_BOHR


def test_reversal_fails_only_at_the_segment_guard_and_exactly_when_predicted(monkeypatch):
    """A real counterexample (a stress state, E far above 10 De): the forward step is legal, its exact reverse is
    refused by the segment guard because q0 + d lies below r_min, although the stored result would be q0 again."""
    run, gap = _near_r_min(Q(49, 100))
    assert 0 < gap < 2 * Q(49, 100) * UNIT
    s0 = run.atoms
    assert TR.reverse_segment_passes(run) is False
    C.step(run)                                                              # forward: legal
    back = TR.time_reverse(run)
    with pytest.raises(C.PhysicsDomainExceeded, match="drift segment"):
        C.step(back)
    back = TR.time_reverse(run)
    monkeypatch.setattr(C, "R_MIN2", C.R_MIN2 - Q(1, 1 << 40))               # only the guard: the map itself inverts
    C.step(back)
    assert back.atoms == _T(s0)
    monkeypatch.undo()
    run, gap = _near_r_min(Q(1, 5))                                          # residual smaller than the gap
    assert 2 * Q(1, 5) * UNIT < gap
    s0 = run.atoms
    assert TR.reverse_segment_passes(run) is True
    C.step(run)
    back = TR.time_reverse(run)
    C.step(back)
    assert back.atoms == _T(s0)


def test_d_valid_is_not_closed_under_time_reversal():
    """T keeps E_rel and |L| (so b): an H-part state reverses to an H-part state. A canonical F-part state reverses to
    an outbound state that is not canonical: unsupported. Reversal is a map on executor states, not on D_valid."""
    run = _run(*OUTER_INBOUND)
    back = TR.time_reverse(run)
    assert C.relative_energy_enclosure(back, 256) == C.relative_energy_enclosure(run, 256)
    assert back.validation["validation_status"] == run.validation["validation_status"] == "numerical_validated"
    bo = I.orbiting(Q(1, 2))[0]
    st = D.canonical_initial_state("1/2", bo * Q(995, 1000))
    f = C.new_run(I.POS, 40, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=I.MOM)
    assert f.validation["validation_status"] == "numerical_validated"
    assert TR.time_reverse(f).validation["validation_status"] == "unsupported"


def test_premises_are_refused():
    run = _run(*OUTER_INBOUND)
    edge = C.Run(POS, MOM, H, (run.atoms[0], C.Atom("Ar40", run.atoms[1].r, (MOM.lo, 0, 0))))
    with pytest.raises(TR.NotReversible, match="minimum"):
        TR.time_reverse(edge)
    v1 = C.Run(POS, MOM, H, run.atoms, drift="v1")
    with pytest.raises(TR.NotReversible, match="v2"):
        TR.time_reverse(v1)


def test_fault_injection_a_drift_rounding_that_is_not_odd_symmetric_breaks_reversal(monkeypatch):
    """Floor instead of half-even: floor(-x) != -floor(x). The one-step round trip no longer returns: the lemma's
    premise is what the passing tests above depend on."""
    def floor_displacement(pos, mom, a, dt):
        m = C.SPECIES_MASS[a.species]
        return tuple((p * dt / m * (1 << 48)).__floor__() for p in C.drift_momentum(mom, a.p))
    run = _run(*OUTER_INBOUND)
    s0 = run.atoms
    monkeypatch.setattr(C, "displacement", floor_displacement)
    C.step(run)
    back = TR.time_reverse(run)
    C.step(back)
    assert back.atoms != _T(s0)
