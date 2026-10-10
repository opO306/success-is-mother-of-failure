"""Other-CPU route check V0: pure checks on the real Vast A resume V1 records. No physics, GPU or paid execution."""
import copy
from pathlib import Path

import pytest
from experiments.adaptive_execution_learning_v1.core import raw_hash, read
from experiments.other_cpu_route_check_v0 import measure as M

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / M.ORIGINAL / 'A'
PROPOSAL = dict(decision='TRY_HINT_FIRST', hint='W6', measure_first=['SERIAL', 'W6'], fallback_order=['W3', 'W4'])


def vast(method, repeat):
    return read(A / f'measurement/{method}_{repeat}.json')


def ledger(method='W6', repeat=0):
    return copy.deepcopy(vast(method, repeat)['service'])


@pytest.mark.parametrize('method,repeat', M.ORDER)
def test_every_vast_record_is_clean_and_matches_the_pinned_fingerprint(method, repeat):
    assert M.fingerprint(M.check_service(method, ledger(method, repeat))) == M.REFERENCE_SHA256


def test_pinned_reference_equals_the_independent_vast_replay():
    replay = read(A / 'replay.json')['14/1000/163']['result']
    result = M.check_service('SERIAL', ledger('SERIAL'))
    keys = M.PASS_FIELDS + ('endpoints_scaled',)
    assert {k: replay[k] for k in keys} == {k: result[k] for k in keys}


def test_one_changed_cell_changes_the_fingerprint():
    result = copy.deepcopy(M.check_service('W6', ledger()))
    result['cells'][0] += 1
    assert M.fingerprint(result) != M.REFERENCE_SHA256


def _pass(s): return s['passes'][0]
def _result(s): return s['passes'][0]['attempts'][0]['result']


MUTATIONS = [
    ('not decided', lambda s: s.update(status='STOP_OUT_OF_RANGE'), 'NOT_A_CLEAN_P163_RUN'),
    ('precision retry', lambda s: s.update(p_sequence=[163, 165]), 'NOT_A_CLEAN_P163_RUN'),
    ('service event', lambda s: s.update(events=[{'pass': 0, 'event': 'DEVICE_ERROR'}]), 'SERVICE_EVENTS'),
    ('other request', lambda s: s.update(N=12), 'REQUEST_DIFFERS'),
    ('other precision', lambda s: _pass(s).update(requested_p=165), 'PRECISION_OR_RESTART'),
    ('not original start', lambda s: _pass(s).update(start='LAST_STATE'), 'PRECISION_OR_RESTART'),
    ('fallback attempt', lambda s: _pass(s)['attempts'].append(copy.deepcopy(_pass(s)['attempts'][0])), 'FALLBACK_OR_RETRY'),
    ('decided at other p', lambda s: s.update(final_p=165), 'NOT_A_CLEAN_P163_RUN'),
    ('two passes counted', lambda s: s.update(n_passes=2), 'NOT_A_CLEAN_P163_RUN'),
    ('plan at other p', lambda s: _pass(s)['attempts'][0]['plan'].update(p=165), 'METHOD_DIFFERS'),
    ('no result', lambda s: _pass(s)['attempts'][0].update(result=None), 'RESULT_NOT_OK'),
    ('result backend mix', lambda s: _result(s).update(backend='CPU_SERIAL'), 'RESULT_NOT_OK'),
    ('runner error', lambda s: _result(s).update(status_class='CPU_RUNNER_ERROR'), 'RESULT_NOT_OK'),
    ('placement unconfirmed', lambda s: _result(s).update(executed_placement_ok=False), 'PLACEMENT_OR_PRECISION'),
    ('effective precision', lambda s: _result(s).update(effective_p=165), 'PLACEMENT_OR_PRECISION'),
    ('attempt differs from pass', lambda s: _result(s)['cells'].__setitem__(0, _result(s)['cells'][0] + 1),
     'ATTEMPT_PASS_DIFFER:cells'),
]


@pytest.mark.parametrize('name,mutate,code', MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_unclean_runs_are_refused(name, mutate, code):
    svc = ledger()
    mutate(svc)
    with pytest.raises(ValueError, match=code):
        M.check_service('W6', svc)


def test_requested_method_must_match_the_executed_plan():
    with pytest.raises(ValueError, match='METHOD_DIFFERS'):
        M.check_service('SERIAL', ledger('W6'))
    with pytest.raises(ValueError, match='METHOD_DIFFERS'):
        M.check_service('W6', ledger('SERIAL'))


def records(walls=None, fingerprints=None):
    out = []
    for method, repeat in M.ORDER:
        obs = vast(method, repeat)['observation']
        wall = obs['wall_ns'] if walls is None else walls[method][repeat]
        fp = M.REFERENCE_SHA256 if fingerprints is None else fingerprints.get((method, repeat), M.REFERENCE_SHA256)
        service = round(vast(method, repeat)['service']['service_wall_s'] * 1e9)
        out.append(dict(method=method, repeat=repeat, wall_ns=wall, cpu_ns=obs['cpu_ns'], service_wall_ns=service,
                        fingerprint=fp))
    return out


def test_vast_numbers_are_stable_and_confirm_the_hint():
    summary = M.summarize(records())
    assert summary['stable'] and summary['pairs_identical'] == [True] * 5
    assert summary['W6']['wall_max_ns'] < summary['SERIAL']['wall_min_ns']
    verdict = M.judged(PROPOSAL, summary)
    assert verdict['decision'] == 'HINT_CONFIRMED_SUBMIT_FOR_EXISTING_ADMISSION' and verdict['authority'] == 'NONE'
    assert verdict['verdict_usable'] is True
    assert summary['SERIAL']['service_wall_median_ns'] == M.VAST_MEDIANS_NS['service_wall']['SERIAL']
    assert summary['W6']['service_wall_median_ns'] == M.VAST_MEDIANS_NS['service_wall']['W6']


def test_unstable_spread_marks_the_verdict_unusable():
    walls = {'SERIAL': [100, 100, 100, 100, 130], 'W6': [10, 10, 10, 10, 10]}
    verdict = M.judged(PROPOSAL, M.summarize(records(walls)))
    assert verdict['decision'] == 'HINT_CONFIRMED_SUBMIT_FOR_EXISTING_ADMISSION'
    assert verdict['verdict_usable'] is False and verdict['usable_reason'] == 'SPREAD_OVER_1_25_NOT_PROFILE_GRADE'


@pytest.mark.parametrize('method,repeat', [('SERIAL', 0), ('W6', 0)])
def test_vast_outer_clocks_pass_the_inspector_clock_rules(method, repeat):
    obj = vast(method, repeat)
    M.check_clock(obj['service'], obj['observation']['wall_ns'], obj['observation']['cpu_ns'])


def test_outer_wall_shorter_than_service_is_refused():
    svc = ledger()
    with pytest.raises(ValueError, match='OUTER_WALL_EXCLUDES_SERVICE'):
        M.check_clock(svc, round(svc['service_wall_s'] * 1e9) - 1, 10 ** 12)


def test_lost_worker_cpu_is_refused():
    svc = ledger()
    attempts = round(_result(svc)['cpu_s'] * 1e9)
    with pytest.raises(ValueError, match='OBSERVED_CPU_EXCLUDES_ATTEMPTS'):
        M.check_clock(svc, 10 ** 12, attempts // 2)


def test_overlapping_times_fall_back_to_self_search():
    walls = {'SERIAL': [100, 101, 102, 103, 104], 'W6': [99, 100, 101, 102, 105]}
    verdict = M.judged(PROPOSAL, M.summarize(records(walls)))
    assert verdict['decision'] == 'FALLBACK_SELF_SEARCH' and verdict['next_measure'] == ['W3', 'W4']


def test_one_differing_result_refuses_the_check():
    summary = M.summarize(records(fingerprints={('W6', 3): '0' * 64}))
    assert summary['pairs_identical'] == [True, True, True, False, True]
    assert M.judged(PROPOSAL, summary)['decision'] == 'REFUSED_RESULTS_NOT_IDENTICAL'


def test_four_repeats_are_refused():
    with pytest.raises(ValueError, match='FIVE_REPEATS'):
        M.summarize(records()[:-1])


def test_non_positive_clock_is_refused():
    walls = {'SERIAL': [0, 1, 1, 1, 1], 'W6': [1, 1, 1, 1, 1]}
    with pytest.raises(ValueError, match='CLOCK_INVALID'):
        M.summarize(records(walls))


@pytest.mark.parametrize('top,stable', [(125, True), (126, False)])
def test_spread_boundary_is_1_25(top, stable):
    walls = {'SERIAL': [100, 100, 100, 100, top], 'W6': [10, 10, 10, 10, 10]}
    summary = M.summarize(records(walls))
    assert summary['SERIAL']['wall_spread_ok'] is stable and summary['W6']['wall_spread_ok'] is True


def test_order_is_the_sealed_resume_order():
    protocol = read(ROOT / 'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/protocol.json')
    assert [list(x) for x in M.ORDER] == protocol['order'] and protocol['stage']['methods'] == list(M.EXPECTED_PLAN)


def test_pinned_source_hashes_match_this_tree():
    assert raw_hash(ROOT / M.A_CODE_SEAL) == M.A_CODE_SEAL_SHA256
    assert raw_hash(ROOT / M.TABLET_CODE_SEAL) == M.TABLET_CODE_SEAL_SHA256
    assert all(raw_hash(ROOT / f) == h for f, h in M.V1_FILES.items())
    assert read(A / 'session.json')['code_manifest_sha256'] == M.A_CODE_SEAL_SHA256


def test_existing_output_directory_is_refused(tmp_path):
    with pytest.raises(FileExistsError):
        M.main(['--out', str(tmp_path), '--phase', 'preflight'])


def _fake_service(monkeypatch, differ_at=None):
    """run_request replaced by the stored Vast ledgers (clocks zeroed); no physics."""
    from experiments.adaptive_execution_v1 import experience as EXP
    from experiments.adaptive_execution_v1 import service as SVC
    calls = []

    def fake(req, strategy, env, perf, store, **kw):
        method = strategy.split('_', 1)[1]
        repeat = sum(1 for c in calls if c == method)
        calls.append(method)
        svc = ledger(method, repeat)
        svc['service_wall_s'] = 0.0
        for pz in svc['passes']:
            pz['cpu_s'] = 0.0
            for a in pz['attempts']:
                a['result']['cpu_s'] = 0.0
        if (method, repeat) == differ_at:
            for target in (_pass(svc), _result(svc)):
                target['cells'][0] += 1
        sum(range(300000))                              # some CPU so the outer clock is positive
        return svc
    monkeypatch.setattr(SVC, 'run_request', fake)
    monkeypatch.setattr(EXP, 'load_store', lambda: None)
    return calls


def test_measure_stops_at_the_first_differing_result_after_saving_it(tmp_path, monkeypatch):
    calls = _fake_service(monkeypatch, differ_at=('W6', 1))
    with pytest.raises(ValueError, match='RESULT_DIFFERS_FROM_VAST:W6_1'):
        M.measure(tmp_path, dict(env={'env_id': 'x'}, boot_id='b'), log=lambda *a, **k: None)
    assert calls == ['SERIAL', 'W6', 'W6']
    saved = read(tmp_path / 'runs/W6_1.json')
    assert saved['fingerprint'] != M.REFERENCE_SHA256 and not (tmp_path / 'runs/SERIAL_1.json').exists()


def test_measure_full_order_with_identical_results(tmp_path, monkeypatch):
    calls = _fake_service(monkeypatch)
    out = M.measure(tmp_path, dict(env={'env_id': 'x'}, boot_id='b'), log=lambda *a, **k: None)
    assert [(r['method'], r['repeat']) for r in out] == list(M.ORDER) and len(calls) == 10
    assert all(r['fingerprint'] == M.REFERENCE_SHA256 for r in out)


def test_measure_refuses_to_start_without_budget(tmp_path, monkeypatch):
    calls = _fake_service(monkeypatch)
    monkeypatch.setattr(M, 'TOTAL_SECONDS', M.PER_RUN_SECONDS - 1)
    with pytest.raises(TimeoutError, match='TOTAL_BUDGET'):
        M.measure(tmp_path, dict(env={'env_id': 'x'}, boot_id='b'), log=lambda *a, **k: None)
    assert calls == [] and read(tmp_path / 'STOP.json')['reason'] == 'TOTAL_BUDGET'
