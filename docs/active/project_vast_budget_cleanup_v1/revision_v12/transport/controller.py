"""A-resume-derived administrative transport; requires separate NEW human authorization.

No network at import, no project imports, no local tests/calculations.
Execute only after static preparation AND an explicit new-window approval.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
import zipfile
import psutil
from state_contract import inspect, decode
from supervisor import confirm_stop

def guardian_alive(pid):
    try:
        process=psutil.Process(pid)
        return process.is_running() and process.status()!=psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess,psutil.AccessDenied):return False

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FIRST_CODE = '18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09'
FIRST_PROTO = 'f03bc97a79e1a22ece4964270032d8829f7a208e961c09806c8f7bc10351013c'
SCOPE_HASH = 'da96a821a7aa8f6f9e2537959babf68420a0d7b8ac008b2c9751cee331ff8484'
BUDGET_PROTOCOL_SHA = hashlib.sha256((HERE.parent/'policy.json').read_bytes()).hexdigest()
ORIGINAL_SCOPE = ROOT / 'docs/active/bounded_admin_recovery_v0/closure_v1/scope_protocol.json'
KIND = CODE = PROTO = ZIP_HASH = SOURCE = INVENTORY = INVENTORY_HASH = EXPECTED = SPEC = None
PRIOR_POLICY_FEE_BOUND = Decimal('0')
PRIOR_ACTUAL_POLICY_FEE = None
GUARD = ROOT / 'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
PRIOR = ROOT / 'docs/active/adaptive_experience_tablet_v0/remote_20261009_attempt3/closure.json'
VENV = '/usr/local/bin/python3'
TARGET_PROTOCOL_SHA = BUDGET_PROTOCOL_SHA
TARGET_PROTOCOL = HERE.parent / 'policy.json'
PREVIOUS_B = ROOT / 'docs/active/bounded_admin_recovery_v0/budget_supplement_v1/remote_result_b_95_20261009_075708/closure.json'
FAILED_GATE = ROOT / 'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/run_approved_20261009_0130/closure.json'


def configure(kind):
    global KIND, CODE, PROTO, ZIP_HASH, SOURCE, INVENTORY, INVENTORY_HASH, EXPECTED, SPEC
    KIND = kind; SPEC = load(HERE / 'package_bindings.json')[kind]
    CODE, PROTO, ZIP_HASH = SPEC['code_sha256'], SPEC['protocol_sha256'], SPEC['zip_sha256']
    SOURCE, INVENTORY = ROOT / SPEC['archive'], ROOT / SPEC['inventory']
    INVENTORY_HASH, EXPECTED = SPEC['inventory_sha256'], SPEC['expected_tests']


def verify_local_package():
    if sha(INVENTORY.read_bytes()) != INVENTORY_HASH or sha(SOURCE.read_bytes()) != ZIP_HASH:
        raise ValueError('EXACT_NEW_PACKAGE_EXTERNAL_PINS')
    inventory = load(INVENTORY)
    if inventory['zip_sha256'] != ZIP_HASH or inventory['entries'] != SPEC['entries']:
        raise ValueError('INVENTORY_PACKAGE_SCOPE')
    if KIND == 'A':
        if sha((ROOT/SPEC['case_inventory']).read_bytes()) != SPEC['case_inventory_sha256']:
            raise ValueError('ORIGINAL_320_CASE_INVENTORY_PIN')
        code = load(ROOT / 'experiments/adaptive_experience_tablet_v0/code_seal.json')
        required = dict(code['files'], **{'experiments/adaptive_experience_tablet_v0/code_seal.json': FIRST_CODE,
            'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json':
            'ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60'})
        if len(code['files']) != 812 or inventory['files'] != required or len(required) != 814:
            raise ValueError('PRESERVE_813_PLUS_EXACT_EXISTING_SEAL')
    else:
        seal = load(ROOT / SPEC['local_code_seal'])
        required = dict(seal['files'], **{'admin_policy/source_seal.json': CODE})
        if inventory['files'] != required or len(required) != 10 or seal['expected_tests'] != 95:
            raise ValueError('EXACT_SEPARATE_POLICY_PACKAGE')
        original = load(ROOT / 'experiments/bounded_admin_recovery_v0/code_seal_v2.json')['files']
        for name in SPEC['original_policy_files']:
            if required[name] != original[name]: raise ValueError('ORIGINAL_95_SOURCE_DRIFT')
    with zipfile.ZipFile(SOURCE) as z:
        names = z.namelist()
        if (len(names) != SPEC['entries'] or len(names) != len(set(names))
                or len(names) != len(set(n.casefold() for n in names)) or set(names) != set(required)
                or sum(i.file_size for i in z.infolist()) != inventory['uncompressed_bytes']):
            raise ValueError('EXACT_PACKAGE_MEMBERS_AND_SIZE')
        for info in z.infolist():
            safe_name(info.filename)
            if info.is_dir() or info.flag_bits & 1 or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError('PACKAGE_REGULAR_UNENCRYPTED_ONLY')
        for name, wanted in required.items():
            if sha(z.read(name)) != wanted: raise ValueError('PACKAGE_CRC_OR_RAW_HASH:' + name)
    return dict(package_kind=KIND, entries=SPEC['entries'], inventory_sha256=INVENTORY_HASH, zip_sha256=ZIP_HASH)


def utc(): return datetime.now(timezone.utc).isoformat()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(canonical(obj)); f.flush(); os.fsync(f.fileno())


def load(path):
    # Reject duplicate keys, NaN and Infinity rather than accept ambiguous approval/manifest.
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('DUPLICATE_JSON_KEY:' + k)
            result[k] = v
        return result
    def invalid(value):
        raise ValueError('NONFINITE_JSON:' + value)
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_constant=invalid)


def safe_name(name):
    if (not isinstance(name, str) or not name or '\x00' in name or '\\' in name or ':' in name or PurePosixPath(name).is_absolute()
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('ARCHIVE_PATH_SCOPE:' + name)


def local_preflight(approval):
    from execution_authority import require_claim
    require_claim(approval['paid_approval_path'],approval['paid_approval_sha256'])
    # New delegated operational binding; no human signatures or approvals minted.
    policy_raw=(HERE.parent/'policy.json').read_bytes(); policy=load(HERE.parent/'policy.json')
    request=HERE.parent/'authorization_request.txt'
    seal_raw=(HERE.parent/'operational_seal.json').read_bytes(); seal=load(HERE.parent/'operational_seal.json')
    if (sha(request.read_bytes())!=policy['authorization_raw_sha256']
        or approval.get('authorization_raw_sha256')!=policy['authorization_raw_sha256']
        or approval.get('policy_sha256')!=sha(policy_raw)
        or approval.get('operational_seal_sha256')!=sha(seal_raw)
        or approval.get('schema')!='PROJECT_VAST_DELEGATED_INSTANCE_BINDING_V1'
        or approval.get('role')!='IMPLEMENTER_BINDING_OF_USER_DELEGATION_NOT_HUMAN_SIGNATURE'
        or approval.get('explicit_user_approval') is not True or approval.get('exclusive') is not True
        or approval.get('allocation_mode')!='ADOPT_RUNNING'
        or approval.get('scope')!='OFFLINE_ONLY' or approval.get('campaign_total_cap_usd')!='2.00'
        or approval.get('approval_reference')!=policy['authorization_reference']):
        raise ValueError('EXACT_USER_DELEGATION_POLICY_AND_NEW_VERSION_REQUIRED')
    for name,wanted in seal['files'].items():
        safe_name(name)
        if sha((HERE.parent/name).read_bytes())!=wanted:raise ValueError('NEW_OPERATIONAL_SOURCE_SEAL:'+name)
    for name,wanted in policy['preserved_files'].items():
        safe_name(name)
        if sha((ROOT/name).read_bytes())!=wanted:raise ValueError('ORIGINAL_OPERATIONAL_SOURCE_DRIFT:'+name)
    fixed=dict(package_kind=KIND, code_sha256=CODE, protocol_sha256=PROTO, zip_sha256=ZIP_HASH,
        inventory_sha256=INVENTORY_HASH, expected_tests=EXPECTED, physics_calls=0,gpu_calls=0,
        allocation_seconds=600,compute_seconds=120,stop_confirmation_seconds=180,hourly_cap_usd='0.25')
    if any(approval.get(k)!=v for k,v in fixed.items()):raise ValueError('UNCHANGED_GUEST_SCOPE_BINDING')
    if not re.fullmatch(r'[a-z0-9_]{8,48}',approval.get('run_id','')):raise ValueError('EXCLUSIVE_RUN_ID')
    now=datetime.now(timezone.utc)
    if not datetime.fromisoformat(approval['approved_utc'])<=now<datetime.fromisoformat(approval['expires_utc']):
        raise ValueError('BINDING_TIME_WINDOW')
    owner_path=Path(approval['owner_record'])
    owner=load(owner_path)
    if (sha(owner_path.read_bytes())!=approval['owner_record_sha256']
        or any(owner.get(k)!=approval.get(k) for k in ('instance_id','machine_id','country','run_id'))
        or owner.get('authorization_raw_sha256')!=policy['authorization_raw_sha256']):
        raise ValueError('NEW_RENTED_OWNER_BINDING')
    connection=dict(api_ssh_host=owner['api_ssh_host'],api_ssh_port=owner['api_ssh_port'],
        ssh_host=owner['public_ipaddr'],ssh_port=owner['direct_ssh_port'],
        transport_ssh_host=owner['public_ipaddr'],transport_ssh_port=owner['direct_ssh_port'])
    if any(approval.get(k)!=v for k,v in connection.items()):raise ValueError('OWNER_CONNECTION_BINDING')
    if (Path(approval['known_hosts_file']).parent!=owner_path.parent
        or sha(Path(approval['known_hosts_file']).read_bytes())!=approval['known_hosts_sha256']):
        raise ValueError('LEASE_HOST_KEY_FILE_PIN')
    from budget import Ledger
    ledger=Ledger(policy['ledger_path']); events,_=ledger.read(); balance=ledger.balances(events)
    if owner['reservation_token'] not in balance['active'] or balance['remaining']<0:
        raise ValueError('ACTIVE_CUMULATIVE_PROJECT_RESERVATION_REQUIRED')
    checks=[]
    for name in ('protocol_seal.json','preservation_manifest.json','code_seal.json'):
        manifest=load(ROOT/'experiments/adaptive_experience_tablet_v0'/name)
        for relative,wanted in manifest['files'].items():
            safe_name(relative)
            if sha((ROOT/relative).read_bytes())!=wanted:raise ValueError('PRESERVED_PACKAGE_SOURCE:'+relative)
        checks.append(dict(manifest=name,files=len(manifest['files'])))
    checks.append(verify_local_package())
    if KIND=='A':validate_policy_receipt(approval)
    return checks


def validate_policy_receipt(approval):
    path=Path(approval['B_stage_closeout']); close=load(path)
    if sha(path.read_bytes())!=approval['B_stage_closeout_sha256']:
        raise ValueError('B_STAGE_CLOSEOUT_RAW_PIN')
    if (close.get('package_kind')!='B' or close.get('passed') is not True
        or close.get('destroy',{}).get('status')!='DESTROY_CONFIRMED'
        or close.get('stop',{}).get('status')!='STOP_CONFIRMED'
        or close.get('recovery',{}).get('verified') is not True or not close.get('budget_settled')
        or close.get('authorization_raw_sha256')!=load(HERE.parent/'policy.json')['B_origin_authorization_raw_sha256']):
        raise ValueError('B_ACTUAL_95_RECOVERY_STOP_DESTROY_COST_REQUIRED')
    from budget import Ledger
    events,_=Ledger(load(HERE.parent/'policy.json')['ledger_path']).read()
    token=close['owner']['reservation_token']
    if not any(e.get('action')=='SETTLE' and e.get('token')==token and e.get('destroy_confirmed') is True for e in events):
        raise ValueError('B_ACTUAL_LEDGER_SETTLEMENT_REQUIRED')
    required={'owner.json','binding.json','outer_stop.json','outer_destroy.json','outer_recovery.json','cost_closeout.json',
        'transport/closure.json','transport/recovered/output/status.json','transport/recovered/output/junit.xml',
        'transport/recovered/output/physics_guard.json','transport/recovery_verified.json'}
    if not required.issubset(close.get('raw_files',{})):raise ValueError('B_MANDATORY_RAW_EVIDENCE')
    owner=load(path.parent/'owner.json')
    if any(close['owner'].get(k)!=owner.get(k) for k in ('instance_id','machine_id','country','run_id','reservation_token')):
        raise ValueError('B_CLOSEOUT_OWNER_DRIFT')
    for name in ('outer_stop.json','outer_destroy.json','outer_recovery.json'):
        if load(path.parent/name).get('instance_id')!=owner['instance_id']:raise ValueError('B_CLOSEOUT_INSTANCE_ID')
    cost=load(path.parent/'cost_closeout.json')
    for source,wanted in cost['billing_raw_files'].items():
        if sha(Path(source).read_bytes())!=wanted:raise ValueError('B_PROVIDER_BILLING_RAW_DRIFT')
    if not any(e.get('action')=='OBSERVE' and e.get('cost_closeout_sha256')==sha((path.parent/'cost_closeout.json').read_bytes()) for e in events):
        raise ValueError('B_FRESH_COST_OBSERVATION_REQUIRED')
    root=path.parent/'transport'; status=load(root/'recovered/output/status.json')
    B=load(HERE/'package_bindings.json')['B']
    import xml.etree.ElementTree as ET
    cases=ET.parse(root/'recovered/output/junit.xml').getroot().findall('.//testcase')
    guard=load(root/'recovered/output/physics_guard.json')
    if (status.get('status')!='PASS' or status.get('tests')!=95
        or any(status.get(k)!=0 for k in ('failed','errors','skipped','physics_calls','gpu_calls'))
        or status.get('code_sha256')!=B['code_sha256'] or status.get('protocol_sha256')!=B['protocol_sha256']
        or len(cases)!=95 or len({c.attrib['classname']+'::'+c.attrib['name'] for c in cases})!=95
        or any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped'))
        or guard.get('blocked_attempts')!=[] or guard.get('new_physics_calls')!=0 or guard.get('gpu_calls')!=0):
        raise ValueError('B_ORIGINAL_RAW_JUNIT_AND_GUARD_REQUIRED')
    for relative,wanted in close['raw_files'].items():
        safe_name(relative)
        if sha((path.parent/relative).read_bytes())!=wanted:raise ValueError('B_STAGE_EVIDENCE_DRIFT')


class Transport:
    def __init__(self, approval, cli, key, out):
        self.auth, self.cli, self.key, self.out = approval, str(cli), str(key), out
        self.guest = '/workspace/tablet_v0_' + KIND.lower() + '_' + approval['run_id']
        self.supervisor = None
        self.armed = None
        self.remote_created = False
        self.identity_verified = False
        self.recovered = False
        self.owns_stop = False
        self.start_ns = None
        self.started_utc = None
        self.index = 0
        self.clock_fault = None
        self.payload_returncode = None
        # A-resume argv dispatch retained: no PowerShell/cmd shell builds remote Python.
        self.ssh_argv = ['ssh', '-T', '-i', self.key, '-p', str(approval.get('transport_ssh_port',approval['ssh_port'])), '-o', 'BatchMode=yes',
                         '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
                         '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
                         'root@' + approval.get('transport_ssh_host',approval['ssh_host'])]

    def measured_clocks(self):
        if self.start_ns is None:return 0, 0
        mono = (time.monotonic_ns() - self.start_ns) / 1e9
        wall = (datetime.now(timezone.utc) - datetime.fromisoformat(self.started_utc)).total_seconds()
        if mono < 0 or abs(mono - wall) > 2:
            self.clock_fault = 'ALLOCATION_CLOCK_DRIFT'
        return mono, wall

    def age(self):
        mono, wall = self.measured_clocks()
        if self.clock_fault:raise ValueError(self.clock_fault)
        return max(mono, wall)

    def cleanup_age(self):
        # Retain first monotonic clock for stop-only cleanup; drift never authorizes more work.
        mono, wall = self.measured_clocks()
        return max(0, mono) if self.clock_fault else max(mono, wall)

    def stop_control_check(self):
        from admin_revalidation import SafetyStop
        if self.auth.get('lease_watchdog_pid') is not None and not guardian_alive(self.auth['lease_watchdog_pid']):
            raise SafetyStop('ENTIRE_LEASE_STOP_CONTROL_LOST')
        if (self.supervisor is None or self.supervisor.poll() is not None
                or (self.out/'completion.json').exists() or (self.out/'supervisor_final.json').exists()
                or (self.out/'guardian/final.json').exists()):
            raise SafetyStop('OUTSIDE_STOP_CONTROL_LOST')
        if self.armed is not None:
            pid = load(self.out/'guardian_pid.json')['pid']
            if type(pid) is not int or pid < 1:raise ValueError('GUARDIAN_PID_REQUIRED')
            if not guardian_alive(pid):raise SafetyStop('GENERIC_GUARDIAN_PROCESS_LOST')

    def emit(self, event, **kw):
        obj = dict(event=event, observed_utc=utc(), monotonic_ns=time.monotonic_ns(), **kw)
        with (self.out / 'events.jsonl').open('ab') as f:
            f.write(canonical(obj) + b'\n'); f.flush(); os.fsync(f.fileno())

    def run(self, argv, name, timeout, input=None):
        if argv[0]!='scp':return self.run_once(argv,name,timeout,input)
        from admin_revalidation import transient_connection
        deadline=time.monotonic()+timeout
        for attempt in range(1,4):
            self.stop_control_check()
            left=deadline-time.monotonic()
            if left<=0:raise TimeoutError('UNCHANGED_SCP_PHASE_DEADLINE')
            try:return self.run_once(argv,name,left,input)
            except RuntimeError as error:
                from admin_revalidation import SafetyStop
                if isinstance(error,SafetyStop):raise
                prefix=self.out/('%03d_' % self.index + name)
                stderr=prefix.with_suffix('.stderr').read_text(encoding='utf-8',errors='replace')
                if attempt==3 or not transient_connection(stderr):raise
                self.emit('ADMIN_SAME_INSTANCE_TRANSFER_REVALIDATION',phase=name,attempt=attempt,
                          original_deadline_unchanged=True,no_guest_gate_reexecution=True)
                self.control(max(.1,deadline-time.monotonic()),phase_deadline=deadline)
        raise RuntimeError('SCP_ATTEMPTS_EXHAUSTED')

    def run_once(self, argv, name, timeout, input=None):
        if argv[0] in ('ssh','scp') and self.auth.get('known_hosts_file'):
            argv=[argv[0],'-o','UserKnownHostsFile='+self.auth['known_hosts_file'],*argv[1:]]
        self.index += 1
        prefix = self.out / ('%03d_' % self.index + name)
        child = None
        with prefix.with_suffix('.stdout').open('xb') as a, prefix.with_suffix('.stderr').open('xb') as b:
            try:
                if argv[0] in ('ssh', 'scp') and self.armed is not None:
                    self.stop_control_check()
                    child = subprocess.Popen(argv, stdin=subprocess.PIPE if input is not None else None, stdout=a, stderr=b)
                    limit = time.monotonic() + timeout
                    send = input
                    while True:
                        self.stop_control_check()
                        self.age()
                        remaining = limit - time.monotonic()
                        if remaining <= 0:raise subprocess.TimeoutExpired(argv, timeout)
                        try:
                            child.communicate(input=send, timeout=min(.5, remaining))
                            self.stop_control_check()
                            self.age()
                            break
                        except subprocess.TimeoutExpired:
                            send = None
                    result = child
                else:
                    result = subprocess.run(argv, input=input, stdout=a, stderr=b, timeout=timeout)
            except BaseException as exc:
                if child is not None and child.poll() is None:
                    child.kill()
                    child.wait(timeout=2)
                self.emit('COMMAND_EXCEPTION', phase=name, error=repr(exc), log_prefix=str(prefix))
                raise
        self.emit('TRANSPORT_EXIT', phase=name, returncode=result.returncode, log_prefix=str(prefix))
        if result.returncode:raise RuntimeError('ADMIN_PHASE_FAILED:' + name)
        return prefix.with_suffix('.stdout').read_bytes()

    def show(self, name, timeout=12):
        roles = dict(initial_instance='initial', restart_status='restart', phase_control='control', final_instance='final')
        if name not in roles:raise ValueError('API_CALLSITE_ROLE_REQUIRED')
        raw = self.run([self.cli, '--raw', '--retry', '1', 'show', 'instance', str(self.auth['instance_id'])], name, timeout)
        record = decode(raw)
        state = inspect(record, self.auth, roles[name])
        self.emit('STATE_OBSERVED', phase=name, **state)
        return dict(record, _admin_state=state['state'], _ssh_ready=state['connection_ready'], _rate_within_cap=state['rate_within_cap'])

    def control(self, required_seconds, *, phase_deadline=None):
        self.stop_control_check()
        handoff = self.handoff()
        if self.age() + required_seconds + 12 >= handoff:raise TimeoutError('ABSOLUTE_PHASE_TIME_RESERVE')
        if phase_deadline is not None and time.monotonic()>=phase_deadline:raise TimeoutError('UNCHANGED_SCP_PHASE_DEADLINE')
        api_timeout=12 if phase_deadline is None else min(12,phase_deadline-time.monotonic())
        observed = self.show('phase_control',timeout=api_timeout)
        if phase_deadline is not None and time.monotonic()>=phase_deadline:raise TimeoutError('UNCHANGED_SCP_PHASE_DEADLINE')
        # API latency is a state transition window: recheck control before any new SSH/SCP.
        self.stop_control_check()
        if self.age() + required_seconds + 12 >= handoff:raise TimeoutError('ABSOLUTE_PHASE_TIME_RESERVE')
        if observed['_admin_state'] != 'RUNNING' or not observed['_ssh_ready']:raise ValueError('INSTANCE_NOT_READY')
        if self.armed is not None and canonical(load(self.out/'guardian/armed.json')) != canonical(self.armed):
            raise ValueError('OUTSIDE_ARM_RECEIPT_CHANGED')

    def handoff(self):
        if self.armed is None: return 400
        armed_age = (datetime.fromisoformat(self.armed['armed_utc']) - datetime.fromisoformat(self.started_utc)).total_seconds()
        return min(400, armed_age + self.armed['deadline_seconds'])

    def py(self, script_name, args, name, timeout=30,phase_deadline=None,required_seconds=None):
        if script_name!='guest_probe.py':return self.py_once(script_name,args,name,timeout,phase_deadline,required_seconds)
        deadline=min(time.monotonic()+timeout,phase_deadline if phase_deadline is not None else float('inf'))
        for attempt in range(1,4):
            left=deadline-time.monotonic()
            if left<=0:raise TimeoutError('UNCHANGED_PREPARATION_RPC_DEADLINE')
            try:return self.py_once(script_name,args,name,left,deadline,required_seconds)
            except (RuntimeError,subprocess.TimeoutExpired) as error:
                if attempt==3 or not self.connection_reply_unconfirmed(error):raise
                self.emit('ADMIN_EMPTY_ROOT_PREPARATION_RECHECK',attempt=attempt,no_gate_launch=True,absolute_window_unchanged=True)

    def py_once(self, script_name, args, name, timeout=30,phase_deadline=None,required_seconds=None):
        self.control(timeout if required_seconds is None else required_seconds,phase_deadline=phase_deadline)
        if phase_deadline is not None:
            timeout=min(timeout,phase_deadline-time.monotonic())
            if timeout<=0:raise TimeoutError('UNCHANGED_RPC_PHASE_DEADLINE')
        if script_name=='guest_job.py':
            # __file__ and detached argv must resolve to the uploaded, pinned script.
            command=shlex.join([VENV,'-B',self.guest+'/guest_job.py',*map(str,args)])
            return self.run([*self.ssh_argv,command],name,timeout)
        script = (HERE / script_name).read_bytes()
        # Linux shell sees shlex-quoted tokens only; Python source travels on SSH stdin.
        command = shlex.join([VENV if script_name != 'guest_probe.py' else 'python3', '-B', '-', *map(str, args)])
        return self.run([*self.ssh_argv, command], name, timeout, input=script)

    def upload(self, local, remote_name, name, timeout=35):
        safe_name(remote_name)
        self.control(timeout)
        # Preserve successful A-resume SCP legacy mode. All destinations live in a new exclusive root.
        command = ['scp', '-O', '-i', self.key, '-P', str(self.auth.get('transport_ssh_port',self.auth['ssh_port'])), '-o', 'BatchMode=yes',
                   '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
                   str(local), 'root@' + self.auth.get('transport_ssh_host',self.auth['ssh_host']) + ':' + self.guest + '/' + remote_name]
        self.run(command, name, timeout)

    def connection_reply_unconfirmed(self,error):
        from admin_revalidation import SafetyStop,transient_connection
        self.stop_control_check()  # Loss of termination control is never a reconnect case.
        if isinstance(error,SafetyStop):return False
        paths=sorted(self.out.glob('%03d_*.stderr'%self.index))
        stderr=paths[-1].read_text(encoding='utf-8',errors='replace') if paths else ''
        if any(marker in stderr.lower() for marker in ('host key verification failed','remote host identification has changed','permission denied')):return False
        return isinstance(error,subprocess.TimeoutExpired) or (str(error).startswith('ADMIN_PHASE_FAILED:') and transient_connection(stderr))

    def run_remote_job(self, command, script_sha256, *, timeout_seconds=140,disconnect_probe=False):
        # Every exclusive job has its own finality and finite recovery budget.
        self.writer_completion_verified=False;self.recovered=False;self.recovery_index=0
        job_id=self.auth['run_id']+'_gate'
        spec=dict(instance_id=self.auth['instance_id'],run_id=self.auth['run_id'],job_id=job_id,guest_root=self.guest,
                  wrapper_sha256=sha((HERE/'guest_job.py').read_bytes()),command=command,
                  command_script_sha256=script_sha256,timeout_seconds=timeout_seconds,job_role=getattr(self,'evidence_job_role','A320_GUEST' if KIND=='A' else 'B95_GUEST'))
        write(self.out/'job_spec.json',spec)
        self.upload(HERE/'guest_job.py','guest_job.py','job_wrapper_upload',12)
        self.upload(self.out/'job_spec.json','job_spec.json','job_spec_upload',12)
        self.job_spec_sha256=sha(canonical(spec))
        write(self.out/'job_launch_intent.json',dict(job_id=job_id,instance_id=self.auth['instance_id'],spec_sha256=self.job_spec_sha256))
        # Launch once. Lost reply is followed only by status, never by relaunch.
        try:
            if disconnect_probe:
                # Deliberately time out/kill the local SSH client while the detached probe writes.
                self.py('guest_disconnect_launch.py',[self.guest,self.auth['instance_id'],job_id],'job_launch_disconnect',2,required_seconds=timeout_seconds+96+2)
            else:self.py('guest_job.py',['launch',self.guest+'/job',self.auth['instance_id'],job_id],'job_launch',12,required_seconds=timeout_seconds+96+12)
        except (RuntimeError,subprocess.TimeoutExpired) as error:
            if not self.connection_reply_unconfirmed(error):raise
            self.emit('JOB_LAUNCH_REPLY_UNCONFIRMED',error=repr(error),no_relaunch=True)
        deadline=min(time.monotonic()+timeout_seconds+12,self.start_ns/1e9+self.handoff()-96)
        consecutive_errors=0
        while time.monotonic()<deadline:
            self.stop_control_check()
            try:
                value=decode(self.py('guest_job.py',['status',self.guest+'/job',self.auth['instance_id'],job_id],'job_status',min(12,max(.1,deadline-time.monotonic())),phase_deadline=deadline))
                consecutive_errors=0
            except (RuntimeError,subprocess.TimeoutExpired) as error:
                if not self.connection_reply_unconfirmed(error):raise
                consecutive_errors+=1;self.emit('JOB_STATUS_REPLY_UNCONFIRMED',attempt=consecutive_errors,error=repr(error))
                if consecutive_errors>=3:raise RuntimeError('JOB_STATUS_UNCONFIRMED_PRESERVE_NO_RELAUNCH')
                time.sleep(.5);continue
            if value.get('instance_id')!=self.auth['instance_id'] or value.get('run_id')!=self.auth['run_id'] or value.get('job_id')!=job_id or value.get('spec_sha256')!=self.job_spec_sha256:raise ValueError('JOB_STATUS_OWNER_OR_SPEC_DRIFT')
            self.emit('JOB_STATE_OBSERVED',job_id=job_id,state=value['state'])
            if value['state'] in ('EXITED_SUCCESS','EXITED_FAILURE'):
                if value.get('writer_completion_verified') is not True:raise ValueError('JOB_WRITERS_UNCONFIRMED')
                write(self.out/'job_final_observation.json',value)
                self.writer_completion_verified=True;self.job_final_observation=value
                return value
            if value['state'] in ('NOT_CLAIMED','UNKNOWN_WRITERS'):raise RuntimeError('JOB_UNKNOWN_PRESERVE_NO_RELAUNCH')
            time.sleep(.5)
        raise TimeoutError('UNCHANGED_JOB_AND_RECOVERY_ABSOLUTE_WINDOW')

    def recover(self):
        if not self.remote_created or not self.identity_verified:return
        attempt=getattr(self,'recovery_index',0)+1;self.recovery_index=attempt
        if attempt>3:raise ValueError('RECOVERY_ATTEMPTS_EXHAUSTED')
        final=getattr(self,'writer_completion_verified',False)
        folder=self.out/('final_recovery_attempt_%d'%attempt if final else 'partial_recovery_%d'%attempt)
        folder.mkdir(parents=True,exist_ok=True)
        write(folder/'recovery_attempted.json',dict(reason='FINAL_RECOVERY' if final else 'PARTIAL_ONLY',observed_utc=utc()))
        evidence_code=getattr(self,'evidence_code_sha256',CODE)
        pack=decode(self.py('guest_recover.py',[self.guest,self.auth['instance_id'],evidence_code,self.auth['run_id'],'capture%d'%attempt],'package_evidence',25))
        if final and pack.get('writer_completion_verified') is not True:raise ValueError('FINAL_WRITER_PROOF_LOST')
        if pack.get('remote_archive')!=self.guest+'/.recovery/capture%d/evidence.zip'%attempt:raise ValueError('RECOVERY_REMOTE_ARCHIVE_SCOPE')
        self.control(35);dest=folder/'evidence.zip'
        if dest.exists():raise ValueError('RECOVERY_DESTINATION_EXISTS')
        argv=['scp','-O','-i',self.key,'-P',str(self.auth.get('transport_ssh_port',self.auth['ssh_port'])),'-o','BatchMode=yes',
              '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','root@'+self.auth.get('transport_ssh_host',self.auth['ssh_host'])+':'+pack['remote_archive'],str(dest)]
        self.run(argv,'raw_evidence_download',35)
        if sha(dest.read_bytes())!=pack['sha256']:raise ValueError('RECOVERED_ZIP_HASH')
        recovered=folder/'recovered'
        with zipfile.ZipFile(dest) as z:
            names=z.namelist();manifest=decode(z.read('evidence_manifest.json'))
            if (len(names)!=len(set(names)) or len(names)!=len({n.casefold() for n in names}) or z.testzip() is not None
                or manifest.get('instance_id')!=self.auth['instance_id'] or manifest.get('code_sha256')!=evidence_code
                or manifest.get('run_id')!=self.auth['run_id'] or len(manifest['files'])!=pack['files']
                or set(names)!=set(manifest['files'])|{'evidence_manifest.json'}):raise ValueError('RAW_RECOVERY_MANIFEST_OR_FILE_SET')
            for item in z.infolist():
                safe_name(item.filename)
                if item.is_dir() or item.flag_bits&1 or stat.S_IFMT(item.external_attr>>16) not in (0,stat.S_IFREG):raise ValueError('RECOVERY_NON_REGULAR_MEMBER')
            for name,wanted in manifest['files'].items():
                if sha(z.read(name))!=wanted:raise ValueError('RAW_RECOVERY_HASH:'+name)
            recovered.mkdir(exist_ok=False)
            for name in names:
                path=recovered/name;path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as f:f.write(z.read(name))
        write(folder/'recovery_verified.json',dict(files=pack['files'],zip_sha256=pack['sha256'],all_raw_hashes_match=True,
              writer_completion_verified=final and pack.get('writer_completion_verified') is True,
              job_observation=pack['job_observation'],job_spec_sha256=getattr(self,'job_spec_sha256',None),
              scope='FINAL_EXISTING_ORIGINALS' if final else 'PARTIAL_ONLY_NOT_DELETION_AUTHORITY'))
        if final:
            # Canonical final evidence is published only after this entire attempt validates.
            shutil.copyfile(dest,self.out/'evidence.zip')
            shutil.copytree(recovered,self.out/'recovered')
            write(self.out/'recovery_verified.json',load(folder/'recovery_verified.json'))
            self.recovered=True

    def recover_final(self):
        from admin_revalidation import transient_connection
        while getattr(self,'recovery_index',0)<3:
            try:return self.recover()
            except (RuntimeError,subprocess.TimeoutExpired) as error:
                from admin_revalidation import SafetyStop
                if isinstance(error,SafetyStop):raise
                paths=sorted(self.out.glob('%03d_*.stderr'%self.index))
                message=paths[-1].read_text(encoding='utf-8',errors='replace') if paths else ''
                if not transient_connection(message) or getattr(self,'recovery_index',0)>=3:raise
                self.emit('FINAL_RECOVERY_ADMIN_RETRY',error=repr(error),no_guest_gate_reexecution=True,absolute_window_unchanged=True)

    def validate_result(self):
        data = self.out / 'recovered'
        if ((data / 'ticket.json').read_bytes() != (self.out / 'offline_ticket.json').read_bytes()
                or (data / 'armed.json').read_bytes() != (self.out / 'armed.json').read_bytes()):
            raise ValueError('RECOVERED_APPROVAL_RAW_BINDING')
        status = load(data / 'output/status.json')
        if (status.get('status') != 'PASS' or status.get('tests') != EXPECTED
                or any(status.get(k) != 0 for k in ('failed', 'errors', 'skipped', 'physics_calls', 'gpu_calls'))
                or status.get('code_sha256') != CODE or status.get('protocol_sha256') != PROTO
                or status.get('benchmark_complete') is not (KIND == 'A')):
            raise ValueError('EXACT_PACKAGE_OFFLINE_GATE_NOT_PASSED')
        import xml.etree.ElementTree as ET
        cases = ET.parse(data / 'output/junit.xml').getroot().findall('.//testcase')
        ids = [c.attrib['classname']+'::'+c.attrib['name'] for c in cases]
        if (len(cases) != EXPECTED or len(set(ids)) != EXPECTED
                or any(c.find(tag) is not None for c in cases for tag in ('failure', 'error', 'skipped'))):
            raise ValueError('RECOVERED_JUNIT_GATE')
        if KIND == 'A':
            original_ids = load(ROOT / SPEC['case_inventory'])['ids']
            if set(ids) != set(original_ids): raise ValueError('EXACT_ORIGINAL_320_CASE_IDENTITIES')
        guard = load(data / 'output/physics_guard.json')
        if (guard.get('blocked_attempts') != [] or guard.get('new_physics_calls') != 0 or guard.get('gpu_calls') != 0
                or not 0 <= status['wall_ns'] <= 120 * 10**9 or not 0 <= status['cpu_ns'] <= 120 * 10**9):
            raise ValueError('PACKAGE_GUARD_OR_RESOURCE_SCOPE')
        if KIND == 'B':
            if status.get('package_kind') != 'B' or not 0 <= status['process_tree_peak_rss_bytes'] <= 536870912:
                raise ValueError('B_MEMORY_AND_SCOPE')
            return status
        benchmark = load(data / 'output/benchmark.json')
        if (guard.get('blocked_attempts') != [] or guard.get('new_physics_calls') != 0 or guard.get('gpu_calls') != 0
                or benchmark.get('complete') is not True or benchmark.get('physics_calls') != 0
                or benchmark.get('gpu_calls') != 0):
            raise ValueError('GUARD_OR_BENCHMARK_INCOMPLETE')
        if (benchmark.get('repeats') != 31 or [x['records'] for x in benchmark['index_growth']] != [100, 1000, 10000]
                or not 0 <= status['wall_ns'] <= 120 * 10**9 or not 0 <= status['cpu_ns'] <= 120 * 10**9):
            raise ValueError('RECOVERED_BENCHMARK_OR_RESOURCE_SCOPE')
        return status

    def execute_payload(self):
        self.writer_completion_verified=False
        self.upload(SOURCE, 'source.zip', 'source_upload', 40)
        self.upload(INVENTORY, 'inventory.json', 'inventory_upload', 12)
        verified = json.loads(self.py('guest_source_verify.py', [self.guest, ZIP_HASH, INVENTORY_HASH, CODE, PROTO, KIND], 'source_verify', 25))
        write(self.out / 'source_upload_verified.json', verified)
        ticket = dict(gate='ADAPTIVE_EXPERIENCE_TABLET_CPU_ROUTE_V0' if KIND == 'A' else 'BOUNDED_ADMIN_RECOVERY_POLICY_95_V0',
                      scope='OFFLINE_ONLY', explicit_user_approval=True, package_kind=KIND,
                      zip_sha256=ZIP_HASH, inventory_sha256=INVENTORY_HASH, expected_tests=EXPECTED,
                      approval_reference=self.auth['approval_reference'], instance_id=self.auth['instance_id'],
                      machine_id=self.auth['machine_id'], country=self.auth['country'], code_sha256=CODE,
                      protocol_sha256=PROTO, physics_calls=0, gpu_calls=0, armed_sha256=sha(canonical(self.armed)),
                      allocation_start_utc=self.started_utc, allocation_seconds=600)
        write(self.out / 'offline_ticket.json', ticket)
        self.upload(self.out / 'armed.json', 'armed.json', 'upload_armed', 12)
        self.upload(self.out / 'offline_ticket.json', 'ticket.json', 'upload_ticket', 12)
        # Full 140s wrapper + 96s two control queries/package/download + stop headroom.
        if self.age() >= 150:
            raise TimeoutError('GATE_START_REQUIRES_FULL_COMPUTE_AND_RECOVERY_RESERVE')
        if self.age() + 140 + 96 >= self.handoff():
            raise TimeoutError('ARMED_DEADLINE_FULL_GATE_AND_RECOVERY_RESERVE')
        self.upload(HERE/'guest_gate.py','guest_gate.py','gate_wrapper_upload',12)
        job=self.run_remote_job([VENV,'-B',self.guest+'/guest_gate.py',self.guest,VENV,str(self.auth['instance_id']),ticket['armed_sha256'],sha((self.out/'offline_ticket.json').read_bytes())],sha((HERE/'guest_gate.py').read_bytes()),timeout_seconds=140)
        gate_rc=job['terminal']['returncode']
        self.payload_returncode=gate_rc
        self.recover_final()
        if gate_rc!=0 or job['state']!='EXITED_SUCCESS':raise ValueError('REMOTE_OFFLINE_EXIT:'+str(gate_rc))
        self.validate_result()
        return gate_rc

    def execute(self):
        local_preflight(self.auth)  # Direct entry is guarded too, before initial Provider observation.
        from execution_authority import begin_transport
        begin_transport(self.auth.get('paid_approval_path'),self.auth.get('paid_approval_sha256'))
        failure = None
        gate_rc = None
        trigger = 'FAILED'
        final = None
        try:
            initial = self.show('initial_instance')
            write(self.out / 'initial_instance.json', initial)
            if self.auth.get('allocation_mode') != 'ADOPT_RUNNING' and initial['actual_status'] not in ('exited', 'stopped'):
                raise ValueError('EXCLUSIVE_STOPPED_INSTANCE_REQUIRED')
            if datetime.now(timezone.utc) >= datetime.fromisoformat(self.auth['expires_utc']):
                raise ValueError('APPROVAL_EXPIRED_BEFORE_ALLOCATION')
            if self.auth.get('allocation_mode')=='ADOPT_RUNNING':
                self.owns_stop=True  # Approved running server requires cleanup even if watchdog startup fails.
            self.start_ns = time.monotonic_ns()
            self.started_utc = utc()
            write(self.out / 'allocation_start.json', dict(monotonic_ns=self.start_ns, observed_utc=self.started_utc,
                  prior_failed_attempts=3, prior_closed_window_sha256=self.auth['prior_closed_window_sha256'],
                  new_window_separately_authorized=True, provenance='BEFORE_AUTHORIZED_ADOPTION; NEVER_RESET' if self.auth.get('allocation_mode')=='ADOPT_RUNNING' else 'BEFORE_AUTHORIZED_RESTART; NEVER_RESET'))
            lease = dict(scope='STOP_CONTROL_ONLY', exclusive=True, explicit_user_approval=True,
                         approval_reference=self.auth['approval_reference'], prior_failed_attempts=3,
                         new_window_separately_authorized=True, instance_id=self.auth['instance_id'],
                         machine_id=self.auth['machine_id'], country=self.auth['country'],
                         allocation_monotonic_ns=self.start_ns, allocation_start_utc=self.started_utc,
                         guardian_sha256=sha(GUARD.read_bytes()), supervisor_sha256=sha((HERE / 'supervisor.py').read_bytes()),
                         cli=self.cli, repo_root=str(ROOT), out=str(self.out),
                         state_contract_sha256=sha((HERE/'state_contract.py').read_bytes()),
                         guardian_driver_sha256=sha((HERE/'guardian_driver.py').read_bytes()),
                         hourly_cap_usd=self.auth.get('hourly_cap_usd','0.25'),
                         budget_amendment_sha256=self.auth.get('budget_amendment_sha256'),
                         admin_target_protocol_sha256=TARGET_PROTOCOL_SHA)
            write(self.out / 'supervisor_lease.json', lease)
            self.supervisor = subprocess.Popen([sys.executable, '-B', str(HERE / 'supervisor.py'), '--lease',
                      str(self.out / 'supervisor_lease.json')], cwd=ROOT,
                      env=dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1'),
                      stdout=(self.out / 'supervisor.stdout').open('xb'), stderr=(self.out / 'supervisor.stderr').open('xb'),
                      creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
            until = time.monotonic() + 10
            while not (self.out / 'supervisor_ready.json').exists():
                if self.supervisor.poll() is not None or time.monotonic() >= until:
                    raise ValueError('PRE_RESTART_STOP_SUPERVISOR_NOT_READY')
                time.sleep(.1)
            ready = load(self.out / 'supervisor_ready.json')
            if (ready.get('lease_sha256') != sha((self.out / 'supervisor_lease.json').read_bytes())
                    or ready.get('instance_id') != self.auth['instance_id'] or self.supervisor.poll() is not None):
                raise ValueError('SUPERVISOR_READY_LEASE_HASH')
            self.owns_stop = True  # Exact stopped instance + human exclusive restart/stop scope established.
            if self.auth.get('allocation_mode') == 'ADOPT_RUNNING':
                self.stop_control_check()
                host = self.show('phase_control')
                self.emit('ADOPT_EXISTING_RUNNING', restart_requests=0)
            else:
                self.run([self.cli, '--raw', '--retry', '1', 'start', 'instance', str(self.auth['instance_id'])], 'restart', 12)
                until = time.monotonic() + 45
                while time.monotonic() < until:
                    host = self.show('restart_status')
                    if host['_admin_state'] == 'RUNNING' and host['_ssh_ready']:
                        break
                    time.sleep(1)
                else:
                    raise TimeoutError('BOUNDED_RESTART_NOT_RUNNING')
            write(self.out / 'running_instance.json', host)
            until = time.monotonic() + 25
            while not (self.out / 'guardian/armed.json').exists():
                if self.supervisor.poll() is not None or time.monotonic() >= until:
                    raise ValueError('GENERIC_GUARDIAN_NOT_ARMED')
                time.sleep(.1)
            self.armed = load(self.out / 'guardian/armed.json')
            generic = load(self.out / 'guardian_lease.json')
            if (self.armed.get('status') != 'ARMED' or self.armed.get('outside_guest') is not True
                    or self.armed.get('guardian_sha256') != sha(GUARD.read_bytes())
                    or any(self.armed.get(k) != self.auth[k] for k in ('instance_id', 'machine_id', 'country', 'approval_reference'))
                    or self.armed.get('deadline_seconds') != generic['deadline_seconds']
                    or self.armed.get('confirmation_seconds') != 180):
                raise ValueError('ARMED_APPROVAL_BINDING')
            armed_age = (datetime.fromisoformat(self.armed['armed_utc']) - datetime.fromisoformat(self.started_utc)).total_seconds()
            if not 0 <= armed_age or armed_age + self.armed['deadline_seconds'] > 420:
                raise ValueError('ARMED_ABSOLUTE_HANDOFF_BOUND')
            write(self.out / 'armed.json', self.armed)
            # Administrative rechecks preserve this original preparation/time budget.
            if self.age() >= 100:
                raise TimeoutError('GUEST_PREPARATION_RESERVE')
            write(self.out/'remote_writes_started.json',dict(instance_id=self.auth['instance_id'],observed_utc=utc()))
            self.remote_created = True  # Persist BEFORE any remote project writes
            probe = json.loads(self.py('guest_probe.py', [self.auth['instance_id'], VENV, self.guest], 'guest_identity', 20))
            write(self.out / 'guest_probe.json', probe)
            if probe.get('actual_container_id') != str(self.auth['instance_id']):
                raise ValueError('OBSERVED_GUEST_ID_REQUIRED')
            self.identity_verified = True
            gate_rc = self.execute_payload()
            trigger = 'COMPLETED'
        except BaseException as exc:
            failure = repr(exc)
            trigger = 'DEADLINE' if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else 'FAILED'
            self.emit('CONTROLLER_STOP', reason=failure)
            if self.remote_created and self.identity_verified and not self.recovered :
                try:
                    self.recover()
                except BaseException as recovery_error:
                    self.emit('RECOVERY_FAILED', error=repr(recovery_error))
        finally:
            gate_rc = self.payload_returncode
            if self.supervisor is not None:
                try:
                    write(self.out / 'completion.json', dict(trigger=trigger, reason=failure, gate_returncode=gate_rc,
                                                            recovered=self.recovered, observed_utc=utc()))
                except FileExistsError:
                    trigger = 'DEADLINE' if self.cleanup_age() >= self.handoff() else 'FAILED'
                except BaseException as exc:
                    trigger = 'FAILED'
                    failure = 'COMPLETION_MARKER_WRITE_FAILED:' + repr(exc)
                try:
                    self.supervisor.wait(timeout=max(.1, 592 - self.cleanup_age()))
                except BaseException as exc:
                    self.emit('SUPERVISOR_WAIT_UNCONFIRMED', error=repr(exc))
            if self.owns_stop:
                stop_path=self.out/'supervisor_final.json'
                try:
                    observed_stop=load(stop_path) if stop_path.exists() else None
                except BaseException:
                    observed_stop=None
                if not observed_stop or observed_stop.get('result',{}).get('status')!='STOP_CONFIRMED' or observed_stop.get('result',{}).get('instance_id')!=self.auth['instance_id']:
                    if trigger=='COMPLETED':trigger='FAILED';failure='OUTSIDE_STOP_RECEIPT_MISSING'
                    transport=self
                    class FallbackControl:
                        timeout_seconds=12
                        def stop(control):
                            transport.run([transport.cli,'--raw','--retry','1','stop','instance',str(transport.auth['instance_id'])], 'controller_fallback_stop',control.timeout_seconds)
                        def show(control):
                            observed=transport.show('final_instance',timeout=control.timeout_seconds)
                            if observed['_admin_state']=='STARTING':raise ValueError('EXITED_WITH_RUNNING_INTENT_IS_NOT_STOPPED')
                            return observed
                    remaining=int(min(180,590-self.cleanup_age()))
                    if remaining>=1:
                        result=confirm_stop(FallbackControl(),self.auth['instance_id'],'FAILED',confirm_seconds=remaining,now=time.monotonic,sleep=time.sleep)
                    else:result=dict(status='STOP_UNCONFIRMED',instance_id=self.auth['instance_id'],manual_confirmation_required=True,external_warning=True)
                    write(self.out/'controller_fallback_final.json',dict(result=result,source='ORIGINAL_CONFIRM_STOP_WITH_EXACT_LEASED_IO',observed_utc=utc()))
                try:
                    final = self.show('final_instance', timeout=max(.1, min(8, 600 - self.cleanup_age())))
                    write(self.out / 'final_instance.json', final)
                    if not final['_rate_within_cap']:
                        trigger = 'FAILED'; failure = 'FINAL_PRICE_CAP_VIOLATION_OBSERVED'
                except BaseException as exc:
                    self.emit('FINAL_STATUS_UNCONFIRMED', error=repr(exc))
            try:
                stop = load(self.out / 'supervisor_final.json') if (self.out / 'supervisor_final.json').exists() else None
                if (self.out/'controller_fallback_final.json').exists():stop=load(self.out/'controller_fallback_final.json')
            except BaseException as exc:
                stop = None
                failure = 'SUPERVISOR_RECEIPT_UNREADABLE:' + repr(exc)
            final_age = self.cleanup_age() if self.start_ns is not None else 0
            final_clocks = self.measured_clocks()
            if self.clock_fault:
                trigger = 'FAILED'; failure = self.clock_fault
            confirmed = bool(stop and stop['result']['status'] == 'STOP_CONFIRMED' and final
                             and final['_admin_state'] == 'STOPPED' and stop['result'].get('instance_id') == self.auth['instance_id'])
            write(self.out / 'closure.json', dict(trigger=trigger, reason=failure, gate_returncode=gate_rc,
                  recovery_verified=self.recovered, actual_stop_confirmed=confirmed, allocation_start_utc=self.started_utc,
                  clock_fault=self.clock_fault, measured_mono_wall=final_clocks,
                  prior_failed_attempts=3, automatic_physics_retry=False, administrative_revalidation_authorized=True, planned_no_new_physics=True, gpu_calls=0 if trigger=='COMPLETED' else None, local_dynamic_tests=0,
                  prior_tablet_gate_attempts=1, closed_failed_gate_sha256=sha(FAILED_GATE.read_bytes()),
                  package_kind=KIND, zip_sha256=ZIP_HASH, inventory_sha256=INVENTORY_HASH,
                  allocation_age_seconds=str(final_age), run_fee_upper_bound_usd=str(Decimal(self.auth.get('hourly_cap_usd','0.25'))*Decimal(str(final_age))/3600),
                  prior_policy_run_fee_bound_usd=str(PRIOR_POLICY_FEE_BOUND), campaign_total_cap_usd='2.00',
                  target_protocol_sha256=TARGET_PROTOCOL_SHA, prior_B_failed_closure_sha256=sha(PREVIOUS_B.read_bytes()),
                  prior_B_failed_windows=1, prior_local_invocation_failures=1,
                  preparation_fee_reserve_usd=load(TARGET_PROTOCOL)['preparation_fee_reserve_usd'],
                  prior_policy_actual_execution_fee_usd=str(PRIOR_ACTUAL_POLICY_FEE) if PRIOR_ACTUAL_POLICY_FEE is not None else None,
                  budget_protocol_sha256=BUDGET_PROTOCOL_SHA, observed_utc=utc(),
                  status='COMPLETED' if trigger == 'COMPLETED' and confirmed else trigger if confirmed else 'UNRESOLVED',
                  execution_outcome=trigger, stop_status='STOP_CONFIRMED' if confirmed else 'STOP_UNCONFIRMED'))
            if KIND == 'B' and trigger == 'COMPLETED' and confirmed:
                names = ['closure.json', 'final_instance.json', 'supervisor_final.json', 'guardian/armed.json', 'evidence.zip']
                if (self.out/'guardian/final.json').exists(): names.append('guardian/final.json')
                paths = [self.out / n for n in names] + [p for p in (self.out/'recovered').rglob('*') if p.is_file()]
                write(self.out/'policy_completion.json', dict(role='AUTHOR_RECOVERED_POLICY_95_GATE',
                      status='COMPLETED', package_kind='B', tests=95, actual_stop_confirmed=True,
                      code_sha256=CODE, zip_sha256=ZIP_HASH, inventory_sha256=INVENTORY_HASH,
                      independent_authority_certification=False,
                      raw_files={p.relative_to(self.out).as_posix():sha(p.read_bytes()) for p in paths}))
        return 0 if trigger == 'COMPLETED' and confirmed else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--approval', required=True, type=Path)
    parser.add_argument('--cli', required=True, type=Path)
    parser.add_argument('--key', required=True, type=Path)
    parser.add_argument('--package-kind', required=True, choices=['A', 'B'])
    args = parser.parse_args()
    approval = load(args.approval)
    configure(args.package_kind)
    checks = local_preflight(approval)  # BEFORE out creation, API query, paid clock, restart or guardian.
    if not args.cli.is_file() or not args.key.is_file():
        raise ValueError('CLI_OR_KEY_FILE_MISSING')
    out = HERE / ('run_' + approval['run_id'])
    out.mkdir(exist_ok=False)
    write(out / 'human_authorization.json', approval)
    write(out / 'source_preflight.json', dict(checks=checks, zip_sha256=ZIP_HASH, observed_utc=utc()))
    return Transport(approval, args.cli, args.key, out).execute()


if __name__ == '__main__':
    raise SystemExit(main())
