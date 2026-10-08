"""Approval-gated sequential research controller. No production hookup or Vast start API."""
import argparse
import json
import os
import platform
import subprocess
import sys
import time
import threading
import uuid
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .common import HERE,ROOT,canonical,digest,read,write_new,raw_hash,check_seals,public,code_manifest_path
from . import bridge,governance,knowledge,costs,a_safety
from experiments.adaptive_execution_real_learning_pilot_a_resume_v1 import policy as RP,evidence as RE,offline as RO


def authorize(ticket,stage,code,*,instance_id,platform_name):
    if (platform_name!='Linux' or ticket.get('gate') not in ('ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0', 'ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_A_RESUME_V1')
            or ticket.get('scope')!='REAL_RESEARCH' or ticket.get('explicit_user_approval') is not True
            or not ticket.get('approval_reference') or str(ticket.get('instance_id'))!=str(instance_id)
            or not ticket.get('machine_id') or not ticket.get('country') or stage not in ticket.get('stages',[])
            or ticket.get('code_seal_sha256')!=code): raise ValueError('REAL_EXECUTION_NOT_AUTHORIZED')
    rate=Decimal(str(ticket.get('hourly_usd','NaN')))
    if not rate.is_finite() or not 0<=rate<=Decimal('0.25'): raise ValueError('PRICE_CAP')
    return ticket


def code_check():
    check_seals(); seal=read(code_manifest_path())
    for path,expected in seal['files'].items():
        if raw_hash(ROOT/path)!=expected: raise ValueError('SOURCE_INTEGRITY:'+path)
    return raw_hash(code_manifest_path())


def signed(key,domain,body): return {'body':body,'signature':key.sign(domain+canonical(body)).hex()}


def collect_a(capture,first_gate,after_record):
    """No second capture until the saved first result passes the separate inspector."""
    records=[]
    for method,repeat in RP.protocol()['order']:
        obj=capture(method,repeat); records.append(obj)
        if len(records)==1: first_gate(obj)
        after_record(obj)
    return records


def close_inspector(process):
    if process.poll() is not None: return
    try:
        process.stdin.write(json.dumps({'operation':'CLOSE'})+'\n'); process.stdin.flush()
    except (BrokenPipeError,OSError): pass  # Keep the already recorded STOP reason.
    try: process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate(); process.wait(timeout=10)


class Pilot:
    def __init__(self,ticket,host,armed,offline,out):
        self.code=code_check(); self.ticket=ticket; self.root=Path(out); self.root.mkdir(parents=True,exist_ok=False)
        authorize(ticket,'A',self.code,instance_id=host['id'],platform_name=platform.system())
        if (ticket.get('gate')!=RP.protocol()['gate'] or ticket.get('resume_protocol_sha256')!=RP.protocol_hash()
                or ticket.get('fresh_run_id')!=a_safety.armed_digest(armed)):
            raise ValueError('FRESH_A_RESUME_APPROVAL_REQUIRED')
        if str(host['id'])!=os.environ.get('CONTAINER_ID'): raise ValueError('ACTUAL_CONTAINER_INSTANCE_MISMATCH')
        if (str(armed.get('instance_id'))!=str(host['id']) or armed.get('status')!='ARMED'
                or armed.get('outside_guest') is not True or armed.get('guardian_sha256')!=raw_hash(HERE/'guardian.py')
                or armed.get('approval_reference')!=ticket['approval_reference']
                or armed.get('machine_id')!=ticket['machine_id'] or armed.get('country')!=ticket['country']
                or host.get('machine_id')!=ticket['machine_id'] or host.get('country')!=ticket['country']
                or host.get('actual_status')!='running' or Decimal(str(host['dph_total']))>Decimal('0.25')
                or Decimal(str(host['dph_total']))>Decimal(str(ticket['hourly_usd']))
                or ticket.get('approve_research_profile') is not True): raise ValueError('HOST_GUARDIAN_OR_MANAGER_APPROVAL_REFUSED')
        RO.validate_status(offline,self.code,read(code_manifest_path())['expected_tests'])
        if ticket.get('stages')!=['A'] or ticket.get('safety_policy_sha256')!=a_safety.policy_hash():
            raise ValueError('A_ONLY_SAFETY_APPROVAL_REQUIRED')
        self.armed=armed; self.heartbeat_path=Path(ticket['heartbeat_path']); self.heartbeat_sequence=0
        self.control_lock=threading.Lock()
        limits=a_safety.remaining(armed)
        self.deadline=time.monotonic()+limits['compute']
        self.control_check()
        self.rate=Decimal(str(host['dph_total']))
        self.started=time.monotonic_ns(); self.start_cpu=bridge.cpu_clock(); self.book=costs.Book(self.root/'costs')
        # Separate research roots exist before the first completion record. Same UID is disclosed.
        self.ruler=Ed25519PrivateKey.generate()
        self.inspector_log=(self.root/'inspector_stderr.log').open('xb')
        self.inspector_process=subprocess.Popen([sys.executable,'-m','experiments.adaptive_execution_real_learning_pilot_v0.inspector',
                        '--serve',str(self.root)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.inspector_log,text=True)
        with bridge.deadline(30): hello=json.loads(self.inspector_process.stdout.readline())
        if hello['code_manifest_sha256']!=self.code: raise ValueError('INSPECTOR_SOURCE_MIX')
        self.roots=governance.Roots(hello['inspector_public_key'],public(self.ruler.public_key()),'RESEARCH_ONLY')
        write_new(self.root/'provision.json',dict(roots=self.roots.__dict__,ticket=ticket,host_observation=host,
                guardian=armed,offline_gate=offline,os_isolation='ABSENT; SAME_UID_RESEARCH_CONTROLLER',
                host_attestation='API_WHITELIST_AND_GUEST_BOOT_ID; NOT_HARDWARE_ATTESTATION'))
        self.mgr=governance.Manager(self.root/'manager',self.root/'controller_witness',self.roots,self.ruler)
        self.gpu=None

    def control_check(self):
        with self.control_lock:
            self.heartbeat_sequence=a_safety.validate_heartbeat(read(self.heartbeat_path),self.armed,
                                          minimum_sequence=self.heartbeat_sequence)

    def seconds(self):
        self.control_check()
        remaining=self.deadline-time.monotonic()
        if remaining<10: raise TimeoutError('ALLOCATION_BUDGET_STOP')
        import psutil
        proc=psutil.Process(); members=[proc,*proc.children(recursive=True)]
        rss=sum(p.memory_info().rss for p in members if p.is_running())
        if rss>2048*1024**2: raise ValueError('AGGREGATE_RSS_CAP_STOP')
        return min(480,remaining)

    def charged(self,category,fn):
        self.seconds(); start=time.monotonic_ns(); cpu=bridge.cpu_clock(self.gpu)
        import psutil
        verifier=psutil.Process(self.inspector_process.pid); vstart=verifier.cpu_times(); vstart_ns=int((vstart.user+vstart.system)*10**9)
        try: return fn()
        finally:
            endcpu=bridge.cpu_clock(self.gpu)
            vend=verifier.cpu_times(); delta=int((vend.user+vend.system)*10**9)-vstart_ns
            self.book.charge(category,time.monotonic_ns()-start,sum(endcpu[k]-cpu[k] for k in cpu)+delta)

    def inspect(self,path,operation='INSPECT'):
        self.inspector_process.stdin.write(json.dumps({'operation':operation,'stage':path.name})+'\n'); self.inspector_process.stdin.flush()
        with bridge.deadline(self.seconds()): response=json.loads(self.inspector_process.stdout.readline())
        write_new(path/(operation+'_process.json'),response)
        expected=RE.VERDICTS[operation]
        receipt_path=path/RE.RECEIPTS[operation]
        if response.get('verdict')!=expected or response.get('receipt_sha256')!=raw_hash(receipt_path):
            raise ValueError('INDEPENDENT_INSPECTOR_REFUSED')
        RE.check_receipt(self.roots.inspector,RE.strict_read(receipt_path),path,RE.strict_read(path/'session.json'),operation)

    def child(self,module,directory,stdin=None):
        env=dict(os.environ); env['PYTHONPATH']=str(ROOT)
        proc=subprocess.run([sys.executable,'-m',module,str(directory)],input=stdin,capture_output=True,text=True,
                            timeout=self.seconds(),env=env)
        write_new(directory/(module.rsplit('.',1)[-1]+'_process.json'),dict(returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr))
        if proc.returncode: raise ValueError('INDEPENDENT_PROCESS_REFUSED:'+module)

    def approval(self,target,goal,name):
        body=self.mgr.approval_body(target,goal,name,self.ticket['approval_reference']+'; research profile delegation')
        return signed(self.ruler,b'REAL_PILOT_APPROVAL\0',body)

    def stage(self,spec):
        stage=spec['id']; authorize(self.ticket,stage,self.code,instance_id=self.ticket['instance_id'],platform_name=platform.system())
        if stage!='A' or (spec['N'],spec['T'],spec['goal'],spec['methods'])!=(14,1000,'WALL_MIN',['SERIAL','W6']):
            raise ValueError('RESUME_A_ONLY')
        path=self.root/stage; path.mkdir(); self.seconds()
        cost_start=self.book.total()
        cost_start_index=len(self.book.events.history())
        from experiments.adaptive_execution_v1 import environment as ENV,experience as EXP,selector as SEL,adapters as AD
        from .inspector import validate_record
        env=self.charged('environment_prepare',ENV.collect)
        if not SEL.cpu_verified(env) or 'W6' not in SEL.placements(env):
            raise ValueError('CPU_CORRECTNESS_OR_SIX_PHYSICAL_CORE_QUOTA_PREFLIGHT_REFUSED')
        from experiments.evidence_canonicalization_v0.fingerprints import CONTENT_VERSION,policy_hash
        session=dict(origin='OBSERVED_REAL',session_id=str(uuid.uuid4()),N=spec['N'],T=spec['T'],goal=spec['goal'],
              methods=spec['methods'],env=env,hostname=platform.node(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              instance_id=self.ticket['instance_id'],machine_id=self.ticket['machine_id'],code_manifest_sha256=self.code,
              evidence_version=2,initial_content_version=CONTENT_VERSION,evidence_policy_sha256=policy_hash(),
              resume_protocol_sha256=RP.protocol_hash())
        write_new(path/'session.json',session); write_new(path/'knowledge_before.json',knowledge.gaps(session))
        write_new(path/'learning_value_before.json',dict(knowledge.value(),
                  execution_basis='EXPLICIT_USER_RESEARCH_PILOT_SCOPE; NOT_AUTOMATIC_VALUE_APPROVAL'))
        store=EXP.load_store(); before=self.mgr.begin(session['goal'],session)
        if self.mgr.choose(before,session)!='LEGACY': raise ValueError('HISTORICAL_PROFILE_IMPORTED')
        # Policy probe is not a trajectory. The first measured call is explicitly SERIAL.
        if self.ticket.get('resume_protocol_sha256'):
            legacy_plan=SEL.select(spec['N'],spec['T'],163,session['goal'],env,perf=None).record()
            write_new(path/'legacy_selector_before.json',legacy_plan)
            if legacy_plan['backend']!='CPU_SERIAL': raise ValueError('LEGACY_SERIAL_BASELINE_NOT_CONFIRMED')
        if stage=='B':
            if not SEL.gpu_eligible(12,1000,163,env,False)[0]: raise ValueError('CURRENT_GPU_NOT_ELIGIBLE')
            def prepare():
                from experiments.gpu_pair_vector_v1 import pv_host as PH
                lib,arch,_=PH.build(path/'gpu_build')
                self.gpu=AD.GpuWorker(lib)
                if not self.gpu.ready: raise ValueError('GPU_NOT_READY')
                write_new(path/'gpu_prepare.json',{'arch':arch,'hello':self.gpu.hello})
            self.charged('GPU_prepare',prepare)
        if stage!='A': raise ValueError('RESUME_A_ONLY')
        replay=None; seen=[]
        def capture(method,rep,directory,snapshot,reason,category):
            code_check()
            return self.charged(category,lambda:RE.capture_cost(directory,session,method,rep,
                lambda:bridge.capture(directory,session,method,rep,store,gpu=self.gpu,snapshot=snapshot,
                             reason=reason,seconds=self.seconds()),lambda:bridge.cpu_clock(self.gpu)))
        def first_gate(obj):
            nonlocal replay
            self.charged('independent_replay',lambda:self.child('experiments.adaptive_execution_real_learning_pilot_v0.replay_worker',path))
            replay=RE.strict_read(path/'replay.json')
            self.charged('first_independent_inspection',lambda:self.inspect(path,'CHECK_FIRST'))
        def after_record(obj):
            seen.append(obj)
            self.charged('verification_signing_management',lambda:validate_record(obj,session,replay))
            estimate=max(x['observation']['wall_ns'] for x in seen)*(11-len(seen))*5//4
            remaining=int((self.deadline-time.monotonic())*10**9)
            write_new(path/f'budget_after_{len(seen):02d}.json',dict(estimate_ns=estimate,remaining_ns=remaining,
                       kind='UNVERIFIED_CURRENT_SESSION_PLANNING_ONLY'))
            if estimate>remaining: raise TimeoutError('MEASURED_BUDGET_RISK_STOP')
        records=collect_a(lambda method,rep:capture(method,rep,path/'measurement',before,
                         'EXPLICIT_SERIAL_FIRST_GATE' if method=='SERIAL' and rep==0 else 'USER_AUTHORIZED_EXPERIMENT',
                         'measurement'),first_gate,after_record)
        # Independent reader process computes the receipt; controller never fabricates its approval result.
        self.charged('verification_signing_management',lambda:self.inspect(path))
        def promote():
            profile=self.mgr.admit(read(path/'receipt.json'))
            self.mgr.activate(self.approval(profile['id'],session['goal'],stage+'-activate'))
            return profile
        profile=self.charged('verification_signing_management',promote)
        after=self.mgr.begin(session['goal'],session); choice=self.mgr.choose(after,session)
        if self.mgr.choose(before,session)!='LEGACY': raise ValueError('MID_REQUEST_PROFILE_SWAP')
        write_new(path/'knowledge_after.json',knowledge.gaps(session,session['methods']))
        learned=capture(choice,5,path/'next_request',after,'APPROVED_FRESH_SESSION_RESEARCH_PROFILE','learned_request')
        self.charged('verification_signing_management',lambda:validate_record(learned,session,replay))
        self.charged('verification_signing_management',lambda:self.inspect(path,'CHECK_NEXT'))
        def rollback():
            self.mgr.rollback(self.approval('LEGACY',session['goal'],stage+'-rollback'))
            if self.mgr.choose(self.mgr.begin(session['goal'],session),session)!='LEGACY': raise ValueError('ROLLBACK_FAILED')
            if self.mgr.choose(after,session)!=choice: raise ValueError('IN_FLIGHT_SNAPSHOT_CHANGED')
            plan=SEL.select(spec['N'],spec['T'],163,session['goal'],env,perf=None).record()
            if plan['backend']!='CPU_SERIAL': raise ValueError('LEGACY_SELECTOR_ROLLBACK_FAILED')
            write_new(path/'legacy_selector_after_rollback.json',plan)
        self.charged('rollback',rollback)
        metric='wall_ns' if session['goal']=='WALL_MIN' else 'cpu_ns'
        before_cost,_=RE.read_cost(path/'measurement',records[0],session)
        after_cost,_=RE.read_cost(path/'next_request',learned,session)
        baseline=before_cost[metric]; measured=after_cost[metric]
        # The first serial observation is the baseline request, not learning overhead a second time.
        stagecost=self.book.total(); overhead=stagecost[metric]-cost_start[metric]-baseline-measured
        verify_cost=sum(x['payload'][metric] for x in self.book.events.history()[cost_start_index:]
                        if x['payload']['category']=='verification_signing_management')
        write_new(path/'learning_value_after.json',knowledge.value(saving_ns=max(0,baseline-measured),confirmed_reuses=1,
              measurement_ns=max(0,overhead-verify_cost),verification_ns=verify_cost,accuracy_in_scope=True,
              available_ns=max(0,int((self.deadline-time.monotonic())*10**9))))
        analysis=costs.recovery(overhead_ns=max(0,overhead),baseline_ns=baseline,learned_ns=measured,observed_reuses=1)
        improved=choice!='SERIAL' and measured<baseline
        report=dict(status='REAL_LEARNING_LOOP_VALIDATED' if improved else 'REAL_LEARNING_NOT_READY',
                stage=stage,goal=session['goal'],before_method='SERIAL',after_method=choice,
                before_observation=before_cost,after_observation=after_cost,
                before_calculation_observation=records[0]['observation'],after_calculation_observation=learned['observation'],
                cost_scope=RP.protocol()['request_cost_scope'],first_gate='SIGNED_FIRST_RESULT_CHECKED',fresh_replays=1,
                profile_id=profile['id'],cost=analysis,rollback='NEXT_REQUEST_LEGACY_CONFIRMED',
                formula_independence='UNRESOLVED_SHARED_RWFORCE',production='NOT_CONNECTED')
        write_new(path/'stage_report.json',report)
        return report

    def run(self):
        from .resources import Watch
        watch=Watch(self.deadline,self.control_check); watch.start()
        reports=[]
        try:
            for spec in [RP.protocol()['stage']]:
                if spec['id'] not in self.ticket['stages']: continue
                if spec['id']=='B' and (not reports or reports[0]['status']!='REAL_LEARNING_LOOP_VALIDATED'):
                    raise ValueError('A_NOT_PASSED_B_REFUSED')
                reports.append(self.stage(spec))
            status='REAL_LEARNING_LOOP_VALIDATED' if reports and all(r['status']=='REAL_LEARNING_LOOP_VALIDATED' for r in reports) else 'REAL_LEARNING_NOT_READY'
        except BaseException as error:
            status='REAL_LEARNING_FAIL'
            write_new(self.root/'STOP.json',{'status':'STOP','reason':str(error),'partial_reports':reports})
        finally:
            watch.close()
            if self.gpu is not None:
                self.gpu.close()
                if self.gpu.proc.is_alive(): self.gpu.proc.terminate(); self.gpu.proc.join(timeout=5)
                self.gpu=None
            close_inspector(self.inspector_process)
            self.inspector_log.close()
        cpu=bridge.cpu_clock(); total_cpu=sum(cpu[k]-self.start_cpu[k] for k in cpu); total_wall=time.monotonic_ns()-self.started
        self.book.charge('job_total',total_wall,total_cpu)
        result=dict(status=status,stages=reports,total_wall_ns=total_wall,total_cpu_ns=total_cpu,
                  hourly_usd=str(self.rate),approved_hourly_cap_usd=self.ticket['hourly_usd'],billing_level='RATE_ESTIMATE_ONLY_NO_BILLING_RECEIPT',
                  estimated_job_usd=str(self.rate*Decimal(total_wall)/Decimal(3600*10**9)),
                  shutdown='EXTERNAL_GUARDIAN_CONFIRMATION_REQUIRED',production='NOT_CONNECTED')
        result['whole_job_recovery_by_goal']={}
        for report in reports:
            metric='wall_ns' if report['goal']=='WALL_MIN' else 'cpu_ns'
            baseline=report['before_observation'][metric]; learned=report['after_observation'][metric]
            whole=total_wall if metric=='wall_ns' else total_cpu
            result['whole_job_recovery_by_goal'][report['goal']]=costs.recovery(overhead_ns=max(0,whole-baseline-learned),
                         baseline_ns=baseline,learned_ns=learned,observed_reuses=1)
        result['allocation_cost_status']='EXTERNAL_ALLOCATION_CLOSEOUT_REQUIRED'
        result['whole_job_recovery_scope']='RUNNER_ONLY_PROVISIONAL; NOT_WHOLE_ALLOCATION'
        write_new(self.root/'report.json',result); return result


def main():
    parser=argparse.ArgumentParser()
    for name in ('authorization','host_observation','guardian','offline_checks','out'): parser.add_argument('--'+name.replace('_','-'),required=True,type=Path)
    args=parser.parse_args()
    pilot=Pilot(read(args.authorization),read(args.host_observation),read(args.guardian),read(args.offline_checks),args.out)
    result=pilot.run(); print(result['status'],flush=True)
    return 0 if result['status'] in ('REAL_LEARNING_LOOP_VALIDATED','REAL_LEARNING_COST_USEFUL') else 2


if __name__=='__main__': raise SystemExit(main())
