"""Tablet v1 transfer hints: order of measurement only. Uses the same signed original evidence as v0 tests."""
from types import SimpleNamespace
import pytest
from experiments.adaptive_execution_real_learning_pilot_v0.common import canonical
from experiments.adaptive_execution_v1 import environment as ENV
from experiments.adaptive_experience_tablet_v0 import policy, routes
from experiments.adaptive_experience_tablet_v1 import transfer
from tests.test_adaptive_experience_tablet_v0 import archive, request, environment, qualified, read  # noqa: F401 (fixture)

SERIAL_FAST = [63344440951, 63453308798, 63513931309, 63813575137, 63995227386]
W6_FAST = [13467727548, 13496457721, 13508699536, 13514429215, 13579909889]


def other_machine_proposal(archive, cores=6):
    tablet, _, _, entry = archive
    return tablet.load(entry), transfer.propose(tablet.load(entry), request(), qualified(environment(cores)))


def test_other_machine_signed_record_orders_w6_first(archive):
    _, p = other_machine_proposal(archive)
    assert p['decision'] == 'TRY_HINT_FIRST' and p['hint'] == 'W6' and p['authority'] == 'NONE'
    assert p['measure_first'] == ['SERIAL', 'W6'] and p['fallback_order'] == ['W3', 'W4']
    assert p['source']['recorded']['hint']['max'] == 13579909889 < p['source']['recorded']['SERIAL']['min'] == 63344440951
    assert p['current_env_id'] != p['source']['env_id'] and p['repeats_required'] == 5


def test_same_machine_same_session_is_not_a_transfer_hint(archive):
    tablet, root, _, entry = archive
    session = read(root / 'A/session.json')
    p = transfer.propose(tablet.load(entry), request(session['env']), qualified(session['env']), session)
    assert p['decision'] == 'NO_HINT_NEEDS_CALIBRATION' and p['measure_first'][0] == 'SERIAL' and 'hint' not in p


@pytest.mark.parametrize('cores,order', [(4, ['SERIAL', 'W3']), (5, ['SERIAL', 'W3', 'W4']), (1, ['SERIAL'])])
def test_machine_that_cannot_run_w6_gets_no_hint(archive, cores, order):
    _, p = other_machine_proposal(archive, cores)
    assert p['decision'] == 'NO_HINT_NOT_SEPARATED_OR_NOT_EXECUTABLE_HERE' and p['measure_first'] == order


def test_cgroup_quota_below_six_gets_no_hint(archive):
    tablet, _, _, entry = archive
    env = environment(); env['cpu_quota'] = 4; env['env_id'] = ENV.env_id(env)
    p = transfer.propose(tablet.load(entry), request(), qualified(env))
    assert p['decision'] == 'NO_HINT_NOT_SEPARATED_OR_NOT_EXECUTABLE_HERE' and p['measure_first'] == ['SERIAL', 'W3']


def test_cpu_min_goal_never_hinted(archive):
    tablet, _, _, entry = archive
    p = transfer.propose(tablet.load(entry), dict(request(), goal='CPU_MIN'), qualified(environment()))
    assert p['decision'] == 'NO_HINT_GOAL_NOT_ELIGIBLE' and 'hint' not in p


def test_unverified_object_is_refused_as_hint(archive):
    tablet, _, _, entry = archive
    fake = SimpleNamespace(metadata=tablet.load(entry).metadata, session_bytes=tablet.load(entry).session_bytes)
    p = transfer.propose(fake, request(), qualified(environment()))
    assert p['decision'] == 'NO_HINT_REFUSED' and 'hint' not in p


def stub(stats, platform='linux'):
    env = dict(environment(), platform=platform)
    return SimpleNamespace(metadata=dict(stats=stats, profile_id='p', session_id='s', env_id='e', cpu_model='m'),
                           session_bytes=canonical(dict(env=env)))


@pytest.mark.parametrize('stats,platform,want', [
    (dict(SERIAL=dict(wall_ns=dict(min=10, max=20)), W6=dict(wall_ns=dict(min=5, max=10))), 'linux', 'NO_HINT_NOT_SEPARATED_OR_NOT_EXECUTABLE_HERE'),
    (dict(SERIAL=dict(wall_ns=dict(min=10, max=20)), W6=dict(wall_ns=dict(min=5, max=9))), 'windows', 'NO_HINT_PLATFORM_DIFFERS'),
    (dict(SERIAL=dict(wall_ns=dict(min=10, max=20)), W6=dict(wall_ns=dict(min=5, max=9))), 'linux', 'TRY_HINT_FIRST'),
])
def test_past_overlap_or_platform_blocks_hint(monkeypatch, stats, platform, want):
    monkeypatch.setattr(transfer.policy, 'classify', lambda *a, **k: 'TRANSFER_HINT_ONLY')
    assert transfer.propose(stub(stats, platform), request(), qualified(environment()))['decision'] == want


def test_confirmed_here_is_only_a_submission_and_v0_still_serial(archive):
    exp, p = other_machine_proposal(archive)
    r = transfer.judge(p, SERIAL_FAST, W6_FAST, [True] * 5)
    assert r == dict(authority='NONE', decision='HINT_CONFIRMED_SUBMIT_FOR_EXISTING_ADMISSION', method='W6', next_measure=[],
                     observed=dict(SERIAL=dict(min=SERIAL_FAST[0], max=SERIAL_FAST[-1]), hint=dict(min=W6_FAST[0], max=W6_FAST[-1])))
    host = qualified(environment())
    plans = routes.candidates(request(), host)
    assert policy.safe_method('WALL_MIN', plans, experience=exp, request=request(), host_info=host, session=None) == 'SERIAL'


def test_overlap_here_falls_back_to_self_search(archive):
    _, p = other_machine_proposal(archive)
    r = transfer.judge(p, [100, 101, 102, 103, 104], [90, 95, 99, 100, 120], [True] * 5)
    assert r['decision'] == 'FALLBACK_SELF_SEARCH' and r['next_measure'] == ['W3', 'W4'] and r['method'] is None


@pytest.mark.parametrize('flags', [[True] * 4 + [False], [True] * 4, None, [1] * 5])
def test_any_result_difference_is_a_stop_not_a_fallback(archive, flags):
    _, p = other_machine_proposal(archive)
    r = transfer.judge(p, SERIAL_FAST, W6_FAST, flags)
    assert r['decision'] == 'REFUSED_RESULTS_NOT_IDENTICAL' and r['next'] == 'STOP_AND_INVESTIGATE' and r['method'] is None


@pytest.mark.parametrize('serial,hint', [(SERIAL_FAST[:4], W6_FAST), (SERIAL_FAST, W6_FAST + [1]), (SERIAL_FAST, [0] + W6_FAST[1:]),
                                         (SERIAL_FAST, [True] + W6_FAST[1:]), (SERIAL_FAST, [1.5] + W6_FAST[1:]), (None, W6_FAST)])
def test_malformed_repeats_refused(archive, serial, hint):
    _, p = other_machine_proposal(archive)
    with pytest.raises(ValueError, match='EXACT_POSITIVE_INTEGER_REPEATS_REQUIRED'):
        transfer.judge(p, serial, hint, [True] * 5)


def test_judge_requires_a_real_hint_proposal(archive):
    _, p = other_machine_proposal(archive, 4)
    for proposal in (p, None, dict(decision='TRY_HINT_FIRST')):
        with pytest.raises(ValueError, match='NO_HINT_TO_CHECK'):
            transfer.judge(proposal, SERIAL_FAST, W6_FAST, [True] * 5)
