"""Remote CPU-only administrative simulation. Never invokes B95/A320 or provider commands."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path,PurePosixPath
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import runpy
import io
import contextlib
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[3]
TRANSPORT=BASE/'transport'
OLD=ROOT/'docs/active/bounded_admin_recovery_v0/target_54988176_b_v1/transport'
TRACE=[]
def load_module(name,path):
    if str(path.parent) not in sys.path:sys.path.insert(0,str(path.parent))
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def raw(label): return json.loads((BASE/'fixtures'/f'{label}.json').read_bytes())
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(canonical(obj))
def auth():
    a=json.loads((ROOT/'docs/active/bounded_admin_recovery_v0/target_54988176_b_v1/human_approvals/b_95_es_20261009_082647.json').read_bytes())
    a['run_id']='test_only_admin_simulation';a['expires_utc']='2026-10-09T12:15:00+00:00'
    a['approval_reference']='TEST_ONLY_NO_HUMAN_EXECUTION_AUTHORITY';a['human_approval_text']='SYNTHETIC_INPUT';a['fixture_role']='TEST_ONLY';return a

class Clock:
    def __init__(self):self.value=100.;self.wall_shift=0.;self.hook=lambda:None
    def monotonic(self):return self.value
    def monotonic_ns(self):return int(self.value*1e9)
    def sleep(self,seconds):self.value+=seconds;self.hook()
    def now(self):return datetime(2026,10,9,12,tzinfo=timezone.utc)+timedelta(seconds=self.value-100+self.wall_shift)
    def datetime_type(self):
        clock=self
        class D(datetime):
            @classmethod
            def now(cls,tz=None):return clock.now()
        return D

class Backend:
    """External process/CLI/SSH/SCP boundary only. Core transport methods remain original."""
    def __init__(self,m,out,scenario,clock):
        self.m=m;self.out=out;self.scenario=scenario;self.clock=clock;self.commands=[];self.state='stopped';self.starts=0;self.gates=0;self.stops=0;self.polls=0;self.killed=0
        self.scripts={hashlib.sha256((TRANSPORT/n).read_bytes()).hexdigest():n for n in ('guest_probe.py','guest_source_verify.py','guest_gate.py','guest_recover.py','guest_job.py')}
    def api(self,phase):
        self.polls+=1
        if phase=='initial_instance':r=raw('stopped')
        elif phase=='final_instance':r=raw('final_stopped') if self.state=='stopped' else raw('stopping')
        elif self.state=='stopped':r=raw('stopped')
        else:r=raw('running')
        if self.scenario=='wrong_initial_id' and phase=='initial_instance':r['id']=111
        if self.scenario=='queued_initial' and phase=='initial_instance':r['intended_status']='running'
        if self.scenario=='ports_delay' and phase=='restart_status' and self.polls<4:r.pop('ports',None)
        if self.scenario=='ports_never_ready' and phase=='restart_status':r.pop('ports',None)
        if self.scenario=='wrong_running_port' and phase=='restart_status':r['ports']['22/tcp'][0]['HostPort']='40471'
        if self.scenario=='stop_during_control' and phase=='phase_control':r['intended_status']='stopped'
        if self.scenario=='marker_during_api' and phase=='phase_control':write(self.out/'completion.json',dict(trigger='FAILED'))
        if self.scenario=='final_missing' and phase=='final_instance':r=raw('running')
        if self.scenario=='final_api_error' and phase=='final_instance':raise OSError('MOCK_FINAL_API_FAILURE')
        if self.scenario=='final_wrong_machine' and phase=='final_instance':r['machine_id']=150666
        if self.scenario=='late_clock_drift' and phase=='final_instance':self.clock.wall_shift=20
        if self.scenario=='final_price_violation' and phase=='final_instance':r['dph_total']=1
        return r
    def execute_io(self,argv,input,stdout,stderr):
        phase=Path(stdout.name).stem.split('_',1)[1]
        self.commands.append(dict(phase=phase,argv=list(map(str,argv)),mock=True))
        if argv[0]=='mock_vast':
            if 'start' in argv:self.starts+=1;self.state='running';data={}
            else:data=self.api(phase)
        elif argv[0]=='ssh':
            name=self.scripts[hashlib.sha256(input).hexdigest()] if input is not None else 'guest_job.py'
            if self.scenario=='ssh_fail':return 255
            if name=='guest_probe.py':data=dict(actual_container_id='999' if self.scenario=='container_mismatch' else '54988176')
            elif name=='guest_source_verify.py':
                if self.scenario in ('zip_mismatch','zip_missing'):raise ValueError('MOCK_SOURCE_HASH_OR_MISSING')
                data=dict(status='RAW_SOURCE_VERIFIED')
            elif name=='guest_job.py':
                import shlex
                action=shlex.split(argv[-1])[3]
                if action=='launch':
                    self.gates+=1
                    if self.scenario=='clock_drift':self.clock.wall_shift=20
                spec=json.loads((self.out/'job_spec.json').read_bytes())
                identity=dict(instance_id=54988176,run_id=auth()['run_id'],job_id=auth()['run_id']+'_gate',
                              spec_sha256=hashlib.sha256(canonical(spec)).hexdigest(),boot_id='TEST_ONLY_BOOT',pid=42,pgid=42,startticks=100)
                terminal=dict(identity,returncode=1 if self.scenario=='gate_failure' else 0,error=None,all_descendants_reaped=True,remaining_children=[],subreaper_verified=True)
                data=dict(identity=identity,terminal=terminal,terminal_sha256=hashlib.sha256(canonical(terminal)).hexdigest(),
                          instance_id=54988176,run_id=auth()['run_id'],job_id=auth()['run_id']+'_gate',spec_sha256=identity['spec_sha256'],
                          boot_id='TEST_ONLY_BOOT',state='EXITED_FAILURE' if self.scenario=='gate_failure' else 'EXITED_SUCCESS',writer_completion_verified=True)
                self.job_observation=data
            elif name=='guest_gate.py':
                self.gates+=1
                if self.scenario=='clock_drift':self.clock.wall_shift=20
                data=dict(returncode=1 if self.scenario=='gate_failure' else 0)
            else:data=self.make_evidence()
        elif argv[0]=='scp':
            if phase=='raw_evidence_download':
                if self.scenario=='recovery_disconnect':return 255
                dest=Path(argv[-1]);dest.write_bytes(self.zip_bytes)
                if self.scenario=='recovery_corrupt':dest.write_bytes(b'partial')
                if self.scenario=='marker_during_download':write(self.out/'completion.json',dict(trigger='FAILED'))
            data=None
        else:raise AssertionError('UNAPPROVED_EXTERNAL_COMMAND:'+str(argv))
        if data is not None:stdout.write(canonical(data));stdout.flush()
        return 0
    def make_evidence(self):
        import io,zipfile
        m=self.m
        ticket=(self.out/'offline_ticket.json').read_bytes();armed=(self.out/'armed.json').read_bytes()
        status=dict(status='PASS',package_kind='B',tests=95,failed=0,errors=0,skipped=0,physics_calls=0,gpu_calls=0,
            code_sha256=m.CODE,protocol_sha256=m.PROTO,benchmark_complete=False,wall_ns=1000,cpu_ns=1000,process_tree_peak_rss_bytes=4096)
        if self.scenario=='result_skip':status['skipped']=1
        guard=dict(blocked_attempts=[],new_physics_calls=0,gpu_calls=0)
        xml='<testsuites><testsuite>'+''.join('<testcase classname="TEST_ONLY_NEVER_B95" name="synthetic_%d"/>'%i for i in range(95))+'</testsuite></testsuites>'
        files={'ticket.json':ticket,'armed.json':armed,'output/status.json':canonical(status),'output/junit.xml':xml.encode(),'output/physics_guard.json':canonical(guard)}
        if self.scenario=='partial_evidence':files.pop('output/junit.xml')
        files.update({'gate_exit.json':canonical(dict(returncode=1 if self.scenario=='gate_failure' else 0,error=None)),
                      'job_spec.json':(self.out/'job_spec.json').read_bytes(),'job/identity.json':canonical(self.job_observation['identity']),
                      'job/terminal.json':canonical(self.job_observation['terminal'])})
        manifest=dict(writer_completion_verified=True,inventory_stable=True,scope='COMPLETE_EXISTING_FILES_AFTER_WRITERS_EXIT',job_observation=self.job_observation,instance_id=54988176,code_sha256=m.CODE,run_id=auth()['run_id'],files={n:hashlib.sha256(v).hexdigest() for n,v in files.items()})
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for n,v in files.items():z.writestr(n,v)
            z.writestr('evidence_manifest.json',canonical(manifest))
        self.zip_bytes=stream.getvalue()
        return dict(sha256=hashlib.sha256(self.zip_bytes).hexdigest(),files=len(files),remote_archive='/workspace/tablet_v0_b_'+auth()['run_id']+'/.recovery/capture1/evidence.zip',writer_completion_verified=True,job_observation=self.job_observation)
    def run(self,argv,input=None,stdout=None,stderr=None,timeout=None,**kwargs):
        if stdout is None:raise AssertionError('UNEXPECTED_CAPTURE_IO')
        return SimpleNamespace(returncode=self.execute_io(argv,input,stdout,stderr))
    def Popen(self,argv,**kwargs):
        if 'supervisor.py' in str(argv):return SupervisorBoundary(self)
        return CommandBoundary(self,argv,kwargs)
    def shim(self):return SimpleNamespace(run=self.run,Popen=self.Popen,PIPE=subprocess.PIPE,TimeoutExpired=subprocess.TimeoutExpired,CREATE_NO_WINDOW=0,CREATE_NEW_PROCESS_GROUP=0)

class CommandBoundary:
    def __init__(self,b,argv,kwargs):self.b=b;self.argv=argv;self.kw=kwargs;self.returncode=None;self.calls=0
    def communicate(self,input=None,timeout=None):
        self.calls+=1
        if self.b.scenario=='guard_lost_during_gate' and self.kw.get('stdout'):
            phase=Path(self.kw['stdout'].name).stem
            if phase.endswith('job_launch'):
                write(self.b.out/'guardian/final.json',dict(status='STOP_UNCONFIRMED'))
                raise subprocess.TimeoutExpired(self.argv,timeout)
        self.returncode=self.b.execute_io(self.argv,input,self.kw['stdout'],self.kw['stderr']);return None,None
    def kill(self):self.b.killed+=1;self.returncode=255
    def wait(self,timeout=None):return self.returncode
    def poll(self):return self.returncode

class SupervisorBoundary:
    def __init__(self,b):
        self.b=b;self.dead=False
        lease=b.out/'supervisor_lease.json'
        if b.scenario!='supervisor_not_ready':write(b.out/'supervisor_ready.json',dict(instance_id=54988176,lease_sha256=hashlib.sha256(lease.read_bytes()).hexdigest()))
    def poll(self):
        b=self.b
        if (b.out/'running_instance.json').exists() and not (b.out/'guardian_lease.json').exists():
            generic=dict(deadline_seconds=360);write(b.out/'guardian_lease.json',generic)
            if b.scenario!='guardian_not_armed':
                armed=dict(status='ARMED',outside_guest=True,guardian_sha256=hashlib.sha256(b.m.GUARD.read_bytes()).hexdigest(),
                  instance_id=54988176,machine_id=150665,country='ES',approval_reference=auth()['approval_reference'],
                  deadline_seconds=360,confirmation_seconds=180,armed_utc=b.clock.now().isoformat())
                write(b.out/'guardian/armed.json',armed);write(b.out/'guardian_pid.json',dict(pid=123456))
        return 1 if b.scenario=='supervisor_exited' else None
    def wait(self,timeout=None):
        b=self.b;sup=load_module('actual_stop_core',TRANSPORT/'supervisor.py')
        class Cli:
            def stop(self):b.stops+=1;b.state='stopped' if b.scenario!='stop_unconfirmed' else 'running'
            def show(self):
                if b.scenario=='stop_api_failure':raise OSError('MOCK_STOP_API_ERROR')
                return raw('final_stopped') if b.state=='stopped' else raw('running')
        stop=sup.confirm_stop(Cli(),54988176,'FAILED',confirm_seconds=180,now=b.clock.monotonic,sleep=b.clock.sleep)
        write(b.out/'supervisor_final.json',dict(result=stop))
        if (b.out/'guardian/armed.json').exists():write(b.out/'guardian/final.json',stop)
        return 0

def configured():
    m=load_module('transport_candidate',TRANSPORT/'controller.py');m.configure('B');return m

class ExecutionTests(unittest.TestCase):
    def execute_case(self,scenario,success,expected_starts=1,max_gates=1):
        m=configured();clock=Clock()
        out=ROOT/'.simulated'/scenario;out.mkdir(parents=True,exist_ok=False)
        b=Backend(m,out,scenario,clock)
        with patch.object(m,'subprocess',b.shim()),patch.object(m,'time',clock),patch.object(m,'datetime',clock.datetime_type()),patch.object(m,'guardian_alive',lambda pid:scenario!='guardian_dead_pid'),patch.object(m,'local_preflight',return_value=['TEST_ONLY_EXTERNAL_AUTHORITY_BOUNDARY']),patch('execution_authority.begin_transport',return_value=None):
            t=m.Transport(auth(),'mock_vast','mock_key',out);result=t.execute()
        closure=json.loads((out/'closure.json').read_bytes())
        self.assertEqual(result==0,success,(scenario,closure))
        self.assertEqual(b.starts,expected_starts)
        self.assertLessEqual(b.gates,max_gates)
        self.assertTrue(all('root@188.245.20.75' in c['argv'] or c['argv'][0] not in ('ssh','scp') or 'root@188.245.20.75:' in ' '.join(c['argv']) for c in b.commands))
        if not success:self.assertFalse((out/'policy_completion.json').exists())
        TRACE.append(dict(case=scenario,expected='COMPLETED' if success else 'REFUSED/STOP',actual=closure,
            commands=b.commands,starts=b.starts,gates=b.gates,stop_requests=b.stops,next_gate_blocked=b.gates<=max_gates,
            role='TEST_ONLY_EXTERNAL_PROCESS_SIMULATION; NEVER_B95_EVIDENCE'))
    def test_normal(self):self.execute_case('normal',True)
    def test_delayed_ports(self):self.execute_case('ports_delay',True)

FAILURES={
 'wrong_initial_id':(0,0),'queued_initial':(0,0),'ports_never_ready':(1,0),'wrong_running_port':(1,0),
 'supervisor_not_ready':(0,0),'supervisor_exited':(0,0),'guardian_not_armed':(1,0),
 'ssh_fail':(1,0),'container_mismatch':(1,0),'zip_mismatch':(1,0),'zip_missing':(1,0),
 'stop_during_control':(1,0),'marker_during_api':(1,0),'gate_failure':(1,1),'clock_drift':(1,1),
 'recovery_disconnect':(1,1),'recovery_corrupt':(1,1),'partial_evidence':(1,1),'result_skip':(1,1),
 'stop_unconfirmed':(1,1),'stop_api_failure':(1,1),'final_missing':(1,1),'final_api_error':(1,1),'final_wrong_machine':(1,1),
 'guard_lost_during_gate':(1,0),'guardian_dead_pid':(1,0),'late_clock_drift':(1,1),
 'marker_during_download':(1,1),'final_price_violation':(1,1)}
for name,(starts,gates) in FAILURES.items():
    def _failure_case(self,n=name,s=starts,g=gates):self.execute_case(n,False,s,g)
    setattr(ExecutionTests,'test_'+name,_failure_case)

# Direct supervisor/guardian entry-point cases are added before candidate execution.
