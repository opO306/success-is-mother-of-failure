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
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FIRST_CODE = '18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09'
FIRST_PROTO = 'f03bc97a79e1a22ece4964270032d8829f7a208e961c09806c8f7bc10351013c'
SCOPE_HASH = 'da96a821a7aa8f6f9e2537959babf68420a0d7b8ac008b2c9751cee331ff8484'
BUDGET_PROTOCOL_SHA = '16db1a2dae38d2fc9d5713e9340b966257611da49ae6856529d9e59d7f126f43'
ORIGINAL_SCOPE = ROOT / 'docs/active/bounded_admin_recovery_v0/closure_v1/scope_protocol.json'
KIND = CODE = PROTO = ZIP_HASH = SOURCE = INVENTORY = INVENTORY_HASH = EXPECTED = SPEC = None
PRIOR_POLICY_FEE_BOUND = Decimal('0')
PRIOR_ACTUAL_POLICY_FEE = None
GUARD = ROOT / 'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
PRIOR = ROOT / 'docs/active/adaptive_experience_tablet_v0/remote_20261009_attempt3/closure.json'
VENV = '/usr/bin/python3'
TARGET_PROTOCOL_SHA = '0d5eb00aebc6e31fdf24670fe4d63a900359804da1f8926126ecb76877f0861d'
TARGET_PROTOCOL = HERE.parent / 'target_protocol.json'
PREVIOUS_B = ROOT / 'docs/active/bounded_admin_recovery_v0/budget_supplement_v1/remote_result_b_95_20261009_075708/closure.json'
FAILED_GATE = ROOT / 'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/run_approved_20261009_0130/closure.json'


def configure(kind):
    global KIND, CODE, PROTO, ZIP_HASH, SOURCE, INVENTORY, INVENTORY_HASH, EXPECTED, SPEC
    if kind != 'B': raise ValueError('NEW_TARGET_B_ONLY_A_REQUIRES_SEPARATE_PREPARATION_AND_APPROVAL')
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


def validate_policy_receipt(approval):
    global PRIOR_POLICY_FEE_BOUND
    path = (ROOT / approval['policy_gate_receipt']).resolve()
    if not path.is_relative_to(HERE.resolve()) or sha(path.read_bytes()) != approval['policy_gate_receipt_sha256']:
        raise ValueError('POLICY_GATE_RECEIPT_EXTERNAL_PIN')
    receipt = load(path); B = load(HERE/'package_bindings.json')['B']
    if (receipt.get('role') != 'AUTHOR_RECOVERED_POLICY_95_GATE' or receipt.get('package_kind') != 'B'
            or receipt.get('status') != 'COMPLETED' or receipt.get('tests') != 95
            or receipt.get('zip_sha256') != B['zip_sha256'] or receipt.get('inventory_sha256') != B['inventory_sha256']
            or receipt.get('code_sha256') != B['code_sha256'] or receipt.get('actual_stop_confirmed') is not True):
        raise ValueError('B_GATE_MUST_FINISH_BEFORE_A_APPROVAL')
    required = [path.parent / n for n in ('closure.json','final_instance.json','supervisor_final.json',
                 'recovered/output/status.json','recovered/output/junit.xml','recovered/output/physics_guard.json')]
    if not {p.relative_to(ROOT).as_posix() for p in required}.issubset(receipt['raw_files']):
        raise ValueError('COMPLETE_POLICY_GATE_RAW_RECEIPTS_REQUIRED')
    for relative, wanted in receipt['raw_files'].items():
        safe_name(relative); source = (ROOT/relative).resolve()
        if not source.is_relative_to(path.parent) or sha(source.read_bytes()) != wanted:
            raise ValueError('POLICY_GATE_RECOVERED_RAW_BINDING')
    closure = load(path.parent/'closure.json')
    final = load(path.parent/'final_instance.json')
    status = load(path.parent/'recovered/output/status.json')
    cases = __import__('xml.etree.ElementTree', fromlist=['parse']).parse(path.parent/'recovered/output/junit.xml').getroot().findall('.//testcase')
    ids = [c.attrib['classname']+'::'+c.attrib['name'] for c in cases]
    if (closure.get('status') != 'COMPLETED' or closure.get('actual_stop_confirmed') is not True
            or final.get('actual_status') not in ('exited','stopped') or status.get('status') != 'PASS'
            or status.get('tests') != 95 or any(status.get(k) != 0 for k in ('failed','errors','skipped','physics_calls','gpu_calls'))
            or status.get('code_sha256') != B['code_sha256'] or status.get('protocol_sha256') != B['protocol_sha256']
            or not 0 <= status['wall_ns'] <= 120*10**9 or not 0 <= status['cpu_ns'] <= 120*10**9
            or not 0 <= status['process_tree_peak_rss_bytes'] <= 536870912
            or len(cases) != 95 or len(set(ids)) != 95
            or any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped'))):
        raise ValueError('RECOVERED_POLICY_GATE_NOT_PASSED')
    guard = load(path.parent/'recovered/output/physics_guard.json')
    if guard.get('blocked_attempts') != [] or guard.get('new_physics_calls') != 0 or guard.get('gpu_calls') != 0:
        raise ValueError('POLICY_GUARD_RAW_RESULT')
    elapsed = Decimal(str(closure['allocation_age_seconds']))
    bound = Decimal(str(closure['run_fee_upper_bound_usd']))
    if (not elapsed.is_finite() or not 0 <= elapsed <= 600 or not bound.is_finite()
            or bound != Decimal('0.25') * elapsed / 3600 or not 0 <= bound <= Decimal('0.05')):
        raise ValueError('B_FIRST_CLOCK_EXECUTION_FEE_BOUND')
    PRIOR_POLICY_FEE_BOUND = bound
    validate_B_cost_confirmation(approval, path, closure)


def validate_B_cost_confirmation(approval, policy_path, closure):
    # Explicit human review of provider evidence AFTER B has stopped; no cost receipt is minted here.
    global PRIOR_POLICY_FEE_BOUND, PRIOR_ACTUAL_POLICY_FEE
    path = (ROOT / approval['B_cost_confirmation']).resolve()
    if (path.parent != policy_path.parent or not path.is_relative_to(HERE.resolve())
            or path.is_symlink() or sha(path.read_bytes()) != approval['B_cost_confirmation_sha256']):
        raise ValueError('B_POST_STOP_COST_CONFIRMATION_EXTERNAL_PIN')
    cost = load(path)
    if (cost.get('schema') != 'B_POST_STOP_PROVIDER_EXECUTION_COST_CONFIRMATION_V1'
            or cost.get('human_confirmed') is not True or not cost.get('confirmation_reference')
            or not cost.get('human_confirmation_text') or cost.get('package_kind') != 'B'
            or cost.get('budget_protocol_sha256') != BUDGET_PROTOCOL_SHA
            or cost.get('policy_gate_receipt_sha256') != approval['policy_gate_receipt_sha256']
            or cost.get('closure_sha256') != sha((path.parent/'closure.json').read_bytes())
            or cost.get('final_instance_sha256') != sha((path.parent/'final_instance.json').read_bytes())
            or cost.get('cost_basis') != 'PROVIDER_REPORTED_EXECUTION_FEE'
            or cost.get('billing_scope') != 'EXECUTION_ONLY' or not cost.get('raw_files')):
        raise ValueError('B_ACTUAL_COST_AND_HUMAN_REVIEW_REQUIRED')
    confirmed = datetime.fromisoformat(cost['confirmed_utc'])
    closed = datetime.fromisoformat(closure['observed_utc'])
    approved = datetime.fromisoformat(approval['approved_utc'])
    if confirmed.tzinfo is None or not closed <= confirmed <= approved:
        raise ValueError('B_COST_CONFIRMATION_MUST_FOLLOW_STOP_AND_PRECEDE_A_APPROVAL')
    for relative, wanted in cost['raw_files'].items():
        safe_name(relative); source = ROOT/relative
        if (source.is_symlink() or not source.resolve().is_relative_to(path.parent)
                or not source.is_file() or sha(source.read_bytes()) != wanted):
            raise ValueError('B_PROVIDER_COST_RAW_EVIDENCE')
    if not isinstance(cost.get('actual_execution_fee_usd'), str):
        raise ValueError('EXPLICIT_DECIMAL_EXECUTION_FEE_REQUIRED')
    actual = Decimal(cost['actual_execution_fee_usd'])
    if not actual.is_finite() or not 0 <= actual <= Decimal('0.05'):
        raise ValueError('B_ACTUAL_EXECUTION_FEE_CAP')
    PRIOR_ACTUAL_POLICY_FEE = actual
    PRIOR_POLICY_FEE_BOUND = max(PRIOR_POLICY_FEE_BOUND, actual)


# The following four functions retain the successful A-resume bodies (format only).
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
    global PRIOR_POLICY_FEE_BOUND
    if sha(TARGET_PROTOCOL.read_bytes()) != TARGET_PROTOCOL_SHA:
        raise ValueError('NEW_TARGET_PROTOCOL_EXTERNAL_PIN')
    target = load(TARGET_PROTOCOL)
    prior = load(PREVIOUS_B)
    if (sha(PREVIOUS_B.read_bytes()) != target['prior_B_failed_closure_sha256']
            or prior['status'] != 'DEADLINE' or prior['actual_stop_confirmed'] is not True
            or approval.get('target_protocol_sha256') != TARGET_PROTOCOL_SHA
            or approval.get('prior_B_failed_closure_sha256') != target['prior_B_failed_closure_sha256']
            or approval.get('prior_B_failed_windows') != 1
            or approval.get('prior_local_invocation_failures') != 1
            or approval.get('preparation_fee_reserve_usd') != target['preparation_fee_reserve_usd']
            or approval.get('prior_B_fee_bound_usd') != target['prior_B_fee_bound_usd']):
        raise ValueError('PRIOR_FAILURE_AND_PREPARATION_COST_MUST_BE_RETAINED')
    PRIOR_POLICY_FEE_BOUND = Decimal(target['prior_B_fee_bound_usd']) + Decimal(target['preparation_fee_reserve_usd'])
    if PRIOR_POLICY_FEE_BOUND + 2 * Decimal('0.25') * 600 / 3600 > Decimal('0.10'):
        raise ValueError('PREVIOUS_COST_PLUS_TWO_FULL_WINDOWS_EXCEEDS_CAMPAIGN')
    seal = load(HERE / 'transport_seal.json')
    for name, wanted in seal['files'].items():
        safe_name(name)
        if sha((HERE / name).read_bytes()) != wanted:
            raise ValueError('ADMIN_TRANSPORT_SEAL:' + name)
    if sha(ORIGINAL_SCOPE.read_bytes()) != SCOPE_HASH:
        raise ValueError('FROZEN_PREPARATION_SCOPE_CHANGED')
    if sha((HERE.parent/'budget_protocol.json').read_bytes()) != BUDGET_PROTOCOL_SHA:
        raise ValueError('SEALED_BUDGET_SUPPLEMENT_CHANGED')
    # No approval is minted by the controller. Template false is rejected before ANY API/SSH.
    if (approval.get('schema') != 'EXACT_TARGET_54988176_B_ONLY_HUMAN_APPROVAL_V1'
            or approval.get('explicit_user_approval') is not True
            or approval.get('new_window_separately_authorized') is not True
            or approval.get('restart_exact_instance_authorized') is not True
            or approval.get('exclusive') is not True
            or not approval.get('approval_reference') or not approval.get('human_approval_text')
            or approval.get('prior_failed_attempts') != 3
            or approval.get('prior_closed_window_sha256') != sha(PRIOR.read_bytes())
            or approval.get('transport_seal_sha256') != sha((HERE / 'transport_seal.json').read_bytes())
            or approval.get('scope_protocol_sha256') != SCOPE_HASH
            or approval.get('budget_protocol_sha256') != BUDGET_PROTOCOL_SHA
            or approval.get('previous_transport_seal_sha256') != 'e40e3d59d7ee17685631b2a93d96e34d510bfe49779d98b8a1a42fcb6501e802'
            or approval.get('closed_failed_gate_sha256') != sha(FAILED_GATE.read_bytes())
            or approval.get('prior_tablet_gate_attempts') != 1):
        raise ValueError('NEW_WINDOW_EXPLICIT_HUMAN_APPROVAL_REQUIRED')
    fixed = dict(instance_id=54988176, machine_id=150665, country='ES', ssh_host='188.245.20.75', ssh_port=40470,
                 api_ssh_host='ssh5.vast.ai', api_ssh_port=23876, runtime='/usr/bin/python3',
                 scope='OFFLINE_ONLY', code_sha256=CODE, protocol_sha256=PROTO, zip_sha256=ZIP_HASH,
                 allocation_seconds=600, compute_seconds=120, recovery_deadline_seconds=420,
                 aggregate_cpu_seconds=120, cpu_affinity_count=1, memory_bytes=536870912,
                 stop_confirmation_seconds=180, hourly_cap_usd='0.25', total_cap_usd='0.05',
                 campaign_total_cap_usd='0.10',
                 physics_calls=0, gpu_calls=0, expected_tests=EXPECTED,
                 package_kind=KIND, inventory_sha256=INVENTORY_HASH, package_entries=SPEC['entries'])
    if any(approval.get(k) != v for k, v in fixed.items()):
        raise ValueError('APPROVED_SCOPE_BINDING')
    run_id = approval.get('run_id', '')
    if not re.fullmatch(r'[a-z0-9_]{8,48}', run_id):
        raise ValueError('EXCLUSIVE_RUN_ID_REQUIRED')
    stamp = datetime.fromisoformat(approval['approved_utc'])
    expires = datetime.fromisoformat(approval['expires_utc'])
    now = datetime.now(timezone.utc)
    if stamp.tzinfo is None or expires.tzinfo is None or not stamp <= now < expires:
        raise ValueError('FRESH_APPROVAL_TIME_REQUIRED')
    for name, wanted in (('code_seal.json', FIRST_CODE), ('protocol.json', FIRST_PROTO)):
        if sha((ROOT / 'experiments/adaptive_experience_tablet_v0' / name).read_bytes()) != wanted:
            raise ValueError('SEALED_HEADER_DRIFT')
    checks = []
    for name in ('protocol_seal.json', 'preservation_manifest.json', 'code_seal.json'):
        manifest = load(ROOT / 'experiments/adaptive_experience_tablet_v0' / name)
        for rel, wanted in manifest['files'].items():
            safe_name(rel)
            if sha((ROOT / rel).read_bytes()) != wanted:
                raise ValueError('LOCAL_RAW_SOURCE:' + rel)
        checks.append(dict(manifest=name, files=len(manifest['files']), mismatches=[]))
    if sha(SOURCE.read_bytes()) != ZIP_HASH:
        raise ValueError('SEALED_SOURCE_ZIP')
    checks.append(verify_local_package())
    if KIND == 'A': validate_policy_receipt(approval)
    return checks


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
        # A-resume argv dispatch retained: no PowerShell/cmd shell builds remote Python.
        self.ssh_argv = ['ssh', '-T', '-i', self.key, '-p', str(approval['ssh_port']), '-o', 'BatchMode=yes',
                         '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
                         '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
                         'root@' + approval['ssh_host']]

    def age(self):
        if self.start_ns is None:
            return 0
        mono = (time.monotonic_ns() - self.start_ns) / 1e9
        wall = (datetime.now(timezone.utc) - datetime.fromisoformat(self.started_utc)).total_seconds()
        if abs(mono - wall) > 2:
            raise ValueError('ALLOCATION_CLOCK_DRIFT')
        return max(mono, wall)

    def emit(self, event, **kw):
        obj = dict(event=event, observed_utc=utc(), monotonic_ns=time.monotonic_ns(), **kw)
        with (self.out / 'events.jsonl').open('ab') as f:
            f.write(canonical(obj) + b'\n'); f.flush(); os.fsync(f.fileno())

    def run(self, argv, name, timeout, input=None):
        self.index += 1
        prefix = self.out / ('%03d_' % self.index + name)
        with prefix.with_suffix('.stdout').open('xb') as a, prefix.with_suffix('.stderr').open('xb') as b:
            try:
                result = subprocess.run(argv, input=input, stdout=a, stderr=b, timeout=timeout)
            except BaseException as exc:
                self.emit('COMMAND_EXCEPTION', phase=name, error=repr(exc), log_prefix=str(prefix))
                raise
        self.emit('TRANSPORT_EXIT', phase=name, returncode=result.returncode, log_prefix=str(prefix))
        if result.returncode:
            raise RuntimeError('ADMIN_PHASE_FAILED:' + name)
        return prefix.with_suffix('.stdout').read_bytes()

    def show(self, name, timeout=12):
        raw = self.run([self.cli, '--raw', '--retry', '1', 'show', 'instance', str(self.auth['instance_id'])], name, timeout)
        record = json.loads(raw)
        country = record.get('country') or str(record.get('geolocation', '')).rsplit(',', 1)[-1].strip()
        if (record.get('id') != self.auth['instance_id'] or record.get('machine_id') != self.auth['machine_id']
                or country != self.auth['country'] or record.get('ssh_host') != self.auth['api_ssh_host']
                or record.get('ssh_port') != self.auth['api_ssh_port']
                or record.get('public_ipaddr') != self.auth['ssh_host']
                or str(self.auth['ssh_port']) not in {p.get('HostPort') for p in record.get('ports', {}).get('22/tcp', [])}):
            raise ValueError('EXACT_INSTANCE_API_BINDING')
        rate = Decimal(str(record['dph_total']))
        if not rate.is_finite() or not 0 <= rate <= Decimal('0.25') or rate * 600 / 3600 > Decimal('0.05'):
            raise ValueError('PRICE_CAP')
        # Reserve A's full 600s at the approved maximum, not an old/current cheaper quote.
        if PRIOR_POLICY_FEE_BOUND + Decimal('0.25') * 600 / 3600 > Decimal('0.10'):
            raise ValueError('B_PLUS_A_EXECUTION_FEE_CAP_REQUIRES_REMAINING_RESERVE')
        return record

    def control(self, required_seconds):
        # Generic guardian has NO A heartbeat. Check supervisor/process receipt AND fresh API.
        if (self.supervisor is None or self.supervisor.poll() is not None
                or (self.out / 'completion.json').exists() or (self.out / 'supervisor_final.json').exists()
                or (self.out / 'guardian/final.json').exists()):
            raise RuntimeError('OUTSIDE_STOP_CONTROL_LOST')
        handoff = self.handoff()
        if self.age() + required_seconds + 12 >= handoff:
            raise TimeoutError('ABSOLUTE_PHASE_TIME_RESERVE')
        observed = self.show('phase_control')
        if observed['actual_status'] != 'running':
            raise ValueError('INSTANCE_NOT_RUNNING')
        if self.armed is not None:
            current = load(self.out / 'guardian/armed.json')
            if canonical(current) != canonical(self.armed):
                raise ValueError('OUTSIDE_ARM_RECEIPT_CHANGED')

    def handoff(self):
        if self.armed is None: return 400
        armed_age = (datetime.fromisoformat(self.armed['armed_utc']) - datetime.fromisoformat(self.started_utc)).total_seconds()
        return min(400, armed_age + self.armed['deadline_seconds'])

    def py(self, script_name, args, name, timeout=30):
        self.control(timeout)
        script = (HERE / script_name).read_bytes()
        # Linux shell sees shlex-quoted tokens only; Python source travels on SSH stdin.
        command = shlex.join([VENV if script_name != 'guest_probe.py' else 'python3', '-B', '-', *map(str, args)])
        return self.run([*self.ssh_argv, command], name, timeout, input=script)

    def upload(self, local, remote_name, name, timeout=35):
        safe_name(remote_name)
        self.control(timeout)
        # Preserve successful A-resume SCP legacy mode. All destinations live in a new exclusive root.
        command = ['scp', '-O', '-i', self.key, '-P', str(self.auth['ssh_port']), '-o', 'BatchMode=yes',
                   '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
                   str(local), 'root@' + self.auth['ssh_host'] + ':' + self.guest + '/' + remote_name]
        self.run(command, name, timeout)

    def recover(self):
        if not self.remote_created or not self.identity_verified:
            return
        write(self.out / 'recovery_attempted.json', dict(reason='RAW_EVIDENCE_RECOVERY', observed_utc=utc()))
        pack = json.loads(self.py('guest_recover.py', [self.guest, self.auth['instance_id'], CODE, self.auth['run_id']],
                                 'package_evidence', timeout=25))
        self.control(35)
        dest = self.out / 'evidence.zip'
        if dest.exists():
            raise ValueError('RECOVERY_DESTINATION_EXISTS')
        argv = ['scp', '-O', '-i', self.key, '-P', str(self.auth['ssh_port']), '-o', 'BatchMode=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
                'root@' + self.auth['ssh_host'] + ':' + self.guest + '/evidence.zip', str(dest)]
        self.run(argv, 'raw_evidence_download', 35)
        if sha(dest.read_bytes()) != pack['sha256']:
            raise ValueError('RECOVERED_ZIP_HASH')
        recovered = self.out / 'recovered'
        with zipfile.ZipFile(dest) as z:
            names = z.namelist()
            manifest = json.loads(z.read('evidence_manifest.json'))
            if (len(names) != len(set(names)) or len(names) != len({n.casefold() for n in names}) or z.testzip() is not None
                    or manifest.get('instance_id') != self.auth['instance_id'] or manifest.get('code_sha256') != CODE
                    or manifest.get('run_id') != self.auth['run_id'] or len(manifest['files']) != pack['files']
                    or set(names) != set(manifest['files']) | {'evidence_manifest.json'}):
                raise ValueError('RAW_RECOVERY_MANIFEST_OR_FILE_SET')
            # Validate ALL entries before writing even one extracted output.
            for item in z.infolist():
                safe_name(item.filename)
                if item.is_dir() or item.flag_bits & 1 or stat.S_IFMT(item.external_attr >> 16) not in (0, stat.S_IFREG):
                    raise ValueError('RECOVERY_NON_REGULAR_MEMBER')
            for name, wanted in manifest['files'].items():
                if sha(z.read(name)) != wanted:
                    raise ValueError('RAW_RECOVERY_HASH:' + name)
            recovered.mkdir(exist_ok=False)
            for name in names:
                path = recovered / name
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as f:
                    f.write(z.read(name))
        write(self.out / 'recovery_verified.json', dict(files=pack['files'], zip_sha256=pack['sha256'],
              all_raw_hashes_match=True))
        self.recovered = True

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

    def execute(self):
        failure = None
        gate_rc = None
        trigger = 'FAILED'
        final = None
        try:
            initial = self.show('initial_instance')
            write(self.out / 'initial_instance.json', initial)
            if initial['actual_status'] not in ('exited', 'stopped'):
                raise ValueError('EXCLUSIVE_STOPPED_INSTANCE_REQUIRED')
            if datetime.now(timezone.utc) >= datetime.fromisoformat(self.auth['expires_utc']):
                raise ValueError('APPROVAL_EXPIRED_BEFORE_ALLOCATION')
            self.start_ns = time.monotonic_ns()
            self.started_utc = utc()
            write(self.out / 'allocation_start.json', dict(monotonic_ns=self.start_ns, observed_utc=self.started_utc,
                  prior_failed_attempts=3, prior_closed_window_sha256=self.auth['prior_closed_window_sha256'],
                  new_window_separately_authorized=True, provenance='BEFORE_AUTHORIZED_RESTART; NEVER_RESET'))
            lease = dict(scope='STOP_CONTROL_ONLY', exclusive=True, explicit_user_approval=True,
                         approval_reference=self.auth['approval_reference'], prior_failed_attempts=3,
                         new_window_separately_authorized=True, instance_id=self.auth['instance_id'],
                         machine_id=self.auth['machine_id'], country=self.auth['country'],
                         allocation_monotonic_ns=self.start_ns, allocation_start_utc=self.started_utc,
                         guardian_sha256=sha(GUARD.read_bytes()), supervisor_sha256=sha((HERE / 'supervisor.py').read_bytes()),
                         cli=self.cli, repo_root=str(ROOT), out=str(self.out))
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
            if ready.get('lease_sha256') != sha((self.out / 'supervisor_lease.json').read_bytes()):
                raise ValueError('SUPERVISOR_READY_LEASE_HASH')
            self.owns_stop = True  # Exact stopped instance + human exclusive restart/stop scope established.
            self.run([self.cli, '--raw', '--retry', '1', 'start', 'instance', str(self.auth['instance_id'])], 'restart', 12)
            until = time.monotonic() + 45
            while time.monotonic() < until:
                host = self.show('restart_status')
                if host['actual_status'] == 'running':
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
            # Preparation has an explicit budget; don't repair anything within this paid window.
            if self.age() >= 100:
                raise TimeoutError('GUEST_PREPARATION_RESERVE')
            self.remote_created = True  # Probe may create the root then disconnect: preserve partial evidence.
            probe = json.loads(self.py('guest_probe.py', [self.auth['instance_id'], VENV, self.guest], 'guest_identity', 20))
            write(self.out / 'guest_probe.json', probe)
            if probe.get('actual_container_id') != str(self.auth['instance_id']):
                raise ValueError('OBSERVED_GUEST_ID_REQUIRED')
            self.identity_verified = True
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
            gate = json.loads(self.py('guest_gate.py', [self.guest, VENV, self.auth['instance_id'], ticket['armed_sha256'],
                             sha((self.out / 'offline_ticket.json').read_bytes())], 'offline_gate', 140))
            gate_rc = gate['returncode']
            # Always recover failures. Do not rerun tests or repackage a partially created evidence ZIP.
            self.recover()
            if gate_rc != 0:
                raise ValueError('REMOTE_OFFLINE_EXIT:' + str(gate_rc))
            self.validate_result()
            trigger = 'COMPLETED'
        except BaseException as exc:
            failure = repr(exc)
            trigger = 'DEADLINE' if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else 'FAILED'
            self.emit('CONTROLLER_STOP', reason=failure)
            if self.remote_created and self.identity_verified and not self.recovered and not (self.out / 'recovery_attempted.json').exists():
                try:
                    self.recover()
                except BaseException as recovery_error:
                    self.emit('RECOVERY_FAILED', error=repr(recovery_error))
        finally:
            if self.supervisor is not None:
                try:
                    write(self.out / 'completion.json', dict(trigger=trigger, reason=failure, gate_returncode=gate_rc,
                                                            recovered=self.recovered, observed_utc=utc()))
                except FileExistsError:
                    trigger = 'DEADLINE' if self.age() >= self.handoff() else 'FAILED'
                except BaseException as exc:
                    trigger = 'FAILED'
                    failure = 'COMPLETION_MARKER_WRITE_FAILED:' + repr(exc)
                try:
                    self.supervisor.wait(timeout=max(.1, 592 - self.age()))
                except BaseException as exc:
                    self.emit('SUPERVISOR_WAIT_UNCONFIRMED', error=repr(exc))
            if self.owns_stop:
                try:
                    final = self.show('final_instance', timeout=max(.1, min(8, 600 - self.age())))
                    write(self.out / 'final_instance.json', final)
                except BaseException as exc:
                    self.emit('FINAL_STATUS_UNCONFIRMED', error=repr(exc))
            try:
                stop = load(self.out / 'supervisor_final.json') if (self.out / 'supervisor_final.json').exists() else None
            except BaseException as exc:
                stop = None
                failure = 'SUPERVISOR_RECEIPT_UNREADABLE:' + repr(exc)
            confirmed = bool(stop and stop['result']['status'] == 'STOP_CONFIRMED' and final
                             and final['actual_status'] in ('exited', 'stopped'))
            final_age = self.age() if self.start_ns is not None else 0
            write(self.out / 'closure.json', dict(trigger=trigger, reason=failure, gate_returncode=gate_rc,
                  recovery_verified=self.recovered, actual_stop_confirmed=confirmed, allocation_start_utc=self.started_utc,
                  prior_failed_attempts=3, auto_retry=False, no_new_physics=True, gpu_calls=0, local_dynamic_tests=0,
                  prior_tablet_gate_attempts=1, closed_failed_gate_sha256=sha(FAILED_GATE.read_bytes()),
                  package_kind=KIND, zip_sha256=ZIP_HASH, inventory_sha256=INVENTORY_HASH,
                  allocation_age_seconds=str(final_age), run_fee_upper_bound_usd=str(Decimal('0.25')*Decimal(str(final_age))/3600),
                  prior_policy_run_fee_bound_usd=str(PRIOR_POLICY_FEE_BOUND), campaign_total_cap_usd='0.10',
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
                      raw_files={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in paths}))
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
