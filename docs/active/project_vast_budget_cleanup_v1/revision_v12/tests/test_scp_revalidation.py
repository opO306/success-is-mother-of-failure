"""Use actual Transport.run/control; fake subprocess/API/clock only, remote execution."""
import importlib.util,sys
from pathlib import Path
import pytest
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'transport'))
spec=importlib.util.spec_from_file_location('actual_scp_candidate',BASE/'transport/controller.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Clock:
    value=0
    def now(self):return self.value

class Boundary(m.Transport):
    def __init__(self,out,clock,failures,elapsed=0,api_elapsed=0):
        self.out=out;self.clock=clock;self.failures=list(failures);self.elapsed=elapsed;self.api_elapsed=api_elapsed
        self.index=0;self.calls=[];self.events=[];self.armed=None;self.api_timeouts=[];self.lost=False
    def stop_control_check(self):
        if self.lost:raise RuntimeError('OUTSIDE_STOP_CONTROL_LOST')
    def age(self):return self.clock.value
    def handoff(self):return 400
    def emit(self,event,**fields):self.events.append(event)
    def show(self,name,timeout=12):
        self.api_timeouts.append(timeout);self.clock.value+=min(self.api_elapsed,timeout)
        return dict(_admin_state='RUNNING',_ssh_ready=True)
    def run_once(self,argv,name,timeout,input=None):
        self.index+=1;self.calls.append(argv[0]);self.clock.value+=min(self.elapsed,timeout)
        prefix=self.out/('%03d_'%self.index+name)
        error=self.failures.pop(0) if self.failures else None
        prefix.with_suffix('.stderr').write_text(error or '')
        if error:raise RuntimeError('ADMIN_PHASE_FAILED:'+name)
        return b'TEST_ONLY_TRANSFER_OK'

def setup(monkeypatch,tmp_path,failures,elapsed=0,api_elapsed=0):
    clock=Clock();monkeypatch.setattr(m.time,'monotonic',clock.now)
    return Boundary(tmp_path,clock,failures,elapsed,api_elapsed)

def test_actual_scp_closed_then_success(monkeypatch,tmp_path):
    b=setup(monkeypatch,tmp_path,['Connection closed',None])
    assert b.run(['scp'],'upload',35)==b'TEST_ONLY_TRANSFER_OK' and len(b.calls)==2

def test_actual_three_closed_failure_limit(monkeypatch,tmp_path):
    b=setup(monkeypatch,tmp_path,['Connection closed']*4)
    with pytest.raises(RuntimeError):b.run(['scp'],'upload',35)
    assert len(b.calls)==3

@pytest.mark.parametrize('message',['REMOTE HOST IDENTIFICATION HAS CHANGED','Permission denied'])
def test_actual_security_failure_no_scp_retry(monkeypatch,tmp_path,message):
    b=setup(monkeypatch,tmp_path,[message,None])
    with pytest.raises(RuntimeError):b.run(['scp'],'upload',35)
    assert len(b.calls)==1

def test_actual_guard_lost_no_transfer(monkeypatch,tmp_path):
    b=setup(monkeypatch,tmp_path,[]);b.lost=True
    with pytest.raises(RuntimeError):b.run(['scp'],'upload',35)
    assert b.calls==[]

def test_actual_remaining_one_second_api_bounded(monkeypatch,tmp_path):
    b=setup(monkeypatch,tmp_path,['Connection closed',None],elapsed=34,api_elapsed=12)
    with pytest.raises(TimeoutError):b.run(['scp'],'upload',35)
    assert b.api_timeouts==[1] and b.clock.value==35 and len(b.calls)==1

def test_actual_guest_gate_command_never_repeated(monkeypatch,tmp_path):
    b=setup(monkeypatch,tmp_path,['Connection closed',None])
    with pytest.raises(RuntimeError):b.run(['ssh','TEST_ONLY_GUEST_GATE'],'offline_gate',35)
    assert len(b.calls)==1 and not b.api_timeouts

def test_job_launch_full_window_is_rechecked_after_api_before_ssh(monkeypatch,tmp_path):
    b=setup(monkeypatch,tmp_path,[],api_elapsed=12);b.clock.value=130
    with pytest.raises(TimeoutError):
        b.py('guest_job.py',['launch','TEST_ONLY',7,'job'],'job_launch',12,required_seconds=140+96+12)
    assert b.calls==[] and b.api_timeouts==[12]

def test_identity_safety_stop_is_never_classified_as_connection_loss(monkeypatch,tmp_path):
    from admin_revalidation import SafetyStop
    b=setup(monkeypatch,tmp_path,[])
    assert b.connection_reply_unconfirmed(SafetyStop('ADMIN_INSTANCE_OR_MAPPING_CHANGED')) is False

@pytest.mark.parametrize('message,expected',[('Connection closed',True),('Permission denied; Connection closed',False),('REMOTE HOST IDENTIFICATION HAS CHANGED',False),('Traceback: wrong job',False)])
def test_job_reconnect_classifier_preserves_security_and_integrity(monkeypatch,tmp_path,message,expected):
    b=setup(monkeypatch,tmp_path,[]);b.index=1
    (tmp_path/'001_job_launch.stderr').write_text(message)
    assert b.connection_reply_unconfirmed(RuntimeError('ADMIN_PHASE_FAILED:job_launch')) is expected
