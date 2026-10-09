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
        self.scripts={hashlib.sha256((TRANSPORT/n).read_bytes()).hexdigest():n for n in ('guest_probe.py','guest_source_verify.py','guest_gate.py','guest_recover.py')}
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
            name=self.scripts[hashlib.sha256(input).hexdigest()]
            if self.scenario=='ssh_fail':return 255
            if name=='guest_probe.py':data=dict(actual_container_id='999' if self.scenario=='container_mismatch' else '54988176')
            elif name=='guest_source_verify.py':
                if self.scenario in ('zip_mismatch','zip_missing'):raise ValueError('MOCK_SOURCE_HASH_OR_MISSING')
                data=dict(status='RAW_SOURCE_VERIFIED')
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
        manifest=dict(instance_id=54988176,code_sha256=m.CODE,run_id=auth()['run_id'],files={n:hashlib.sha256(v).hexdigest() for n,v in files.items()})
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for n,v in files.items():z.writestr(n,v)
            z.writestr('evidence_manifest.json',canonical(manifest))
        self.zip_bytes=stream.getvalue()
        return dict(sha256=hashlib.sha256(self.zip_bytes).hexdigest(),files=len(files))
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
            if phase.endswith('offline_gate'):
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

class StateContractTests(unittest.TestCase):
    def test_original_failure_reproduced(self):
        old=load_module('transport_frozen_failed',OLD/'controller.py');old.configure('B')
        with tempfile.TemporaryDirectory() as d:
            t=old.Transport(auth(),'mock_vast','mock_key',Path(d));t.run=lambda *args,**kw:canonical(raw('stopped'))
            with self.assertRaisesRegex(ValueError,'EXACT_INSTANCE_API_BINDING'):t.show('initial_instance')
        TRACE.append(dict(case='original_failure',input='ACTUAL stopped fixture',expected='reject',actual='EXACT_INSTANCE_API_BINDING',next_commands=0))

    def test_state_matrix(self):
        s=load_module('state_contract_actual',TRANSPORT/'state_contract.py')
        cases=[('stopped','initial','STOPPED'),('final_stopped','final','STOPPED'),('stopping','final','STOPPING'),('running','control','RUNNING')]
        for fixture,phase,state in cases:
            with self.subTest(fixture=fixture,phase=phase):self.assertEqual(s.inspect(raw(fixture),auth(),phase)['state'],state)
            TRACE.append(dict(case='state_matrix',input=fixture,phase=phase,expected=state,actual=state,source='ACTUAL'))

    def test_counterexample_matrix(self):
        s=load_module('state_contract_actual',TRANSPORT/'state_contract.py')
        cases=[]
        for field,value in [('id',0),('machine_id',0),('geolocation','France, FR'),('dph_total',float('nan')),('actual_status','weird')]:
            r=raw('stopped');r[field]=value;cases.append((field,'initial',r,ValueError))
        for field,value in [('public_ipaddr','192.0.2.1'),('ssh_host','wrong.example'),('ssh_port',1),('ports',[]),('ports',{'22/tcp':[{'HostPort':'40471'}]}),('ports',{'22/tcp':[{'HostPort':'40470'},{'HostPort':'40471'}]}),('intended_status','stopped')]:
            r=raw('running');r[field]=value;cases.append((field,'control',r,ValueError))
        for label,phase,r,error in cases:
            with self.subTest(label=label,value=repr(r.get(label))):
                with self.assertRaises(error):s.inspect(r,auth(),phase)
            TRACE.append(dict(case='mutated_counterexample',mutation=label,phase=phase,input=repr(r),expected='reject',actual='reject',next_commands=0,source='SYNTHETIC_FROM_ACTUAL'))
        r=raw('running');r.pop('ports');self.assertFalse(s.inspect(r,auth(),'restart')['connection_ready'])
        r=raw('stopped');r['intended_status']='running';self.assertEqual(s.inspect(r,auth(),'restart')['state'],'STARTING')
        with self.assertRaises(ValueError):s.inspect(r,auth(),'initial')
        with self.assertRaises(ValueError):s.decode(b'{"id":1,"id":2}')
        with self.assertRaises(ValueError):s.decode(b'{"dph_total":NaN}')

    def test_package_bytes_and_unapproved_main(self):
        m=configured();checked=m.verify_local_package()
        self.assertEqual(checked['entries'],10)
        with self.assertRaisesRegex(ValueError,'STATE_CONTRACT_SIMULATION_AND_NEW_APPROVAL_REQUIRED'):
            m.local_preflight(dict(explicit_user_approval=False))
        TRACE.append(dict(case='package_and_unapproved_main',actual='Exact original B ZIP10 raw checked; false/missing ready authority refused',next_commands=0,B95_executed=0))

    def test_callsite_inventory(self):
        import ast
        tree=ast.parse((TRANSPORT/'controller.py').read_text())
        calls=[n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
            and n.func.attr=='show' and n.args and isinstance(n.args[0],ast.Constant)]
        self.assertEqual(set(calls),{'initial_instance','restart_status','phase_control','final_instance'})

class OutsideControlTests(unittest.TestCase):
    def test_checked_cli_real_confirm_stop(self):
        s=load_module('state_contract_checked',TRANSPORT/'state_contract.py')
        sup=load_module('outside_actual_confirm',TRANSPORT/'supervisor.py')
        for scenario in ('stopped','queued','wrong_machine','api_error'):
            clock=Clock();calls=[]
            def io_run(argv,**kwargs):
                calls.append(argv)
                if 'stop' in argv:return SimpleNamespace(returncode=0,stdout=b'{}')
                if scenario=='api_error':raise OSError('MOCK_API_OFFLINE')
                r=raw('stopped')
                if scenario=='queued':r['intended_status']='running'
                if scenario=='wrong_machine':r['machine_id']=0
                return SimpleNamespace(returncode=0,stdout=canonical(r))
            with patch.object(s,'subprocess',SimpleNamespace(run=io_run)):
                result=sup.confirm_stop(s.CheckedCli('mock_vast',54988176,auth()),54988176,'FAILED',confirm_seconds=180,now=clock.monotonic,sleep=clock.sleep)
            self.assertEqual(result['status']=='STOP_CONFIRMED',scenario=='stopped')
            self.assertTrue(all(c[-1]=='54988176' for c in calls))
            self.assertFalse(any('start' in c for c in calls))
            TRACE.append(dict(case='actual_confirm_stop_'+scenario,actual=result,commands=calls,expected='STOP_CONFIRMED' if scenario=='stopped' else 'STOP_UNCONFIRMED'))

    def test_actual_supervisor_and_guardian_main(self):
        for scenario in ('normal','clock_drift','guardian_cli_wrong_machine'):
            clock=Clock();out=ROOT/'.simulated'/('actual_main_'+scenario);out.mkdir(parents=True,exist_ok=False)
            sup=load_module('outside_supervisor_entry',TRANSPORT/'supervisor.py')
            driver=load_module('guardian_driver_entry',TRANSPORT/'guardian_driver.py')
            guard_path=ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
            if str(guard_path.parent) not in sys.path:sys.path.insert(0,str(guard_path.parent))
            guardian=load_module('guardian_raw_entry',guard_path)
            state=load_module('checked_entry_state',TRANSPORT/'state_contract.py')
            calls=[];running=[True]
            def fake_cli(argv,**kwargs):
                calls.append(list(map(str,argv)))
                if 'stop' in argv:running[0]=False;return SimpleNamespace(returncode=0,stdout=b'{}')
                record=raw('running' if running[0] else 'stopped')
                if scenario=='guardian_cli_wrong_machine':record['machine_id']=0
                return SimpleNamespace(returncode=0,stdout=canonical(record))
            actual_confirm=sup.confirm_stop
            def timed_confirm(*args,**kwargs):return actual_confirm(*args,**kwargs,now=clock.monotonic,sleep=clock.sleep)
            guard_confirm=guardian.confirm_stop
            def timed_guard(*args,**kwargs):return guard_confirm(*args,**kwargs,now=clock.monotonic,sleep=clock.sleep)
            lease=dict(scope='STOP_CONTROL_ONLY',exclusive=True,explicit_user_approval=True,approval_reference='TEST_ONLY main linkage',
                prior_failed_attempts=3,new_window_separately_authorized=True,instance_id=54988176,machine_id=150665,country='ES',
                allocation_monotonic_ns=clock.monotonic_ns(),allocation_start_utc=clock.now().isoformat(),cli='mock_vast',repo_root=str(ROOT),out=str(out),
                guardian_sha256=hashlib.sha256(guard_path.read_bytes()).hexdigest(),supervisor_sha256=hashlib.sha256((TRANSPORT/'supervisor.py').read_bytes()).hexdigest(),
                state_contract_sha256=hashlib.sha256((TRANSPORT/'state_contract.py').read_bytes()).hexdigest(),guardian_driver_sha256=hashlib.sha256((TRANSPORT/'guardian_driver.py').read_bytes()).hexdigest())
            lease_path=out/'lease.json';write(lease_path,lease);write(out/'running_instance.json',raw('running'))
            class Child:
                pid=123456
                def poll(self):return None
                def wait(self,timeout=None):
                    argv=['--guardian',str(guard_path),'--authorization',str(out/'guardian_lease.json'),
                          '--out',str(out/'guardian'),'--marker',str(out/'completion.json'),'--cli','mock_vast']
                    with patch.object(driver,'load_guardian',lambda p:guardian),patch.object(driver,'CheckedCli',state.CheckedCli),patch.object(sys,'argv',list(sys.argv)):
                        return driver.main(argv)
            def tick():
                if scenario=='clock_drift':clock.wall_shift=10
                elif clock.value>=101 and not (out/'completion.json').exists():write(out/'completion.json',dict(trigger='COMPLETED'))
            clock.hook=tick
            fake_process=SimpleNamespace(Popen=lambda *a,**k:Child(),CREATE_NO_WINDOW=0,CREATE_NEW_PROCESS_GROUP=0,TimeoutExpired=subprocess.TimeoutExpired)
            with (patch.object(sup,'subprocess',fake_process),patch.object(sup,'time',clock),patch.object(sup,'datetime',clock.datetime_type()),
                  patch.object(sup,'confirm_stop',timed_confirm),patch.object(sup,'CheckedCli',state.CheckedCli),
                  patch.object(guardian,'time',clock),patch.object(guardian,'datetime',clock.datetime_type()),patch.object(guardian,'confirm_stop',timed_guard),
                  patch.object(state,'subprocess',SimpleNamespace(run=fake_cli))):
                rc=sup.main(['--lease',str(lease_path)])
            receipt=json.loads((out/'supervisor_final.json').read_bytes())
            self.assertEqual(receipt['result']['status']=='STOP_CONFIRMED',scenario!='guardian_cli_wrong_machine')
            self.assertTrue((out/'guardian/armed.json').exists() if scenario=='normal' else True)
            if scenario=='clock_drift':self.assertIn('CLOCK_DRIFT',receipt['failure'])
            self.assertFalse(any('start' in c for c in calls))
            TRACE.append(dict(case='actual_main_'+scenario,actual=receipt,returncode=rc,commands=calls,role='TEST_ONLY actual main methods with fake process/time/CLI'))

class GuestCodeTests(unittest.TestCase):
    def test_actual_pid1_probe(self):
        original_read=Path.read_bytes;original_is_file=Path.is_file
        for scenario,environ in [('normal',b'CONTAINER_ID=54988176\0'),('missing',b'PATH=x\0'),('wrong',b'CONTAINER_ID=7\0'),('duplicate',b'CONTAINER_ID=54988176\0CONTAINER_ID=54988176\0')]:
            made=[]
            def reads(path):return environ if str(path)=='/proc/1/environ' else original_read(path)
            def files(path):return True if str(path)=='/mock/python' else original_is_file(path)
            def mkdir(path,*args,**kwargs):
                if str(path)=='/workspace/tablet_v0_TEST_ONLY':made.append(str(path));return
                raise AssertionError('UNEXPECTED_PROBE_WRITE')
            with patch.object(sys,'argv',['probe','54988176','/mock/python','/workspace/tablet_v0_TEST_ONLY']),patch.object(Path,'read_bytes',reads),patch.object(Path,'is_file',files),patch.object(Path,'mkdir',mkdir),contextlib.redirect_stdout(io.StringIO()):
                if scenario=='normal':runpy.run_path(str(TRANSPORT/'guest_probe.py'),run_name='__main__')
                else:
                    with self.assertRaises(ValueError):runpy.run_path(str(TRANSPORT/'guest_probe.py'),run_name='__main__')
            self.assertEqual(len(made),1 if scenario=='normal' else 0)
            TRACE.append(dict(case='actual_guest_probe_'+scenario,input=repr(environ),actual='created' if made else 'refused',next_guest_writes=len(made),filesystem_boundary='mock PID1/runtime/mkdir only'))

    def test_actual_package_verifier(self):
        m=configured()
        for scenario in ('normal','missing_zip','changed_zip'):
            guest=ROOT/'.simulated'/('guest_source_'+scenario);guest.mkdir(parents=True,exist_ok=False)
            (guest/'inventory.json').write_bytes(m.INVENTORY.read_bytes())
            if scenario!='missing_zip':(guest/'source.zip').write_bytes(m.SOURCE.read_bytes() if scenario=='normal' else b'changed')
            argv=['verify',str(guest),m.ZIP_HASH,m.INVENTORY_HASH,m.CODE,m.PROTO,'B']
            with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
                if scenario=='normal':runpy.run_path(str(TRANSPORT/'guest_source_verify.py'),run_name='__main__')
                else:
                    with self.assertRaises((ValueError,FileNotFoundError)):runpy.run_path(str(TRANSPORT/'guest_source_verify.py'),run_name='__main__')
            self.assertEqual((guest/'source').exists(),scenario=='normal')
            TRACE.append(dict(case='actual_guest_source_'+scenario,actual='verified/extracted' if scenario=='normal' else 'refused before extraction',B95_executed=0))

    def test_actual_gate_identity_ticket_boundary(self):
        m=configured();original_read=Path.read_bytes
        for scenario in ('normal','wrong_pid1','ticket_changed','zip_changed'):
            guest=ROOT/'.simulated'/('actual_gate_'+scenario);guest.mkdir(parents=True,exist_ok=False)
            (guest/'source').mkdir();(guest/'source.zip').write_bytes(m.SOURCE.read_bytes());(guest/'inventory.json').write_bytes(m.INVENTORY.read_bytes())
            now=datetime.now(timezone.utc).isoformat()
            armed=dict(instance_id=54988176,machine_id=150665,country='ES',approval_reference='TEST_ONLY',armed_utc=now,deadline_seconds=360)
            armed_bytes=canonical(armed);armed_hash=hashlib.sha256(armed_bytes).hexdigest();(guest/'armed.json').write_bytes(armed_bytes)
            ticket=dict(package_kind='B',instance_id=54988176,machine_id=150665,country='ES',approval_reference='TEST_ONLY',armed_sha256=armed_hash,
                zip_sha256=m.ZIP_HASH,inventory_sha256=m.INVENTORY_HASH,allocation_start_utc=now)
            ticket_bytes=canonical(ticket);ticket_hash=hashlib.sha256(ticket_bytes).hexdigest();(guest/'ticket.json').write_bytes(ticket_bytes)
            if scenario=='ticket_changed':(guest/'ticket.json').write_bytes(ticket_bytes+b' ')
            if scenario=='zip_changed':(guest/'source.zip').write_bytes(b'changed')
            calls=[]
            def guest_io(argv,**kwargs):calls.append(argv);return SimpleNamespace(returncode=0)
            def reads(path):
                if str(path)=='/proc/1/environ':return b'CONTAINER_ID='+ (b'9' if scenario=='wrong_pid1' else b'54988176')+b'\0'
                return original_read(path)
            with (patch.object(sys,'argv',['gate',str(guest),'/mock/python','54988176',armed_hash,ticket_hash]),
                  patch.object(Path,'read_bytes',reads),patch.object(subprocess,'run',guest_io),contextlib.redirect_stdout(io.StringIO())):
                if scenario=='normal':runpy.run_path(str(TRANSPORT/'guest_gate.py'),run_name='__main__')
                else:
                    with self.assertRaises(ValueError):runpy.run_path(str(TRANSPORT/'guest_gate.py'),run_name='__main__')
            self.assertEqual(len(calls),1 if scenario=='normal' else 0)
            TRACE.append(dict(case='actual_guest_gate_'+scenario,expected_mock_child_calls=1 if scenario=='normal' else 0,actual_mock_child_calls=len(calls),B95_executed=0,process_boundary='fake child; actual wrapper checks'))

    def test_actual_raw_recovery_pack(self):
        guest=ROOT/'.simulated/actual_recover';guest.mkdir(parents=True,exist_ok=False)
        (guest/'diagnostic.json').write_bytes(canonical(dict(role='TEST_ONLY',error='MOCK')))
        (guest/'source.zip').write_bytes(b'excluded')
        with patch.object(sys,'argv',['recover',str(guest),'54988176','TEST_ONLY_CODE_HASH','TEST_ONLY_RUN']),contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(TRANSPORT/'guest_recover.py'),run_name='__main__')
        import zipfile
        with zipfile.ZipFile(guest/'evidence.zip') as z:
            manifest=json.loads(z.read('evidence_manifest.json'))
            self.assertNotIn('source.zip',manifest['files'])
            self.assertEqual(manifest['files']['diagnostic.json'],hashlib.sha256((guest/'diagnostic.json').read_bytes()).hexdigest())
        TRACE.append(dict(case='actual_raw_recovery',actual='original packer hash bound; source excluded',B95_executed=0))

class ExecutionTests(unittest.TestCase):
    def execute_case(self,scenario,success,expected_starts=1,max_gates=1):
        m=configured();clock=Clock()
        out=ROOT/'.simulated'/scenario;out.mkdir(parents=True,exist_ok=False)
        b=Backend(m,out,scenario,clock)
        with patch.object(m,'subprocess',b.shim()),patch.object(m,'time',clock),patch.object(m,'datetime',clock.datetime_type()),patch.object(m,'guardian_alive',lambda pid:scenario!='guardian_dead_pid'):
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

class AdministrativeEntryTests(unittest.TestCase):
    def test_admin_false_scope_refused(self):
        boot=load_module('paid_admin_bootstrap_test',TRANSPORT/'admin_bootstrap.py')
        with self.assertRaisesRegex(ValueError,'EXPLICIT_ADMIN_ONLY_SCOPE_REQUIRED'):boot.preflight(dict(explicit_user_approval=False))
        TRACE.append(dict(case='admin_false_scope',actual='refused before external IO',B95_executed=False))

    def test_admin_result_raw_counterexamples(self):
        boot=load_module('paid_admin_result_test',TRANSPORT/'admin_bootstrap.py')
        with patch.object(boot.c,'KIND','ADMIN'),patch.object(boot.c,'EXPECTED',2):
            for scenario in ('normal','ticket_changed','arm_changed','entry_cpu','entry_affinity','skip','incomplete_cases'):
                out=ROOT/'.simulated'/('admin_validation_'+scenario);data=out/'recovered';(data/'output').mkdir(parents=True)
                for name in ('admin_ticket.json','armed.json'):
                    (out/name).write_bytes(b'{"role":"TEST_ONLY"}');(data/name).write_bytes((out/name).read_bytes())
                status=dict(role='ADMIN_TRANSPORT_CPU_SIMULATION_ONLY; NOT_B95_OR_A320',status='PASS',tests=2,expected_tests=2,error=None,
                    blocked_attempts=[],failed=0,errors=0,skipped=0,new_physics_calls=0,gpu_calls=0,real_provider_calls_inside_simulation=0,
                    real_subprocess_calls_inside_simulation=0,B95_executed=False,A320_executed=False,independent_authority_certification=False,
                    wall_ns=1000,cpu_ns=1000,peak_rss_bytes=4096,cpu_affinity=[0])
                entry=dict(returncode=0,error=None,actual_container_id='54988176',B95_executed=False,A320_executed=False,
                    new_physics_calls=0,gpu_calls=0,wall_seconds=.1,aggregate_cpu_seconds=.1,aggregate_peak_rss_bytes=4096,cpu_affinity=[0])
                if scenario=='ticket_changed':(data/'admin_ticket.json').write_bytes(b'changed')
                if scenario=='arm_changed':(data/'armed.json').write_bytes(b'changed')
                if scenario=='entry_cpu':entry['aggregate_cpu_seconds']=121
                if scenario=='entry_affinity':entry['cpu_affinity']=[0,1]
                if scenario=='skip':status['skipped']=1
                cases=[dict(id='TEST_ONLY_'+str(i),outcome='PASS') for i in range(1 if scenario=='incomplete_cases' else 2)]
                write(data/'output/status.json',status);write(data/'admin_entry_exit.json',entry);write(data/'output/case_results.json',dict(cases=cases))
                (data/'output/junit.xml').write_text('<testsuites>'+''.join('<testcase name="'+x['id']+'"/>' for x in cases)+'</testsuites>')
                t=boot.AdminTransport(auth(),'mock_vast','mock_key',out)
                if scenario=='normal':self.assertEqual(t.validate_result()['status'],'PASS')
                else:
                    with self.assertRaises(ValueError):t.validate_result()
                self.assertEqual((out/'admin_result_verified.json').exists(),scenario=='normal')
                TRACE.append(dict(case='admin_raw_result_'+scenario,actual='PASS' if scenario=='normal' else 'REFUSED',B95_executed=False))

    def test_actual_admin_entry_scope_and_hash(self):
        import zipfile,resource,psutil,os,time
        from types import SimpleNamespace as NS
        original_read=Path.read_bytes
        for scenario in ('normal','ticket_hash','wrong_scope','wrong_arm','zip_hash','child_failure'):
            guest=ROOT/'.simulated'/('tablet_v0_entry_'+scenario);guest.mkdir(parents=True)
            ticket=auth();now=datetime.now(timezone.utc);first=(now-timedelta(seconds=1)).isoformat()
            ticket.update(schema='HUMAN_PAID_ADMIN_VALIDATION_ONLY_V1',scope='ADMIN_SIMULATION_AND_ACTUAL_TRANSPORT_STOP_ONLY',
                package_kind='ADMIN',expected_tests=1,B95_authorized=False,A320_authorized=False,allocation_start_utc=first,
                approved_utc=(now-timedelta(seconds=20)).isoformat(),expires_utc=(now+timedelta(seconds=300)).isoformat())
            armed=dict(status='ARMED',outside_guest=True,confirmation_seconds=180,instance_id=54988176,machine_id=150665,country='ES',
                approval_reference=ticket['approval_reference'],guardian_sha256=hashlib.sha256((ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py').read_bytes()).hexdigest(),
                armed_utc=first,deadline_seconds=360)
            if scenario=='wrong_scope':ticket['scope']='OFFLINE_ONLY'
            if scenario=='wrong_arm':armed['machine_id']=0
            write(guest/'armed.json',armed);arm_sha=hashlib.sha256((guest/'armed.json').read_bytes()).hexdigest();ticket['armed_sha256']=arm_sha
            write(guest/'admin_ticket.json',ticket);ticket_sha=hashlib.sha256((guest/'admin_ticket.json').read_bytes()).hexdigest()
            if scenario=='ticket_hash':ticket_sha='0'*64
            member='docs/active/bounded_admin_recovery_v0/target_52763685_admin_v1/run_admin_simulation.py';payload=b'# TEST_ONLY fake child boundary\n'
            with zipfile.ZipFile(guest/'source.zip','x') as z:z.writestr(member,payload)
            zip_sha=hashlib.sha256((guest/'source.zip').read_bytes()).hexdigest()
            write(guest/'inventory.json',dict(role='UNVALIDATED_ADMIN_CANDIDATE_INPUTS_ONLY',B95_executed=False,
                files={member:hashlib.sha256(payload).hexdigest()},uncompressed_bytes=len(payload)))
            inv_sha=hashlib.sha256((guest/'inventory.json').read_bytes()).hexdigest()
            if scenario=='zip_hash':zip_sha='0'*64
            external=[]
            class Child:
                returncode=2 if scenario=='child_failure' else 0
                def poll(self):return self.returncode
            class Process:
                def children(self,recursive=False):return []
                def cpu_times(self):return NS(user=.1,system=.1)
                def memory_info(self):return NS(rss=4096)
            def popen(argv,**kwargs):external.append(argv);return Child()
            def mapped_path(value):
                if value=='/workspace':return guest.parent
                if value=='/workspace/tablet_v0_TEST_ONLY_ADMIN':return guest
                return Path(value)
            def reads(path):return b'CONTAINER_ID=54988176\0' if str(path)=='/proc/1/environ' else original_read(path)
            argv=['entry','/workspace/tablet_v0_TEST_ONLY_ADMIN','54988176',zip_sha,inv_sha,'1',ticket_sha,arm_sha]
            with (patch.object(sys,'argv',argv),patch.dict(sys.modules,{'pathlib':NS(Path=mapped_path,PurePosixPath=PurePosixPath)}),patch.object(Path,'read_bytes',reads),
                  patch.object(subprocess,'Popen',popen),patch.object(psutil,'Process',Process),contextlib.redirect_stdout(io.StringIO())):
                if scenario in ('normal','child_failure'):runpy.run_path(str(TRANSPORT/'remote_admin_entry.py'),run_name='__main__')
                else:
                    with self.assertRaises(ValueError):runpy.run_path(str(TRANSPORT/'remote_admin_entry.py'),run_name='__main__')
            self.assertEqual(len(external),1 if scenario in ('normal','child_failure') else 0)
            self.assertEqual((guest/'admin_entry_exit.json').exists(),scenario in ('normal','child_failure'))
            if scenario=='child_failure':self.assertEqual(json.loads((guest/'admin_entry_exit.json').read_bytes())['returncode'],2)
            TRACE.append(dict(case='actual_admin_entry_'+scenario,actual_mock_child_calls=len(external),B95_executed=False,external_boundary='fake child/PID1/workspace only; actual wrapper'))

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
    def test(self,n=name,s=starts,g=gates):self.execute_case(n,False,s,g)
    setattr(ExecutionTests,'test_'+name,test)

# Direct supervisor/guardian entry-point cases are added before candidate execution.
class NewNORunningTargetTests(unittest.TestCase):
    def no_auth(self):
        a=auth();a.update(schema='HUMAN_PAID_ADMIN_NO_52763685_V1',instance_id=52763685,machine_id=3448,country='NO',
            ssh_host='81.166.162.13',ssh_port=12408,api_ssh_host='ssh2.vast.ai',api_ssh_port=13684,hourly_cap_usd='0.28',
            scope='ADMIN_SIMULATION_AND_ACTUAL_TRANSPORT_STOP_ONLY',allocation_mode='ADOPT_RUNNING',exclusive=True,
            admin_target_protocol_sha256=hashlib.sha256((BASE/'target_protocol.json').read_bytes()).hexdigest())
        return a

    def test_no_cap_and_running_adoption_binding(self):
        state=load_module('new_no_state_contract',TRANSPORT/'state_contract.py');a=self.no_auth();r=raw('no_running')
        self.assertEqual(state.inspect(r,a,'initial')['state'],'RUNNING')
        for field,value in [('exclusive',False),('explicit_user_approval',False),('admin_target_protocol_sha256',None),('admin_target_protocol_sha256','0'*64),('machine_id',0)]:
            bad=dict(a);bad[field]=value
            with self.assertRaises(ValueError):state.inspect(r,bad,'initial')
        bad=dict(r,dph_total=.29)
        with self.assertRaises(ValueError):state.inspect(bad,a,'control')
        bad=dict(r,intended_status='stopped')
        with self.assertRaises(ValueError):state.inspect(bad,a,'initial')
        import ast
        bootstrap=load_module('no_actual_bootstrap_approval_boundary',TRANSPORT/'admin_bootstrap.py')
        tree=ast.parse((TRANSPORT/'admin_bootstrap.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='preflight')
        node=next(n.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fixed' for t in n.targets))
        trial=dict(a,**{k.arg:ast.literal_eval(k.value) for k in node.keywords})
        trial['run_id']='admin_test_only_binding'
        for field,value in [('approval_reference','TEST_ONLY_NO_HUMAN_AUTHORITY'),('human_approval_text','PAST_APPROVAL')]:
            current=json.loads((BASE/'target_protocol.json').read_bytes());bad=dict(trial,approval_reference=current['approval_reference'],human_approval_text=current['human_approval_text']);bad[field]=value
            with patch.object(bootstrap.c,'datetime',Clock().datetime_type()),self.assertRaisesRegex(ValueError,'CURRENT_HUMAN_APPROVAL_EXACT_LINK_REQUIRED'):bootstrap.preflight(bad)
        TRACE.append(dict(case='NO_actual_readonly_cap_and_adoption',actual='bound; missing authority/wrong core/rate/stopping refused',role='TEST_ONLY; actual fixture'))

    def test_no_original_guardian_hourly_gate(self):
        path=ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
        if str(path.parent) not in sys.path:sys.path.insert(0,str(path.parent))
        guardian=load_module('original_no_hourly_gate',path)
        budget=path.parent/'offline_budget_amendment_52763685.json'
        a=self.no_auth();a.update(experiment_scope='OFFLINE_ONLY',deadline_seconds=240,budget_amendment_sha256=hashlib.sha256(budget.read_bytes()).hexdigest())
        self.assertEqual(guardian.hourly_cap(a),.28)
        for field,value in [('deadline_seconds',241),('machine_id',0),('budget_amendment_sha256','0'*64)]:
            bad=dict(a);bad[field]=value
            with self.assertRaises(ValueError):guardian.hourly_cap(bad)
        TRACE.append(dict(case='NO_original_guardian_hourly_gate',actual='unchanged raw gate .28;240 bound/ID/hash counterexamples refused',role='TEST_ONLY; no original policy edits'))

    def test_actual_controller_adopts_without_start(self):
        for scenario in ('no_adopt','no_supervisor_popen_failure','no_supervisor_ready_mismatch','no_supervisor_exited','no_fallback_queued_exit'):
            m=configured();a=self.no_auth();clock=Clock();out=ROOT/'.simulated'/scenario;out.mkdir(parents=True)
            class NOBoundary(Backend):
                def api(self,phase):
                    self.polls+=1;r=raw('no_running')
                    if self.state=='stopped':r.update(actual_status='exited',intended_status='running' if scenario=='no_fallback_queued_exit' else 'stopped');r.pop('ports',None)
                    return r
                def execute_io(self,argv,input,stdout,stderr):
                    if argv[0]=='ssh' and self.scripts.get(hashlib.sha256(input).hexdigest())=='guest_probe.py':
                        self.commands.append(dict(phase='guest_identity',argv=list(map(str,argv)),mock=True));stdout.write(canonical(dict(actual_container_id='52763685')));stdout.flush();return 0
                    if argv[0]=='mock_vast' and 'stop' in argv:
                        self.commands.append(dict(phase='controller_fallback_stop',argv=list(map(str,argv)),mock=True));self.stops+=1;self.state='stopped';stdout.write(b'{}');stdout.flush();return 0
                    return super().execute_io(argv,input,stdout,stderr)
                def make_evidence(self):
                    import zipfile
                    pack=super().make_evidence()
                    with zipfile.ZipFile(io.BytesIO(self.zip_bytes)) as z:files={n:z.read(n) for n in z.namelist()}
                    manifest=json.loads(files['evidence_manifest.json']);manifest['instance_id']=52763685;files['evidence_manifest.json']=canonical(manifest)
                    stream=io.BytesIO()
                    with zipfile.ZipFile(stream,'w') as z:
                        for n,v in files.items():z.writestr(n,v)
                    self.zip_bytes=stream.getvalue();pack['sha256']=hashlib.sha256(self.zip_bytes).hexdigest();return pack
                def Popen(self,argv,**kwargs):
                    if 'supervisor.py' in str(argv):
                        if scenario in ('no_supervisor_popen_failure','no_fallback_queued_exit'):raise OSError('TEST_ONLY_POPEN_FAILURE')
                        return NOSupervisor(self)
                    return CommandBoundary(self,argv,kwargs)
            class NOSupervisor:
                def __init__(self,b):
                    self.b=b;write(out/'supervisor_ready.json',dict(instance_id=0 if scenario=='no_supervisor_ready_mismatch' else 52763685,lease_sha256=hashlib.sha256((out/'supervisor_lease.json').read_bytes()).hexdigest()))
                def poll(self):
                    if scenario=='no_supervisor_exited':return 2
                    if (out/'running_instance.json').exists() and not (out/'guardian_lease.json').exists():
                        write(out/'guardian_lease.json',dict(deadline_seconds=240));write(out/'guardian_pid.json',dict(pid=123456))
                        armed=dict(status='ARMED',outside_guest=True,guardian_sha256=hashlib.sha256(m.GUARD.read_bytes()).hexdigest(),instance_id=52763685,machine_id=3448,country='NO',
                            approval_reference=a['approval_reference'],deadline_seconds=240,confirmation_seconds=180,armed_utc=clock.now().isoformat())
                        write(out/'guardian/armed.json',armed)
                    return None
                def wait(self,timeout=None):
                    if scenario!='no_adopt':return 2
                    self.b.stops+=1;self.b.state='stopped'
                    stop=dict(status='STOP_CONFIRMED',instance_id=52763685,events=[dict(event='TEST_ONLY_STOP')])
                    write(out/'supervisor_final.json',dict(result=stop));write(out/'guardian/final.json',stop);return 0
            b=NOBoundary(m,out,scenario,clock);b.state='running'
            with patch.object(m,'subprocess',b.shim()),patch.object(m,'time',clock),patch.object(m,'datetime',clock.datetime_type()),patch.object(m,'guardian_alive',lambda pid:True):
                rc=m.Transport(a,'mock_vast','mock_key',out).execute()
            closure=json.loads((out/'closure.json').read_bytes())
            self.assertEqual(rc,0 if scenario=='no_adopt' else 2,closure);self.assertEqual(closure['actual_stop_confirmed'],scenario!='no_fallback_queued_exit');self.assertEqual(b.starts,0);self.assertEqual(b.stops,3 if scenario=='no_fallback_queued_exit' else 1)
            if scenario=='no_fallback_queued_exit':self.assertEqual(json.loads((out/'controller_fallback_final.json').read_bytes())['result']['status'],'STOP_UNCONFIRMED')
            self.assertEqual(closure['package_kind'],'B') # Synthetic legacy validator; physical B module is never invoked.
            TRACE.append(dict(case='NO_actual_controller_'+scenario,actual=closure,starts=b.starts,stops=b.stops,commands=b.commands,role='TEST_ONLY_NO_REAL_B95; external IO fake'))

if __name__=='__main__':unittest.main()
