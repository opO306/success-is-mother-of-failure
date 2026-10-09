from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from admin_revalidation import transfer_on_same_instance,AdministrativeUnavailable,SafetyStop

class Clock:
    value=0
    def now(self):return self.value

def test_same_transfer_reset_then_success(tmp_path):
    clock=Clock();calls=[];checks=[]
    def operation(folder,left):
        calls.append(left);clock.value+=1
        if len(calls)==1:
            (folder/'upload.stderr').write_text('Connection reset')
            raise ValueError('ADMIN_UPLOAD_FAILED')
    result=transfer_on_same_instance(10,tmp_path,operation,lambda:checks.append(1),lambda left:None,now=clock.now)
    assert result==2 and calls==[10,9] and checks

def test_identity_api_latency_cannot_extend_deadline(tmp_path):
    clock=Clock();caps=[];calls=[]
    def identity(left):caps.append(left);clock.value+=left
    with pytest.raises(AdministrativeUnavailable):transfer_on_same_instance(3,tmp_path,lambda *x:calls.append(x),lambda:None,identity,now=clock.now)
    assert caps==[3] and calls==[]

@pytest.mark.parametrize('message',['Permission denied','Host key verification failed','arbitrary failure'])
def test_unclassified_or_security_no_repeat(tmp_path,message):
    calls=[]
    def operation(folder,left):
        calls.append(1);(folder/'upload.stderr').write_text(message);raise ValueError(message)
    with pytest.raises(ValueError):transfer_on_same_instance(10,tmp_path,operation,lambda:None,lambda left:None,now=lambda:0)
    assert len(calls)==1

def test_original_failed_attempt_counts_toward_three(tmp_path):
    calls=[]
    def operation(folder,left):
        calls.append(1);(folder/'upload.stderr').write_text('Connection reset');raise ValueError('reset')
    with pytest.raises(ValueError):transfer_on_same_instance(10,tmp_path,operation,lambda:None,lambda left:None,maximum_attempts=2,now=lambda:0)
    assert len(calls)==2

def test_control_loss_prevents_upload(tmp_path):
    calls=[]
    def control():raise SafetyStop('LOST')
    with pytest.raises(SafetyStop):transfer_on_same_instance(10,tmp_path,lambda *x:calls.append(1),control,lambda left:None,now=lambda:0)
    assert calls==[]
