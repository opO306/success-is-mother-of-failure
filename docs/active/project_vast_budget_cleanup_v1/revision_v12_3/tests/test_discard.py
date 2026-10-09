from datetime import datetime,timedelta,timezone
import hashlib,json
import pytest
import discard_owned as d

OWNER=dict(instance_id=d.INSTANCE,machine_id=d.MACHINE,country='US',label='lbl',reservation_token='project_v12_a_20261009_181249')


def packet(tmp_path):
    evidence=tmp_path/'evidence.json';evidence.write_text('{"a":1}')
    p=tmp_path/'packet.json'
    p.write_text(json.dumps(dict(owner=OWNER,uninspected_scope=d.UNINSPECTED,provider_state=dict(volumes=[]),
                                 evidence_files={str(evidence):hashlib.sha256(evidence.read_bytes()).hexdigest()})))
    return p,evidence


def approval(tmp_path,p,**overrides):
    now=datetime.now(timezone.utc)
    value=dict(decision=d.DECISION,accepted=True,instance_id=d.INSTANCE,packet_path=str(p),packet_sha256=d.sha(p),
               actual_human_answer='삭제 승인',actual_question='손실 목록 확인 후 삭제?',acknowledged_uninspected_scope=d.UNINSPECTED,
               approved_utc=(now-timedelta(seconds=5)).isoformat(),valid_until_utc=(now+timedelta(seconds=1800)).isoformat())
    value.update(overrides)
    a=tmp_path/'approval.json';raw=json.dumps(value).encode();a.write_bytes(raw)
    return a,hashlib.sha256(raw).hexdigest()


def test_exact_approval_passes(tmp_path):
    p,_=packet(tmp_path);a,digest=approval(tmp_path,p)
    assert d.validate_approval(a,digest,OWNER)[0]['decision']==d.DECISION


@pytest.mark.parametrize('override',[dict(decision='DESTROY'),dict(instance_id=1),dict(packet_sha256='0'*64),dict(accepted=False),
                                     dict(actual_human_answer=''),dict(acknowledged_uninspected_scope=[])])
def test_inexact_approval_refused(tmp_path,override):
    p,_=packet(tmp_path);a,digest=approval(tmp_path,p,**override)
    with pytest.raises(ValueError):d.validate_approval(a,digest,OWNER)


def test_evidence_changed_after_packet_refused(tmp_path):
    p,evidence=packet(tmp_path);a,digest=approval(tmp_path,p)
    evidence.write_text('{"a":2}')
    with pytest.raises(ValueError,match='EVIDENCE_DRIFT'):d.validate_approval(a,digest,OWNER)


def test_expired_or_owner_drift_refused(tmp_path):
    p,_=packet(tmp_path);now=datetime.now(timezone.utc)
    a,digest=approval(tmp_path,p,valid_until_utc=(now-timedelta(seconds=1)).isoformat())
    with pytest.raises(ValueError,match='TIME_WINDOW'):d.validate_approval(a,digest,OWNER)
    a,digest=approval(tmp_path,p)
    with pytest.raises(ValueError):d.validate_approval(a,digest,dict(OWNER,label='other'))


class FakeProvider:
    def __init__(self,status='exited',gone_after=1,volumes=()):
        self.status=status;self.gone_after=gone_after;self.volumes_after=list(volumes);self.destroys=0;self.calls=[]
    def row(self):return dict(id=d.INSTANCE,machine_id=d.MACHINE,country='US',label='lbl',actual_status=self.status,intended_status='stopped')
    def call(self,*args,json_result=True,timeout=15):
        self.calls.append(args)
        if args[:2]==('show','instance'):return self.row()
        if args[0]=='destroy':self.destroys+=1;return b'destroying'
        raise AssertionError(args)
    def instances(self,timeout=15):return [] if self.destroys>=self.gone_after else [self.row()]
    def volumes(self,timeout=15):return self.volumes_after


class Clock:
    def __init__(self):self.t=0.0
    def now(self):return self.t
    def sleep(self,s):self.t+=max(s,1)


def test_destroy_requires_actual_stop(tmp_path):
    with pytest.raises(ValueError,match='STOP_REQUIRED'):d.destroy_exact(FakeProvider(status='running'),OWNER,[],tmp_path/'j')


def test_destroy_confirmed_only_when_gone_and_volumes_unchanged(tmp_path):
    c=Clock();p=FakeProvider(gone_after=2)
    result=d.destroy_exact(p,OWNER,[],tmp_path/'j',now=c.now,sleep=c.sleep)
    assert result['status']=='DESTROY_CONFIRMED' and result['attempts']==2 and len(list((tmp_path/'j').glob('destroy_attempt_*.json')))==2
    with pytest.raises(ValueError,match='RESIDUAL_VOLUME'):d.destroy_exact(FakeProvider(volumes=[{'id':1}]),OWNER,[],tmp_path/'k',now=Clock().now,sleep=Clock().sleep)


def test_destroy_never_more_than_three_requests(tmp_path):
    c=Clock();p=FakeProvider(gone_after=99)
    result=d.destroy_exact(p,OWNER,[],tmp_path/'j',now=c.now,sleep=c.sleep)
    assert result['status']=='DESTROY_UNCONFIRMED' and p.destroys==3
    with pytest.raises(ValueError,match='ATTEMPTS_EXCEEDED'):d.destroy_exact(p,OWNER,[],tmp_path/'j',now=c.now,sleep=c.sleep)


def test_settle_extension_then_unchanged_reconcile(tmp_path,monkeypatch):
    from budget import Ledger
    import cleanup
    ledger=tmp_path/'ledger.jsonl';L=Ledger(ledger)
    L.append(dict(action='INIT',cap='1',historical_bound='0.1'))
    L.append(dict(action='RESERVE',token=OWNER['reservation_token'],amount='0.05'))
    L.append(dict(action='RESERVE',token=d.EXTENSION_TOKEN,amount='0.06'))
    seen=[]
    monkeypatch.setattr(cleanup,'reconcile_destroyed',lambda provider,owner,out,path,destroyed,receipt_name:seen.append(owner) or dict(remaining_after_pending='x'))
    with pytest.raises(ValueError):d.settle(None,OWNER,tmp_path,ledger,dict(status='DESTROY_UNCONFIRMED',instance_id=d.INSTANCE))
    d.settle(None,dict(OWNER,extension_reservations=[1]),tmp_path,ledger,dict(status='DESTROY_CONFIRMED',instance_id=d.INSTANCE))
    active=L.balances(L.read()[0])['active']
    assert d.EXTENSION_TOKEN not in active and OWNER['reservation_token'] in active  # main token is the unchanged reconcile's job
    assert 'extension_reservations' not in seen[0]
