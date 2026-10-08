"""Explicit-approval-only remote file tests, historical review and bounded overhead measurement."""
import argparse
import os
import platform
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from .policy import HERE,ROOT,raw_hash,check_policy
from . import history,correction
from experiments.adaptive_execution_real_learning_pilot_v0.common import read,write_new
from experiments.adaptive_execution_real_learning_pilot_v0.runner import code_check
from experiments.adaptive_execution_real_learning_pilot_v0.bridge import deadline,cpu_clock


EXPECTED_TESTS=202  # 142 original +60 new; static count checked before sealing.


def gate_seconds(ticket,policy):
    cap=min(policy['remote_proposal']['wall_seconds'],policy['remote_proposal']['aggregate_cpu_seconds'])
    seconds=ticket.get('remaining_seconds',cap)
    if type(seconds) is not int or not 1<=seconds<=cap: raise ValueError('REMAINING_BUDGET_CANNOT_WIDEN')
    return seconds


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--authorization',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path); args=parser.parse_args()
    ticket=read(args.authorization); p=check_policy(); code=code_check(); armed=read(args.authorization.parent/'armed.json')
    now=datetime.now(timezone.utc); start=datetime.fromisoformat(ticket['allocation_start_utc'])
    arm=datetime.fromisoformat(armed['armed_utc'])
    seconds=gate_seconds(ticket,p)
    from decimal import Decimal
    price=Decimal(str(armed.get('hourly_usd','NaN')))
    if (platform.system()!='Linux' or ticket.get('gate')!=p['gate'] or ticket.get('scope')!='EVIDENCE_OFFLINE_ONLY'
            or ticket.get('explicit_user_approval') is not True or not ticket.get('approval_reference')
            or ticket.get('code_seal_sha256')!=code or ticket.get('policy_sha256')!=raw_hash(HERE/'protocol.json')
            or str(ticket.get('instance_id'))!=os.environ.get('CONTAINER_ID') or ticket.get('physics_calls')!=0
            or ticket.get('gpu_calls')!=0 or armed.get('status')!='ARMED' or armed.get('outside_guest') is not True
            or not price.is_finite() or not 0<=price<=Decimal('0.25')
            or any(ticket.get(k)!=armed.get(k) for k in ('instance_id','machine_id','country','approval_reference'))
            or armed.get('guardian_sha256')!=raw_hash(ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py')
            or not 0<armed.get('deadline_seconds',0)<=p['remote_proposal']['guardian_deadline_seconds_max']
            or start.tzinfo is None or not 0<=(arm-start).total_seconds()<=60
            or not 0<=(now-arm).total_seconds()<=60): raise ValueError('EVIDENCE_OFFLINE_NOT_AUTHORIZED')
    args.out.mkdir(parents=True,exist_ok=False); begin=time.monotonic_ns(); cpu=cpu_clock()
    resource.setrlimit(resource.RLIMIT_CPU,(seconds,seconds)); resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0)); os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
             EVIDENCE_PHYSICS_GUARD_REPORT=str(args.out.resolve()/'physics_guard.json'))
    write_new(args.out/'authorization_used.json',ticket)
    def phase(name,argv):
        left=seconds-(time.monotonic_ns()-begin)/1e9
        if left<=1: raise TimeoutError('EVIDENCE_OFFLINE_BUDGET')
        with (args.out/(name+'.log')).open('xb') as log:
            result=subprocess.run([sys.executable,*argv],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=left)
        if result.returncode: raise ValueError('EVIDENCE_OFFLINE_PHASE_FAILED:'+name)
    try:
        with deadline(seconds):
            phase('tests',['-m','pytest','tests/test_adaptive_execution_verification_v0.py',
                  'tests/test_adaptive_execution_learning_v1.py','tests/test_adaptive_execution_real_learning_pilot_v0.py',
                  'tests/test_evidence_canonicalization_v0.py','-q','-p','no:cacheprovider',
                  '-p','experiments.evidence_canonicalization_v0.physics_guard','--junitxml='+str(args.out.resolve()/'junit.xml')])
            cases=ET.parse(args.out/'junit.xml').getroot().findall('.//testcase')
            if len(cases)!=EXPECTED_TESTS or any(c.find('skipped') is not None or c.find('error') is not None or c.find('failure') is not None for c in cases):
                raise ValueError('EXACT_TEST_COUNT_OR_FAILURE')
            phase('historical_review',['-m','experiments.adaptive_execution_real_learning_pilot_v0.inspector',
                  '--review-history','--out',str(args.out.resolve()/'historical_review')])
            r=args.out/'historical_review'; roots=read(r/'review_roots.json'); receipt=read(r/'historical_review_receipt.json')
            certificate=correction.derive(receipt,roots['inspector_public_key'])
            correction.validate(certificate,roots['inspector_public_key'])
            write_new(args.out/'derived_correction.json',certificate)  # PENDING; no manager activation.
            phase('overhead',['-m','experiments.evidence_canonicalization_v0.benchmark','--out',str(args.out.resolve()/'overhead')])
            history.check_preservation(); code_check()
        wall=time.monotonic_ns()-begin; end=cpu_clock(); aggregate=sum(end[k]-cpu[k] for k in cpu)
        if max(wall,aggregate)>seconds*10**9: raise ValueError('EVIDENCE_OFFLINE_BUDGET')
        write_new(args.out/'status.json',dict(status='EVIDENCE_FORMAT_V0_READY',historical_status='HISTORICAL_REVIEW_COMPLETE',
             tests=len(cases),failed=0,skipped=0,wall_ns=wall,cpu_ns=aggregate,new_physics_calls=0,gpu_calls=0,
             code_seal_sha256=code,original_status='REAL_LEARNING_FAIL',manager_approval='PENDING',production='NOT_CONNECTED'))
        return 0
    except BaseException as error:
        status='OVERHEAD_NOT_ACCEPTABLE' if str(error).endswith(':overhead') else 'EVIDENCE_FORMAT_FAIL'
        end=cpu_clock(); wall=time.monotonic_ns()-begin; aggregate=sum(end[k]-cpu[k] for k in cpu)
        write_new(args.out/'status.json',dict(status=status,reason=str(error),new_physics_calls=0,gpu_calls=0,
                  original_status='REAL_LEARNING_FAIL',code_seal_sha256=code,wall_ns=wall,cpu_ns=aggregate,
                  allocated_seconds=seconds))
        return 2


if __name__=='__main__': raise SystemExit(main())
