"""Fresh-approval, continuous-guardian remote gate; existing 202 plus new faults."""
import argparse
import os
import platform
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from . import policy, evidence
from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
from experiments.adaptive_execution_real_learning_pilot_v0.common import ROOT,HERE,write_new,raw_hash,read
from experiments.adaptive_execution_real_learning_pilot_v0.bridge import cpu_clock,deadline


def validate_status(status,code,expected):
    if (status.get('status')!='PASS' or status.get('code_seal_sha256')!=code
            or status.get('resume_protocol_sha256')!=policy.protocol_hash() or status.get('tests')!=expected
            or status.get('failed')!=0 or status.get('skipped')!=0 or status.get('physics_calls')!=0
            or status.get('gpu_calls')!=0 or status.get('mode')!='OFFLINE_CONTRACT_ONLY'):
        raise ValueError('A_RESUME_OFFLINE_GATE_REFUSED')


def authorize(ticket,armed,code,instance):
    p=policy.protocol(); a_safety.offline_lease(ticket,armed)
    if (platform.system()!='Linux' or ticket.get('gate')!=p['gate'] or not ticket.get('approval_reference')
            or ticket.get('code_seal_sha256')!=code or ticket.get('resume_protocol_sha256')!=policy.protocol_hash()
            or str(ticket.get('instance_id'))!=str(instance) or ticket.get('approval_reference')!=armed.get('approval_reference')
            or ticket.get('fresh_run_id')!=a_safety.armed_digest(armed)
            or armed.get('guardian_sha256')!=raw_hash(HERE/'guardian.py')):
        raise ValueError('A_RESUME_OFFLINE_NOT_AUTHORIZED')
    if a_safety.remaining(armed)['compute']<=120: raise ValueError('A_COMPUTE_BUDGET_TOO_SMALL_FOR_OFFLINE_GATE')
    a_safety.validate_heartbeat(read(ticket['heartbeat_path']),armed)


def monitor(ticket,armed,cpu_start):
    import psutil
    a_safety.validate_heartbeat(read(ticket['heartbeat_path']),armed)
    proc=psutil.Process(); children=proc.children(recursive=True); rss=proc.memory_info().rss; live=0
    for child in children:
        try:
            rss+=child.memory_info().rss; t=child.cpu_times(); live+=int((t.user+t.system)*10**9)
        except psutil.NoSuchProcess: pass
    now=cpu_clock(); aggregate=sum(now[k]-cpu_start[k] for k in now)+live
    if rss>512*1024**2 or aggregate>120*10**9: raise ValueError('OFFLINE_AGGREGATE_RESOURCE_STOP')


def main():
    from experiments.adaptive_execution_real_learning_pilot_v0.runner import code_check
    parser=argparse.ArgumentParser(); parser.add_argument('--authorization',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path); args=parser.parse_args()
    ticket=read(args.authorization); armed=read(args.authorization.parent/'armed.json'); code=code_check()
    authorize(ticket,armed,code,os.environ.get('CONTAINER_ID'))
    from experiments.adaptive_execution_real_learning_pilot_v0.common import code_manifest_path
    expected=read(code_manifest_path())['expected_tests']
    args.out.mkdir(parents=True,exist_ok=False); start=time.monotonic_ns(); cpu=cpu_clock()
    resource.setrlimit(resource.RLIMIT_CPU,(120,120)); resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0)); os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
             EVIDENCE_PHYSICS_GUARD_REPORT=str(args.out.resolve()/'physics_guard.json'))
    write_new(args.out/'authorization_used.json',ticket)
    try:
        from experiments.adaptive_execution_real_learning_pilot_v0.resources import Watch
        watch=Watch(time.monotonic()+120,lambda:monitor(ticket,armed,cpu))
        watch.start()
        try:
            with deadline(120),(args.out/'tests.log').open('xb') as log:
                result=subprocess.run([sys.executable,'-m','pytest',
                   'tests/test_adaptive_execution_verification_v0.py','tests/test_adaptive_execution_learning_v1.py',
                   'tests/test_adaptive_execution_real_learning_pilot_v0.py','tests/test_evidence_canonicalization_v0.py',
                   'tests/test_adaptive_execution_real_learning_pilot_a_resume_v1.py','-q','-p','no:cacheprovider',
                   '-p','experiments.evidence_canonicalization_v0.physics_guard','--junitxml='+str(args.out.resolve()/'junit.xml')],
                   cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=110)
        finally: watch.close()
        cases=ET.parse(args.out/'junit.xml').getroot().findall('.//testcase')
        end=cpu_clock(); wall=time.monotonic_ns()-start; aggregate=sum(end[k]-cpu[k] for k in cpu)
        failed=sum(x.find('failure') is not None or x.find('error') is not None for x in cases)
        skipped=sum(x.find('skipped') is not None for x in cases)
        guard=evidence.strict_read(args.out/'physics_guard.json')
        status='PASS' if result.returncode==0 and len(cases)==expected and failed==skipped==0 else 'STOP_TEST_GATE_FAILURE'
        if max(wall,aggregate)>120*10**9 or guard.get('blocked_attempts'): status='STOP_BUDGET_OR_PHYSICS_ATTEMPT'
        code_check(); a_safety.validate_heartbeat(read(ticket['heartbeat_path']),armed)
        write_new(args.out/'status.json',dict(status=status,tests=len(cases),failed=failed,skipped=skipped,
                 wall_ns=wall,cpu_ns=aggregate,code_seal_sha256=code,resume_protocol_sha256=policy.protocol_hash(),
                 physics_calls=0,gpu_calls=0,mode='OFFLINE_CONTRACT_ONLY'))
        return 0 if status=='PASS' else 2
    except BaseException as error:
        write_new(args.out/'status.json',dict(status='STOP_OFFLINE_FAILURE',reason=str(error),physics_calls=0,gpu_calls=0,
                 code_seal_sha256=code,resume_protocol_sha256=policy.protocol_hash()))
        return 2


if __name__=='__main__': raise SystemExit(main())
