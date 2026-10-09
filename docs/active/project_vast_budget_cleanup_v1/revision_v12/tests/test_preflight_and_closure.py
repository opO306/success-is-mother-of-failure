"""TEST_SOURCE_ONLY: no execution authorization; external boundaries faked."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from preflight import require_tools,before_any_rental,require_finite_policy
from closure_policy import file_state,decide,validate_exact_discard_approval
from cleanup import destroy_with_disposition,finite_deadline_ns,setup_states


OWNER={'instance_id':7,'machine_id':8,'country':'KR','label':'TEST_ONLY'}
T='2026-10-09T12:00:00+00:00';DEADLINE='2026-10-09T12:10:00+00:00'
NO='NO_RESEARCH_COMMANDS_ISSUED_BY_THIS_CONTROLLER'


def tools(tmp_path):
    paths={}
    for n in ('vastai','ssh','scp','rsync','key'):
        p=tmp_path/n;p.write_bytes(b'TEST_ONLY');paths[n]=p
    (tmp_path/'key.pub').write_text('ssh-ed25519 TEST_ONLY_PUBLIC',encoding='utf-8')
    return paths


def test_missing_rsync_refuses_before_provider_boundary(tmp_path):
    p=tools(tmp_path);calls=[]
    def run(*args,**kwargs):calls.append(args);raise AssertionError('MISSING_TOOL_MUST_BE_FOUND_BEFORE_VERSION_IO')
    with pytest.raises(ValueError,match='MISSING_RECOVERY_TOOL_BEFORE_RENT:rsync'):
        before_any_rental(p['vastai'],p['key'],{},tmp_path/'receipt',which=lambda n:None if n=='rsync' else str(p[n]),run=run)
    assert calls==[]
    receipt=json.loads((tmp_path/'receipt/preflight_refused.json').read_bytes())
    assert receipt['created_instances']==0 and receipt['status']=='REFUSED_BEFORE_ANY_PROVIDER_CALL'


def test_tool_presence_and_version_are_only_local_evidence(tmp_path):
    p=tools(tmp_path)
    result=require_tools(p['vastai'],p['key'],which=lambda n:str(p[n]),
        run=lambda *a,**kw:SimpleNamespace(returncode=0,stdout=b'VERSION_TEST_ONLY',stderr=b''))
    assert result['status']=='LOCAL_TOOLS_PRESENT_NOT_REMOTE_TRANSPORT_VERIFIED'
    assert result['paths']['rsync']==str(p['rsync'].resolve())


@pytest.mark.parametrize('bad',[1,-1])
def test_bad_version_refuses(tmp_path,bad):
    p=tools(tmp_path)
    with pytest.raises(ValueError,match='VERSION_FAILED'):
        require_tools(p['vastai'],p['key'],which=lambda n:str(p[n]),run=lambda *a,**kw:SimpleNamespace(returncode=bad,stdout=b'',stderr=b'bad'))


def test_finite_protocol_requires_human_loss_consent():
    policy={'schema':'FINITE_SETUP_CLOSURE_V2','lease_seconds':1200,'recovery_seconds':180,'cleanup_seconds':220,
            'recovery_attempts':3,'prelease_setup_loss_consent':{'accepted':False}}
    with pytest.raises(ValueError,match='NO_PRELEASE_FINITE_SETUP_DISCARD_CONSENT_NO_RENT'):require_finite_policy(policy)


def test_no_local_receipt_is_unknown_not_absent():
    assert file_state(owner_id=7)['existence']=='UNKNOWN'


@pytest.mark.parametrize('after_stop,expected',[(False,'UNKNOWN'),(True,'ABSENT_OBSERVED_AFTER_STOP')])
def test_absence_requires_closed_stopped_observation(after_stop,expected):
    state=file_state(owner_id=7,observation={'instance_id':7,'read_complete':True,'exists':False,'after_actual_stop':after_stop})
    assert state['existence']==expected


@pytest.mark.parametrize('observation',[{'instance_id':8,'read_complete':True,'exists':True},
                                     {'instance_id':7,'read_complete':False,'exists':False}])
def test_wrong_or_incomplete_observation_never_confirms(observation):
    with pytest.raises(ValueError):file_state(owner_id=7,observation=observation)


def test_real_presence_without_bytes_is_created_unrecovered():
    assert file_state(owner_id=7,observation={'instance_id':7,'read_complete':True,'exists':True,'after_actual_stop':True})=={
        'existence':'CREATED_UNRECOVERED','recovery':'UNRECOVERED','finality':'FINAL'}


def test_snapshot_recovery_never_becomes_final(tmp_path):
    p=tmp_path/'log';p.write_bytes(b'partial')
    observation={'instance_id':7,'read_complete':True,'exists':True,'content_sha256':hashlib.sha256(b'partial').hexdigest()}
    state=file_state(owner_id=7,observation=observation,local_file=p)
    assert state['finality']=='SNAPSHOT'
    result=decide(OWNER,{'log':state},now_utc=T,deadline_utc=DEADLINE,research_state=NO,important_recovery_verified=True)
    assert result['delete_eligible'] is False


@pytest.mark.parametrize('state',['UNKNOWN','CREATED_UNRECOVERED'])
def test_exact_setup_loss_is_not_automatic_without_consent(state):
    files={'log':{'existence':state}}
    r=decide(OWNER,files,now_utc=DEADLINE,deadline_utc=DEADLINE,research_state=NO,important_recovery_verified=True,recovery_attempts=3)
    assert r['action']=='WAIT_EXPLICIT_DISCARD_APPROVAL' and not r['delete_eligible']


def test_expired_preapproved_setup_can_close_without_claiming_raw_verified():
    r=decide(OWNER,{'runtime_setup.log':{'existence':'CREATED_UNRECOVERED'}},now_utc=DEADLINE,deadline_utc=DEADLINE,
             research_state=NO,important_recovery_verified=True,setup_discard_consent=True)
    assert r['delete_eligible'] and r['raw_verified'] is False and r['accepted_loss_files']=={'runtime_setup.log':'CREATED_UNRECOVERED'}


def test_preapproved_loss_does_not_allow_early_deadline_delete():
    r=decide(OWNER,{'log':{'existence':'UNKNOWN'}},now_utc=T,deadline_utc=DEADLINE,
             research_state=NO,important_recovery_verified=True,setup_discard_consent=True,recovery_attempts=3)
    assert r['action']=='WAIT_UNTIL_PREAPPROVED_DEADLINE' and not r['delete_eligible']


@pytest.mark.parametrize('research_state',['IMPORTANT_WRITES_STARTED','UNKNOWN'])
def test_important_raw_never_uses_setup_waiver(research_state):
    r=decide(OWNER,{'log':{'existence':'UNKNOWN'}},now_utc=DEADLINE,deadline_utc=DEADLINE,
             research_state=research_state,important_recovery_verified=False,setup_discard_consent=True)
    assert r['action']=='PRESERVE_IMPORTANT_RAW' and not r['delete_eligible']


def test_explicit_user_hold_wins_over_preapproved_setup_loss():
    r=decide(OWNER,{'log':{'existence':'UNKNOWN'}},now_utc=DEADLINE,deadline_utc=DEADLINE,
             research_state=NO,important_recovery_verified=True,setup_discard_consent=True,user_hold=True)
    assert r['action']=='HOLD_BY_USER' and not r['delete_eligible']


def test_destroy_without_verified_disposition_has_no_external_calls():
    provider=SimpleNamespace(call=lambda *a,**k:(_ for _ in ()).throw(AssertionError('NO_PROVIDER_CALL')))
    with pytest.raises(ValueError,match='VERIFIED_DISPOSITION_AUTHORITY_REQUIRED'):
        destroy_with_disposition(provider,OWNER,{'delete_eligible':True,'instance_id':7},[])


def test_fake_human_approval_without_raw_and_exact_packet_is_refused(tmp_path):
    p=tmp_path/'packet';p.write_text(json.dumps({'owner':OWNER}))
    raw=tmp_path/'approval';raw.write_text('TEST_ONLY_NOT_AUTHORITY')
    with pytest.raises(ValueError):validate_exact_discard_approval({'raw_path':str(raw)},p,OWNER,now_utc=T)


@pytest.mark.parametrize('raw',[b'{',b'null',b'[]'])
def test_partial_or_wrong_failure_receipt_keeps_absolute_guard(tmp_path,raw):
    (tmp_path/'failure.json').write_bytes(raw)
    assert finite_deadline_ns({'allocation_monotonic_ns':100},tmp_path,{'lease_seconds':1200,'cleanup_seconds':220,'recovery_seconds':180})==980_000_000_100


def test_failure_recovery_window_can_only_shorten_lease_deadline(tmp_path):
    (tmp_path/'failure.json').write_text(json.dumps({'recovery_window_start_monotonic_ns':1_000_000_100}))
    assert finite_deadline_ns({'allocation_monotonic_ns':100},tmp_path,{'lease_seconds':1200,'cleanup_seconds':220,'recovery_seconds':180})==181_000_000_100
