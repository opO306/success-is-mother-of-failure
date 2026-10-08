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
ROOT = HERE.parents[3]
CODE = '18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09'
PROTO = 'f03bc97a79e1a22ece4964270032d8829f7a208e961c09806c8f7bc10351013c'
ZIP_HASH = 'ea24dd1ff2b70d4cfff56d0af9fa6d5b49f280322160189a9b132d0e0a480392'
SOURCE = ROOT / 'docs/active/adaptive_experience_tablet_v0/source_7b264a42/source_7b264a42.zip'
GUARD = ROOT / 'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
PRIOR = ROOT / 'docs/active/adaptive_experience_tablet_v0/remote_20261009_attempt3/closure.json'
VENV = '/workspace/rlp_A_8d4115e5/venv/bin/python'


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
    if (not name or '\\' in name or ':' in name or PurePosixPath(name).is_absolute()
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('ARCHIVE_PATH_SCOPE:' + name)


def local_preflight(approval):
    seal = load(HERE / 'transport_seal_v3.json')
    for name, wanted in seal['files'].items():
        safe_name(name)
        if sha((HERE / name).read_bytes()) != wanted:
            raise ValueError('ADMIN_TRANSPORT_SEAL:' + name)
    # No approval is minted by the controller. Template false is rejected before ANY API/SSH.
    if (approval.get('schema') != 'TABLET_NEW_WINDOW_HUMAN_APPROVAL'
            or approval.get('explicit_user_approval') is not True
            or approval.get('new_window_separately_authorized') is not True
            or approval.get('restart_exact_instance_authorized') is not True
            or approval.get('exclusive') is not True
            or not approval.get('approval_reference') or not approval.get('human_approval_text')
            or approval.get('prior_failed_attempts') != 3
            or approval.get('prior_closed_window_sha256') != sha(PRIOR.read_bytes())
            or approval.get('transport_seal_sha256') != sha((HERE / 'transport_seal_v3.json').read_bytes())):
        raise ValueError('NEW_WINDOW_EXPLICIT_HUMAN_APPROVAL_REQUIRED')
    fixed = dict(instance_id=54815136, machine_id=56006, country='FR', ssh_host='ssh9.vast.ai', ssh_port=26992,
                 scope='OFFLINE_ONLY', code_sha256=CODE, protocol_sha256=PROTO, zip_sha256=ZIP_HASH,
                 allocation_seconds=600, compute_seconds=120, recovery_deadline_seconds=420,
                 stop_confirmation_seconds=180, hourly_cap_usd='0.25', total_cap_usd='0.05',
                 physics_calls=0, gpu_calls=0, expected_tests=320)
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
    for name, wanted in (('code_seal.json', CODE), ('protocol.json', PROTO)):
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
    code = load(ROOT / 'experiments/adaptive_experience_tablet_v0/code_seal.json')
    seal_name = 'experiments/adaptive_experience_tablet_v0/code_seal.json'
    with zipfile.ZipFile(SOURCE) as z:
        if (len(z.namelist()) != 813 or len(set(z.namelist())) != 813
                or set(z.namelist()) != set(code['files']) | {seal_name} or z.testzip() is not None):
            raise ValueError('LOCAL_PACKAGE_SCOPE')
        for name, wanted in dict(code['files'], **{seal_name: CODE}).items():
            if sha(z.read(name)) != wanted:
                raise ValueError('LOCAL_PACKAGE_RAW_HASH:' + name)
    return checks


class Transport:
    def __init__(self, approval, cli, key, out):
        self.auth, self.cli, self.key, self.out = approval, str(cli), str(key), out
        self.guest = '/workspace/tablet_v0_' + approval['run_id']
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
                or country != self.auth['country'] or record.get('ssh_host') != self.auth['ssh_host']
                or record.get('ssh_port') != self.auth['ssh_port']):
            raise ValueError('EXACT_INSTANCE_API_BINDING')
        rate = Decimal(str(record['dph_total']))
        if not rate.is_finite() or not 0 <= rate <= Decimal('0.25') or rate * 600 / 3600 > Decimal('0.05'):
            raise ValueError('PRICE_CAP')
        return record

    def control(self, required_seconds):
        # Generic guardian has NO A heartbeat. Check supervisor/process receipt AND fresh API.
        if (self.supervisor is None or self.supervisor.poll() is not None
                or (self.out / 'completion.json').exists() or (self.out / 'supervisor_final.json').exists()
                or (self.out / 'guardian/final.json').exists()):
            raise RuntimeError('OUTSIDE_STOP_CONTROL_LOST')
        if self.age() + required_seconds + 12 >= 400:
            raise TimeoutError('ABSOLUTE_PHASE_TIME_RESERVE')
        observed = self.show('phase_control')
        if observed['actual_status'] != 'running':
            raise ValueError('INSTANCE_NOT_RUNNING')
        if self.armed is not None:
            current = load(self.out / 'guardian/armed.json')
            if canonical(current) != canonical(self.armed):
                raise ValueError('OUTSIDE_ARM_RECEIPT_CHANGED')

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
            if (len(names) != len(set(names)) or z.testzip() is not None
                    or manifest.get('instance_id') != self.auth['instance_id'] or manifest.get('code_sha256') != CODE
                    or manifest.get('run_id') != self.auth['run_id'] or len(manifest['files']) != pack['files']
                    or set(names) != set(manifest['files']) | {'evidence_manifest.json'}):
                raise ValueError('RAW_RECOVERY_MANIFEST_OR_FILE_SET')
            # Validate ALL entries before writing even one extracted output.
            for item in z.infolist():
                safe_name(item.filename)
                if item.is_dir() or stat.S_ISLNK(item.external_attr >> 16):
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
        if (status.get('status') != 'PASS' or status.get('tests') != 320
                or any(status.get(k) != 0 for k in ('failed', 'errors', 'skipped', 'physics_calls', 'gpu_calls'))
                or status.get('code_sha256') != CODE or status.get('protocol_sha256') != PROTO
                or status.get('benchmark_complete') is not True):
            raise ValueError('EXACT_320_OFFLINE_GATE_NOT_PASSED')
        import xml.etree.ElementTree as ET
        cases = ET.parse(data / 'output/junit.xml').getroot().findall('.//testcase')
        if len(cases) != 320 or any(c.find(tag) is not None for c in cases for tag in ('failure', 'error', 'skipped')):
            raise ValueError('RECOVERED_JUNIT_GATE')
        guard = load(data / 'output/physics_guard.json')
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
            verified = json.loads(self.py('guest_source_verify.py', [self.guest, ZIP_HASH, CODE, PROTO], 'source_verify', 25))
            write(self.out / 'source_upload_verified.json', verified)
            ticket = dict(gate='ADAPTIVE_EXPERIENCE_TABLET_CPU_ROUTE_V0', scope='OFFLINE_ONLY', explicit_user_approval=True,
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
                    trigger = 'FAILED'  # Absolute watchdog already handed off: cannot promote completion.
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
            write(self.out / 'closure.json', dict(trigger=trigger, reason=failure, gate_returncode=gate_rc,
                  recovery_verified=self.recovered, actual_stop_confirmed=confirmed, allocation_start_utc=self.started_utc,
                  prior_failed_attempts=3, auto_retry=False, no_new_physics=True, gpu_calls=0, local_dynamic_tests=0,
                  status='COMPLETED' if trigger == 'COMPLETED' and confirmed else 'UNRESOLVED'))
        return 0 if trigger == 'COMPLETED' and confirmed else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--approval', required=True, type=Path)
    parser.add_argument('--cli', required=True, type=Path)
    parser.add_argument('--key', required=True, type=Path)
    args = parser.parse_args()
    approval = load(args.approval)
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
