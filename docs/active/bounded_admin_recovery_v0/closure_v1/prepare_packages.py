"""Exclusive local stdlib packaging/static analysis; no project import or tests."""
import ast
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE_HASH = 'da96a821a7aa8f6f9e2537959babf68420a0d7b8ac008b2c9751cee331ff8484'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())
def write(path, obj):
    raw = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True).encode() + b'\n'
    with Path(path).open('xb') as f: f.write(raw)
def rel(path): return Path(path).relative_to(ROOT).as_posix()
def file_hash(path): return sha(Path(path).read_bytes())
def safe(name):
    if (not name or '\\' in name or ':' in name or name.startswith('/')
            or any(p in ('', '.', '..') for p in name.split('/'))): raise ValueError('PATH:' + name)


def preserved():
    scope = read(HERE / 'scope_protocol.json')
    if file_hash(HERE / 'scope_protocol.json') != SCOPE_HASH: raise ValueError('SCOPE_SEAL')
    checks = []
    base = 'experiments/adaptive_experience_tablet_v0/'
    manifests = [(base + n, ROOT) for n in ('protocol_seal.json', 'preservation_manifest.json', 'code_seal.json')]
    old = ROOT / 'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009'
    manifests += [(rel(old / 'transport_seal_v3.json'), old),
                  ('experiments/bounded_admin_recovery_v0/code_seal_v2.json', ROOT),
                  ('docs/active/adaptive_experience_tablet_v0/remote_20261009_evidence_manifest.json', ROOT),
                  ('docs/active/adaptive_experience_tablet_v0/remote_results_20261009_0130/evidence_manifest.json', ROOT)]
    for name, anchor in manifests:
        obj = read(ROOT/name); bad = [p for p,h in obj['files'].items() if file_hash(anchor/p) != h]
        checks.append(dict(manifest=name, raw_sha256=file_hash(ROOT/name), files=len(obj['files']), mismatches=bad))
        if bad: raise ValueError('BASELINE_SOURCE_CHANGED:' + name)
    if file_hash(ROOT / scope['original_package']['archive']) != scope['original_package']['zip_sha256']:
        raise ValueError('FIRST_ZIP_HASH')
    write(HERE / 'preservation_before.json', dict(baseline=scope['baseline_commit'], checks=checks,
          original_zip_sha256=scope['original_package']['zip_sha256'], dynamic_tests=0, project_imports=0, paid_actions=0))
    return scope


def make_A(scope):
    original = scope['original_package']; first = ROOT / original['archive']
    ip = ROOT / original['inventory']
    if file_hash(ip) != original['inventory_sha256']: raise ValueError('FIRST_INVENTORY_HASH')
    inventory = read(ip); extra = scope['package_A']['only_addition']; extra_name = next(iter(extra))
    extra_raw = (ROOT / extra_name).read_bytes()
    if sha(extra_raw) != extra[extra_name]: raise ValueError('EXISTING_EXTRA_RAW_HASH')
    git_raw = subprocess.check_output(['git', 'show', scope['baseline_commit'] + ':' + extra_name], cwd=ROOT)
    if git_raw != extra_raw: raise ValueError('EXTRA_BASELINE_GIT_ORIGIN')
    out = HERE / 'package_A'; out.mkdir(exist_ok=False)
    target = out / 'tablet_814.zip'
    with zipfile.ZipFile(first) as src, zipfile.ZipFile(target, 'x') as dst:
        infos = src.infolist(); names = [i.filename for i in infos]
        if len(names) != 813 or set(names) != set(inventory['files']) or len(set(names)) != 813:
            raise ValueError('EXACT_ORIGINAL_813')
        for info in infos:
            safe(info.filename)
            if info.is_dir() or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError('ORIGINAL_REGULAR_ONLY')
            data = src.read(info.filename)
            if sha(data) != inventory['files'][info.filename]: raise ValueError('ORIGINAL_MEMBER_HASH')
            dst.writestr(copy.copy(info), data)
        dst.writestr(extra_name, extra_raw, compress_type=zipfile.ZIP_DEFLATED)
    files = dict(inventory['files'], **extra)
    with zipfile.ZipFile(target) as z:
        if set(z.namelist()) != set(files) or len(z.namelist()) != 814 or z.testzip() is not None:
            raise ValueError('NEW_A_EXACT_SET_CRC')
        bad = [k for k,v in files.items() if sha(z.read(k)) != v]
        if bad: raise ValueError('NEW_A_RAW_MISMATCH')
        raw_size = sum(i.file_size for i in z.infolist())
    if file_hash(first) != original['zip_sha256']: raise ValueError('FIRST_ZIP_MODIFIED')
    new_inventory = dict(schema='PACKAGE_A_CLOSURE_814', status='RAW_PACKAGE_PREPARED_NOT_EXECUTED',
                         original_zip_sha256=original['zip_sha256'], zip_sha256=file_hash(target),
                         archive=rel(target), entries=814, uncompressed_bytes=raw_size, files=files)
    write(out / 'inventory.json', new_inventory)
    original_seal = ('docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/'
                     'run_20261008_approved_3/recovered/output_offline/authorization_used.json')
    if read(ROOT/original_seal)['code_seal_sha256'] != sha(extra_raw): raise ValueError('SUCCESSFUL_ORIGIN_PIN')
    write(out / 'member_comparison.json', dict(status='AUTHOR_RAW_COMPARISON; SEPARATE_REVIEW_PENDING',
          first_zip_sha256=original['zip_sha256'], candidate_zip_sha256=file_hash(target),
          unchanged_existing=813, removed=[], changed=[], additions=extra, crc_failure=None,
          source_git_commit=scope['baseline_commit'], git_blob_matches=True,
          historical_success_authority=original_seal, historical_authority_sha256=file_hash(ROOT/original_seal),
          extra_raw_bytes=len(extra_raw), files={k:dict(before=v, after=files[k], unchanged=True) for k,v in inventory['files'].items()}))
    return new_inventory


def path_review(A):
    original_contract = ROOT / 'docs/active/bounded_admin_recovery_v0/dependency_contract.json'
    contract = read(original_contract)
    original_root = ('docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/'
                     'run_20261008_approved_3/recovered/output_actual/')
    historical = {k:v for k,v in A['files'].items() if k.startswith(original_root)}
    if not historical: raise ValueError('HISTORICAL_FIXTURE_REQUIRED')
    signed_raw = []
    with zipfile.ZipFile(ROOT / A['archive']) as z:
        for name in historical:
            if not name.endswith('.json'): continue
            obj = json.loads(z.read(name))
            # Profiles contain the signed inspector receipt; direct receipts are also retained.
            envelope = obj.get('receipt', obj) if isinstance(obj, dict) else {}
            body = envelope.get('body', {}) if isinstance(envelope, dict) else {}
            bindings = body.get('raw_files') if isinstance(body, dict) else None
            if not bindings: continue
            stage = original_root + 'A/'
            for relative, wanted in bindings.items():
                safe(relative); full = stage + relative
                if full not in A['files'] or sha(z.read(full)) != wanted:
                    raise ValueError('DECLARED_SIGNED_RAW_DEPENDENCY:' + full)
                signed_raw.append(dict(receipt=name, target=full, raw_sha256=wanted,
                                       signature_verification='DEFERRED_TO_EXISTING_320_GATE'))
    contract['required_files'].update(historical)
    contract['baseline'] = '352f9d1b'
    contract['review'] = 'SIGNED_RAW_REFERENCE_AND_ALL_ORIGINAL_ARCHIVE_FIXTURES; AST_PATH_ACCESS_REVIEW_ATTACHED'
    write(HERE / 'dependency_contract_v1.json', contract)
    sources = set(contract['required_files'])
    sources.update(('experiments/adaptive_execution_real_learning_pilot_a_resume_v1/evidence.py',
                    'experiments/adaptive_execution_real_learning_pilot_v0/governance.py'))
    accesses = []
    for name in sorted(s for s in sources if s.endswith('.py')):
        tree = ast.parse((ROOT/name).read_bytes(), filename=name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call): continue
            func = node.func
            short = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ''
            if short in ('read', 'strict_read', 'raw_hash', 'read_bytes', 'read_text', 'open', 'glob', 'copytree'):
                text = ast.unparse(node)
                accesses.append(dict(source=name, line=node.lineno, expression=text,
                        resolution='HISTORICAL_ARCHIVE_DECLARED' if 'ORIGINAL' in text else
                                   'OS_OBSERVATION' if '/proc/' in text or '/sys/' in text else
                                   'FIXTURE_TEMP_OR_DYNAMIC_RUNTIME_ACCESS_REQUIRES_EXECUTION_REVIEW'))
    write(HERE / 'dependency_path_review.json', dict(status='STATIC_DECLARED_ONLY; DYNAMIC_COMPLETENESS_NOT_PROVEN',
          execution_manifests=15, historical_fixture_files=len(historical), declared_signed_raw_bindings=signed_raw,
          path_accesses=accesses, archive_prefix=original_root,
          covered=['source/policy seals', 'A session/replay/measurement/raw-cost receipts', 'manager profiles/events/roots',
                   'controller witnessed signed head', 'test fixture copytree and file reads', 'runtime read/glob paths'],
          excluded_from_runtime_manifest_interpretation=['historical A-source shipping manifest'],
          notes=['Raw hashes checked; no new signature verifier or authority was created.',
                 'Dynamic/generated temp files and Linux topology paths are not package membership proof.']))


def make_B(scope, directory='package_B'):
    if directory not in ('package_B', 'package_B_v2', 'package_B_v3'): raise ValueError('EXCLUSIVE_B_VERSION')
    out = HERE / directory; out.mkdir(exist_ok=False)
    originals = ['experiments/bounded_admin_recovery_v0/' + n for n in
                 ('__init__.py', 'package_gate.py', 'planning.py', 'protocol.json')]
    originals.append(scope['package_B']['original_test_file'])
    if file_hash(ROOT / originals[-1]) != scope['package_B']['original_test_file_sha256']:
        raise ValueError('ORIGINAL_95_FIXTURE_CHANGED')
    p = dict(schema='BOUNDED_ADMIN_POLICY_TEST_HARNESS_V1', mode='TEST_ONLY; NOT_PRODUCTION',
             expected_tests=95, test_file=originals[-1], aggregate_cpu_seconds=120, wall_seconds=120,
             memory_bytes=536870912, cpu_affinity_count=1, physics_calls=0, gpu_calls=0,
             guardian_sha256=scope['transport']['guardian_sha256'], approval_required=True,
             pytest_environment='REMOVE_PYTEST_ADDOPTS_PYTEST_PLUGINS_PYTHONPATH; ROOT_ONLY',
             pytest_configuration='EXPLICIT_SEALED_PYTEST_INI_AND_CONFCUTDIR_ROOT',
             external_receipt_fixture_scope='SYNTHETIC_PINS_ONLY; NOT_REAL_INDEPENDENT_CERTIFICATION')
    write(out / 'harness_protocol.json', p)
    data = {name:(ROOT/name).read_bytes() for name in originals}
    data['admin_policy/offline.py'] = (HERE/'policy_harness/offline.py').read_bytes()
    data['admin_policy/guard.py'] = (HERE/'policy_harness/guard.py').read_bytes()
    data['admin_policy/pytest.ini'] = (HERE/'policy_harness/pytest.ini').read_bytes()
    data['admin_policy/protocol.json'] = (out/'harness_protocol.json').read_bytes()
    seal = dict(schema='BOUNDED_ADMIN_POLICY_TEST_SOURCE_SEAL', original_code_seal_sha256=scope['package_B']['original_preparation_code_seal_sha256'],
                expected_tests=95, files={k:sha(v) for k,v in data.items()})
    write(out / 'source_seal.json', seal)
    data['admin_policy/source_seal.json'] = (out/'source_seal.json').read_bytes()
    target = out / 'admin_policy_95.zip'
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, body in sorted(data.items()): safe(name); z.writestr(name, body)
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None or len(z.namelist()) != len(data) or set(z.namelist()) != set(data):
            raise ValueError('B_ZIP_STRUCTURE')
        if any(z.read(k) != v for k,v in data.items()): raise ValueError('B_RAW_HASH')
    result = dict(schema='PACKAGE_B_ADMIN_POLICY_95', status='SOURCE_PREPARED_NOT_EXECUTED', archive=rel(target),
                  zip_sha256=file_hash(target), entries=len(data), uncompressed_bytes=sum(map(len,data.values())),
                  files={k:sha(v) for k,v in data.items()}, source_seal_sha256=file_hash(out/'source_seal.json'),
                  protocol_sha256=file_hash(out/'harness_protocol.json'))
    write(out / 'inventory.json', result)
    write(out / 'raw_scope_check.json', dict(entries=len(data), preserved_original_files={k:sha(data[k]) for k in originals},
          original_tests_raw_unchanged=True, namespace_packages=['experiments', 'admin_policy'],
          pytest_autoload=False, no_root_conftest=True, physics_and_GPU_imports_blocked_by_guard=True,
          limitation='DECLARED_IMPORTS_AND_PYTHON_AUDIT_HOOK; NOT_OS_ISOLATION', dynamic_tests=0))
    return result


def copy_gate():
    raw = (ROOT/'experiments/bounded_admin_recovery_v0/package_gate.py').read_text(encoding='utf-8')
    raw = raw.replace("p.add_argument('--out', required=True, type=Path)",
                      "p.add_argument('--candidate-inventory', type=Path)\n    p.add_argument('--candidate-inventory-sha256')\n    p.add_argument('--out', required=True, type=Path)")
    raw = raw.replace('result = inspect_package(args.archive, args.original_inventory, args.contract, args.contract_sha256)',
                      'result = inspect_package(args.archive, args.original_inventory, args.contract, args.contract_sha256,\n                             candidate_inventory=args.candidate_inventory,\n                             candidate_inventory_sha256=args.candidate_inventory_sha256)')
    target = HERE/'package_gate_v1.py'
    with target.open('xb') as f: f.write(raw.encode())
    return target


def main():
    scope = preserved(); A = make_A(scope); path_review(A); B = make_B(scope); copy_gate()
    write(HERE/'packages_summary.json', dict(status='STATIC_ARTIFACTS_PREPARED; GATE_AND_SEPARATE_REVIEW_PENDING',
           A={k:A[k] for k in ('archive','zip_sha256','entries','uncompressed_bytes')},
           B={k:B[k] for k in ('archive','zip_sha256','entries','source_seal_sha256','protocol_sha256')},
           dynamic_tests=0, paid_actions=0, original_closed_budget_reset=False))
    print(json.dumps(dict(A_entries=A['entries'], A_zip_sha256=A['zip_sha256'], B_entries=B['entries'],
                         B_zip_sha256=B['zip_sha256'], dynamic_tests=0, paid_actions=0)))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] in (['--final-B-v2'], ['--final-B-v3']):
        if file_hash(HERE/'scope_protocol.json') != SCOPE_HASH: raise ValueError('SCOPE_SEAL')
        result = make_B(read(HERE/'scope_protocol.json'), 'package_B_v3' if sys.argv[1:] == ['--final-B-v3'] else 'package_B_v2')
        print(json.dumps(dict(B_entries=result['entries'], B_zip_sha256=result['zip_sha256'],
                              source_seal_sha256=result['source_seal_sha256'], protocol_sha256=result['protocol_sha256'])))
    elif not sys.argv[1:]: main()
    else: raise ValueError('STATIC_PREPARATION_MODE')
