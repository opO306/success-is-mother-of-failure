"""V12 A-only fresh approved window. Local work is administrative control only."""
import argparse
import base64
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
import psutil
from admin_revalidation import ready_on_same_instance,SafetyStop,AdministrativeUnavailable
V5=Path(__file__).resolve().parent
sys.path.insert(0,str(V5))
from preflight import before_any_rental
from cleanup import close_owned
from budget import Ledger, charge_total, money, reservation
from lifecycle import Provider, save, save_atomic, identity, stop_owned, destroy_owned, verified_recovery, verify_admin,verify_startup

BASE=V5
ROOT=BASE.parents[3]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def utc():return datetime.now(timezone.utc).isoformat()


def source_preflight(policy):
    if sha(BASE/'authorization_request.txt')!=policy['authorization_raw_sha256']:
        raise ValueError('USER_REQUEST_RAW_DRIFT')
    if sha(BASE/policy['operational_amendment_path'])!=policy['operational_amendment_sha256'] or policy.get('administrative_revalidation_authorized') is not True:
        raise ValueError('ACTUAL_USER_ADMIN_REPAIR_AMENDMENT_REQUIRED')
    seal=read(BASE/'operational_seal.json')
    for relative,wanted in seal['files'].items():
        if sha(BASE/relative)!=wanted:raise ValueError('OPERATIONAL_SOURCE_DRIFT:'+relative)
    for relative,wanted in policy['preserved_files'].items():
        if sha(ROOT/relative)!=wanted:raise ValueError('HISTORICAL_SOURCE_DRIFT:'+relative)
    if policy['project_cap_usd']!='2.00' or policy['local_dynamic_tests'] is not False:
        raise ValueError('PROJECT_POLICY_BOUNDARY')
    for kind,spec in read(BASE/'transport/package_bindings.json').items():
        if sha(ROOT/spec['archive'])!=spec['zip_sha256'] or sha(ROOT/spec['inventory'])!=spec['inventory_sha256']:
            raise ValueError('SEALED_PACKAGE_DRIFT')
    return True


def choose(provider,policy):
    offers=provider.call('search','offers',
        'verified=true rentable=true rented=false reliability>0.98 num_gpus=1 cpu_cores_effective>=2 cpu_ram>=4 dph_total<0.25',
        '-o','dph_total','--limit','15','--storage',str(policy['disk_gb']))
    if not isinstance(offers,list):raise ValueError('OFFERS_LIST_REQUIRED')
    eligible=[]
    for offer in offers:
        if (type(offer.get('id')) is not int or type(offer.get('machine_id')) is not int
            or offer.get('machine_id')==53859 or offer.get('cpu_arch')!='amd64' or not offer.get('public_ipaddr')
            or not isinstance(offer.get('direct_port_count'),int) or offer['direct_port_count']<1
            or money(offer.get('cpu_ram'))<4096 or money(offer.get('disk_space'))<policy['disk_gb']
            or not offer.get('geolocation') or money(offer.get('dph_total'))>Decimal('.25')):continue
        cost=reservation(offer,seconds=policy['lease_seconds'],disk_gb=policy['disk_gb'],
            up_gb=policy['upload_gb'],down_gb=policy['download_gb'],uncertainty=policy['per_instance_uncertainty_usd'])
        eligible.append((money(cost['total']),offer,cost))
    if not eligible:raise ValueError('NO_ELIGIBLE_UNCHANGED_HARNESS_OFFER')
    eligible=[item for item in eligible if item[0]<=money(policy['maximum_new_reservation_usd'])]
    if not eligible:raise ValueError('NO_OFFER_WITHIN_APPROVED_WORST_CASE_RESERVATION')
    eligible.sort(key=lambda item:(item[0],item[1]['id']))
    return eligible[0][1:]


def command(out,argv,name,timeout,input=None,watch=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    save(out/(name+'.command.json'),dict(argv=argv,timeout_seconds=timeout))
    with (out/(name+'.stdout')).open('xb') as a,(out/(name+'.stderr')).open('xb') as b:
        child=None
        try:
            if watch is None:result=subprocess.run(argv,input=input,stdout=a,stderr=b,timeout=timeout)
            else:
                if watch.poll() is not None:raise ValueError('LEASE_WATCHDOG_LOST')
                child=subprocess.Popen(argv,stdin=subprocess.PIPE if input is not None else None,stdout=a,stderr=b)
                until=time.monotonic()+timeout;send=input
                while True:
                    if watch.poll() is not None:raise ValueError('LEASE_WATCHDOG_LOST')
                    left=until-time.monotonic()
                    if left<=0:raise subprocess.TimeoutExpired(argv,timeout)
                    try:child.communicate(input=send,timeout=min(.5,left));break
                    except subprocess.TimeoutExpired:send=None
                if watch.poll() is not None:raise ValueError('LEASE_WATCHDOG_LOST')
                result=child
        except BaseException:
            if child is not None and child.poll() is None:child.kill();child.wait(timeout=2)
            raise
    save(out/(name+'.exit.json'),dict(returncode=result.returncode))
    if result.returncode:raise ValueError('ADMIN_TRANSPORT_COMMAND_FAILED:'+name)
    return (out/(name+'.stdout')).read_bytes()


def command_recheck(out,argv,name,timeout,watch=None):
    """Only identity-bound read or empty-directory preparation, never a test launch."""
    from admin_revalidation import transient_connection
    deadline=time.monotonic()+timeout
    for attempt in range(1,4):
        left=deadline-time.monotonic()
        if left<=0:raise AdministrativeUnavailable('UNCHANGED_ADMIN_PREPARATION_DEADLINE')
        folder=Path(out)/(name+'_rechecks')/('attempt_'+str(attempt))
        try:return command(folder,argv,name,left,watch=watch)
        except (ValueError,subprocess.TimeoutExpired) as error:
            stderr=(folder/(name+'.stderr')).read_text(encoding='utf-8',errors='replace') if (folder/(name+'.stderr')).exists() else ''
            security=any(s in stderr.lower() for s in ('host key verification failed','remote host identification has changed','permission denied'))
            if attempt==3 or security or not (isinstance(error,subprocess.TimeoutExpired) or (str(error).startswith('ADMIN_TRANSPORT_COMMAND_FAILED:') and transient_connection(stderr))):raise


def remote_admin(out,ssh,scp_prefix,owner,watch,policy):
    guest='/workspace/vast_budget_admin_'+owner['run_id']
    save(out/'admin_preparation_started.json',dict(instance_id=owner['instance_id'],guest=guest,observed_utc=utc()))
    script="import pathlib,sys\nids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'CONTAINER_ID=')]\nif ids!=[sys.argv[2]]:raise ValueError('PREPARATION_ACTUAL_INSTANCE_MISMATCH')\np=pathlib.Path(sys.argv[1])\nif p.parent!=pathlib.Path('/workspace') or p.resolve()!=p:raise ValueError('PREPARATION_ROOT_SCOPE')\nif p.exists() and (not p.is_dir() or p.is_symlink() or any(p.iterdir())):raise ValueError('PREPARATION_EXISTING_CONTENT')\np.mkdir(exist_ok=True)"
    command_recheck(out/'admin_io',ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',script,guest,str(owner['instance_id'])])],'mkdir',12,watch=watch)
    from admin_revalidation import transfer_on_same_instance
    deadline=min(time.monotonic()+60,owner['allocation_monotonic_ns']/1e9+policy['lease_seconds']-220-730)
    def control():
        if watch.poll() is not None:raise SafetyStop('LEASE_WATCHDOG_LOST')
    admin_provider=Provider(read(out/'watchdog_lease.json')['cli'],out/'admin_control')
    def upload_identity(left):
        current=identity(admin_provider.call('show','instance',owner['instance_id'],timeout=min(8,left)),owner)
        ports={r.get('HostPort') for r in current.get('ports',{}).get('22/tcp',[])}
        if (current.get('actual_status')!='running' or current.get('intended_status')!='running' or current.get('public_ipaddr')!=owner['public_ipaddr'] or ports!={str(owner['direct_ssh_port'])}):raise SafetyStop('ADMIN_INSTANCE_OR_MAPPING_CHANGED')
        if money(current.get('dph_total'))>money(owner['observed_rate_usd']):raise SafetyStop('ADMIN_PRICE_DRIFT')
    def upload_operation(folder,left):
        command(folder,scp_prefix+[str(BASE/'admin_payload.zip'),'root@'+owner['public_ipaddr']+':'+guest+'/admin.zip'],'upload',left,watch=watch)
    transfer_on_same_instance(deadline,out/'admin_io',upload_operation,control,upload_identity,maximum_attempts=3)
    save(out/'admin_started.json',dict(instance_id=owner['instance_id'],guest=guest,observed_utc=utc(),meaning='BEFORE_ACTUAL_ADMIN_TEST_COMMAND'))
    sys.path.insert(0,str(BASE/'transport'))
    spec=importlib.util.spec_from_file_location('v12_admin_job_transport',BASE/'transport/controller.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.configure('A')
    io=out/'admin_job_io';io.mkdir(exist_ok=False)
    a=dict(owner,run_id=owner['run_id']+'_admin',ssh_host=owner['public_ipaddr'],ssh_port=owner['direct_ssh_port'],known_hosts_file=str(out/'known_hosts'))
    t=module.Transport(a,admin_provider.cli,'C:/Users/zun24/.ssh/vast_ai',io)
    t.remote_created=True;t.identity_verified=True  # Same freshly observed instance, already checked PID1/runtime.
    t.evidence_job_role='ADMIN_TESTS'
    t.guest=guest;t.ssh_argv=ssh;t.start_ns=owner['allocation_monotonic_ns'];t.started_utc=owner['allocation_start_utc']
    t.stop_control_check=control;t.handoff=lambda:policy['lease_seconds']-220
    def admin_control(required_seconds,*,phase_deadline=None):
        control()
        left=owner['allocation_monotonic_ns']/1e9+policy['lease_seconds']-220-time.monotonic()
        if left<required_seconds+600:raise SafetyStop('ADMIN_AND_FULL_A_WINDOW_NO_HEADROOM')
        if phase_deadline is not None:
            left=min(left,phase_deadline-time.monotonic())
            if left<=0:raise TimeoutError('UNCHANGED_ADMIN_RPC_PHASE_DEADLINE')
        upload_identity(min(8,left))
        control()
        if phase_deadline is not None and time.monotonic()>=phase_deadline:raise TimeoutError('UNCHANGED_ADMIN_RPC_PHASE_DEADLINE')
    t.control=admin_control
    t.upload(BASE/'admin_runner.py','admin_runner.py','admin_runner_upload',12)
    job=t.run_remote_job(['/usr/local/bin/python3','-B',guest+'/admin_runner.py',guest,str(owner['instance_id']),sha(BASE/'admin_payload.zip')],sha(BASE/'admin_runner.py'),timeout_seconds=140)
    t.evidence_code_sha256=sha(BASE/'admin_payload.zip')
    t.recover_final()
    from job_proof import closed_archive
    closed=closed_archive(io,a,t.evidence_code_sha256)
    save(out/'admin_closed_originals.json',dict(owner=a,folder=str(io),code_sha256=t.evidence_code_sha256,proof=closed))
    # The already verified archive contains these exact originals; a second SSH
    # fetch would add an unnecessary administrative failure after safe recovery.
    job_raw={n:(io/'recovered'/n).read_bytes() for n in ('job/payload.stdout','job/payload.stderr','job/identity.json','job/terminal.json','job_spec.json')}
    from job_proof import completed_job
    completed_job(job_raw,a,job_observation=job,expected_spec_sha256=t.job_spec_sha256)
    save(out/'admin_job_finality.json',dict(owner=a,job_observation=job,job_spec_sha256=t.job_spec_sha256,raw_sha256={n:hashlib.sha256(v).hexdigest() for n,v in job_raw.items()}))
    folder=out/'admin_job_raw';folder.mkdir(exist_ok=False)
    for n,v in job_raw.items():
        target=folder/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(v)
    raw=job_raw['job/payload.stdout']
    if job['state']!='EXITED_SUCCESS':raise ValueError('ADMIN_WRAPPER_FAILED_RAW_RECOVERED_NOT_PASS')
    result=json.loads(raw)
    if result.get('instance_id')!=owner['instance_id'] or result.get('source_zip_sha256')!=sha(BASE/'admin_payload.zip'):
        raise ValueError('ADMIN_ACTUAL_RESULT_BINDING')
    for name,field in [('stdout.log','stdout_b64'),('stderr.log','stderr_b64'),('junit.xml','junit_b64')]:
        if result.get(field) is None:raise ValueError('ADMIN_RAW_MISSING:'+name)
        (out/name).write_bytes(base64.b64decode(result[field],validate=True))
    for name,field in [('v11_first10.xml','v11_first10_junit_b64'),('v11_first10.stdout','v11_first10_stdout_b64'),('v11_first10.stderr','v11_first10_stderr_b64')]:
        if result.get(field) is None:raise ValueError('V11_FIRST10_RAW_MISSING')
        (out/name).write_bytes(base64.b64decode(result[field],validate=True))
    save(out/'admin_result.json',result)
    cases=ET.parse(out/'junit.xml').getroot().findall('.//testcase')
    failed=sum(c.find('failure') is not None for c in cases)
    errors=sum(c.find('error') is not None for c in cases)
    skipped=sum(c.find('skipped') is not None for c in cases)
    save(out/'admin_verified.json',dict(instance_id=owner['instance_id'],tests=len(cases),failed=failed,errors=errors,skipped=skipped,
        raw_files={name:sha(out/name) for name in ('stdout.log','stderr.log','junit.xml','admin_result.json')},
        role='RECOVERED_ADMIN_RAW_ONLY_NOT_B95',passed=result['returncode']==0 and bool(cases) and failed+errors+skipped==0))
    if result.get('v11_first10_passed') is not True or result['returncode'] or not cases or failed+errors+skipped:raise ValueError('ADMIN_MOCK_GATE_FAILED_ANALYZE_BEFORE_ADMIN_REVALIDATION')
    verify_ssh_disconnect_probe(out,owner,t,ssh,watch)


def verify_ssh_disconnect_probe(out,owner,t,ssh,watch):
    save(out/'ssh_disconnect_probe_started.json',dict(instance_id=owner['instance_id'],observed_utc=utc()))
    original_guest=t.guest;original_out=t.out;original_auth=t.auth
    guest=original_guest+'_disconnect_probe';io=out/'ssh_disconnect_probe';io.mkdir(exist_ok=False)
    mkdir="import pathlib,sys\nids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'CONTAINER_ID=')]\nif ids!=[sys.argv[2]]:raise ValueError('PREPARATION_ACTUAL_INSTANCE_MISMATCH')\np=pathlib.Path(sys.argv[1])\nif p.parent!=pathlib.Path('/workspace') or p.resolve()!=p:raise ValueError('PREPARATION_ROOT_SCOPE')\nif p.exists() and (not p.is_dir() or p.is_symlink() or any(p.iterdir())):raise ValueError('PREPARATION_EXISTING_CONTENT')\np.mkdir(exist_ok=True)"
    command_recheck(io,ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',mkdir,guest,str(owner['instance_id'])])],'mkdir',12,watch=watch)
    t.guest=guest;t.out=io;t.auth=dict(original_auth,run_id=owner['run_id']+'_disconnect_probe');t.evidence_job_role='ADMIN_PROBE'
    try:
        t.upload(BASE/'transport/guest_probe_writer.py','guest_probe_writer.py','probe_writer_upload',12)
        value=t.run_remote_job(['/usr/local/bin/python3','-B',guest+'/guest_probe_writer.py',guest],sha(BASE/'transport/guest_probe_writer.py'),timeout_seconds=12,disconnect_probe=True)
        t.recover_final()
        from job_proof import closed_archive
        closed=closed_archive(io,t.auth,t.evidence_code_sha256)
        save(out/'probe_closed_originals.json',dict(owner=t.auth,folder=str(io),code_sha256=t.evidence_code_sha256,proof=closed))
        if value['state']!='EXITED_SUCCESS':raise ValueError('REAL_SSH_DISCONNECT_PROBE_FAILED')
        save(out/'ssh_disconnect_verified.json',dict(instance_id=owner['instance_id'],job_observation=value,intentional_client_termination=True,actual_status_reconnected=True,scope='ADMIN_PROBE_ONLY_NOT_A320'))
    finally:t.guest=original_guest;t.out=original_out;t.auth=original_auth


def transport_binding(policy,kind,owner,out,B_close):
    spec=read(BASE/'transport/package_bindings.json')[kind]
    binding=dict(schema='PROJECT_VAST_DELEGATED_INSTANCE_BINDING_V1',role='IMPLEMENTER_BINDING_OF_USER_DELEGATION_NOT_HUMAN_SIGNATURE',
        explicit_user_approval=True,exclusive=True,allocation_mode='ADOPT_RUNNING',scope='OFFLINE_ONLY',
        campaign_total_cap_usd='2.00',authorization_raw_sha256=policy['authorization_raw_sha256'],
        policy_sha256=sha(BASE/'policy.json'),operational_seal_sha256=sha(BASE/'operational_seal.json'),
        approval_reference=policy['authorization_reference'],owner_record=str(out/'owner.json'),owner_record_sha256=sha(out/'owner.json'),
        instance_id=owner['instance_id'],machine_id=owner['machine_id'],country=owner['country'],run_id=owner['run_id'],
        api_ssh_host=owner['api_ssh_host'],api_ssh_port=owner['api_ssh_port'],ssh_host=owner['public_ipaddr'],ssh_port=owner['direct_ssh_port'],
        transport_ssh_host=owner['public_ipaddr'],transport_ssh_port=owner['direct_ssh_port'],
        known_hosts_file=str(out/'known_hosts'),known_hosts_sha256=sha(out/'known_hosts'),
        lease_watchdog_pid=read(out/'watchdog_ready.json')['pid'],
        observed_rate_usd=owner['observed_rate_usd'],package_kind=kind,code_sha256=spec['code_sha256'],protocol_sha256=spec['protocol_sha256'],
        zip_sha256=spec['zip_sha256'],inventory_sha256=spec['inventory_sha256'],expected_tests=spec['expected_tests'],physics_calls=0,gpu_calls=0,
        allocation_seconds=600,compute_seconds=120,stop_confirmation_seconds=180,hourly_cap_usd='0.25',
        approved_utc=utc(),expires_utc=(datetime.now(timezone.utc)+timedelta(seconds=600)).isoformat(),
        prior_closed_window_sha256=sha(ROOT/'docs/active/adaptive_experience_tablet_v0/remote_20261009_attempt3/closure.json'))
    binding.update(paid_approval_path=policy['_paid_approval_path'],paid_approval_sha256=policy['_paid_approval_sha256'])
    if kind=='A':binding.update(B_stage_closeout=str(B_close),B_stage_closeout_sha256=sha(B_close))
    return binding


def collect_startup(out,owner,key,watch=None):
    if (out/'startup_verified.json').exists():return verify_startup(out,owner)
    save(out/'startup_recovery_attempted.json',dict(instance_id=owner['instance_id'],observed_utc=utc()))
    known=out/'known_hosts'
    ssh=['ssh','-T','-i',str(key),'-p',str(owner['direct_ssh_port']),'-o','BatchMode=yes','-o','ConnectTimeout=5',
        '-o','UserKnownHostsFile='+str(known),'-o','StrictHostKeyChecking='+('yes' if known.exists() else 'accept-new'),
        'root@'+owner['public_ipaddr']]
    script='import sys,pathlib,json,base64,hashlib\nexpected=sys.argv[1]\nids=[p.split(b"=",1)[1].decode() for p in pathlib.Path("/proc/1/environ").read_bytes().split(b"\\0") if p.startswith(b"CONTAINER_ID=")]\nif ids!=[expected]:raise ValueError("STARTUP_ACTUAL_INSTANCE_MISMATCH")\ndata={};files={}\nfor name in ["runtime_setup.log","runtime_ready"]:\n p=pathlib.Path("/workspace")/name\n if p.exists():\n  if not p.is_file() or p.is_symlink() or p.stat().st_size>8388608:raise ValueError("STARTUP_RAW_FILE_SCOPE")\n  raw=p.read_bytes(); data[name]=base64.b64encode(raw).decode(); files[name]=hashlib.sha256(raw).hexdigest()\nprint(json.dumps({"instance_id":int(ids[0]),"data":data,"files":files,"observed_missing":[n for n in ["runtime_setup.log","runtime_ready"] if n not in files]}))'
    raw=command_recheck(out/'startup_io',ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',script,str(owner['instance_id'])])],
        'recovery',15,watch=watch)
    result=json.loads(raw)
    if result.get('instance_id')!=owner['instance_id'] or set(result.get('files',{}))!=set(result.get('data',{})):
        raise ValueError('STARTUP_ACTUAL_RAW_BINDING')
    folder=out/'startup_raw';folder.mkdir(exist_ok=False)
    for name,data in result['data'].items():
        if name not in ('runtime_setup.log','runtime_ready'):raise ValueError('STARTUP_RECOVERY_PATH')
        (folder/name).write_bytes(base64.b64decode(data,validate=True))
    save(out/'startup_result.json',result)
    save(out/'startup_verified.json',dict(instance_id=owner['instance_id'],files=result['files'],result_sha256=sha(out/'startup_result.json')))
    return verify_startup(out,owner)


def start_owned_once(provider,owner):
    raw=provider.call('start','instance',owner['instance_id'],json_result=False,timeout=15)
    if raw.strip()==('starting instance %d.'%owner['instance_id']).encode():return
    if b'Required resources are currently unavailable' in raw:raise AdministrativeUnavailable('PROVIDER_RESOURCE_UNAVAILABLE_START_QUEUED')
    raise SafetyStop('START_API_ACCEPTANCE_UNCONFIRMED')


def scoped_policy(policy,kind,resume):
    value=dict(policy)
    if kind not in ('A','B'):raise ValueError('EXACT_PACKAGE_KIND_REQUIRED')
    if policy.get('schema')=='V12_A_ONLY_IMPLEMENTATION_NEW_PAID_WINDOW_PENDING' and (kind!='A' or resume is not None):raise SafetyStop('V12_FRESH_A_ONLY_NOT_OLD_EXTENSION')
    value['lease_seconds']=1800 if policy.get('schema')=='V12_A_ONLY_IMPLEMENTATION_NEW_PAID_WINDOW_PENDING' else 1200
    if resume is not None:
        expected=Path(policy['private_root'])/'project_v5_2_b_20261009_145216'
        if kind!='B' or Path(resume).resolve()!=expected.resolve():raise SafetyStop('EXACT_EXTENSION_TARGET_PATH_REQUIRED')
        value['lease_seconds']=3600
    return value


def stage(policy,kind,provider,ledger,key,B_close=None,resume=None):
    from execution_authority import begin_stage
    if kind!='A' or resume is not None:raise SafetyStop('V12_A_ONLY_FRESH_SINGLE_STAGE')
    frozen=read(BASE/'policy.json')
    if {k:v for k,v in policy.items() if k not in ('_paid_approval_path','_paid_approval_sha256')}!=frozen:raise SafetyStop('DIRECT_STAGE_SEALED_POLICY_DRIFT')
    source_preflight(frozen)
    begin_stage(policy['_paid_approval_path'],policy['_paid_approval_sha256'])
    if (Path(provider.cli).resolve()!=Path('C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe').resolve()
        or Path(ledger.path).resolve()!=Path(frozen['ledger_path']).resolve() or Path(key).resolve()!=Path('C:/Users/zun24/.ssh/vast_ai').resolve()
        or B_close is None or sha(B_close)!=frozen['B_stage_closeout_sha256']):raise SafetyStop('DIRECT_STAGE_ADMIN_BINDING_DRIFT')
    balance=ledger.balances(ledger.read()[0])
    if balance['active'] or balance['cap']!=money('2') or balance['remaining']<money('.20'):raise SafetyStop('DIRECT_STAGE_BUDGET_BOUNDARY')
    policy=scoped_policy(policy,kind,resume)
    if resume is not None:
        from preflight import require_time_extension
        require_time_extension(read(BASE/'finite_policy.json'))
    finite=read(V5/'finite_policy.json');finite['lease_seconds']=policy['lease_seconds']
    if policy['lease_seconds']==1800:finite.update(v12_new_window=True,paid_approval_path=policy['_paid_approval_path'],paid_approval_sha256=policy['_paid_approval_sha256'])
    root=Path(policy['private_root'])
    run_id='project_v12_'+kind.lower()+'_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    out=root/run_id;out.mkdir(exist_ok=False)
    before=provider.instances();volumes=provider.volumes()
    if resume is None:
        offer,cost=choose(provider,policy)
        token=run_id
        ledger.append(dict(action='RESERVE',token=token,amount=cost['total'],observed_utc=utc(),offer_id=offer['id'],machine_id=offer['machine_id'],policy_sha256=sha(BASE/'policy.json')))
        label='project-budget-v1-'+run_id
        country=offer['geolocation'].rsplit(',',1)[-1].strip()
        first_ns=time.monotonic_ns();first_utc=utc()
    else:
        old=Path(resume)
        if old.resolve()!=Path('C:\\Users\\zun24\\.codex\\evidence\\project_vast_budget_cleanup_v1_20261009\\project_v5_2_b_20261009_145216').resolve() or sha(old/'stage_closeout.json')!='457412c953caa6c90bff46fa13276075c0ddc56350745726d7c91ed4a7f3329c':raise ValueError('ORIGINAL_STAGE_FIXED_PATH_AND_CLOSEOUT_PIN')
        for name,wanted in read(old/'stage_closeout.json')['raw_files'].items():
            if sha(old/name)!=wanted:raise ValueError('ORIGINAL_PAID_RAW_DRIFT:'+name)
        prior=read(old/'owner.json')
        if prior['instance_id']!=55040957 or prior['machine_id']!=53859:raise ValueError('EXACT_RESUME_OWNER_REQUIRED')
        prior_seal=read(BASE.parent/'revision_v5_2/operational_seal.json')
        for name,wanted in prior_seal['files'].items():
            if sha(BASE.parent/'revision_v5_2'/name)!=wanted:raise ValueError('PRIOR_SEAL_DRIFT')
        old_pid=read(old/'watchdog_ready.json')['pid']
        if psutil.pid_exists(old_pid):raise ValueError('PRIOR_WATCHDOG_STILL_ACTIVE')
        offer=read(old/'selected_offer.json');cost=read(old/'reservation.json')
        token=prior['reservation_token'];label=prior['label'];country=prior['country']
        first_ns=prior['allocation_monotonic_ns'];first_utc=prior['allocation_start_utc']
        balance=ledger.balances(ledger.read()[0])
        if set(balance['active'])!={token} or balance['remaining']<0 or str(balance['active'][token])!=cost['total']:raise ValueError('INHERITED_RESERVATION_REQUIRED')
        current=identity(provider.call('show','instance',prior['instance_id']),prior)
        if current.get('actual_status') not in ('exited','stopped') or current.get('intended_status')!='stopped':raise ValueError('RESUME_REQUIRES_ACTUAL_STOP')
        if money(current['dph_total'])>money(prior['observed_rate_usd']):raise ValueError('RESUME_PRICE_DRIFT')
        if first_ns/1e9+policy['lease_seconds']-220-time.monotonic()<900:raise ValueError('ORIGINAL_LEASE_HEADROOM_INSUFFICIENT')
        extension_token=token+'_time_extension_v7'
        extension_cost=(money(offer['dph_total'])+money(offer['storage_cost'])*8/720)*2400/3600
        ledger.append(dict(action='RESERVE',token=extension_token,amount=str(extension_cost),instance_id=prior['instance_id'],approval_raw_sha256=policy['cap_time_amendment_sha256'],time_extension_approval_raw_sha256=policy['time_extension_sha256'],time_extension_approval_raw_path=str(BASE/policy['time_extension_path']),observed_utc=utc()))
        save(out/'extension_reservation.json',dict(token=extension_token,amount=str(extension_cost),original_allocation_ns=first_ns,maximum_seconds=3600,time_extension_approval_raw_sha256=policy['time_extension_sha256'],time_extension_approval_raw_path=str(BASE/policy['time_extension_path'])))
        save(out/'prior_failure_binding.json',dict(path=str(old),closeout_sha256=sha(old/'stage_closeout.json'),original_allocation_ns=first_ns))
        shutil.copyfile(old/'known_hosts',out/'known_hosts')
    save(out/'selected_offer.json',offer);save(out/'reservation.json',cost)
    lease=dict(cli=provider.cli,label=label,machine_id=offer['machine_id'],country=country,run_id=run_id,
        allocation_monotonic_ns=first_ns,allocation_start_utc=first_utc,maximum_seconds=policy['lease_seconds']-220,
        controller_pid=os.getpid(),controller_create_time=psutil.Process().create_time(),baseline_volumes=volumes,
        request_path=str(BASE/'authorization_request.txt'),authorization_raw_sha256=policy['authorization_raw_sha256'],
        finite_policy=finite,ledger_path=policy['ledger_path'],reservation_token=token)
    save(out/'watchdog_lease.json',lease)
    watch=subprocess.Popen([sys.executable,'-B',str(V5/'watchdog.py'),'--lease',str(out/'watchdog_lease.json')],cwd=BASE,
        stdout=(out/'watchdog.stdout').open('xb'),stderr=(out/'watchdog.stderr').open('xb'),
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
    owner=None;transport=None;passed=False;failure=None;stop=None;destroy=None;recovery=None;settled=False
    create_attempted=False
    try:
        until=time.monotonic()+10
        while not (out/'watchdog_ready.json').exists():
            if watch.poll() is not None or time.monotonic()>=until:raise ValueError('PRE_CREATE_WATCHDOG_NOT_READY')
            time.sleep(.1)
        if read(out/'watchdog_ready.json')['lease_sha256']!=sha(out/'watchdog_lease.json'):raise ValueError('WATCHDOG_LEASE_PIN')
        if resume is None:
            save(out/'create_attempt.json',dict(offer_id=offer['id'],label=label,observed_utc=utc()))
            create_attempted=True
            setup='mkdir -p /workspace && touch /root/.no_auto_tmux && python3 -m pip install --disable-pip-version-check --no-cache-dir pytest==8.3.5 psutil==6.1.1 mpmath==1.3.0 cryptography==44.0.1 > /workspace/runtime_setup.log 2>&1 && touch /workspace/runtime_ready'
            result=provider.call('create','instance',str(offer['id']),'--image','python:3.12-slim-bookworm',
                '--disk',str(policy['disk_gb']),'--ssh','--direct','--label',label,'--onstart-cmd',setup,'--cancel-unavail',timeout=30)
            if result.get('success') is not True or type(result.get('new_contract')) is not int:
                raise ValueError('CREATE_RESULT_UNCONFIRMED_NO_RENT_RETRY')
        else:
            owner=dict(prior,run_id=run_id,local_evidence_destination=str(out),start_request_may_be_queued=True,stop_attempt_journal=str(out/'stop_attempt_journal'),extension_reservations=[dict(token=extension_token,amount=str(extension_cost),time_extension_approval_raw_sha256=policy['time_extension_sha256'],time_extension_approval_raw_path=str(BASE/policy['time_extension_path']))])
            save_atomic(out/'created_owner.json',owner)
            if watch.poll() is not None:raise SafetyStop('LEASE_WATCHDOG_LOST_BEFORE_RESTART')
            save(out/'restart_attempt.json',dict(instance_id=prior['instance_id'],original_allocation_ns=first_ns,observed_utc=utc()))
            start_owned_once(provider,prior)
            result=dict(new_contract=prior['instance_id'])
        owner=dict(v12_owned_job=True,instance_id=result['new_contract'],machine_id=offer['machine_id'],country=country,label=label,run_id=run_id,
            reservation_token=token,authorization_raw_sha256=policy['authorization_raw_sha256'],offer_id=offer['id'],
            allocation_start_utc=first_utc,allocation_monotonic_ns=first_ns,maximum_cost_usd=cost['total'],observed_rate_usd=str(offer['dph_total']),
            test_scope='ADMIN_MOCKS_THEN_B95' if kind=='B' else 'A320_THEN_ORIGINAL_SEARCH_BENCHMARK',local_evidence_destination=str(out))
        if resume is not None:owner=dict(prior,**owner,start_request_may_be_queued=True,stop_attempt_journal=str(out/'stop_attempt_journal'))
        if resume is not None:owner['extension_reservations']=[dict(token=extension_token,amount=str(extension_cost),time_extension_approval_raw_sha256=policy['time_extension_sha256'],time_extension_approval_raw_path=str(BASE/policy['time_extension_path']))]
        if resume is None:save_atomic(out/'created_owner.json',owner)
        until=(first_ns/1e9+policy['initialization_seconds']) if resume is None else min(time.monotonic()+60,first_ns/1e9+policy['lease_seconds']-220-840)
        while time.monotonic()<until:
            current=identity(provider.call('show','instance',owner['instance_id']),owner)
            if money(current.get('dph_total'))>money(offer['dph_total']):raise ValueError('PRICE_EXCEEDS_RESERVED_QUOTE')
            mapping=current.get('ports',{}).get('22/tcp',[]) if isinstance(current.get('ports'),dict) else []
            if current.get('actual_status')=='running' and current.get('intended_status')=='running' and mapping and current.get('ssh_host') and current.get('ssh_port'):
                ports={row.get('HostPort') for row in mapping}
                if len(ports)!=1 or not next(iter(ports)).isdigit():raise ValueError('DIRECT_PORT_MAPPING_AMBIGUOUS')
                owner.update(api_ssh_host=current['ssh_host'],api_ssh_port=current['ssh_port'],public_ipaddr=current['public_ipaddr'],
                    direct_ssh_port=int(next(iter(ports))))
                save_atomic(out/'owner.json',owner)
                break
            if watch.poll() is not None:raise ValueError('WATCHDOG_LOST_DURING_SETUP')
            time.sleep(3)
        else:raise TimeoutError('BOUNDED_CONTAINER_READINESS')
        known=out/'known_hosts'
        # New host key accepted once into this private lease file, then all guest
        # transport uses strict checking of those exact bytes. TOFU, not provider attestation.
        ssh=['ssh','-T','-i',str(key),'-p',str(owner['direct_ssh_port']),'-o','BatchMode=yes','-o','ConnectTimeout=5',
            '-o','UserKnownHostsFile='+str(known),'-o','StrictHostKeyChecking='+('yes' if resume else 'accept-new'),'root@'+owner['public_ipaddr']]
        setup_probe='import pathlib,sys,importlib.metadata as m,json,time\nexpected=sys.argv[1]\nids=[p.split(b"=",1)[1].decode() for p in pathlib.Path("/proc/1/environ").read_bytes().split(bytes([0])) if p.startswith(b"CONTAINER_ID=")]\nif ids!=[expected]:raise RuntimeError("SAFETY_INSTANCE_ID_MISMATCH")\nuntil=time.monotonic()+float(sys.argv[2])\nwhile not pathlib.Path("/workspace/runtime_ready").exists() and time.monotonic()<until:time.sleep(.5)\nif not pathlib.Path("/workspace/runtime_ready").exists():print(json.dumps(dict(status="WAITING",actual_container_id=expected)))\nelse:\n if sys.version_info[:2]!=(3,12):raise RuntimeError("ADMIN_RUNTIME_VERSION_NOT_PINNED")\n versions={n:m.version(n) for n in ["pytest","psutil","mpmath","cryptography"]}\n if versions!={"pytest":"8.3.5","psutil":"6.1.1","mpmath":"1.3.0","cryptography":"44.0.1"}:raise RuntimeError("ADMIN_RUNTIME_DEPENDENCIES_NOT_PINNED")\n print(json.dumps(dict(status="READY",python=sys.version,versions=versions,actual_container_id=expected)))\n'
        left=until-time.monotonic()
        if left<10:raise TimeoutError('RUNTIME_PREPARATION_RESERVE_EXHAUSTED')
        probe_seconds=min(100,left)
        def readiness_control():
            if watch.poll() is not None:raise SafetyStop('LEASE_WATCHDOG_LOST')
        def readiness_identity():
            left=until-time.monotonic()
            if left<2:raise AdministrativeUnavailable('ABSOLUTE_PREPARATION_DEADLINE')
            current=identity(provider.call('show','instance',owner['instance_id'],timeout=min(8,left)),owner)
            mapping=current.get('ports',{}).get('22/tcp',[])
            ports={row.get('HostPort') for row in mapping}
            if (current.get('actual_status')!='running' or current.get('intended_status')!='running'
                or current.get('public_ipaddr')!=owner['public_ipaddr'] or ports!={str(owner['direct_ssh_port'])}):
                raise SafetyStop('INSTANCE_IDENTITY_OR_DIRECT_MAPPING_CHANGED')
            if money(current.get('dph_total'))>money(owner['observed_rate_usd']):raise SafetyStop('PRICE_EXCEEDS_RESERVED_QUOTE')
        def readiness_operation(folder,left):
            readiness_identity()
            left=min(left,until-time.monotonic())
            if left<2:raise AdministrativeUnavailable('ABSOLUTE_PREPARATION_DEADLINE')
            raw=command(folder,ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',setup_probe,str(owner['instance_id']),str(max(0,left-5))])],
                'runtime_probe',left,watch=watch)
            return json.loads(raw)
        result=ready_on_same_instance(owner,until,out/'bootstrap_io',readiness_operation,readiness_control)
        save(out/'runtime.json',result)
        collect_startup(out,owner,key,watch)
        strict_ssh=ssh.copy();strict_ssh=[('StrictHostKeyChecking=yes' if x=='StrictHostKeyChecking=accept-new' else x) for x in strict_ssh]
        scp=['scp','-O','-i',str(key),'-P',str(owner['direct_ssh_port']),'-o','BatchMode=yes','-o','ConnectTimeout=5',
            '-o','UserKnownHostsFile='+str(known),'-o','StrictHostKeyChecking=yes']
        if kind in ('A','B'):remote_admin(out,strict_ssh,scp,owner,watch,policy)
        if watch.poll() is not None:raise ValueError('LEASE_WATCHDOG_LOST_BEFORE_GUEST_GATE')
        save(out/'binding.json',transport_binding(policy,kind,owner,out,B_close))
        sys.path.insert(0,str(BASE/'transport'))
        spec=importlib.util.spec_from_file_location('delegated_transport',BASE/'transport/controller.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.configure(kind)
        binding=read(out/'binding.json');checks=module.local_preflight(binding)
        transport_out=out/'transport';transport_out.mkdir(exist_ok=False)
        save(transport_out/'source_preflight.json',dict(checks=checks));save(transport_out/'human_authorization.json',binding)
        transport=module.Transport(binding,provider.cli,key,transport_out)
        if first_ns/1e9+policy['lease_seconds']-220-time.monotonic()<600:raise AdministrativeUnavailable('FULL_UNCHANGED_GUEST_WINDOW_NOT_AVAILABLE')
        passed=transport.execute()==0
        if not passed:raise ValueError('OFFLINE_GATE_FAILED_PRESERVE_CLASSIFY_NO_PHYSICS_RETRY')
    except BaseException as error:
        failure=repr(error);save_atomic(out/'failure.json',dict(error=failure,observed_utc=utc(),automatic_physics_retry=False,administrative_revalidation_authorized=True,
            recovery_window_start_monotonic_ns=time.monotonic_ns()))
    finally:
        if owner is None and create_attempted:
            try:
                matches=[r for r in provider.instances() if r.get('label')==label and r.get('machine_id')==offer['machine_id']]
                if len(matches)==1:
                    owner=dict(instance_id=matches[0]['id'],machine_id=offer['machine_id'],country=country,label=label,run_id=run_id,
                        reservation_token=token,authorization_raw_sha256=policy['authorization_raw_sha256'])
                    save(out/'uncertain_create_recovered_owner.json',owner)
                elif matches:raise ValueError('AMBIGUOUS_CREATE_OUTCOME')
            except Exception as error:save(out/'create_resolution_failure.json',dict(error=repr(error)))
        if owner:
            try:
                if not (out/'startup_verified.json').exists() and not (out/'startup_recovery_attempted.json').exists():
                    try:collect_startup(out,owner,key)
                    except Exception as error:save(out/'startup_recovery_failure.json',dict(error=repr(error)))
                stop,recovery,destroy=close_owned(provider,owner,out,volumes,finite)
                save(out/'outer_stop.json',stop);save(out/'outer_recovery.json',recovery);save(out/'outer_destroy.json',destroy)
                if destroy['status']=='DESTROY_CONFIRMED':
                    pages=provider.charges();total,count=charge_total(pages)
                    age=Decimal(str((time.monotonic_ns()-first_ns)/1e9))
                    observed=max(Decimal(cost['total']),money(offer['dph_total'])*age/3600+money(cost['upload_reserve'])+money(cost['download_reserve']))
                    save(out/'cost_closeout.json',dict(lease_age_seconds=str(age),conservative_cost_bound=str(observed),
                        provider_account_day_display_total=str(total),provider_entries=count,provider_cost_is_final_invoice=False,
                        retained_full_reservation=cost['total'],budget_reset=False,
                        billing_raw_files={str(p):sha(p) for p in provider.out.glob('*') if p.is_file()}))
                    ledger.append(dict(action='SETTLE',token=token,observed_cost_bound=str(observed),destroy_confirmed=True,observed_utc=utc()))
                    if resume is not None:ledger.append(dict(action='SETTLE',token=extension_token,observed_cost_bound=str(extension_cost),destroy_confirmed=True,observed_utc=utc()))
                    ledger.append(dict(action='OBSERVE',historical_bound=str(total+Decimal('.002')*count+money(policy['historical_uncertainty_usd'])),
                        cost_closeout_sha256=sha(out/'cost_closeout.json'),observed_utc=utc()))
                    settled=True
            except BaseException as error:
                failure=(failure+'; ' if failure else '')+'CLEANUP:'+repr(error)
                save(out/'preservation_or_cleanup_exception.json',dict(error=repr(error),user_decision_required=True))
        # watchdog remains armed if cleanup is unresolved; keep reservation intact.
        if destroy and destroy.get('status')=='DESTROY_CONFIRMED':save(out/'cleanup_done.json',dict(status='OWNED_INSTANCE_GONE',observed_utc=utc()))
        if (out/'cleanup_done.json').exists():
            try:watch.wait(timeout=5)
            except subprocess.TimeoutExpired:watch.terminate()
        raw_files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and not p.name.startswith('stage_closeout')}
        close=dict(package_kind=kind,passed=passed and settled and destroy is not None and destroy.get('status')=='DESTROY_CONFIRMED',
            execution_passed=passed,failure=failure,owner=owner,recovery=recovery,stop=stop,destroy=destroy,
            budget_settled=settled,authorization_raw_sha256=policy['authorization_raw_sha256'],raw_files=raw_files,
            observed_utc=utc(),local_dynamic_tests=0,new_physics_calls=0 if passed else None,gpu_calls=0 if passed else None,direct_controller_physics_commands=0)
        save(out/'stage_closeout.json',close)
    return out/'stage_closeout.json'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--approval',required=True,type=Path)
    parser.add_argument('--approval-sha256',required=True)
    args=parser.parse_args()
    from execution_authority import require_paid_approval
    approved=require_paid_approval(args.approval,args.approval_sha256)  # BEFORE every Provider call/reserve/rental
    policy=read(BASE/'policy.json');source_preflight(policy)
    policy.update(_paid_approval_path=str(args.approval.resolve()),_paid_approval_sha256=args.approval_sha256)
    cli=Path('C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe');key=Path('C:/Users/zun24/.ssh/vast_ai')
    admission=Path(policy['private_root'])/('v12_admission_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    finite=read(BASE/'finite_policy.json');finite.update(lease_seconds=1800,v12_new_window=True,paid_approval_path=policy['_paid_approval_path'],paid_approval_sha256=args.approval_sha256)
    before_any_rental(cli,key,finite,admission)
    from execution_authority import claim_paid_approval
    claim_paid_approval(args.approval,args.approval_sha256)
    provider=Provider(cli,admission/'api');ledger=Ledger(policy['ledger_path'])
    if provider.instances() or provider.volumes():raise SafetyStop('V12_EXPECTED_EMPTY_BASELINE_NO_OTHER_RESOURCE_ACTIONS')
    display,count=charge_total(provider.charges())
    balance=ledger.append(dict(action='OBSERVE',historical_bound=str(display+money('.002')*count+money('.020')),reason='V12_PRELEASE_FRESH_CHARGES',observed_utc=utc()))
    if balance['active'] or balance['cap']!=money('2') or balance['remaining']<money('.20'):raise SafetyStop('V12_FRESH_BUDGET_BOUNDARY')
    B=Path(policy['B_stage_closeout'])
    if sha(B)!=policy['B_stage_closeout_sha256']:raise SafetyStop('B_SUCCESS_HISTORY_DRIFT')
    close_path=stage(policy,'A',provider,ledger,key,B_close=B)
    close=read(close_path)
    print(json.dumps(dict(stage_closeout=str(close_path),passed=close['passed'],failure=close['failure'],budget_settled=close['budget_settled'])))
    return 0 if close['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
