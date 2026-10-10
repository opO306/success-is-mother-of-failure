"""V12.5 confirmed-launch disconnect: no network, no Vast, no physics. A local fake 'ssh' delays, then runs the guest script."""
import inspect,json,subprocess,sys,textwrap,time
from pathlib import Path
from types import SimpleNamespace
import pytest
import disconnect_confirm as D

FAKE_SSH=textwrap.dedent('''
    import os,shlex,sys,time
    time.sleep(float(os.environ.get('FAKE_SSH_DELAY','0')))
    parts=shlex.split(sys.argv[-1]);assert parts[1:3]==['-B','-'],parts
    script=sys.stdin.buffer.read();sys.argv=['-',*parts[3:]]
    exec(compile(script,'<guest>','exec'),{'__name__':'__main__'})
''')


class FakeTransport:
    def __init__(self,tmp_path):
        (tmp_path/'fake_ssh.py').write_text(FAKE_SSH)
        self.ssh_argv=[sys.executable,'-B',str(tmp_path/'fake_ssh.py')];self.auth={};self.out=tmp_path;self.index=0;self.armed=None
        self.events=[];self.controls=[]
    def control(self,required):self.controls.append(required)
    def stop_control_check(self):pass
    def emit(self,event,**kw):self.events.append(dict(kw,event=event))


def guest(report,after='time.sleep(20)',code=0):
    return textwrap.dedent(f'''
        import json,sys,time
        root,instance,job_id=sys.argv[1:]
        report={report}
        if report is not None:print(report,flush=True)
        {after}
        sys.exit({code})
    ''').encode()


def report_json(state='RUNNING',job='job_a',instance=7):
    return 'json.dumps(dict(schema="V12_JOB_OBSERVATION",instance_id=%d,job_id="%s",state="%s"))'%(instance,job,state)


def run(t,script,monkeypatch,delay,wait=D.WAIT_SECONDS):
    monkeypatch.setenv('FAKE_SSH_DELAY',str(delay))
    return D.confirmed_launch(t,script,['/workspace/g',7,'job_a'],'job_launch_disconnect',venv='/usr/local/bin/python3',
                              wait_seconds=wait,required_seconds=138)


def test_slow_connection_longer_than_old_two_seconds_is_confirmed_then_cut(tmp_path,monkeypatch):
    t=FakeTransport(tmp_path);start=time.monotonic()
    out=run(t,guest(report_json()),monkeypatch,3)
    elapsed=time.monotonic()-start
    assert json.loads(out.decode().splitlines()[0])['state']=='RUNNING'
    event=t.events[-1]
    assert event['event']=='INTENTIONAL_CLIENT_TERMINATION_AFTER_LAUNCH_REPORT' and event['seconds_to_report']>=3
    assert elapsed<15  # the guest would hold the session for 20 s more: the client was cut, not waited out
    assert t.controls==[138] and t.index==1 and (tmp_path/'001_job_launch_disconnect.stdout').exists()


def test_v12_2_python_repr_report_is_accepted(tmp_path,monkeypatch):
    t=FakeTransport(tmp_path)
    run(t,guest('repr(dict(instance_id=7,job_id="job_a",state="CLAIMED_UNKNOWN_PID",members=[]))'),monkeypatch,0)
    assert t.events[-1]['state']=='CLAIMED_UNKNOWN_PID'


@pytest.mark.parametrize('report',[report_json(state='NOT_CLAIMED'),report_json(job='other'),report_json(instance=8),'"not a report"','None'])
def test_no_valid_launch_report_keeps_the_original_timeout_path(tmp_path,monkeypatch,report):
    t=FakeTransport(tmp_path)
    with pytest.raises(subprocess.TimeoutExpired):run(t,guest(report),monkeypatch,0,wait=2)
    assert t.events[-1]['event']=='COMMAND_EXCEPTION'


def test_guest_failure_before_report_is_a_phase_failure(tmp_path,monkeypatch):
    t=FakeTransport(tmp_path)
    with pytest.raises(RuntimeError,match='ADMIN_PHASE_FAILED:job_launch_disconnect'):run(t,guest('None',after='pass',code=3),monkeypatch,0)
    assert t.events[-1]['event']=='TRANSPORT_EXIT' and t.events[-1]['returncode']==3 and t.events[-1]['launch_reported'] is False


def test_known_hosts_option_is_inserted_like_run_once(tmp_path,monkeypatch):
    seen=[]
    class Fake:
        def __init__(self,argv,**k):seen.append(argv);raise OSError('stop')
    monkeypatch.setattr(D.subprocess,'Popen',Fake)
    t=FakeTransport(tmp_path);t.ssh_argv=['ssh','-p','1','root@h'];t.auth={'known_hosts_file':'K'}
    with pytest.raises(OSError):D.confirmed_launch(t,b'',['/g',7,'j'],'n',venv='v',required_seconds=1)
    assert seen[0][:3]==['ssh','-o','UserKnownHostsFile=K'] and seen[0][-1]=='v -B - /g 7 j'


def test_controller_py_routes_only_the_disconnect_script(tmp_path,monkeypatch):
    calls=[]
    class Base:
        def py(self,script_name,args,name,timeout=30,phase_deadline=None,required_seconds=None):return ('super',script_name)
    (tmp_path/'guest_disconnect_launch.py').write_bytes(b'ORIGINAL_V12_GUEST')
    module=SimpleNamespace(Transport=Base,HERE=tmp_path,VENV='/usr/local/bin/python3')
    D.patch_controller(module);D.patch_controller(module)
    monkeypatch.setattr(D,'confirmed_launch',lambda t,script,args,name,**k:calls.append((script,args,name,k)) or b'ok')
    t=module.Transport()
    assert t.py('guest_job.py',['status'],'job_status',12)==('super','guest_job.py')
    assert t.py('guest_disconnect_launch.py',['/g',7,'j'],'job_launch_disconnect',2,required_seconds=12+96+2)==b'ok'
    assert calls==[(b'ORIGINAL_V12_GUEST',['/g',7,'j'],'job_launch_disconnect',dict(venv='/usr/local/bin/python3',required_seconds=12+96+30))]
    assert module.Transport.__mro__[1] is Base  # patched once


def test_v12_2_probe_path_uses_confirmed_launch_not_fixed_eight_seconds():
    import fresh_owned
    source=inspect.getsource(fresh_owned.v12_2_regression)
    assert 'disconnect_confirm.confirmed_launch(self,(V12_2/\'disconnect_launch.py\').read_bytes()' in source
    assert ",name,8,input=" not in source
