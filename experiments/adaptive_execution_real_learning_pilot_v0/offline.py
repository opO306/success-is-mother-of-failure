"""Bounded remote contract test gate. Historical reads and mocks only; no physics/GPU."""
import argparse
import os
import platform
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from .common import ROOT,HERE,read,write_new,raw_hash
from .runner import code_check
from .bridge import deadline,cpu_clock


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--authorization',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path); args=parser.parse_args()
    ticket=read(args.authorization); code=code_check()
    if (platform.system()!='Linux' or ticket.get('gate')!='ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0'
            or ticket.get('scope')!='OFFLINE_ONLY' or ticket.get('explicit_user_approval') is not True
            or not ticket.get('approval_reference') or ticket.get('code_seal_sha256')!=code
            or str(ticket.get('instance_id'))!=os.environ.get('CONTAINER_ID')
            or ticket.get('physics_calls')!=0 or ticket.get('gpu_calls')!=0): raise ValueError('OFFLINE_NOT_AUTHORIZED')
    if ticket.get('budget_amendment_sha256')!=raw_hash(HERE/'offline_budget_amendment_52763685.json'):
        raise ValueError('OFFLINE_AMENDMENT_NOT_AUTHORIZED')
    amendment=read(HERE/'offline_budget_amendment_52763685.json')
    if (str(ticket['instance_id'])!=str(amendment['instance_id']) or ticket.get('machine_id')!=amendment['machine_id']
            or ticket.get('country')!=amendment['country'] or ticket.get('hourly_cap_usd')!=amendment['hourly_cap_usd']):
        raise ValueError('OFFLINE_AMENDMENT_SCOPE_REFUSED')
    armed=read(args.authorization.parent/'armed.json')
    if (armed.get('status')!='ARMED' or armed.get('outside_guest') is not True
            or armed.get('instance_id')!=amendment['instance_id']
            or armed.get('guardian_sha256')!=raw_hash(HERE/'guardian.py')
            or armed.get('budget_amendment_sha256')!=ticket['budget_amendment_sha256']): raise ValueError('EXTERNAL_GUARDIAN_NOT_ARMED')
    args.out.mkdir(parents=True,exist_ok=False); start=time.monotonic_ns(); cpu=cpu_clock()
    resource.setrlimit(resource.RLIMIT_CPU,(120,120)); resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0)); os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    write_new(args.out/'authorization_used.json',ticket)
    try:
        with deadline(120),(args.out/'tests.log').open('xb') as log:
            result=subprocess.run([sys.executable,'-m','pytest','tests/test_adaptive_execution_verification_v0.py',
                  'tests/test_adaptive_execution_learning_v1.py','tests/test_adaptive_execution_real_learning_pilot_v0.py',
                  '-q','-p','no:cacheprovider','--junitxml='+str(args.out/'junit.xml')],cwd=ROOT,env=env,
                  stdout=log,stderr=subprocess.STDOUT,timeout=110)
        suites=ET.parse(args.out/'junit.xml').getroot().findall('.//testcase')
        skipped=sum(x.find('skipped') is not None for x in suites)
        failed=sum(x.find('failure') is not None or x.find('error') is not None for x in suites)
        status='PASS' if result.returncode==0 and skipped==0 and failed==0 and len(suites)==122 else 'STOP_TEST_GATE_FAILURE'
        code_check(); end=cpu_clock(); wall=time.monotonic_ns()-start; aggregate=sum(end[k]-cpu[k] for k in cpu)
        if wall>120*10**9 or aggregate>120*10**9: status='STOP_BUDGET'
        write_new(args.out/'status.json',dict(status=status,tests=len(suites),failed=failed,skipped=skipped,
                  wall_ns=wall,cpu_ns=aggregate,code_seal_sha256=code,physics_calls=0,gpu_calls=0,
                  mode='OFFLINE_CONTRACT_ONLY',actual_shutdown='OUTSIDE_GUEST_CONFIRMATION_REQUIRED'))
        return 0 if status=='PASS' else 2
    except BaseException as error:
        write_new(args.out/'status.json',dict(status='STOP_OFFLINE_FAILURE',error=str(error),physics_calls=0,gpu_calls=0))
        return 2


if __name__=='__main__': raise SystemExit(main())
