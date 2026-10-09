"""Remote-only: actual original show/control/CheckedCli with fake external I/O."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util,json,os,sys,subprocess,time
import pytest
from transport_reads import transport_class,checked_class
from read_retry import transient_stderr
base=Path(os.environ['V12_2_ORIGINAL_BASE'])
sys.path.insert(0,str(base/'transport'));sys.path.insert(0,str(base))
spec=importlib.util.spec_from_file_location('v12_2_actual_original_transport',base/'transport/controller.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import state_contract as states
AUTH=dict(instance_id=7,machine_id=8,country='KR',hourly_cap_usd='0.25',api_ssh_host='test',api_ssh_port=22,ssh_host='192.0.2.1',ssh_port=44,schema='PROJECT_VAST_DELEGATED_INSTANCE_BINDING_V1',scope='OFFLINE_ONLY',allocation_mode='ADOPT_RUNNING',explicit_user_approval=True,exclusive=True)
RUN=dict(id=7,machine_id=8,country='KR',dph_total='0.05',actual_status='running',intended_status='running',ssh_host='test',ssh_port=22,public_ipaddr='192.0.2.1',ports={'22/tcp':[{'HostPort':'44'}]})

def setup(monkeypatch,tmp_path,replies):
    clock=[0.];calls=[];events=[];outer=[]
    monkeypatch.setattr(time,'monotonic',lambda:clock[0])
    cls=transport_class(m,100,lambda:outer.append(True));t=cls.__new__(cls)
    t.auth=dict(AUTH);t.cli='TEST_ONLY_CLI';t.out=tmp_path;t.index=0;t.start_ns=None;t.armed=None;t.supervisor=None
    t.emit=lambda event,**kw:events.append((event,kw));t.stop_control_check=lambda:None;t.age=lambda:clock[0];t.handoff=lambda:400
    def run(argv,name,timeout,input=None):
        calls.append((tuple(argv),name,timeout));t.index+=1
        item=replies.pop(0)
        if item=='timeout':clock[0]+=timeout;raise subprocess.TimeoutExpired(argv,timeout)
        if isinstance(item,bytes):
            (tmp_path/('%03d_'%t.index+name)).with_suffix('.stderr').write_bytes(item)
            raise RuntimeError('ADMIN_PHASE_FAILED:'+name)
        return json.dumps(item).encode()
    t.run_once=run
    return t,clock,calls,outer

def test_actual_initial_timeout_then_success_within_same_12(monkeypatch,tmp_path):
    t,c,calls,outer=setup(monkeypatch,tmp_path,['timeout',dict(RUN)])
    assert t.show('initial_instance')['_admin_state']=='RUNNING'
    assert [r[2] for r in calls]==[8,4] and c[0]==8 and outer

def test_actual_phase_timeout_then_success_no_new_gate(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,['timeout',dict(RUN)])
    t.control(10)
    assert len(calls)==2 and all('show' in r[0] and 'instance' in r[0] for r in calls)

def test_actual_three_fast_transient_failures_stop(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,[b'ConnectionError']*4)
    with pytest.raises(Exception):t.show('initial_instance')
    assert len(calls)==3

def test_actual_wrong_identity_not_retried(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,[dict(RUN,id=9),dict(RUN)])
    with pytest.raises(ValueError):t.show('initial_instance')
    assert len(calls)==1

def test_actual_mapping_not_retried(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,[dict(RUN,public_ipaddr='192.0.2.99')])
    with pytest.raises(ValueError):t.show('initial_instance')
    assert len(calls)==1

def test_actual_price_not_retried(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,[dict(RUN,dph_total='1')])
    with pytest.raises(ValueError):t.show('initial_instance')
    assert len(calls)==1

def test_actual_server_stopping_blocks_work(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,['timeout',dict(RUN,intended_status='stopped')])
    with pytest.raises(ValueError):t.control(10)
    assert len(calls)==2

def test_actual_phase_deadline_limits_retry(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,['timeout',dict(RUN)])
    with pytest.raises(subprocess.TimeoutExpired):t.control(10,phase_deadline=6)
    assert [r[2] for r in calls]==[6] and c[0]==6

def test_actual_final_after_completion_keeps_exact_stop_check(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,[dict(RUN,actual_status='exited',intended_status='stopped')])
    (tmp_path/'completion.json').write_text('{}')
    t.stop_control_check=lambda:(_ for _ in ()).throw(ValueError('EXECUTION_ALREADY_CLOSED'))
    assert t.show('final_instance',timeout=8)['_admin_state']=='STOPPED' and len(calls)==1

def test_actual_final_queued_start_is_not_stopped(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,[dict(RUN,actual_status='exited',intended_status='running')])
    assert t.show('final_instance',timeout=8)['_admin_state']=='STARTING'

def test_actual_final_deadline_does_not_reset(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,['timeout',dict(RUN)])
    with pytest.raises(subprocess.TimeoutExpired):t.show('final_instance',timeout=8)
    assert len(calls)==1 and c[0]==8

def test_actual_live_job_not_relaunched_on_read_recovery(monkeypatch,tmp_path):
    t,c,calls,_=setup(monkeypatch,tmp_path,['timeout',dict(RUN)])
    (tmp_path/'job_launch_intent.json').write_text('{"already_launched":true}')
    assert t.show('phase_control')['_admin_state']=='RUNNING'
    assert len(calls)==2 and all('start' not in r[0] for r in calls)

def test_checked_initial_timeout_then_valid_identity(monkeypatch):
    clock=[0.];calls=[]
    monkeypatch.setattr(time,'monotonic',lambda:clock[0])
    def run(argv,**kw):
        calls.append((argv,kw['timeout']))
        if len(calls)==1:clock[0]+=kw['timeout'];raise subprocess.TimeoutExpired(argv,kw['timeout'])
        return SimpleNamespace(returncode=0,stdout=json.dumps(RUN).encode(),stderr=b'')
    monkeypatch.setattr(subprocess,'run',run)
    c=checked_class(states,100)('TEST',7,AUTH,initial_role='guardian_initial')
    assert c.show()['id']==7 and [n for _,n in calls]==[8,4]

def test_checked_wrong_identity_immediate_stop(monkeypatch):
    calls=[]
    def run(argv,**kw):calls.append(argv);return SimpleNamespace(returncode=0,stdout=json.dumps(dict(RUN,id=9)).encode(),stderr=b'')
    monkeypatch.setattr(subprocess,'run',run)
    with pytest.raises(ValueError):checked_class(states,time.monotonic()+30)('TEST',7,AUTH).show()
    assert len(calls)==1

def test_checked_stop_reply_loss_mutation_once(monkeypatch):
    calls=[]
    def run(argv,**kw):calls.append(argv);raise subprocess.TimeoutExpired(argv,kw['timeout'])
    monkeypatch.setattr(subprocess,'run',run)
    with pytest.raises(subprocess.TimeoutExpired):checked_class(states,time.monotonic()+30)('TEST',7,AUTH).stop()
    assert len(calls)==1 and 'stop' in calls[0]

def test_checked_stop_observation_transient_then_stopped(monkeypatch):
    calls=[]
    def run(argv,**kw):
        calls.append(argv)
        if len(calls)==1:return SimpleNamespace(returncode=1,stdout=b'',stderr=b'ReadTimeout')
        return SimpleNamespace(returncode=0,stdout=json.dumps(dict(RUN,actual_status='exited',intended_status='stopped')).encode(),stderr=b'')
    monkeypatch.setattr(subprocess,'run',run)
    assert checked_class(states,time.monotonic()+30)('TEST',7,AUTH).show()['intended_status']=='stopped' and len(calls)==2

def test_authentication_error_is_not_transient():
    assert not transient_stderr(b'403 Forbidden ConnectionError')

def test_invalid_or_unspecified_error_is_not_transient():
    assert not transient_stderr(b'invalid JSON') and not transient_stderr(b'unknown error')

def test_known_network_failure_is_transient():
    assert transient_stderr(b'ConnectionError: connection reset by peer')
