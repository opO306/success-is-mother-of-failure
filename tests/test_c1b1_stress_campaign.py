"""C1-B1 runtime stress campaign (survey_only): deterministic parameter stream, located hot decisions, chunk dedupe."""
from fractions import Fraction as Q

from a_reference import c1b1_stress_campaign as K
from a_reference import c1b1_stress_survey as X


def test_halton_is_the_exact_radical_inverse():
    assert [K.halton(i, 2) for i in range(1, 8)] == [Q(1, 2), Q(1, 4), Q(3, 4), Q(1, 8), Q(5, 8), Q(3, 8), Q(7, 8)]
    assert [K.halton(i, 3) for i in range(1, 5)] == [Q(1, 3), Q(2, 3), Q(1, 9), Q(4, 9)]


def test_stream_scatter_items_are_deterministic_and_inside_the_declared_ranges():
    for i in (1, 2, 3, 5, 6, 7):
        a, b = K.stream_spec(i), K.stream_spec(i)
        assert a == b and a['kind'] == 'stream_scatter' and 'spec_error' not in a
        e = Q(a['label'].split(' e=')[1].split(' ')[0])
        bb = Q(a['label'].split(' b=')[1])
        assert 0 < e < K.E_MAX and 0 <= bb < K.B_MAX_FRAC * X.RE
        assert a['max_steps'] == K.SCATTER_CAP


def test_every_fourth_stream_item_targets_the_orbiting_boundary():
    sp = K.stream_spec(4)
    assert sp['kind'] == 'stream_orbit'
    assert 'spec_error' in sp or sp['max_steps'] == K.ORBIT_CAP


def test_located_hot_decisions_do_not_change_the_trajectory(monkeypatch):
    sp = X.spec('grid', 't', X.canonical(Q(1, 2), Q(1, 2) * X.RE), 6)
    plain = X.run_trajectory(sp, trace=True)
    assert plain['hot'] == []
    monkeypatch.setattr(X.Telemetry, 'HOT_BITS', 128)          # locate every decision
    located = X.run_trajectory(sp, trace=True)
    assert located['trace'] == plain['trace'] and located['decisions'] == plain['decisions']
    assert len(located['hot']) == min(located['decide_calls'], X.Telemetry.HOT_KEEP)
    steps = [h['step'] for h in located['hot']]
    assert steps == sorted(steps) and steps[0] == 0 and steps[-1] == 5
    assert all(h['raw_before_step'] is not None for h in located['hot'])


def test_chunk_dedupe_keeps_the_lowest_item_and_reports_spec_errors(tmp_path):
    def rec(i, key, end='returned_to_start'):
        return {'item': i, 'kind': 'stream_scatter', 'label': f'#{i}', 'transform': None, 'end': end, 'steps': 3,
                'decide_calls': 2, 'decisions': {'128': 2}, 'wall_seconds': 0.1, 'state_key': key, 'hot': [],
                'admission_M': 128, 'd_valid': 'unsupported'}
    recs = [rec(3, 'b'), rec(1, 'a'), rec(2, 'a'),
            {'item': 4, 'kind': 'stream_orbit', 'label': '#4', 'end': 'spec_error', 'spec_error': 'x',
             'decide_calls': 0, 'decisions': {}, 'wall_seconds': 0.0}]
    K.CHUNK, old = 4, K.CHUNK
    try:
        K._finish_chunk(tmp_path, 0, recs, 1.0, lambda m: None)
    finally:
        K.CHUNK = old
    import json
    d = json.loads((tmp_path / 'stream_00000.json').read_text(encoding='utf-8'))
    assert [r['item'] for r in d['records']] == [1, 3] and d['dropped_duplicates'] == ['#2']
    assert len(d['spec_errors']) == 1 and d['aggregate']['precision_all']['decisions'] == 4
    t = json.loads((tmp_path / 'totals.json').read_text(encoding='utf-8'))
    assert t['stream']['trajectories'] == 2 and t['stream']['cross_file_duplicate_states'] == 0


def test_dvalid_statistics_are_kept_apart():
    recs = [{'kind': 'k', 'label': 'a', 'transform': None, 'end': 'returned_to_start', 'steps': 1, 'decide_calls': 1,
             'decisions': {'128': 1}, 'wall_seconds': 0.0, 'd_valid': 'numerical_validated', 'hot': []},
            {'kind': 'k', 'label': 'b', 'transform': None, 'end': 'returned_to_start', 'steps': 1, 'decide_calls': 1,
             'decisions': {'256': 1}, 'wall_seconds': 0.0, 'd_valid': 'unsupported', 'hot': []}]
    a = K.aggregate(recs)
    assert a['precision_by_dvalid']['numerical_validated']['by_precision'] == {'128': 1}
    assert a['precision_by_dvalid']['not_dvalid:unsupported']['by_precision'] == {'256': 1}
