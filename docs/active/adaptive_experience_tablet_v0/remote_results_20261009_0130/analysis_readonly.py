"""Post-stop stdlib evidence analysis; no project import/tests/physics or write API."""
import collections
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/run_approved_20261009_0130'


def read(path):
    return json.loads(path.read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


tree = ET.parse(RUN / 'recovered/output/junit.xml')
suite = tree.getroot().find('testsuite')
cases = tree.getroot().findall('.//testcase')
counts = dict(passed=0, failed=0, errors=0, skipped=0)
modules = collections.defaultdict(collections.Counter)
missing = collections.Counter()
for case in cases:
    kind = 'passed'
    for tag, label in (('failure', 'failed'), ('error', 'errors'), ('skipped', 'skipped')):
        node = case.find(tag)
        if node is not None:
            kind = label
            if label in ('failed', 'errors'):
                match = re.search(r"No such file or directory: '([^']+)'", node.get('message', ''))
                missing[(match.group(1).split('/source/', 1)[1] if match else node.get('message', ''))] += 1
            break
    counts[kind] += 1
    modules[case.get('classname')][kind] += 1
assert len(cases) == 320 and counts == dict(passed=239, failed=50, errors=31, skipped=0)
receipt = read(RUN / 'recovery_verified.json')
assert sha((RUN / 'evidence.zip').read_bytes()) == receipt['zip_sha256']
with zipfile.ZipFile(RUN / 'evidence.zip') as z:
    manifest = json.loads(z.read('evidence_manifest.json'))
    assert len(z.namelist()) == len(set(z.namelist()))
    assert set(z.namelist()) == set(manifest['files']) | {'evidence_manifest.json'}
    assert z.testzip() is None
    for name, wanted in manifest['files'].items():
        assert sha(z.read(name)) == wanted
        assert sha((RUN / 'recovered' / name).read_bytes()) == wanted
assert len(manifest['files']) == receipt['files'] == 10
checks = []
for name in ('protocol_seal.json', 'preservation_manifest.json', 'code_seal.json'):
    path = ROOT / 'experiments/adaptive_experience_tablet_v0' / name
    body = read(path)
    bad = [n for n, wanted in body['files'].items() if sha((ROOT / n).read_bytes()) != wanted]
    assert not bad
    checks.append(dict(manifest=name, files=len(body['files']), mismatches=bad, manifest_sha256=sha(path.read_bytes())))
admin = ROOT / 'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009'
seal = read(admin / 'transport_seal_v3.json')
assert all(sha((admin / n).read_bytes()) == wanted for n, wanted in seal['files'].items())
package_path = ROOT / 'docs/active/adaptive_experience_tablet_v0/source_7b264a42/package_manifest.json'
package = read(package_path)
assert sha((ROOT / package['archive']).read_bytes()) == package['zip_sha256']
source = read(RUN / 'source_upload_verified.json')
guard = read(RUN / 'recovered/output/physics_guard.json')
assert guard['new_physics_calls'] == guard['gpu_calls'] == 0 and guard['blocked_attempts'] == []
events = [json.loads(line) for line in (RUN / 'events.jsonl').read_bytes().splitlines()]
origin = read(RUN / 'allocation_start.json')
last = next(e for e in reversed(events) if e.get('phase') == 'final_instance')
wall = Decimal(str((datetime.fromisoformat(last['observed_utc']) - datetime.fromisoformat(origin['observed_utc'])).total_seconds()))
mono = Decimal(last['monotonic_ns'] - origin['monotonic_ns']) / Decimal(10**9)
host = read(RUN / 'initial_instance.json')
rate = Decimal(str(host['dph_total']))
external = read(RUN / 'supervisor_final.json')
assert external['result']['status'] == 'STOP_CONFIRMED' and external['result']['instance_id'] == 54815136
cli = 'C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe'
fresh = subprocess.run([cli, '--raw', '--retry', '1', 'show', 'instance', '54815136'], capture_output=True, timeout=15)
with (OUT / 'fresh_final_instance.stdout').open('xb') as f:
    f.write(fresh.stdout)
with (OUT / 'fresh_final_instance.stderr').open('xb') as f:
    f.write(fresh.stderr)
if fresh.returncode:
    raise RuntimeError('FRESH_FINAL_API_READ_FAILED')
actual = json.loads(fresh.stdout)
assert actual['id'] == 54815136 and actual['machine_id'] == 56006
assert actual['actual_status'] in ('exited', 'stopped')
write('fresh_final_instance.json', {k: actual.get(k) for k in ('id', 'machine_id', 'actual_status', 'intended_status', 'geolocation', 'dph_total', 'ssh_host', 'ssh_port')})
report = dict(status='REMOTE_TEST_GATE_FAILED; NOT_VALIDATED', observed_utc=datetime.now(timezone.utc).isoformat(),
    tests=len(cases), counts=counts, pytest_log_summary_seconds='12.70', junit_suite_seconds=suite.get('time'),
    by_module={k: dict(v) for k, v in modules.items()}, missing_paths=[dict(relative=n, cases=c,
        exists_in_local_checkout=(ROOT / n).is_file(), included_in_source_zip=n in package['files'],
        raw_sha256=sha((ROOT / n).read_bytes()) if (ROOT / n).is_file() else None) for n, c in missing.items()],
    benchmark='NOT_EXECUTED', aggregate_gate_cpu='NOT_RECORDED_IN_STOP_STATUS',
    gate_wall_and_memory_metrics='NOT_RECORDED_IN_STOP_STATUS', physics_guard=guard, sealed_checks=checks,
    transport_seal_sha256=sha((admin / 'transport_seal_v3.json').read_bytes()), source_zip_sha256=package['zip_sha256'],
    runtime=source, recovery=receipt, prior_administrative_failures=3, new_test_attempts=1,
    auto_retry=False, on_site_code_changes=False, local_dynamic_tests=0, github_push=False, master_merge=False,
    termination=dict(external_stop_confirmed=True, external_result=external['result'],
        controller_actual=read(RUN / 'final_instance.json')['actual_status'], fresh_actual=actual['actual_status']),
    timing=dict(allocation_start_utc=origin['observed_utc'], controller_final_api_utc=last['observed_utc'],
        wall_seconds=str(wall), monotonic_seconds=str(mono), conservative_elapsed_seconds=str(max(wall, mono))),
    cost=dict(hourly_usd=str(rate), running_rate_window_estimate_usd=str(rate * max(wall, mono) / 3600),
        cap_usd='0.05', basis='RUNNING_RATE_WINDOW_ONLY; NOT_INVOICE; EXCLUDES_UNRELATED_OLD_ALLOCATION_AND_SEPARATE_FEES'),
    classification=dict(implemented='SEALED_SOURCE_UNCHANGED', tested='320 EXECUTED; FAILURE STOP PATH OBSERVED',
        independently_verified='NO_NEW_INDEPENDENT_REVIEW_RECEIPT', unconfirmed='BENCHMARK_AND_FULL_OFFLINE_FUNCTION_VALIDATION; COMPLETED/DEADLINE CONTROL PATHS'))
write('author_analysis.json', report)
print(json.dumps({k: report[k] for k in ('status', 'tests', 'counts', 'missing_paths', 'recovery', 'timing', 'cost')}, ensure_ascii=True))
