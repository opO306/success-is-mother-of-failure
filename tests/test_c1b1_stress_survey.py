"""C1-B1 runtime stress survey runner (survey_only): the instrumentation must observe, never change, the executor."""
from fractions import Fraction as Q

import pytest

from a_reference import c1b1_stress_survey as X
from a_reference import c1b1_two_atom as C


def _short(kind='grid', e='1/2', b_frac=Q(1, 2), steps=12, transform=None):
    return X.spec(kind, 'test', X.canonical(Q(e), b_frac * X.RE), steps, transform)


def test_instrumentation_restores_the_original_functions_on_every_exit_path():
    decide, enclosure = C._decide, C.relative_energy_enclosure
    with X.instrumented(X.Telemetry()):
        assert C._decide is not decide
    assert C._decide is decide and C.relative_energy_enclosure is enclosure
    with pytest.raises(RuntimeError):
        with X.instrumented(X.Telemetry()):
            raise RuntimeError('boom')
    assert C._decide is decide and C.relative_energy_enclosure is enclosure


def test_telemetry_on_and_off_give_identical_step_by_step_raw_states():
    for sp in (_short(), _short(kind='headon', b_frac=Q(0))):
        on = X.run_trajectory(sp, telemetry=True, trace=True)
        off = X.run_trajectory(sp, telemetry=False, trace=True)
        assert on['trace'] == off['trace']
        assert (on['end'], on['steps'], on.get('exception')) == (off['end'], off['steps'], off.get('exception'))
        assert off['decide_calls'] == 0 and on['decide_calls'] > 0


def test_refusals_are_identical_with_and_without_telemetry(monkeypatch):
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', 64)       # below START: every decision is ReferenceUndecided
    sp = _short(steps=3)
    on, off = X.run_trajectory(sp, telemetry=True), X.run_trajectory(sp, telemetry=False)
    assert on['end'] == off['end']
    assert on['exception'] == off['exception']


def test_decide_calls_are_counted_not_assumed():
    """Step 1 has two impulses (no cache), later steps one. The canonical state starts ON the x axis (relative
    position (20, 0, 0)), so the very first impulse has only one nonzero component even off axis: 1 + 2, then 2 per
    step. Head-on (y exactly 0 throughout): 1 + 1, then 1 per step. The first guess (4 + 2 per step) missed the
    on-axis start -- the reason the runner counts real calls instead of assuming them."""
    off_axis = X.run_trajectory(_short(steps=5))
    head_on = X.run_trajectory(_short(kind='headon', b_frac=Q(0), steps=5))
    assert off_axis['steps'] == head_on['steps'] == 5
    assert off_axis['decide_calls'] == 1 + 2 + 2 * 4
    assert head_on['decide_calls'] == 2 + 1 * 4
    assert sum(off_axis['decisions'].values()) == off_axis['decide_calls']


def test_reference_undecided_is_classified_before_its_base_class():
    assert issubclass(C.ReferenceUndecided, C.ExecutorLimitExceeded)
    assert X.classify(C.ReferenceUndecided('x')) == 'reference_undecided'
    assert X.classify(C.ExecutorLimitExceeded('x')) == 'executor_limit_exceeded'
    assert X.classify(C.IntegratorDomainExceeded('x')) == 'integrator_domain_exceeded'
    assert X.classify(C.PhysicsDomainExceeded('x')) == 'physics_domain_exceeded'
    assert X.classify(ValueError('x')) == 'unexpected_exception'


def test_undecided_trajectory_records_a_repro_state(monkeypatch):
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', 64)
    rec = X.run_trajectory(_short(steps=3))
    assert rec['end'] == 'reference_undecided'
    assert rec['repro']['initial_state'] and 'failed_after_steps' in rec['repro']


def test_dedupe_is_by_stored_state_and_keeps_transforms():
    a = _short()
    b = dict(a, label='same stored state, other label')
    c = dict(a, transform='swap_xy')
    kept, dropped = X.dedupe([a, b, c])
    assert [s['label'] for s in kept] == ['test', 'test'] and dropped == ['same stored state, other label']


@pytest.mark.parametrize('t', ['swap_xy', 'mirror_x', 'swap_atoms'])
def test_symmetry_transforms_carry_the_final_raw_state(t):
    base = X.run_trajectory(_short(steps=8))
    moved = X.run_trajectory(_short(steps=8, transform=t))
    assert moved['steps'] == base['steps'] and moved['end'] == base['end']
    expect = X.transform_raw([[int(x) for x in v] for v in base['final_raw']], t)
    assert [[int(x) for x in v] for v in moved['final_raw']] == [list(v) for v in expect]


def test_admission_precision_is_counted_apart_from_rounding_decisions():
    rec = X.run_trajectory(_short(steps=2))
    assert rec['admission_M'] is not None
    assert all(k != 'admission' for k in rec['decisions'])


def test_hard_case_point_set_is_the_61936_shell_15_to_18_candidates():
    pts = X.hard_case_points()
    per = {s: sum(1 for x, _ in pts if x == s) for s in (15, 16, 17, 18)}
    assert per == {15: 54419, 16: 6581, 17: 827, 18: 109} and len(pts) == 61936
    assert len(set(pts)) == len(pts)


def test_hard_case_statistics_are_kept_apart_from_trajectories():
    rec = X._point_job((18, int(X.hard_case_points((18,))[0][1])))
    assert rec['end'] == 'decided' and 'kind' not in rec
    dist = X.precision_distribution([rec])
    assert list(dist['by_kind']) == ['18']
