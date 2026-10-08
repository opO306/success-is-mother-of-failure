"""Derived metadata only. Existing inspector signs; existing manager alone approves."""
from . import history
from .policy import HERE,raw_hash
from .fingerprints import policy_hash
from experiments.adaptive_execution_real_learning_pilot_v0.common import canonical,digest,verify,code_manifest_path


def derive(receipt,inspector_public):
    verify(inspector_public,b'REAL_PILOT_RECEIPT\0',receipt)
    b=receipt['body']
    if (b.get('verdict')!='VERIFIED_CONTENT' or b.get('classification')!='FORMAT_EQUIVALENT'
            or b.get('scope')!='HISTORICAL_REVIEW_ONLY' or b.get('original_status')!='REAL_LEARNING_FAIL'
            or b.get('review_code_sha256')!=raw_hash(code_manifest_path()) or b.get('policy_sha256')!=policy_hash() or b.get('new_physics_calls')!=0
            or b.get('independent_replays')!=0 or b.get('formula_independence')!='UNRESOLVED_SHARED_RWFORCE'):
        raise ValueError('CORRECTION_RECEIPT_SCOPE')
    body={k:b[k] for k in ('session_sha256','goal','original_source_sha256','original_manifest_sha256',
              'original_zip_sha256','review_code_sha256','policy_sha256','records')}
    body.update(schema='DERIVED_CONTENT_CORRECTION_V0',classification='FORMAT_EQUIVALENT',
            original_status='REAL_LEARNING_FAIL',scope='HISTORICAL_REVIEW_ONLY',manager_approval='PENDING',
            difference_cause='LEGACY_QP_JSON_V1 insertion order versus canonical persisted mapping order',
            profile_activation='FORBIDDEN_BY_THIS_CERTIFICATE')
    return {'body':body,'inspector_receipt':receipt}


def validate(certificate,inspector_public):
    expected=derive(certificate['inspector_receipt'],inspector_public)
    if canonical(expected)!=canonical(certificate): raise ValueError('CORRECTION_CERTIFICATE_TAMPERED')
    p=history.load_originals(); b=certificate['body']
    if (b['session_sha256']!=digest(p['session']) or b['goal']!=p['session']['goal']
            or any(b[k]!=p[k] for k in ('original_source_sha256','original_manifest_sha256','original_zip_sha256'))
            or len(b['records'])!=10): raise ValueError('CORRECTION_SESSION_OR_PROVENANCE')
    for row,path,raw,obj in zip(b['records'],p['record_paths'],p['record_raw_hashes'],p['records']):
        from .fingerprints import content_hash,legacy_hash,CONTENT_VERSION,LEGACY_VERSION
        if (row.get('source_path')!=path or row.get('raw_sha256')!=raw
                or row.get('legacy_sha256')!=obj['initial_sha256'] or row.get('legacy_sha256')!=legacy_hash(obj['initial_state'])
                or row.get('content_sha256')!=content_hash(obj['initial_state'])
                or row.get('content_version')!=CONTENT_VERSION or row.get('legacy_version')!=LEGACY_VERSION
                or row.get('classification')!='FORMAT_EQUIVALENT' or row.get('replay_errors')!=[]):
            raise ValueError('CORRECTION_RECORD_BINDING')
    return dict(certificate_sha256=digest(certificate),manager_approval='PENDING',scope='HISTORICAL_REVIEW_ONLY',
                original_status='REAL_LEARNING_FAIL',profile_activation='NONE',goal=b['goal'])
