"""Compact evidence checks; raw full PDFs are not required by a clone."""
from decimal import Decimal
from pathlib import Path
from electronic_pilot.frontend_reference_v0.audit import read,sha

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=ROOT/'docs/active/h2_frontend_reference_v0'
EVIDENCE=PACKAGE/'evidence'


def test_all_compact_evidence_matches_packaging_manifest():
    manifest=read(EVIDENCE/'compact_manifest.json')
    for name,meta in manifest['files'].items():
        path=PACKAGE/name
        assert path.stat().st_size==meta['bytes']
        assert sha(path)==meta['sha256']


def test_original_primary_source_byte_pins():
    records=read(EVIDENCE/'sources.json')['records']
    assert len(records)==3
    first=records[0]
    assert first['sha256']=='55bc19137751110a2162f1aaa2268ff8577d2282dad77e9e89f7872743d3dd6e'
    assert first['url']=='https://arxiv.org/pdf/1007.0322v2'
    assert read(EVIDENCE/'sources.json')['independent_author_groups']==2
    assert read(EVIDENCE/'sources.json')['author_preprint_not_a_third_independent_reference'] is True


def test_separate_image_and_text_transcription_paths():
    rows=read(EVIDENCE/'review_paths.json')['extracted_rows']
    assert '-0.120230341178823(15)' in rows['pachucki_2010_v2']['compact_row']
    assert '-0.1202303411778644' in rows['sims_hagstrom_2006_published']['compact_row']
    assert read(EVIDENCE/'stage_A.json')['stored_minus_primary']=='0E-15'
    assert read(EVIDENCE/'stage_A.json')['uncertainty_difference']=='0E-15'


def test_same_quantity_does_not_claim_same_finite_trial_spaces():
    record=read(EVIDENCE/'stage_B.json')
    assert record['status']=='PHYSICAL_QUANTITY_MATCH_SUPPORTED'
    assert record['identical_trial_spaces'] is False
    assert record['observed_state_spatial_irrep']=='NOT_INDEPENDENTLY_CHECKED'


def test_reference_side_not_given_a_manufactured_pass():
    record=read(EVIDENCE/'stage_C.json')
    assert Decimal(record['second_minus_first_hartree'])==Decimal('9.586e-13')
    assert record['within_reported_uncertainty'] is None
    assert record['status']=='REFERENCE_SIDE_UNRESOLVED'
    assert record['meaningful_reference_disagreement'] is False


def test_every_unclosed_downstream_stage_is_unexecuted():
    assert all(row['status']=='NOT_EXECUTED' for row in read(EVIDENCE/'downstream.json').values())
    result=read(EVIDENCE/'summary.json')
    assert result['new_energy_calculations']==result['AO_calls']==result['MO_transform_calls']==result['CI_calls']==0
    assert result['classifications']['FINITE_BASIS_LIMIT_SUPPORTED'] is False
    assert result['not_certified'] is True


def test_prior_physical_failure_and_counterexample_are_preserved():
    record=read(EVIDENCE/'prior_energy_comparison.json')
    assert Decimal(record['original_criterion'])==Decimal('.001')
    assert Decimal(record['primary_retranscription_direct_signed_difference'])==Decimal('.00219920755725297')
    assert record['within_original_criterion'] is False
    assert record['fresh_energy_run'] is False
    frozen=ROOT/'docs/active/h2_ci_layer_audit_v0/evidence/counterexample.json'
    assert sha(frozen)=='5b83f96032a696a060be049ef80b81c420f9d25f90c719bb37c449bfa791c414'


def test_prior_bindings_preserved_and_no_audit_source_drift():
    preserved=read(EVIDENCE/'preservation.json')
    assert preserved['status']=='UNCHANGED'
    assert preserved['inherited_bindings_checked']==972
    assert preserved['protected_bindings_checked']==1095
    seal=read(EVIDENCE/'execution_seal.json')
    # Raw runs intentionally remain outside Git; do not silently skip a required raw replay.
    for key,expected in seal['bound_sha256'].items():
        if key.startswith('worktree:electronic_pilot/frontend_reference_v0/'):
            assert sha(ROOT/key.split(':',1)[1])==expected


def test_preseal_infrastructure_error_is_disclosed():
    record=read(EVIDENCE/'preseal_error_001.json')
    assert record['status']=='PRESEAL_INFRASTRUCTURE_ERROR_PRESERVED'
    assert record['audit_started'] is False
    assert record['seal_output_created'] is False
