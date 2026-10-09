from datetime import datetime,timedelta,timezone
import hashlib,json
import pytest
import authority


def record(**overrides):
    now=datetime.now(timezone.utc)
    value=dict(authority.FIXED,actual_human_answer='승인',actual_question='V12.3 새 서버 30분?',
               implementation_request_sha256=authority.sha(authority.HERE/'authorization_request.txt'),
               operational_seal_sha256=authority.sha(authority.HERE/'operational_seal.json'),
               approved_utc=(now-timedelta(seconds=5)).isoformat(),expires_utc=(now+timedelta(seconds=1800)).isoformat())
    value.update(overrides);return value


def write(tmp_path,value,name='approval.json'):
    path=tmp_path/name;raw=json.dumps(value).encode();path.write_bytes(raw)
    return path,hashlib.sha256(raw).hexdigest()


def test_valid_record_passes(tmp_path):
    path,digest=write(tmp_path,record())
    assert authority.require_paid_approval(path,digest)['schema']==authority.SCHEMA


@pytest.mark.parametrize('override',[dict(schema='V12_ACTUAL_BUNDLED_PAID_APPROVAL'),dict(maximum_reservation_usd='0.30'),
    dict(B95_execution_limit=1),dict(actual_human_answer=''),dict(operational_seal_sha256='0'*64),dict(local_project_dynamic_tests=True)])
def test_scope_or_binding_drift_refused(tmp_path,override):
    path,digest=write(tmp_path,record(**override))
    with pytest.raises(ValueError):authority.require_paid_approval(path,digest)


def test_raw_hash_mismatch_refused(tmp_path):
    path,_=write(tmp_path,record())
    with pytest.raises(ValueError,match='RAW_DRIFT'):authority.require_paid_approval(path,'0'*64)


def test_expired_or_too_long_window_refused(tmp_path):
    now=datetime.now(timezone.utc)
    for value in (record(expires_utc=(now-timedelta(seconds=1)).isoformat()),
                  record(approved_utc=now.isoformat(),expires_utc=(now+timedelta(seconds=3601)).isoformat())):
        path,digest=write(tmp_path,value)
        with pytest.raises(ValueError,match='TIME_WINDOW'):authority.require_paid_approval(path,digest)


def test_claim_is_single_use_and_stage_transport_order(tmp_path,monkeypatch):
    monkeypatch.setattr(authority,'USE_ROOT',tmp_path/'use')
    path,digest=write(tmp_path,record())
    with pytest.raises(FileNotFoundError):authority.begin_stage(path,digest)
    authority.claim_paid_approval(path,digest)
    with pytest.raises(FileExistsError):authority.claim_paid_approval(path,digest)
    with pytest.raises(ValueError,match='PAID_STAGE_USE_REQUIRED'):authority.begin_transport(path,digest)
    authority.begin_stage(path,digest);authority.begin_transport(path,digest)
    with pytest.raises(FileExistsError):authority.begin_transport(path,digest)


def test_install_replaces_v12_functions_in_place():
    import execution_authority
    authority.install()
    for name in authority.NAMES:assert getattr(execution_authority,name) is getattr(authority,name)
