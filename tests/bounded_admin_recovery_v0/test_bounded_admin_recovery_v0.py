"""PREPARED, NOT RUN. Synthetic administrative faults; no project/physics executor.

Receipt pins below are TEST_ONLY stand-ins for externally verified evidence.
Their existence in this fixture supplies no production approval or independence.
"""
import copy
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from experiments.bounded_admin_recovery_v0.package_gate import inspect_package
from experiments.bounded_admin_recovery_v0.planning import review_recovery, review_completion


def raw(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(path, data):
    path.write_bytes(data)
    return sha(data)


@pytest.fixture
def package(tmp_path):
    members = {'runner.py': b'# unchanged\n', 'payload.json': b'{"value":1}'}
    seal = raw({'files': {'payload.json': sha(members['payload.json'])}})
    contract = dict(schema='BOUNDED_ADMIN_PACKAGE_DEPENDENCIES_V0',
                    required_files={'runner.py': sha(members['runner.py'])},
                    runtime_manifests={'seal.json': sha(seal)})
    base = tmp_path / 'first.zip'
    with zipfile.ZipFile(base, 'w') as z:
        for name, data in members.items():
            z.writestr(name, data)
    inventory = dict(files={k: sha(v) for k, v in members.items()}, zip_sha256=sha(base.read_bytes()))
    ip = tmp_path / 'original_inventory.json'
    contract['original_inventory_sha256'] = put(ip, raw(inventory))
    contract['original_zip_sha256'] = inventory['zip_sha256']
    cp = tmp_path / 'dependencies.json'
    ch = put(cp, raw(contract))
    return dict(root=tmp_path, base=base, inventory=ip, contract=cp, contract_hash=ch,
                members=members, seal=seal)


def check(p, members=None):
    if members is None:
        return inspect_package(p['base'], p['inventory'], p['contract'], p['contract_hash'])
    candidate = p['root'] / 'candidate.zip'
    with zipfile.ZipFile(candidate, 'w') as z:
        for name, data in members.items():
            z.writestr(name, data)
    ip = p['root'] / 'candidate_inventory.json'
    h = put(ip, raw(dict(files={k: sha(v) for k, v in members.items()},
                        zip_sha256=sha(candidate.read_bytes()))))
    return inspect_package(candidate, p['inventory'], p['contract'], p['contract_hash'],
                           candidate_inventory=ip, candidate_inventory_sha256=h)


def test_missing_seal_detected_even_when_all_its_references_present(package):
    result = check(package)
    assert result['status'] == 'INCOMPLETE'
    assert result['missing'] == ['seal.json']
    assert result['execution_authorized'] is False


def test_add_exact_existing_seal_preserves_original(package):
    before = package['base'].read_bytes()
    result = check(package, dict(package['members'], **{'seal.json': package['seal']}))
    assert result['status'] == 'COMPLETE_DECLARED_ONLY'
    assert result['execution_authorized'] is False
    assert package['base'].read_bytes() == before


@pytest.mark.parametrize('fault', ['replace', 'delete', 'extra_code', 'wrong_seal', 'escape', 'absolute', 'backslash'])
def test_candidate_cannot_relax_original_or_add_unapproved_paths(package, fault):
    members = dict(package['members'], **{'seal.json': package['seal']})
    if fault == 'replace': members['runner.py'] = b'# weakened\n'
    elif fault == 'delete': del members['runner.py']
    elif fault == 'extra_code': members['new_calculator.py'] = b'pass\n'
    elif fault == 'wrong_seal': members['seal.json'] += b'\n'
    elif fault == 'escape': members['../escape'] = b'x'
    elif fault == 'absolute': members['/absolute'] = b'x'
    else: members['a\\b'] = b'x'
    assert check(package, members)['status'] == 'INTEGRITY_REFUSED'


@pytest.mark.parametrize('fault', ['contract', 'inventory', 'archive', 'duplicate', 'symlink', 'case_alias', 'crc', 'encrypted'])
def test_original_integrity_faults_are_not_missing_file_recovery(package, fault):
    if fault in ('contract', 'inventory'):
        package[fault].write_bytes(package[fault].read_bytes() + b'\n')
    elif fault == 'archive': package['base'].write_bytes(b'not a zip')
    elif fault in ('duplicate', 'symlink', 'case_alias'):
        with zipfile.ZipFile(package['base'], 'a') as z:
            if fault == 'duplicate': z.writestr('runner.py', package['members']['runner.py'])
            elif fault == 'case_alias': z.writestr('Runner.py', b'x')
            else:
                info = zipfile.ZipInfo('link'); info.create_system = 3
                info.external_attr = 0o120777 << 16; z.writestr(info, 'runner.py')
        inv = json.loads(package['inventory'].read_bytes())
        if fault == 'symlink': inv['files']['link'] = sha(b'runner.py')
        inv['zip_sha256'] = sha(package['base'].read_bytes())
        ch = json.loads(package['contract'].read_bytes())
        ch['original_zip_sha256'] = inv['zip_sha256']
        ch['original_inventory_sha256'] = put(package['inventory'], raw(inv))
        package['contract_hash'] = put(package['contract'], raw(ch))
    else:
        data = bytearray(package['base'].read_bytes())
        if fault == 'crc':
            with zipfile.ZipFile(package['base']) as z:
                info = z.getinfo('runner.py')
                offset = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
            data[offset] ^= 1
        else:
            data[6] |= 1
            central = data.find(b'PK\x01\x02'); data[central + 8] |= 1
        package['base'].write_bytes(data)
        inv = json.loads(package['inventory'].read_bytes()); inv['zip_sha256'] = sha(data)
        ch = json.loads(package['contract'].read_bytes()); ch['original_zip_sha256'] = sha(data)
        ch['original_inventory_sha256'] = put(package['inventory'], raw(inv))
        package['contract_hash'] = put(package['contract'], raw(ch))
    assert check(package)['status'] == 'INTEGRITY_REFUSED'


def test_seal_reference_hash_conflict_is_integrity_error(package):
    changed = raw({'files': {'payload.json': '0' * 64}})
    c = json.loads(package['contract'].read_bytes()); c['runtime_manifests']['seal.json'] = sha(changed)
    package['contract_hash'] = put(package['contract'], raw(c))
    assert check(package, dict(package['members'], **{'seal.json': changed}))['status'] == 'INTEGRITY_REFUSED'


def test_unlisted_runtime_reference_remains_incomplete(package):
    changed = raw({'files': {'unlisted.json': sha(b'{}')}})
    c = json.loads(package['contract'].read_bytes()); c['runtime_manifests']['seal.json'] = sha(changed)
    package['contract_hash'] = put(package['contract'], raw(c))
    result = check(package, dict(package['members'], **{'seal.json': changed}))
    assert result['status'] == 'INCOMPLETE' and result['missing'] == ['unlisted.json']


def test_ambiguous_manifest_json_cannot_hide_binding(package):
    changed = b'{"files":{"payload.json":"' + sha(b'bad').encode() + b'","payload.json":"' + sha(package['members']['payload.json']).encode() + b'"}}'
    c = json.loads(package['contract'].read_bytes()); c['runtime_manifests']['seal.json'] = sha(changed)
    package['contract_hash'] = put(package['contract'], raw(c))
    assert check(package, dict(package['members'], **{'seal.json': changed}))['status'] == 'INTEGRITY_REFUSED'


def test_candidate_inventory_without_external_pin_is_refused(package):
    check(package, dict(package['members'], **{'seal.json': package['seal']}))
    result = inspect_package(package['root'] / 'candidate.zip', package['inventory'],
                             package['contract'], package['contract_hash'],
                             candidate_inventory=package['root'] / 'candidate_inventory.json')
    assert result['status'] == 'INTEGRITY_REFUSED'


@pytest.fixture
def proposal():
    initial = dict(allocation_id='first', allocation_start_utc='2026-10-09T00:00:00+00:00',
                   first_attempt_utc='2026-10-09T00:00:10+00:00', original_zip_sha256='a' * 64,
                   failed_evidence_zip_sha256='b' * 64, instance_id=54815136, machine_id=56006,
                   country='FR', prior_failed_attempts=3, handoff_deadline_ms=400000,
                   test_files=['test_' + str(i) for i in range(6)])
    initial['caps'] = json.loads((Path(__file__).resolve().parents[2] /
                                 'experiments/bounded_admin_recovery_v0/protocol.json').read_bytes())['caps']
    common = {k: initial[k] for k in ('allocation_id', 'allocation_start_utc', 'original_zip_sha256',
                                     'failed_evidence_zip_sha256', 'instance_id', 'machine_id', 'country', 'caps')}
    facts = dict(
        provenance=dict(files={'seal.json': 'c' * 64}, existing_sealed_origin=True, verifier_id='judge'),
        preservation=dict(originals_immutable=True),
        classification=dict(error_kinds=['MISSING_EXISTING_SEALED_DEPENDENCY'],
                            nonpasses=81, attributed_nonpasses=81, unclassified=0),
        budget=dict(elapsed_ms=50000, compute_wall_used_ms=15000, aggregate_cpu_used_ms=20000,
                    reserve_repair_ms=10000, reserve_repair_cpu_ms=10000,
                    reserve_suite_wall_ms=60000, reserve_suite_cpu_ms=60000,
                    reserve_recovery_ms=60000, memory_peak_bytes=100000000, cpu_affinity_count=1,
                    hourly_usd='0.13462222222222225', running_fee_used_usd='0.002'),
        control=dict(actual='running', guardian='ARMED', supervisor='CONTROL_OK', outside_guest=True,
                     stop_control_verified=True, cumulative_caps_enforced=True, handoff_deadline_ms=400000),
        package=dict(status='COMPLETE_DECLARED_ONLY', added_files={'seal.json': 'c' * 64},
                     zip_sha256='d' * 64, inventory_sha256='e' * 64, separately_sealed=True,
                     computation_criteria_authority_unchanged=True, expected_tests=320,
                     test_files=initial['test_files']),
        approval=dict(explicit_human_approval=True, approved_utc='2026-10-08T23:59:59+00:00',
                      approval_reference='TEST_ONLY human fixture', recovery_scope={'seal.json': 'c' * 64},
                      max_admin_recoveries=1, max_full_reruns=1, candidate_zip_sha256='d' * 64,
                      candidate_inventory_sha256='e' * 64),
        ledger=dict(admin_recoveries_started=0, full_reruns_started=0, prior_failed_attempts=3))
    policy_hash = sha((Path(__file__).resolve().parents[2] /
                       'experiments/bounded_admin_recovery_v0/protocol.json').read_bytes())
    facts['approval']['policy_sha256'] = policy_hash
    for role in ('budget', 'control', 'ledger'):
        facts[role]['observed_utc'] = '2026-10-09T00:00:50+00:00'
    receipts = {role: raw(dict(common, role=role, verdict='VERIFIED', **body)) for role, body in facts.items()}
    authority = dict(initial=initial, package_author_id='author', policy_sha256=policy_hash,
                     review_utc='2026-10-09T00:00:50+00:00',
                     receipt_pins={k: sha(v) for k, v in receipts.items()})
    return dict(receipts=receipts), authority


def inject(pair, role, key, value, repin=True):
    request, authority = copy.deepcopy(pair)
    obj = json.loads(request['receipts'][role]); obj[key] = value
    request['receipts'][role] = raw(obj)
    if repin: authority['receipt_pins'][role] = sha(request['receipts'][role])
    return request, authority


def test_all_verified_facts_only_produce_review_candidate(proposal):
    request, authority = proposal
    result = review_recovery(request, authority=authority)
    assert result['status'] == 'STATIC_REVIEW_CANDIDATE'
    assert result['execution_authorized'] is False


@pytest.mark.parametrize('kind', ['COMPUTATION', 'NUMERIC_MISMATCH', 'SIGNATURE', 'ORIGINAL_TAMPER',
                                  'SERVER_IDENTITY', 'TERMINATION_CONTROL', 'UNKNOWN', 'MIXED'])
def test_forbidden_or_mixed_error_never_recovers(proposal, kind):
    req, auth = inject(proposal, 'classification', 'error_kinds', ['MISSING_EXISTING_SEALED_DEPENDENCY', kind])
    assert review_recovery(req, authority=auth)['status'] == 'REFUSED'


@pytest.mark.parametrize('role,key,value', [
    ('provenance', 'existing_sealed_origin', False), ('provenance', 'verifier_id', 'author'),
    ('preservation', 'originals_immutable', False), ('classification', 'unclassified', 1),
    ('classification', 'attributed_nonpasses', 80), ('approval', 'explicit_human_approval', False),
    ('approval', 'approved_utc', '2026-10-09T00:00:11+00:00'),
    ('approval', 'max_admin_recoveries', 2), ('approval', 'max_full_reruns', 2),
    ('approval', 'recovery_scope', {'unknown.json': 'c' * 64}),
    ('approval', 'candidate_zip_sha256', 'f' * 64),
    ('approval', 'policy_sha256', 'f' * 64),
    ('package', 'separately_sealed', False), ('package', 'computation_criteria_authority_unchanged', False),
    ('package', 'expected_tests', 239), ('package', 'test_files', ['test_0']),
    ('control', 'actual', 'exited'), ('control', 'guardian', 'FAILED'),
    ('control', 'supervisor', 'FAILED'), ('control', 'outside_guest', False),
    ('control', 'stop_control_verified', False), ('control', 'cumulative_caps_enforced', False),
    ('control', 'instance_id', 123), ('control', 'machine_id', 123), ('control', 'country', 'US'),
    ('control', 'handoff_deadline_ms', 100000),
    ('control', 'handoff_deadline_ms', 410000),
    ('control', 'observed_utc', '2026-10-09T00:00:40+00:00'),
    ('ledger', 'admin_recoveries_started', 1), ('ledger', 'full_reruns_started', 1),
    ('ledger', 'prior_failed_attempts', 0), ('ledger', 'admin_recoveries_started', True),
    ('ledger', 'observed_utc', '2026-10-09T00:00:40+00:00'),
    ('budget', 'aggregate_cpu_used_ms', None), ('budget', 'compute_wall_used_ms', 119999),
    ('budget', 'reserve_repair_cpu_ms', None),
    ('budget', 'aggregate_cpu_used_ms', 119999), ('budget', 'elapsed_ms', 400000),
    ('budget', 'elapsed_ms', -1), ('budget', 'reserve_suite_wall_ms', 0),
    ('budget', 'elapsed_ms', 0), ('budget', 'observed_utc', '2026-10-09T00:00:40+00:00'),
    ('budget', 'memory_peak_bytes', 536870913), ('budget', 'cpu_affinity_count', 2),
    ('budget', 'hourly_usd', '0.251'), ('budget', 'running_fee_used_usd', '0.049'),
    ('budget', 'hourly_usd', 'NaN'), ('budget', 'allocation_id', 'fresh'),
    ('budget', 'allocation_start_utc', '2026-10-09T00:01:00+00:00'),
    ('budget', 'caps', {'allocation_seconds': 600}),
    ('classification', 'nonpasses', 321),
])
def test_recovery_preconditions_fail_closed(proposal, role, key, value):
    req, auth = inject(proposal, role, key, value)
    assert review_recovery(req, authority=auth)['status'] == 'REFUSED'


def test_self_attested_or_altered_receipt_does_not_override_external_pin(proposal):
    req, auth = inject(proposal, 'approval', 'approval_reference', 'self generated', repin=False)
    assert review_recovery(req, authority=auth)['status'] == 'REFUSED'


def test_absent_independent_receipt_is_refused(proposal):
    req, auth = copy.deepcopy(proposal); del req['receipts']['provenance']
    assert review_recovery(req, authority=auth)['status'] == 'REFUSED'


def test_modified_policy_is_not_accepted_as_external_authority(proposal):
    req, auth = copy.deepcopy(proposal); auth['policy_sha256'] = '0' * 64
    assert review_recovery(req, authority=auth)['status'] == 'REFUSED'


def test_json_boolean_cannot_reset_integer_caps(proposal):
    req, auth = copy.deepcopy(proposal)
    auth['initial']['caps']['cpu_affinity_count'] = True
    assert review_recovery(req, authority=auth)['status'] == 'REFUSED'


@pytest.mark.parametrize('fault', ['subset', 'failure', 'error', 'skip', 'duplicate', 'extra', 'benchmark', 'physics', 'gpu'])
def test_full_rerun_requires_exact_all_pass_cases(fault):
    ids = ['case_' + str(i) for i in range(320)]
    body = dict(role='full_rerun', verdict='VERIFIED', cases=[dict(id=i, outcome='passed') for i in ids],
                benchmark_complete=True, new_physics_calls=0, gpu_calls=0)
    if fault == 'subset': body['cases'].pop()
    elif fault in ('failure', 'error', 'skip'): body['cases'][0]['outcome'] = fault
    elif fault == 'duplicate': body['cases'][0]['id'] = body['cases'][1]['id']
    elif fault == 'extra': body['cases'].append(dict(id='extra', outcome='passed'))
    elif fault == 'benchmark': body['benchmark_complete'] = False
    elif fault == 'physics': body['new_physics_calls'] = 1
    else: body['gpu_calls'] = 1
    data = raw(body)
    assert review_completion(data, sha(data), ids)['status'] == 'REFUSED'


def test_prepared_full_rerun_acceptance_does_not_grant_execution():
    ids = ['case_' + str(i) for i in range(320)]
    data = raw(dict(role='full_rerun', verdict='VERIFIED',
                    cases=[dict(id=i, outcome='passed') for i in ids], benchmark_complete=True,
                    new_physics_calls=0, gpu_calls=0))
    result = review_completion(data, sha(data), ids)
    assert result['status'] == 'STATIC_RESULT_CONTRACT_MATCH'
    assert result['execution_authorized'] is False
