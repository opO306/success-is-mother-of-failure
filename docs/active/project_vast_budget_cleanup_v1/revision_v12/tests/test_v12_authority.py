from pathlib import Path
import sys,json,hashlib
from datetime import datetime,timezone,timedelta
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import execution_authority as authority
import campaign

def fixture(tmp_path,monkeypatch):
    base=tmp_path/'base';base.mkdir();(base/'authorization_request.txt').write_bytes(b'TEST_ONLY_IMPLEMENTATION')
    (base/'operational_seal.json').write_bytes(b'TEST_ONLY_STATIC_CANDIDATE')
    monkeypatch.setattr(authority,'BASE',base);monkeypatch.setattr(authority,'USE_ROOT',tmp_path/'uses')
    now=datetime.now(timezone.utc)
    record=dict(schema='V12_ACTUAL_BUNDLED_PAID_APPROVAL',accepted=True,total_cap_usd='2.00',maximum_lease_seconds=1800,maximum_reservation_usd='0.20',new_instance_limit=1,A320_execution_limit=1,B95_execution_limit=0,
        local_project_dynamic_tests=False,physics_calls=0,gpu_calls=0,actual_human_answer='TEST_ONLY_NOT_REAL_AUTHORITY',actual_question='TEST_ONLY',approved_utc=now.isoformat(),expires_utc=(now+timedelta(seconds=3600)).isoformat(),
        implementation_request_sha256=hashlib.sha256((base/'authorization_request.txt').read_bytes()).hexdigest(),operational_seal_sha256=hashlib.sha256((base/'operational_seal.json').read_bytes()).hexdigest())
    def write():
        path=tmp_path/'approval.json';path.write_text(json.dumps(record),encoding='utf-8');return path,hashlib.sha256(path.read_bytes()).hexdigest()
    return record,write

def test_same_paid_approval_cannot_open_second_window_or_stage(tmp_path,monkeypatch):
    record,write=fixture(tmp_path,monkeypatch);path,digest=write()
    authority.claim_paid_approval(path,digest);authority.begin_stage(path,digest)
    with pytest.raises(FileExistsError):authority.claim_paid_approval(path,digest)
    with pytest.raises(FileExistsError):authority.begin_stage(path,digest)
    authority.begin_transport(path,digest)
    with pytest.raises(FileExistsError):authority.begin_transport(path,digest)

@pytest.mark.parametrize('field,value',[('accepted',False),('maximum_lease_seconds',2400),('new_instance_limit',2),('A320_execution_limit',2),('B95_execution_limit',1),('total_cap_usd','10.00'),('gpu_calls',1)])
def test_paid_scope_drift_never_creates_claim(tmp_path,monkeypatch,field,value):
    record,write=fixture(tmp_path,monkeypatch);record[field]=value;path,digest=write()
    with pytest.raises(ValueError):authority.claim_paid_approval(path,digest)
    assert not authority.USE_ROOT.exists()

def test_expired_new_paid_window_is_not_revived(tmp_path,monkeypatch):
    record,write=fixture(tmp_path,monkeypatch);record.update(approved_utc='2026-01-01T00:00:00+00:00',expires_utc='2026-01-01T01:00:00+00:00');path,digest=write()
    with pytest.raises(ValueError,match='TIME_WINDOW'):authority.claim_paid_approval(path,digest)

def test_direct_stage_without_approval_has_zero_provider_calls(tmp_path):
    class NoCalls:
        def instances(self):raise AssertionError('UNAUTHORIZED_PROVIDER')
    with pytest.raises((KeyError,ValueError,TypeError,FileNotFoundError,campaign.SafetyStop)):
        campaign.stage({},'A',NoCalls(),None,None)

@pytest.mark.parametrize('field,value',[('maximum_new_reservation_usd','0.50'),('schema','HISTORICAL_V8_SCOPE'),('lease_seconds',2400),('project_cap_usd','10.00')])
def test_direct_stage_policy_drift_is_rejected_before_provider(tmp_path,monkeypatch,field,value):
    policy=campaign.read(campaign.BASE/'policy.json');policy[field]=value
    class NoCalls:
        def instances(self):raise AssertionError('UNAUTHORIZED_PROVIDER')
    with pytest.raises(campaign.SafetyStop,match='SEALED_POLICY_DRIFT'):
        campaign.stage(policy,'A',NoCalls(),None,None)
