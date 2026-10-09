"""Remote, CPU-only admin suite runner. Not a project test or B/A gate."""
import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import shutil
import sys
import threading
import time
import unittest
import xml.etree.ElementTree as ET
import psutil

BASE=Path(__file__).resolve().parent
FORBIDDEN=('engine','audit','experiments','native','numpy','scipy','torch','cupy','numba','pycuda','tensorflow')
BLOCKED=[]
def deadline_signal(signum,frame):
    # unittest propagates KeyboardInterrupt; the outer finally preserves partial result/trace.
    raise KeyboardInterrupt('ADMIN_SIMULATION_RESOURCE_DEADLINE:'+str(signum))
class ImportBoundary(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            BLOCKED.append(dict(kind='import',name=fullname));raise ImportError('PROJECT_PHYSICS_GPU_IMPORT_FORBIDDEN:'+fullname)

def audit(event,args):
    if event=='subprocess.Popen' or event in ('os.system','os.exec','os.posix_spawn','socket.connect','socket.bind','socket.getaddrinfo'):
        BLOCKED.append(dict(kind='io',event=event));raise RuntimeError('REAL_EXTERNAL_IO_FORBIDDEN:'+event)

def put(path,obj):
    with path.open('xb') as f:f.write(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False).encode())

class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.rows=[];self.started={}
    def startTest(self,test):self.started[test.id()]=time.perf_counter_ns();super().startTest(test)
    def record(self,test,outcome,message=None):
        self.rows.append(dict(id=test.id(),outcome=outcome,message=message,wall_ns=time.perf_counter_ns()-self.started[test.id()]))
    def addSuccess(self,test):self.record(test,'PASS');super().addSuccess(test)
    def addFailure(self,test,err):self.record(test,'FAIL',self._exc_info_to_string(err,test));super().addFailure(test,err)
    def addError(self,test,err):self.record(test,'ERROR',self._exc_info_to_string(err,test));super().addError(test,err)
    def addSkip(self,test,reason):self.record(test,'SKIP',reason);super().addSkip(test,reason)
    def addSubTest(self,test,subtest,err):
        if err is not None:self.record(test,'SUBTEST_FAIL',self._exc_info_to_string(err,test))
        super().addSubTest(test,subtest,err)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--expected',type=int,required=True)
    args=parser.parse_args();args.out.mkdir(exist_ok=False,parents=True)
    if sys.platform!='linux' or sys.version_info[:2]!=(3,12):raise ValueError('REMOTE_LINUX_PYTHON_312_REQUIRED')
    os.environ['CUDA_VISIBLE_DEVICES']=''
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    affinity=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{affinity[0]})
    resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    sys.meta_path.insert(0,ImportBoundary());sys.addaudithook(audit)
    process=psutil.Process();peak=[process.memory_info().rss];done=threading.Event()
    def monitor():
        while not done.wait(.01):peak[0]=max(peak[0],process.memory_info().rss)
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    started=time.perf_counter_ns();cpu=time.process_time_ns();result=None;error=None;module=None;created=[]
    try:
        signal.signal(signal.SIGALRM,deadline_signal);signal.signal(signal.SIGXCPU,deadline_signal);signal.alarm(110)
        spec=importlib.util.spec_from_file_location('admin_simulation_tests',BASE/'tests/test_admin_transport.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        if suite.countTestCases()!=args.expected:raise ValueError('EXACT_ADMIN_CASE_COUNT')
        with (args.out/'unittest.stderr').open('x',encoding='utf-8') as log:
            def factory(*a,**k):
                value=RecordedResult(*a,**k);created.append(value);return value
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=factory,failfast=True).run(suite)
    except BaseException as exc:error=repr(exc)
    finally:
        signal.alarm(0);done.set();thread.join(timeout=1)
        wall=time.perf_counter_ns()-started;used_cpu=time.process_time_ns()-cpu
        if result is None and created:result=created[0]
        rows=result.rows if result else []
        simulated=BASE.parents[3]/'.simulated'
        if simulated.exists():shutil.copytree(simulated,args.out/'TEST_ONLY_simulated_raw')
        status=dict(role='ADMIN_TRANSPORT_CPU_SIMULATION_ONLY; NOT_B95_OR_A320',tests=result.testsRun if result else 0,
            expected_tests=args.expected,failed=len(result.failures) if result else None,errors=len(result.errors) if result else None,
            skipped=len(result.skipped) if result else None,error=error,wall_ns=wall,cpu_ns=used_cpu,peak_rss_bytes=peak[0],
            cpu_affinity=sorted(os.sched_getaffinity(0)),memory_limit_bytes=536870912,
            new_physics_calls=0,gpu_calls=0,real_provider_calls_inside_simulation=0,real_subprocess_calls_inside_simulation=0,
            blocked_attempts=BLOCKED,B95_executed=False,A320_executed=False,independent_authority_certification=False)
        passed=bool(result and result.wasSuccessful() and result.testsRun==args.expected and not result.skipped and not BLOCKED
                    and error is None and wall<=120*10**9 and used_cpu<=120*10**9 and peak[0]<=536870912)
        status['status']='PASS' if passed else 'FAILED'
        put(args.out/'status.json',status);put(args.out/'case_results.json',dict(role='TEST_ONLY',cases=rows))
        put(args.out/'inputs_and_transition_traces.json',dict(role='TEST_ONLY; SYNTHETIC_GATE_RECEIPTS_HAVE_NO_AUTHORITY',records=module.TRACE if module else []))
        xml=ET.Element('testsuites');suite=ET.SubElement(xml,'testsuite',tests=str(status['tests']))
        for row in rows:
            case=ET.SubElement(suite,'testcase',classname='admin_transport_simulation',name=row['id'])
            if row['outcome']!='PASS':ET.SubElement(case,'failure',type=row['outcome']).text=row['message'] or row['outcome']
        ET.ElementTree(xml).write(args.out/'junit.xml',encoding='utf-8',xml_declaration=True)
    print(json.dumps(status,sort_keys=True));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
