"""Runtime Fail-Closed Contract v0 (C1-B1): a step that cannot finish leaves the run EXACTLY as it was.

C.step computes the kick, the drift and every impulse in local variables and writes run.atoms, run.J_cache and
run.t_steps only in its last three lines, after the last check that can refuse. These tests pin that property for
the refusals a real run can meet: ReferenceUndecided (precision cap reached -- forced here by lowering the cap to
128 bits, the executor itself is unchanged), PhysicsDomainExceeded (drift segment into the core) and
ExecutorLimitExceeded (a position leaving its profile's range). A deliberately leaky step shows the check can fail.

The comparison is on the run's raw fields (vars(run)), never through run.validation: that property is a lazy cache
and reading it would change the object being compared.
"""
from fractions import Fraction as Q

import pytest

import a_reference.c1b1_two_atom as C
from a_numeric.profiles import FixedPoint
from a_reference import c1b1_stress_survey as X

POS, MOM, DT = X.POS, X.MOM, X.DT
ULP = Q(1, 1 << 48)
FULL_CAP = C.MAX_PRECISION_BITS
# Found by search at 128 bits: the axis position 20 + 46 ulp is the first one past 20 whose impulse needs 256 bits.
FIRST_IMPULSE_K = 46


def snapshot(run):
    return dict(vars(run))


def canonical_run(e, b_frac):
    st = X.canonical(Q(e), Q(b_frac) * X.RE)
    return C.new_run(POS, DT, st['r_i'], st['p_i'], st['r_j'], st['p_j'], momentum_profile=MOM)


def raw(run):
    i, j = run.atoms
    return (i.r, i.p, j.r, j.p)


def assert_fail_closed(step_fn, run, error):
    before = snapshot(run)
    assert before['_validation'] is None
    with pytest.raises(error):
        step_fn(run)
    after = snapshot(run)
    assert after == before, 'a refused step changed the run'
    assert after['_validation'] is None


def step_until_refused(run, max_steps):
    """Step at the current cap until a step is refused; return the raw states of the accepted steps."""
    seen = [raw(run)]
    while run.t_steps < max_steps:
        before = snapshot(run)
        try:
            C.step(run)
        except C.ReferenceUndecided:
            assert snapshot(run) == before
            return seen
        seen.append(raw(run))
    raise AssertionError('no refusal within max_steps')


def test_first_impulse_refusal_leaves_the_run_unchanged(monkeypatch):
    st = X.canonical(Q(1, 2), Q(0))
    rj = (st['r_j'][0] + FIRST_IMPULSE_K * ULP, Q(0), Q(0))
    run = C.new_run(POS, DT, st['r_i'], st['p_i'], rj, st['p_j'], momentum_profile=MOM)   # admitted at full cap
    assert run.J_cache is None and run.t_steps == 0
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', 128)
    with pytest.raises(C.ReferenceUndecided):                # the refusal comes from the FIRST impulse itself
        C.impulse(C.relative(POS, *run.atoms), DT / 2, MOM)
    assert_fail_closed(C.step, run, C.ReferenceUndecided)
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', FULL_CAP)
    C.step(run)                                              # the same state steps normally at the full cap
    assert run.t_steps == 1


def test_refusal_after_kick_and_drift_leaves_the_run_unchanged(monkeypatch):
    """Step 4 of e = 9 De, b = Re/2 needs 256 bits at its post-drift impulse: the kick and the drift are already
    computed (in locals) when the refusal comes -- the case most exposed to a half-written state."""
    run = canonical_run(9, Q(1, 2))
    for _ in range(3):
        C.step(run)
    assert run.J_cache is not None
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', 128)
    assert_fail_closed(C.step, run, C.ReferenceUndecided)


def test_a_refusal_leaves_no_trace_in_the_trajectory(monkeypatch):
    """Refuse at 128 bits, restore the cap, go on: every raw state equals the plain full-cap run's."""
    n = 60
    ref = canonical_run(9, Q(1, 2))
    expect = [raw(ref)]
    for _ in range(n):
        C.step(ref)
        expect.append(raw(ref))
    run = canonical_run(9, Q(1, 2))
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', 128)
    got = step_until_refused(run, n)
    assert 1 <= run.t_steps < n
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', FULL_CAP)
    while run.t_steps < n:
        C.step(run)
        got.append(raw(run))
    assert got == expect


def test_drift_segment_refusal_leaves_the_run_unchanged():
    ri, rj = (Q(0), Q(-1), Q(0)), (Q(-3), Q(1), Q(0))
    pj = (Q(6000), Q(0), Q(0))                               # ~1000 De: guard test only, as in test_c1b1_two_atom
    run = C.new_run(POS, 40, ri, tuple(-x for x in pj), rj, pj, momentum_profile=MOM, validated_only=False)
    assert_fail_closed(C.step, run, C.PhysicsDomainExceeded)


def test_position_range_refusal_leaves_the_run_unchanged():
    """Positions on FX(40,32) (|r| < 128 bohr), atom j at 127.99 bohr moving outward: the drift leaves the range."""
    small = FixedPoint(40, 32)
    st = X.canonical(Q(9), Q(0))
    p = -st['p_j'][0]                                        # canonical is inbound; flip to outbound
    run = C.new_run(small, DT, (Q(10799, 100), Q(0), Q(0)), (-p, Q(0), Q(0)),
                    (Q(12799, 100), Q(0), Q(0)), (p, Q(0), Q(0)), momentum_profile=MOM)
    for _ in range(200):
        before = snapshot(run)
        try:
            C.step(run)
        except C.ExecutorLimitExceeded:
            assert snapshot(run) == before and run.t_steps > 0
            return
    raise AssertionError('the position range was never exceeded')


def _leaky_step(run):
    """DEFECT FOR THE TEST ONLY: C.step with run.atoms written before the post-drift impulse is decided."""
    pos, mom, dt = run.pos, run.mom, run.dt
    half = dt / 2
    J = run.J_cache if run.J_cache is not None else C.impulse(C.relative(pos, *run.atoms), half, mom)
    atoms = C._kick(mom, run.atoms, J)
    run.atoms = tuple(C._drift(pos, mom, a, dt, rule=run.drift)[0] for a in atoms)
    J = C.impulse(C.relative(pos, *run.atoms), half, mom)
    run.atoms = C._kick(mom, run.atoms, J)
    run.J_cache = J
    run.t_steps += 1


def test_the_fail_closed_check_catches_a_step_that_writes_early(monkeypatch):
    ok = canonical_run(9, Q(1, 2))
    for _ in range(3):
        _leaky_step(ok)                                      # on success the leaky step agrees with the executor
    ref = canonical_run(9, Q(1, 2))
    for _ in range(3):
        C.step(ref)
    assert raw(ok) == raw(ref)
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', 128)
    with pytest.raises(AssertionError, match='changed the run'):
        assert_fail_closed(_leaky_step, ok, C.ReferenceUndecided)
