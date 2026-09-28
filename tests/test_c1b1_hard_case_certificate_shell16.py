"""④-4c-10 shell-16 hard-case certificate (same contract as shells 18/17).

The full re-verification of the stored certificate takes minutes even on 32
cores and runs outside the suite (runs/c1b1_hard_case_certificate_shell16_*).
These tests bind the stored object to the current sources, to the generator's
rows from the ④-4c-9 survey (a different implementation), to sampled fresh
recomputation, and to the coverage compositor.
"""
import ast
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json

import pytest

from a_reference import c1b1_hard_case_certificate as CT
from a_reference import c1b1_hard_case_certificate_shell16 as S
from a_reference import c1b1_hard_case_search as G

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'a_reference/fixtures/c1b1_hard_case_certificate_shell16_v1.json'


def _digest(name):
    return sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


@pytest.fixture(scope='module')
def stored():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_guard_value_reproduces_the_pinned_shell16_guard():
    _, lo, hi, guard, record = G.load_shell(16)
    mine, residual, error = CT.guard_value(lo, hi, CT.RESIDUAL_BITS)
    assert mine == guard
    assert [str(x) for x in residual] == record['residual_interval_ulps']
    assert str(error) == record['numeric_error_ulps']


def test_small_shell16_slice_builds_verifies_and_round_trips():
    dom = S.domain()
    small = {**dom, 'hi': dom['lo']+S.BLOCK_POINTS*16-1}
    ranges = CT.H.blocks(small['lo'], small['hi'], S.BLOCK_POINTS, 2)
    cert = CT.build(ranges, small, S.BLOCK_POINTS)
    wire = json.loads(json.dumps(CT.T.serial(cert)))
    assert CT.verify_certificate(wire, small) == small
    bad = json.loads(json.dumps(wire))
    bad['superblocks'][0]['crossings'] += 1
    with pytest.raises(CT.O.NotCertified):
        CT.verify_certificate(bad, small)


def test_driver_does_not_import_survey_drivers_and_does_not_edit_the_contract():
    tree = ast.parse((ROOT/'a_reference/c1b1_hard_case_certificate_shell16.py').read_text(encoding='utf-8'))
    names = {a.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for a in node.names}
    assert not names & {'c1b1_hard_case_survey', 'c1b1_hard_case_survey_shell17', 'c1b1_hard_case_survey_shell16'}
    shell17 = json.loads((ROOT/S.CERTIFICATE_17).read_text(encoding='utf-8'))
    assert _digest('a_reference/c1b1_hard_case_certificate.py') == \
        shell17['source_sha256']['a_reference/c1b1_hard_case_certificate.py']
    assert _digest('a_reference/c1b1_hard_case_certificate_shell17.py') == \
        shell17['source_sha256']['a_reference/c1b1_hard_case_certificate_shell17.py']


def test_region_budget_before_shell16_is_fourteen():
    run, legacy, boundaries, families, shell18, shell17 = S.layers()
    assert len(legacy)+len(boundaries)+len(families)+3 == 14


# ---- stored full certificate ----

def test_stored_certificate_is_bound_to_current_sources(stored):
    for name, digest in stored['source_sha256'].items():
        assert _digest(name) == digest, name
    for name in (S.S17.SHELL18_CERTIFICATE, S.CERTIFICATE_17):
        assert stored['prior_fixture_sha256'][name] == _digest(name)
    assert stored['certificate']['foundation_sha256'] == {**CT.K.FOUNDATION_HASHES, **CT.FOUNDATION_HASHES}


def test_stored_certificate_headline(stored):
    cert = stored['certificate']
    assert stored['expected_domain'] == cert['domain'] == S.domain()
    assert (cert['version'], cert['status'], cert['global_4_4b']) == (CT.VERSION, 'certified', 'NotCertified')
    assert (cert['block_points'], len(cert['superblocks'])) == (S.BLOCK_POINTS, S.SUPERBLOCKS)
    assert cert['required_bits'] == CT.RESIDUAL_BITS <= 16384
    assert [s['stage'] for s in stored['stages']] == [
        'build', 'verify', 'verify_stored_json', 'coverage_with_shell18_shell17_and_shell16_reverified']


def test_stored_rows_equal_the_generator_rows_of_the_shell16_survey(stored):
    survey = json.loads((ROOT/'a_reference/fixtures/c1b1_hard_case_survey_shell16_v1.json').read_text(encoding='utf-8'))
    mine = [(r['range'], r['derivative_bound'], r['crossings'], r['candidate_intervals'])
            for r in stored['certificate']['superblocks']]
    theirs = [(r['superblock'], r['derivative_bound'], r['crossings'], r['candidate_intervals'])
              for r in survey['superblock_rows']]
    assert mine == theirs
    assert stored['certificate']['candidate_count'] == survey['full_run']['candidate_count']


def test_sampled_stored_rows_recompute_exactly(stored):
    cert = stored['certificate']
    guard = F(cert['guard'])
    rows = cert['superblocks']
    with_candidates = next(i for i, r in enumerate(rows) if r['candidate_intervals'])
    for i in sorted({0, with_candidates, len(rows)-1}):
        a0, b0 = rows[i]['range']
        assert CT._recompute_row((a0, b0, guard, cert['block_points'])) == rows[i]


def test_stored_coverage_recomposes(stored, monkeypatch):
    """Fresh composition over all layers; only the three multi-minute certificate re-verifications
    (shells 18, 17, 16) are replaced by identity checks against their stored objects."""
    run, legacy, boundaries, families, shell18, shell17 = S.layers()
    expected = {id(shell18[0]): shell18[1], id(shell17[0]): shell17[1],
               id(stored['certificate']): stored['expected_domain']}

    def identity(cert, dom, **kwargs):
        assert expected[id(cert)] == dom
        return dom
    monkeypatch.setattr(CT, 'verify_certificate', identity)
    fresh = CT.check_outgoing_coverage(run, F(2), legacy, boundaries, families,
                                       (shell18, shell17, (stored['certificate'], stored['expected_domain'])))
    assert json.loads(json.dumps(CT.T.serial(fresh))) == stored['coverage']
    gaps = fresh['uncovered_intervals']
    assert fresh['used_regions'] == 14 and fresh['status'] == 'not_certified'
    assert not any(g['shell_index'] in (16, 17, 18) for g in gaps)
