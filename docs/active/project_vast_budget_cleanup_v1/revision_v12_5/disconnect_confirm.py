"""V12.5: intentional SSH disconnect only AFTER the guest reports the job was launched.

Failure fixed (V12.4 paid run, server 55124485): the V12 probe killed the local SSH client after a fixed 2.0 s
(V12.2 probe: 8 s). Connection setup on that host took ~6-7 s, so the client died before the guest script ran;
the job was never claimed and the run stopped (JOB_UNKNOWN_PRESERVE_NO_RELAUNCH).

Designer decision (2026-10-10, "1번으로 고쳐 ㄱㄱ"): wait for the guest's own launch report, then terminate the
client. The guest scripts print the launch observation and keep the SSH session open (V12: 10 s, V12.2: 40 s),
so termination still happens while the session is alive. If no valid report arrives within WAIT_SECONDS the
behaviour is the original one: TimeoutExpired -> reply unconfirmed -> status only, never a relaunch.
Guest scripts, job wrapper, status polling, recovery and all verdicts are the unchanged originals.
"""
import ast,json,shlex,subprocess,time

WAIT_SECONDS=30
LAUNCHED={'CLAIMED_UNKNOWN_PID','RUNNING','FINALIZING','EXITED_SUCCESS','EXITED_FAILURE'}


def launch_report(raw,instance_id,job_id):
    """First stdout line that is the guest's launch observation for exactly this job (JSON or Python repr)."""
    for line in raw.decode('utf-8','replace').splitlines():
        line=line.strip()
        if not line:continue
        try:value=json.loads(line)
        except ValueError:
            try:value=ast.literal_eval(line)
            except (ValueError,SyntaxError):continue
        if (isinstance(value,dict) and value.get('job_id')==job_id and value.get('instance_id')==int(instance_id)
                and value.get('state') in LAUNCHED):
            return value
    return None


def confirmed_launch(t,script,args,name,*,venv,wait_seconds=WAIT_SECONDS,required_seconds):
    """Run a guest launch script over SSH; kill the client as soon as the launch is reported."""
    t.control(required_seconds)
    argv=[*t.ssh_argv,shlex.join([venv,'-B','-',*map(str,args)])]
    if argv[0]=='ssh' and t.auth.get('known_hosts_file'):
        argv=[argv[0],'-o','UserKnownHostsFile='+t.auth['known_hosts_file'],*argv[1:]]
    instance_id,job_id=args[1],args[2]
    t.index+=1
    prefix=t.out/('%03d_'%t.index+name)
    stdout_path,stderr_path=prefix.with_suffix('.stdout'),prefix.with_suffix('.stderr')
    child=None;start=time.monotonic()
    with stdout_path.open('xb') as a,stderr_path.open('xb') as b:
        try:
            t.stop_control_check()
            child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=a,stderr=b)
            child.stdin.write(script);child.stdin.close()
            while True:
                t.stop_control_check()
                if getattr(t,'armed',None) is not None:t.age()
                report=launch_report(stdout_path.read_bytes(),instance_id,job_id)
                if report is not None:
                    child.kill();child.wait(timeout=5)
                    t.emit('INTENTIONAL_CLIENT_TERMINATION_AFTER_LAUNCH_REPORT',phase=name,state=report['state'],
                           seconds_to_report=round(time.monotonic()-start,3),log_prefix=str(prefix))
                    return stdout_path.read_bytes()
                code=child.poll()
                if code is not None:
                    t.emit('TRANSPORT_EXIT',phase=name,returncode=code,log_prefix=str(prefix),launch_reported=False)
                    raise RuntimeError('ADMIN_PHASE_FAILED:'+name)
                if time.monotonic()-start>=wait_seconds:raise subprocess.TimeoutExpired(argv,wait_seconds)
                time.sleep(.2)
        except BaseException as exc:
            if child is not None and child.poll() is None:
                child.kill();child.wait(timeout=5)
            if not isinstance(exc,RuntimeError) or not str(exc).startswith('ADMIN_PHASE_FAILED:'):
                t.emit('COMMAND_EXCEPTION',phase=name,error=repr(exc),log_prefix=str(prefix))
            raise


def make_transport(module):
    class ConfirmedDisconnectTransport(module.Transport):
        v12_5_disconnect=True
        def py(self,script_name,args,name,timeout=30,phase_deadline=None,required_seconds=None):
            if script_name!='guest_disconnect_launch.py':
                return super().py(script_name,args,name,timeout,phase_deadline,required_seconds)
            # Original call: timeout 2, required_seconds = job timeout + 96 + 2. Keep the same reserve for the wait.
            required=(required_seconds if required_seconds is not None else timeout)-timeout+WAIT_SECONDS
            script=(module.HERE/script_name).read_bytes()
            return confirmed_launch(self,script,args,name,venv=module.VENV,required_seconds=required)
    return ConfirmedDisconnectTransport


def patch_controller(module):
    if getattr(module,'v12_5_disconnect_installed',False):return module
    module.Transport=make_transport(module)
    module.v12_5_disconnect_installed=True
    return module
