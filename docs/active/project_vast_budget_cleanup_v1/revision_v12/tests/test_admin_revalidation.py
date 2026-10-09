"""Actual readiness core with external boundaries only; executed remotely."""
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from admin_revalidation import ready_on_same_instance,transient_connection,SafetyStop,AdministrativeUnavailable

class Clock:
    value=0
    def now(self):return self.value
    def sleep(self,value):self.value+=value

def test_actual_same_instance_closed_then_ready(tmp_path):
    clock=Clock();seen=[]
    def call(folder,left):
        seen.append((folder.name,left))
        if len(seen)==1:
            (folder/'runtime_probe.stderr').write_text('Connection closed by TEST_ONLY_HOST')
            raise OSError('TEST_ONLY_TRANSIENT')
        return dict(status='READY',actual_container_id='7')
    result=ready_on_same_instance(dict(instance_id=7),180,tmp_path,call,lambda:None,now=clock.now,sleep=clock.sleep)
    assert result['status']=='READY' and len(seen)==2 and clock.value==30
    assert (tmp_path/'attempt_1/readiness.json').exists()

@pytest.mark.parametrize('message',['Host key verification failed','REMOTE HOST IDENTIFICATION HAS CHANGED',
                                  'Permission denied','SAFETY_INSTANCE_ID_MISMATCH','LEASE_WATCHDOG_LOST'])
def test_security_fault_never_transient(message):assert transient_connection(message) is False

def test_actual_wrong_identity_stops_before_retry(tmp_path):
    clock=Clock();seen=[]
    def call(folder,left):seen.append(folder);return dict(status='READY',actual_container_id=99)
    with pytest.raises(SafetyStop):ready_on_same_instance(dict(instance_id=7),180,tmp_path,call,lambda:None,now=clock.now,sleep=clock.sleep)
    assert len(seen)==1

def test_missing_identity_never_ready(tmp_path):
    clock=Clock()
    with pytest.raises(SafetyStop):ready_on_same_instance(dict(instance_id=7),180,tmp_path,lambda *_:dict(status='READY'),lambda:None,now=clock.now,sleep=clock.sleep)

def test_actual_absolute_deadline_not_reset(tmp_path):
    clock=Clock();seen=[]
    def call(folder,left):seen.append(left);clock.value+=left;return dict(status='WAITING',actual_container_id=7)
    with pytest.raises(AdministrativeUnavailable):ready_on_same_instance(dict(instance_id=7),20,tmp_path,call,lambda:None,now=clock.now,sleep=clock.sleep)
    assert seen==[20] and clock.value==20

def test_actual_stop_control_lost_blocks_first_probe(tmp_path):
    clock=Clock();seen=[]
    def control():raise SafetyStop('LEASE_WATCHDOG_LOST')
    with pytest.raises(SafetyStop):ready_on_same_instance(dict(instance_id=7),180,tmp_path,lambda *_:seen.append(1),control,now=clock.now,sleep=clock.sleep)
    assert seen==[]

def test_three_same_instance_attempts_preserve_all_raw(tmp_path):
    clock=Clock();seen=[]
    def call(folder,left):seen.append(folder);return dict(status='WAITING',actual_container_id=7)
    with pytest.raises(AdministrativeUnavailable):ready_on_same_instance(dict(instance_id=7),180,tmp_path,call,lambda:None,now=clock.now,sleep=clock.sleep)
    assert len(seen)==3 and clock.value==60 and all((p/'readiness.json').exists() for p in seen)

def test_arbitrary_error_not_retried_as_transport(tmp_path):
    clock=Clock();seen=[]
    def call(folder,left):seen.append(folder);raise ValueError('ORIGINAL_SOURCE_DRIFT')
    with pytest.raises(ValueError):ready_on_same_instance(dict(instance_id=7),180,tmp_path,call,lambda:None,now=clock.now,sleep=clock.sleep)
    assert len(seen)==1
