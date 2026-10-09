from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from campaign import start_owned_once
from lifecycle import stop_owned
from admin_revalidation import AdministrativeUnavailable,SafetyStop

class Provider:
    def __init__(self,start=b'starting instance 55040957.',stop=b'stopping instance 55040957.'):
        self.start=start;self.stop=stop;self.calls=[]
    def call(self,*args,**kwargs):
        self.calls.append(args)
        if args[0]=='start':return self.start
        if args[0]=='stop':return self.stop
        return dict(id=55040957,machine_id=53859,country='US',label='TEST_ONLY',actual_status='exited',intended_status='stopped')

def owner():return dict(instance_id=55040957,machine_id=53859,country='US',label='TEST_ONLY')

def test_start_success_requires_provider_acceptance():
    p=Provider();start_owned_once(p,owner());assert len(p.calls)==1

def test_cli_zero_queued_output_not_start_success():
    p=Provider(b'Required resources are currently unavailable, state change queued.')
    with pytest.raises(AdministrativeUnavailable):start_owned_once(p,owner())
    assert len(p.calls)==1

def test_arbitrary_start_output_safely_refused():
    p=Provider(b'arbitrary')
    with pytest.raises(SafetyStop):start_owned_once(p,owner())

def test_queued_start_forces_stop_despite_stopped_list(tmp_path):
    p=Provider();clock=[0]
    def sleep(value):clock[0]+=value
    r=stop_owned(p,dict(owner(),start_request_may_be_queued=True,stop_attempt_journal=str(tmp_path)),now=lambda:clock[0],sleep=sleep)
    assert r['status']=='STOP_CONFIRMED' and r['attempts']==1 and any(c[0]=='stop' for c in p.calls)

def test_ordinary_stopped_observation_no_extra_call():
    p=Provider();r=stop_owned(p,owner())
    assert r['status']=='STOP_CONFIRMED' and r['attempts']==0 and all(c[0]!='stop' for c in p.calls)

def test_queue_cancellation_unaccepted_never_confirmed_from_stopped_list(tmp_path):
    p=Provider(stop=b'not accepted');clock=[0]
    def sleep(value):clock[0]+=value
    r=stop_owned(p,dict(owner(),start_request_may_be_queued=True,stop_attempt_journal=str(tmp_path)),seconds=10,now=lambda:clock[0],sleep=sleep)
    assert r['status']=='STOP_UNCONFIRMED' and r['attempts']==3 and r['errors']

def test_parent_and_watchdog_share_three_failed_stop_requests(tmp_path):
    p=Provider(stop=b'not accepted');clock=[0]
    def sleep(value):clock[0]+=value
    owned=dict(owner(),start_request_may_be_queued=True,stop_attempt_journal=str(tmp_path))
    a=stop_owned(p,owned,seconds=30,now=lambda:clock[0],sleep=sleep)
    before=sum(c[0]=='stop' for c in p.calls)
    b=stop_owned(p,owned,seconds=30,now=lambda:clock[0],sleep=sleep)
    assert a['status']==b['status']=='STOP_UNCONFIRMED' and before==3
    assert sum(c[0]=='stop' for c in p.calls)==3 and b['new_attempts']==0


def test_partial_intent_is_reserved_without_parsing_or_extra_fourth_call(tmp_path):
    (tmp_path/'intent_1.json.pending').write_text('{partial')
    p=Provider(stop=b'not accepted');clock=[0]
    def sleep(value):clock[0]+=value
    r=stop_owned(p,dict(owner(),start_request_may_be_queued=True,stop_attempt_journal=str(tmp_path)),seconds=30,now=lambda:clock[0],sleep=sleep)
    assert r['status']=='STOP_UNCONFIRMED' and r['attempts']==3
    assert sum(c[0]=='stop' for c in p.calls)==2
    assert (tmp_path/'intent_1.json.pending').read_text()=='{partial'


def test_partial_ack_is_not_accepted_as_completed_stop(tmp_path):
    import json
    (tmp_path/'intent_1.json').write_text(json.dumps(dict(instance_id=55040957,machine_id=53859)))
    (tmp_path/'ack_1.json.pending').write_text('{partial')
    p=Provider(stop=b'not accepted');clock=[0]
    def sleep(value):clock[0]+=value
    r=stop_owned(p,dict(owner(),start_request_may_be_queued=True,stop_attempt_journal=str(tmp_path)),seconds=30,now=lambda:clock[0],sleep=sleep)
    assert r['status']=='STOP_UNCONFIRMED' and r['attempts']==3
    assert sum(c[0]=='stop' for c in p.calls)==2
