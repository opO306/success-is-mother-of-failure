"""TEST_ONLY: real budget/lifecycle functions, external I/O and clocks faked."""
from decimal import Decimal
from pathlib import Path
import json
import sys
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from budget import Ledger, money, reservation, charge_total
from lifecycle import Provider, stop_owned, destroy_owned, verified_recovery, identity


OWNER = dict(instance_id=7, machine_id=8, country='KR', label='TEST_ONLY_OWNER',run_id='TEST_ONLY')
STOP = dict(status='STOP_CONFIRMED', instance_id=7)
RECOVERED = dict(verified=True, instance_id=7,writer_completion_verified=True,final_files_verified=True)


class Clock:
    def __init__(self): self.value=0
    def now(self): return self.value
    def sleep(self, value): self.value+=value


class Fake:
    def __init__(self, *, show_error=False, actual='running', intended='running', wrong_id=False,
                 list_error=False, volume_change=False, destroy_error=False):
        self.record=dict(id=99 if wrong_id else 7,machine_id=8,country='KR',label='TEST_ONLY_OWNER',
                         actual_status=actual,intended_status=intended)
        self.show_error=show_error; self.list_error=list_error; self.volume_change=volume_change
        self.destroy_error=destroy_error; self.stops=0; self.destroys=0; self.deleted=False
    def call(self,*args,**kwargs):
        if args[:2]==('stop','instance'):
            self.stops+=1; self.show_error=False
            self.record.update(actual_status='exited',intended_status='stopped'); return b'OK'
        if args[:2]==('destroy','instance'):
            self.destroys+=1; self.deleted=True
            if self.destroy_error:raise TimeoutError('DESTROY_RESPONSE_LOST')
            return b'OK'
        if self.show_error:raise TimeoutError('SHOW_DOWN')
        return self.record
    def instances(self,**kwargs):
        if self.list_error:raise TimeoutError('LIST_DOWN')
        return [] if self.deleted else [self.record]
    def volumes(self,**kwargs):return [{'id':123}] if self.volume_change else []


@pytest.mark.parametrize('value',[None,True,-1,'NaN','Infinity','-Infinity'])
def test_unknown_cost_never_zero(value):
    with pytest.raises(Exception):money(value)


@pytest.mark.parametrize('field',['dph_total','storage_cost','inet_up_cost','inet_down_cost'])
def test_missing_offer_price_refuses(field):
    offer=dict(dph_total='2',storage_cost='.2',inet_up_cost='.1',inet_down_cost='.1')
    offer.pop(field)
    with pytest.raises(Exception):reservation(offer,seconds=900,disk_gb=8,up_gb=1,down_gb=1,uncertainty='.02')


def test_total_policy_accepts_price_above_one_hourly():
    offer=dict(dph_total='2',storage_cost='.2',inet_up_cost=0,inet_down_cost=0)
    cost=reservation(offer,seconds=120,disk_gb=8,up_gb=1,down_gb=1,uncertainty='.02')
    assert Decimal(cost['total'])<1


def page(**changes):
    p=dict(success=True,count=1,next_token=None,
           results=[dict(source='instance-7',start=1,end=2,type='instance',amount='.25')])
    p.update(changes);return p


def test_full_provider_amount():assert charge_total([page()])==(Decimal('.25'),1)


@pytest.mark.parametrize('pages',[[],[page(success=False)],[page(next_token='more')],[page(count=0)],
    [page(next_token='more'),page()], [dict(success=True,count=0,results=[])]])
def test_billing_empty_error_duplicate_or_partial_refuses(pages):
    with pytest.raises(Exception):charge_total(pages)


def ledger(path):
    result=Ledger(path);result.append(dict(action='INIT',cap='1.00',historical_bound='.364'));return result


def test_persistent_reservation_not_reset(tmp_path):
    l=ledger(tmp_path/'ledger.jsonl');l.append(dict(action='RESERVE',token='B',amount='.1'))
    events,_=Ledger(l.path).read();assert l.balances(events)['remaining']==Decimal('.536')
    with pytest.raises(ValueError):l.append(dict(action='INIT',cap='1',historical_bound='0'))


def test_duplicate_reservation_blocked(tmp_path):
    l=ledger(tmp_path/'ledger.jsonl');l.append(dict(action='RESERVE',token='B',amount='.1'))
    with pytest.raises(ValueError):l.append(dict(action='RESERVE',token='B',amount='.1'))


def test_overspend_before_rental(tmp_path):
    l=ledger(tmp_path/'ledger.jsonl')
    with pytest.raises(ValueError):l.append(dict(action='RESERVE',token='B',amount='.637'))
    events,_=l.read();assert len(events)==1


def test_settle_requires_destroy_and_keeps_delayed_cost(tmp_path):
    l=ledger(tmp_path/'ledger.jsonl');l.append(dict(action='RESERVE',token='B',amount='.1'))
    with pytest.raises(ValueError):l.append(dict(action='SETTLE',token='B',observed_cost_bound='0',destroy_confirmed=False))
    result=l.append(dict(action='SETTLE',token='B',observed_cost_bound='0',destroy_confirmed=True))
    assert result['spent']==Decimal('.464')


def test_corrupted_ledger_refuses(tmp_path):
    l=ledger(tmp_path/'ledger.jsonl');l.path.write_bytes(l.path.read_bytes().replace(b'0.364',b'0.000'))
    # Replace raw historical value whether formatting was .364 or 0.364.
    l.path.write_bytes(l.path.read_bytes().replace(b'.364',b'.000'))
    with pytest.raises(ValueError):l.read()


def test_outstanding_crash_lock_refuses(tmp_path):
    l=ledger(tmp_path/'ledger.jsonl');l.path.with_suffix('.lock').write_bytes(b'CRASH')
    with pytest.raises(FileExistsError):l.append(dict(action='RESERVE',token='B',amount='.1'))


def test_show_loss_still_sends_owned_stop():
    p=Fake(show_error=True);c=Clock();r=stop_owned(p,OWNER,now=c.now,sleep=c.sleep)
    assert p.stops==1 and r['status']=='STOP_CONFIRMED' and r['errors']


def test_exited_with_running_intent_needs_stop():
    p=Fake(actual='exited',intended='running');c=Clock();r=stop_owned(p,OWNER,now=c.now,sleep=c.sleep)
    assert p.stops==1 and r['status']=='STOP_CONFIRMED'


def test_wrong_owner_not_destroyed():
    with pytest.raises(ValueError):identity(Fake(wrong_id=True).record,OWNER)


def test_stale_stop_receipt_not_destroyed():
    p=Fake();c=Clock()
    with pytest.raises(ValueError):destroy_owned(p,OWNER,RECOVERED,STOP,[],now=c.now,sleep=c.sleep)
    assert p.destroys==0


@pytest.mark.parametrize('proof',[{},dict(verified=False,instance_id=7),dict(verified=True,instance_id=9)])
def test_unrecovered_refuses_destroy(proof):
    p=Fake(actual='exited',intended='stopped');c=Clock()
    with pytest.raises(ValueError):destroy_owned(p,OWNER,proof,STOP,[],now=c.now,sleep=c.sleep)
    assert p.destroys==0


def test_destroy_and_fresh_list_confirmed():
    p=Fake(actual='exited',intended='stopped');c=Clock()
    r=destroy_owned(p,OWNER,RECOVERED,STOP,[],now=c.now,sleep=c.sleep)
    assert r['status']=='DESTROY_CONFIRMED' and p.destroys==1


def test_destroy_lost_response_requires_fresh_list():
    p=Fake(actual='exited',intended='stopped',destroy_error=True);c=Clock()
    r=destroy_owned(p,OWNER,RECOVERED,STOP,[],now=c.now,sleep=c.sleep)
    assert r['status']=='DESTROY_CONFIRMED' and r['errors']


def test_list_timeout_never_means_destroy_confirmed():
    p=Fake(actual='exited',intended='stopped',list_error=True);c=Clock()
    r=destroy_owned(p,OWNER,RECOVERED,STOP,[],now=c.now,sleep=c.sleep)
    assert r['status']=='DESTROY_UNCONFIRMED' and p.destroys==3


def test_residual_volume_prevents_success():
    p=Fake(actual='exited',intended='stopped',volume_change=True);c=Clock()
    with pytest.raises(ValueError):destroy_owned(p,OWNER,RECOVERED,STOP,[],now=c.now,sleep=c.sleep)


def test_partial_remote_writes_never_assumed_empty(tmp_path):
    with pytest.raises(ValueError):verified_recovery(tmp_path,OWNER,True)
    assert verified_recovery(tmp_path,OWNER,False)['basis']=='NO_REMOTE_PROJECT_WRITES'


@pytest.mark.parametrize('raw',[b'null',b'{}',b'{"success":false}',b'[{"id":7},{"id":7}]'])
def test_invalid_provider_list_not_empty(raw,tmp_path):
    def run(*args,**kwargs):return SimpleNamespace(returncode=0,stdout=raw,stderr=b'')
    p=Provider('FAKE',tmp_path,runner=run)
    with pytest.raises(ValueError):p.instances()


def test_direct_destroy_without_final_files_has_zero_provider_calls():
    class NoCalls:
        def call(self,*args,**kwargs):raise AssertionError('NO_PROVIDER_CALL_BEFORE_FINALITY')
    with pytest.raises(ValueError,match='TERMINAL_WRITER_AND_FINAL_FILES'):
        destroy_owned(NoCalls(),OWNER,dict(RECOVERED,final_files_verified=False),STOP,[])
