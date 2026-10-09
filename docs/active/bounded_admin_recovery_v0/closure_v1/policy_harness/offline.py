"""REMOTE Linux only: exact sealed 95-case administrative fixture, one run.

No signer, rental/restart client, physics code or retry. Resources include this
process and its pytest child. Ticket/guardian remain outside supplied authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import signal
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent


def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def read(path): return json.loads(Path(path).read_bytes())
def write(path, obj):
    with Path(path).open('xb') as f: f.write(canonical(obj))


def check_source():
    seal_raw = (HERE / 'source_seal.json').read_bytes()
    for name, wanted in json.loads(seal_raw)['files'].items():
        if ('\\' in name or ':' in name or PurePosixPath(name).is_absolute()
                or any(p in ('', '.', '..') for p in name.split('/'))):
            raise ValueError('B_SOURCE_PATH')
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()) or sha(path.read_bytes()) != wanted:
            raise ValueError('B_SOURCE_RAW_HASH:' + name)
    return sha(seal_raw), sha((HERE / 'protocol.json').read_bytes())


def authorize(ticket, armed, code, protocol):
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(ticket['allocation_start_utc'])).total_seconds()
    arm_age = (datetime.fromisoformat(armed['armed_utc']) - datetime.fromisoformat(ticket['allocation_start_utc'])).total_seconds()
    rate = Decimal(str(armed['hourly_usd']))
    guardian = read(HERE / 'protocol.json')['guardian_sha256']
    if (platform.system() != 'Linux' or ticket.get('gate') != 'BOUNDED_ADMIN_RECOVERY_POLICY_95_V0'
            or ticket.get('package_kind') != 'B' or ticket.get('scope') != 'OFFLINE_ONLY'
            or ticket.get('explicit_user_approval') is not True or not ticket.get('approval_reference')
            or ticket.get('code_sha256') != code or ticket.get('protocol_sha256') != protocol
            or ticket.get('expected_tests') != 95 or ticket.get('allocation_seconds') != 600
            or ticket.get('physics_calls') != 0 or ticket.get('gpu_calls') != 0
            or str(ticket.get('instance_id')) != os.environ.get('CONTAINER_ID')
            or any(ticket.get(k) != armed.get(k) for k in ('instance_id', 'machine_id', 'country', 'approval_reference'))
            or armed.get('status') != 'ARMED' or armed.get('outside_guest') is not True
            or ticket.get('armed_sha256') != sha(canonical(armed)) or armed.get('confirmation_seconds') != 180
            or armed.get('guardian_sha256') != guardian
            or type(armed.get('deadline_seconds')) is not int or not 1 <= armed['deadline_seconds'] <= 420
            or not 0 <= age < 200 or not 0 <= arm_age <= age
            or arm_age + armed['deadline_seconds'] + 180 > 600
            or age + 120 + 96 > arm_age + armed['deadline_seconds']
            or not rate.is_finite() or not 0 <= rate <= Decimal('0.25') or rate * 600 / 3600 > Decimal('0.05')):
        raise ValueError('B_FRESH_EXTERNAL_AUTHORITY_AND_BUDGET_REQUIRED')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authorization', type=Path, required=True)
    parser.add_argument('--armed', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    code, protocol = check_source(); ticket = read(args.authorization); armed = read(args.armed)
    authorize(ticket, armed, code, protocol)
    args.out.mkdir(exist_ok=False); write(args.out / 'authorization_used.json', ticket)
    import resource
    import psutil
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    started = time.monotonic_ns(); proc = None; peak = 0; stop = threading.Event(); violations = []
    cases = []

    def usage():
        own = resource.getrusage(resource.RUSAGE_SELF)
        dead = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = sum(Decimal(str(v)) for v in (own.ru_utime, own.ru_stime, dead.ru_utime, dead.ru_stime))
        rss = 0
        for child in [psutil.Process(), *psutil.Process().children(recursive=True)]:
            try:
                rss += child.memory_info().rss
                if child.pid != os.getpid():
                    t = child.cpu_times(); cpu += Decimal(str(t.user)) + Decimal(str(t.system))
            except psutil.NoSuchProcess: pass
        return int((cpu * 10**9).to_integral_value(rounding=ROUND_CEILING)), rss

    def check_limits():
        nonlocal peak
        cpu, rss = usage(); peak = max(peak, rss)
        if (time.monotonic_ns() - started > 120 * 10**9 or cpu > 120 * 10**9 or rss > 536870912
                or sha(canonical(read(args.armed))) != sha(canonical(armed))):
            raise ValueError('B_RESOURCE_OR_ARM_STOP')

    def monitor():
        while not stop.is_set():
            try:
                check_limits()
            except BaseException as exc:
                violations.append(repr(exc))
                if proc is not None and proc.poll() is None:
                    try: os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                return
            if stop.wait(.05): return

    watch = threading.Thread(target=monitor, daemon=True)
    reason = None; returncode = None
    try:
        p = read(HERE / 'protocol.json')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                   ADMIN_POLICY_GUARD_REPORT=str(args.out.resolve() / 'physics_guard.json'))
        for key in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTHONPATH'): env.pop(key, None)
        env['PYTHONPATH'] = str(ROOT)
        with (args.out / 'tests.log').open('xb') as log:
            check_limits()
            proc = subprocess.Popen([sys.executable, '-B', '-m', 'pytest', p['test_file'], '-q',
                   '-c', str(HERE / 'pytest.ini'), '--confcutdir=' + str(ROOT),
                   '-p', 'no:cacheprovider', '-p', 'admin_policy.guard',
                   '--junitxml=' + str(args.out.resolve() / 'junit.xml')], cwd=ROOT, env=env,
                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            watch.start()
            returncode = proc.wait(timeout=95)
        cases = ET.parse(args.out / 'junit.xml').getroot().findall('.//testcase')
        ids = [c.attrib['classname'] + '::' + c.attrib['name'] for c in cases]
        guard = read(args.out / 'physics_guard.json')
        if (returncode != 0 or len(cases) != 95 or len(set(ids)) != 95
                or any(c.find(tag) is not None for c in cases for tag in ('failure', 'error', 'skipped'))
                or guard.get('blocked_attempts') != [] or violations):
            raise ValueError('EXACT_95_ADMIN_POLICY_GATE_STOP')
        check_source()
    except BaseException as error:
        reason = repr(error)
    finally:
        if proc is not None and proc.poll() is None:
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            proc.wait(timeout=5)
        stop.set()
        if watch.is_alive(): watch.join(timeout=1)
        cpu, rss = usage(); peak = max(peak, rss); wall = time.monotonic_ns() - started
        if violations or wall > 120 * 10**9 or cpu > 120 * 10**9 or peak > 536870912:
            reason = reason or 'B_RESOURCE_CAP_STOP'
        status = dict(status='PASS' if reason is None else 'STOP', reason=reason, tests=len(cases),
                      failed=sum(c.find('failure') is not None for c in cases),
                      errors=sum(c.find('error') is not None for c in cases),
                      skipped=sum(c.find('skipped') is not None for c in cases),
                      wall_ns=wall, cpu_ns=cpu, process_tree_peak_rss_bytes=peak,
                      code_sha256=code, protocol_sha256=protocol, physics_calls=0, gpu_calls=0,
                      benchmark_complete=False, package_kind='B', pytest_returncode=returncode)
        write(args.out / 'status.json', status)
    return 0 if reason is None else 2


if __name__ == '__main__': raise SystemExit(main())
