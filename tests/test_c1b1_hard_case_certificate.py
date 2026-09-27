"""④-4c-6 shell-18 formal certificate: independent re-derivation, coverage
composition, and fault injection.

survey_only artifacts (c1b1_hard_case_search/_survey) are separate from this
certificate contract; nothing here reads or trusts the earlier survey
fixture's claims.
"""
import ast
import copy
from fractions import Fraction as F
from pathlib import Path

import pytest

from a_reference import c1b1_family_checker as K
from a_reference import c1b1_hard_case_certificate as CT
from a_reference import c1b1_hard_case_checker as H

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def small_domain():
    lo = 312500000000000000
    hi = lo+CT.SHELL_18_BLOCK_LENGTH*64-1
    return {'kind': 'axis_lattice_interval', 'axis': 0, 'lo': lo, 'hi': hi}


@pytest.fixture(scope='module')
def small_cert(small_domain):
    ranges = H.blocks(small_domain['lo'], small_domain['hi'], CT.SHELL_18_BLOCK_LENGTH, 2)
    return CT.build(ranges, small_domain, CT.SHELL_18_BLOCK_LENGTH)


def test_guard_value_reproduces_the_pinned_shell18_fixture_guard():
    from a_reference import c1b1_hard_case_search as G
    _, lo, hi, guard, record = G.load_shell(18)
    mine, residual, error = CT.guard_value(lo, hi, CT.RESIDUAL_BITS)
    assert mine == guard
    assert str(residual[0]) == record['residual_interval_ulps'][0]
    assert str(residual[1]) == record['residual_interval_ulps'][1]
    assert str(error) == record['numeric_error_ulps']


def test_build_certificate_verifies(small_domain, small_cert):
    domain = CT.verify_certificate(small_cert, small_domain)
    assert domain == small_domain
    assert small_cert['block_points'] == CT.SHELL_18_BLOCK_LENGTH


def test_build_refuses_when_a_real_hazard_survives(monkeypatch):
    """A synthetic identity + inflated guard has a real hazard; build must refuse."""
    monkeypatch.setattr(K, 'frozen_identity', lambda: ({1: 2, 0: 1}, {1: 7, 0: 1}, {}, {0: 1}))
    monkeypatch.setattr(CT, 'guard_value', lambda a, b, bits: (F(1, 3), (F(0), F(0)), F(0)))
    domain = {'kind': 'axis_lattice_interval', 'axis': 0, 'lo': 1, 'hi': 200}
    with pytest.raises(H.O.NotCertified, match='hazard'):
        CT.build(((1, 200),), domain, 33)


def test_verify_rejects_a_smaller_forged_derivative_bound(small_domain, small_cert):
    bad = copy.deepcopy(small_cert)
    bad['superblocks'] = [dict(r) for r in bad['superblocks']]
    bad['superblocks'][0]['derivative_bound'] = '0'
    with pytest.raises(H.O.NotCertified):
        CT.verify_certificate(bad, small_domain)


@pytest.mark.parametrize('mutate,match', [
    (lambda c: c.update(guard='1/100000000000000000000000000000'), None),
    (lambda c: c.update(candidate_count=c['candidate_count']+1), None),
    (lambda c: c.update(impulse_abs_upper='999999999999999999999'), None),
    (lambda c: c.update(domain={**c['domain'], 'hi': c['domain']['hi']-1}), None),
    (lambda c: c.update(momentum_scale=10**30), None),
    (lambda c: c['foundation_sha256'].__setitem__('a_reference/c1b1_hard_case_checker.py', '0'*64), None),
    (lambda c: c.update(P=tuple((k, v+1 if i == 0 else v) for i, (k, v) in enumerate(c['P']))), None),
    (lambda c: c.update(residual_interval=('0', '0')), None),
    (lambda c: c.update(status='candidate'), None),
    (lambda c: c.update(version='wrong-version'), None),
    (lambda c: c.update(scope='wrong-scope'), None),
    (lambda c: c.update(required_bits=8192), None),
    (lambda c: c.__setitem__('Q_max', c['Q_max']+1), None),
])
def test_verify_rejects_tampered_certificates(small_domain, small_cert, mutate, match):
    bad = copy.deepcopy(small_cert)
    mutate(bad)
    with pytest.raises(H.O.NotCertified):
        CT.verify_certificate(bad, small_domain)


def test_verify_rejects_a_dropped_candidate_interval(small_domain, small_cert):
    """Real shell-18 slices have ~0 candidates, so inject a claimed interval and then drop it."""
    bad = copy.deepcopy(small_cert)
    bad['superblocks'] = [dict(r) for r in bad['superblocks']]
    extra = [[small_domain['lo'], small_domain['lo']]]
    bad['superblocks'][0]['candidate_intervals'] = extra+bad['superblocks'][0]['candidate_intervals']
    with pytest.raises(H.O.NotCertified):
        CT.verify_certificate(bad, small_domain)
    good = copy.deepcopy(small_cert)
    if any(r['candidate_intervals'] for r in good['superblocks']):
        idx = next(i for i, r in enumerate(good['superblocks']) if r['candidate_intervals'])
        good['superblocks'] = [dict(r) for r in good['superblocks']]
        good['superblocks'][idx]['candidate_intervals'] = good['superblocks'][idx]['candidate_intervals'][1:]
        with pytest.raises(H.O.NotCertified):
            CT.verify_certificate(good, small_domain)


def test_verify_rejects_noncontiguous_or_wrong_span_ranges(small_domain, small_cert):
    bad = copy.deepcopy(small_cert)
    bad['superblocks'] = list(bad['superblocks'][:-1])
    with pytest.raises(H.O.NotCertified):
        CT.verify_certificate(bad, small_domain)


def test_verify_rejects_external_domain_mismatch(small_domain, small_cert):
    other = {**small_domain, 'lo': small_domain['lo']+1}
    with pytest.raises(H.O.NotCertified):
        CT.verify_certificate(small_cert, other)


def test_verify_rejects_precision_below_required(small_domain, small_cert):
    with pytest.raises(H.O.NotCertified):
        CT.verify_certificate(small_cert, small_domain, execution_limit=2048)


def test_parallel_and_serial_build_agree(small_domain):
    ranges = H.blocks(small_domain['lo'], small_domain['hi'], CT.SHELL_18_BLOCK_LENGTH, 2)
    serial = CT.build(ranges, small_domain, CT.SHELL_18_BLOCK_LENGTH, workers=1)
    parallel = CT.build(ranges, small_domain, CT.SHELL_18_BLOCK_LENGTH, workers=2)
    assert serial == parallel


def test_certificate_does_not_import_the_survey_driver():
    tree = ast.parse((ROOT/'a_reference/c1b1_hard_case_certificate.py').read_text(encoding='utf-8'))
    names = {a.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for a in node.names}
    assert 'c1b1_hard_case_survey' not in names


def test_check_outgoing_coverage_layers_on_top_of_existing_84_gaps(small_domain, small_cert):
    """The composed coverage never claims more than what actually verifies."""
    from a_reference import c1b1_two_atom as C
    from a_numeric import FixedPoint
    import json
    from a_reference import c1b1_rounding_regions as R
    from a_reference import c1b1_half_ulp_boundaries as HB

    original = json.loads((ROOT/'a_reference/fixtures/c1b1_rounding_regions_v1.json').read_text(encoding='utf-8'))
    legacy = [R.certify_finite_points(original['finite_acceptance']['domain']['points'], bits=256)]
    for c in original['analytic_and_singleton_certificates']:
        d = c['domain']
        legacy.append(R.certify_finite_points(d['points'], bits=c['bits']) if d['kind'] == 'finite_points' else
                      R.certify_axis_zero_region(d['axis'], d['lo'], d['hi'], bits=c['bits']))
    boundary_fixture = json.loads((ROOT/'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json').read_text(encoding='utf-8'))
    boundaries = [(HB.certify_axis_domain(g['certificate']['domain']['axis'], g['certificate']['domain']['lo'],
                                          g['certificate']['domain']['hi']), g['certificate']['domain'])
                  for g in boundary_fixture['groups'] if g['certificate']['status'] == 'certified']
    families_report = json.loads((ROOT/'a_reference/fixtures/c1b1_family_certificates_v1.json').read_text(encoding='utf-8'))
    families = tuple((g['certificate'], g['expected_domain']) for g in families_report['groups'])
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0), (10, 0, 0), (1, 0, 0),
                    momentum_profile=FixedPoint(96, 80))
    before = CT.FC.check_outgoing_coverage(run, F(2), legacy, boundaries, families)
    after = CT.check_outgoing_coverage(run, F(2), legacy, boundaries, families, ((small_cert, small_domain),))
    assert after['used_regions'] == before['used_regions']+1
    # This tiny slice does not cover the full shell 18 axis interval, so the
    # composed coverage must still show it as not fully certified.
    assert after['status'] == 'not_certified'
    assert len(after['uncovered_intervals']) <= len(before['uncovered_intervals'])


def test_coverage_rejects_over_budget_region_count(small_domain, small_cert):
    with pytest.raises(H.O.NotCertified):
        CT.check_outgoing_coverage(None, F(2), (), (), (), ((small_cert, small_domain),)*65)


# ---- regression: a whole superblock must not be treated as one quadratic block ----

def test_rows_match_the_generator_on_the_survey_fixture_superblocks():
    """Cross-implementation check (not the same function checking itself):
    certificate rows vs the generator rows stored by the ④-4c-5 survey."""
    import json
    fixture = json.loads((ROOT/'a_reference/fixtures/c1b1_hard_case_survey_v1.json').read_text(encoding='utf-8'))
    from a_reference import c1b1_hard_case_search as G
    _, lo, hi, _, _ = G.load_shell(18)
    guard, _, _ = CT.guard_value(lo, hi, CT.RESIDUAL_BITS)
    for row in (fixture['superblock_rows'][0], fixture['superblock_rows'][-1]):
        a0, b0 = row['superblock']
        mine = CT._recompute_row((a0, b0, guard, CT.SHELL_18_BLOCK_LENGTH))
        assert mine['derivative_bound'] == row['derivative_bound']
        assert mine['crossings'] == row['crossings']
        assert mine['candidate_intervals'] == row['candidate_intervals']


def test_single_block_superblock_bug_inflates_candidates_and_hits_the_work_limit(small_domain):
    """The mistake that stalled the first full run: one quadratic block per superblock."""
    ranges = H.blocks(small_domain['lo'], small_domain['hi'], CT.SHELL_18_BLOCK_LENGTH, 1)
    whole = small_domain['hi']-small_domain['lo']+1
    split = CT.build(ranges, small_domain, CT.SHELL_18_BLOCK_LENGTH)
    lumped = CT.build(ranges, small_domain, whole)
    assert lumped['candidate_count'] > 100*max(1, split['candidate_count'])


def test_candidate_work_limit_refuses_instead_of_stalling(small_domain, monkeypatch):
    monkeypatch.setattr(CT, 'MAX_CANDIDATES', 0)
    ranges = H.blocks(small_domain['lo'], small_domain['hi'], CT.SHELL_18_BLOCK_LENGTH, 1)
    whole = small_domain['hi']-small_domain['lo']+1
    with pytest.raises(H.O.NotCertified, match='work limit'):
        CT.build(ranges, small_domain, whole)


# ---- stored full shell-18 certificate (a_reference/fixtures/c1b1_hard_case_certificate_v1.json) ----
# The full independent re-verification of this stored JSON takes ~10 minutes
# with 6 workers and was run once outside the suite
# (runs/c1b1_hard_case_certificate_20260928/verify_wire.log). The tests below
# tie the stored object to the current sources, to the separate generator's
# rows, to sampled fresh recomputation, and to the coverage compositor.

@pytest.fixture(scope='module')
def stored():
    import json
    return json.loads((ROOT/'a_reference/fixtures/c1b1_hard_case_certificate_v1.json').read_text(encoding='utf-8'))


def test_stored_certificate_is_bound_to_current_sources(stored):
    from hashlib import sha256
    for name, digest in stored['source_sha256'].items():
        assert sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest, name
    assert stored['certificate']['foundation_sha256'] == {**K.FOUNDATION_HASHES, **CT.FOUNDATION_HASHES}


def test_stored_certificate_headline(stored):
    from a_reference import c1b1_hard_case_search as G
    cert = stored['certificate']
    _, lo, hi, _, _ = G.load_shell(18)
    assert stored['expected_domain'] == cert['domain'] == {'kind': 'axis_lattice_interval', 'axis': 0, 'lo': lo, 'hi': hi}
    assert (cert['status'], cert['global_4_4b'], cert['candidate_count']) == ('certified', 'NotCertified', 109)
    assert (cert['block_points'], len(cert['superblocks'])) == (CT.SHELL_18_BLOCK_LENGTH, CT.SHELL_18_SUPERBLOCKS)
    assert cert['required_bits'] == CT.RESIDUAL_BITS <= 16384


def test_stored_rows_equal_the_separate_generator_rows_on_all_superblocks(stored):
    """Certificate rows (checker implementation) vs survey rows (generator implementation)."""
    import json
    survey = json.loads((ROOT/'a_reference/fixtures/c1b1_hard_case_survey_v1.json').read_text(encoding='utf-8'))
    mine = [(r['range'], r['derivative_bound'], r['crossings'], r['candidate_intervals'])
            for r in stored['certificate']['superblocks']]
    theirs = [(r['superblock'], r['derivative_bound'], r['crossings'], r['candidate_intervals'])
              for r in survey['superblock_rows']]
    assert mine == theirs


def test_sampled_stored_rows_recompute_exactly(stored):
    cert = stored['certificate']
    guard = F(cert['guard'])
    rows = cert['superblocks']
    with_candidates = next(i for i, r in enumerate(rows) if r['candidate_intervals'])
    for i in sorted({0, with_candidates, len(rows)-1}):
        a0, b0 = rows[i]['range']
        assert CT._recompute_row((a0, b0, guard, cert['block_points'])) == rows[i]


def test_stored_coverage_recomposes_from_the_stored_certificate(stored, monkeypatch):
    """Fresh composition over the existing layers; only the 10-minute re-verification
    of the stored certificate is replaced by an identity check against it."""
    import json
    from a_reference import c1b1_rounding_diagnosis as T
    from a_reference import c1b1_two_atom as C
    from a_reference import c1b1_rounding_regions as R
    from a_reference import c1b1_half_ulp_boundaries as HB
    from a_numeric import FixedPoint

    def identity(cert, expected, **kwargs):
        assert cert is stored['certificate'] and expected == stored['expected_domain']
        return expected
    monkeypatch.setattr(CT, 'verify_certificate', identity)
    original = json.loads((ROOT/'a_reference/fixtures/c1b1_rounding_regions_v1.json').read_text(encoding='utf-8'))
    legacy = [R.certify_finite_points(original['finite_acceptance']['domain']['points'], bits=256)]
    for c in original['analytic_and_singleton_certificates']:
        d = c['domain']
        legacy.append(R.certify_finite_points(d['points'], bits=c['bits']) if d['kind'] == 'finite_points' else
                      R.certify_axis_zero_region(d['axis'], d['lo'], d['hi'], bits=c['bits']))
    boundary_fixture = json.loads((ROOT/'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json').read_text(encoding='utf-8'))
    boundaries = [(HB.certify_axis_domain(g['certificate']['domain']['axis'], g['certificate']['domain']['lo'],
                                          g['certificate']['domain']['hi']), g['certificate']['domain'])
                  for g in boundary_fixture['groups'] if g['certificate']['status'] == 'certified']
    families_report = json.loads((ROOT/'a_reference/fixtures/c1b1_family_certificates_v1.json').read_text(encoding='utf-8'))
    families = tuple((g['certificate'], g['expected_domain']) for g in families_report['groups'])
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0), (10, 0, 0), (1, 0, 0),
                    momentum_profile=FixedPoint(96, 80))
    fresh = CT.check_outgoing_coverage(run, F(2), legacy, boundaries, families,
                                       ((stored['certificate'], stored['expected_domain']),))
    assert json.loads(json.dumps(T.serial(fresh))) == stored['coverage']
    assert (fresh['used_regions'], len(fresh['uncovered_intervals']), fresh['status']) == (12, 83, 'not_certified')
    assert all(g['shell_index'] != 18 for g in fresh['uncovered_intervals'])


def test_wire_format_certificate_verifies(small_domain, small_cert):
    import json
    from a_reference import c1b1_rounding_diagnosis as T
    wire = json.loads(json.dumps(T.serial(small_cert)))
    assert CT.verify_certificate(wire, small_domain) == small_domain
