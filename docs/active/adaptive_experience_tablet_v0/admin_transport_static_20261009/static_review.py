"""Standalone AST/raw-hash reviewer. Never imports or executes transport/project code.

Only this stdlib analysis script may be run during static preparation.
It records structural observations, not injected-failure execution or SSH validation.
"""
import ast
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = ROOT / 'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/run_20261008_approved_3'
TABLET = ROOT / 'experiments/adaptive_experience_tablet_v0'
SOURCE = ROOT / 'docs/active/adaptive_experience_tablet_v0/source_7b264a42/source_7b264a42.zip'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def dump(node):
    return ast.dump(node, include_attributes=False)


def definition(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='static_review_result.json')
    args = parser.parse_args()
    if Path(args.out).name != args.out or not args.out.endswith('.json'):
        raise ValueError('STATIC_REPORT_FILENAME_SCOPE')
    report = dict(scope='AST_RAW_HASH_AND_MANUAL_CONTROL_FLOW_REVIEW_ONLY',
                  observed_utc=datetime.now(timezone.utc).isoformat(), project_imports=0,
                  transport_execution=0, remote_commands=0, dynamic_tests=0, paid_actions=0,
                  baseline='284f655c', observed_failure_count_unchanged=3, findings=[])
    trees = {p.name: ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in HERE.glob('*.py')}
    report['parsed_python_files'] = sorted(trees)
    report['reviewed_python_sha256'] = {p.name: sha(p.read_bytes()) for p in HERE.glob('*.py')}
    # AST body equivalence substantiates concrete code reuse instead of a prose claim.
    old = ast.parse((OLD / 'controller.py').read_text(encoding='utf-8'))
    guard = ast.parse((ROOT / 'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py').read_text(encoding='utf-8'))
    report['reused_ast_identical'] = {}
    for name in ('utc', 'canonical', 'sha', 'write'):
        match = dump(definition(old, name)) == dump(definition(trees['controller.py'], name))
        assert match, name
        report['reused_ast_identical']['A_resume.' + name] = match
    for name in ('Cli', 'confirm_stop'):
        match = dump(definition(guard, name)) == dump(definition(trees['supervisor.py'], name))
        assert match, name
        report['reused_ast_identical']['guardian.' + name] = match
    local_tree = trees['controller.py']
    assert all(not (isinstance(n, (ast.Import, ast.ImportFrom)) and
                   any(x.name.startswith(('experiments', 'engine', 'a_reference', 'audit')) for x in n.names))
               for n in ast.walk(local_tree))
    for name in ('controller.py', 'supervisor.py'):
        for node in ast.walk(trees[name]):
            if isinstance(node, ast.Call):
                assert not any(k.arg == 'shell' and not (isinstance(k.value, ast.Constant) and k.value.value is False)
                               for k in node.keywords), 'SHELL_DISPATCH:' + name
    report['local_transport_project_imports'] = 0
    report['shell_true_dispatches'] = 0
    instance_fields = [k.value for n in ast.walk(trees['guest_gate.py']) if isinstance(n, ast.Call)
                       for k in n.keywords if k.arg == 'CONTAINER_ID']
    assert len(instance_fields) == 1 and isinstance(instance_fields[0], ast.Name) and instance_fields[0].id == 'actual'
    report['guest_container_environment_source'] = 'actual PID1 value, not expected-id literal'
    # Only stdlib POSIX lexical round trip. Does not invoke PowerShell, SSH, shell or Python guest.
    vectors = [[], ['plain', 'white space', "single'quote", 'double"quote', '한글', '$HOME', '`id`',
                     '$(touch /tmp/no)', '; echo no', '\\', '\n', ''],
               ['/workspace/tablet_v0_future_approval', '54815136', 'C:/path with spaces/key']]
    for lexical_args in vectors:
        tokens = ['python3', '-B', '-', *lexical_args]
        assert shlex.split(shlex.join(tokens)) == tokens
    report['posix_lexical_roundtrip_vectors'] = len(vectors)
    report['roundtrip_scope'] = 'stdlib tokenization only; no real SSH invocation'
    for name in ('local_preflight', 'control', 'recover', 'validate_result', 'execute'):
        report.setdefault('control_flow_entry_lines', {})[name] = definition(local_tree, name).lineno
    # Historical successful raw package revalidation (read only).
    manifest = read(OLD / 'evidence_manifest.json')
    receipt = read(OLD / 'recovery_verified.json')
    with zipfile.ZipFile(OLD / 'evidence.zip') as z:
        assert sha((OLD / 'evidence.zip').read_bytes()) == receipt['zip_sha256']
        assert set(z.namelist()) == set(manifest['files']) | {'evidence_manifest.json'}
        assert len(z.namelist()) == len(set(z.namelist())) and z.testzip() is None
        for name, wanted in manifest['files'].items():
            assert sha(z.read(name)) == wanted, name
            assert sha((OLD / 'recovered' / name).read_bytes()) == wanted, name
    assert len(manifest['files']) == receipt['files'] == 111
    assert read(OLD / 'closure.json')['controller_trigger'] == 'COMPLETED'
    assert read(OLD / 'guardian/final.json')['status'] == 'STOP_CONFIRMED'
    report['successful_reference'] = dict(raw_files_rechecked=111, recovery_receipt=True, stop_receipt=True,
                                          controller_sha256=sha((OLD / 'controller.py').read_bytes()))
    report['sealed_sources'] = []
    for name in ('protocol_seal.json', 'preservation_manifest.json', 'code_seal.json'):
        manifest = read(TABLET / name)
        mismatches = [rel for rel, wanted in manifest['files'].items() if sha((ROOT / rel).read_bytes()) != wanted]
        assert not mismatches, mismatches
        report['sealed_sources'].append(dict(manifest=name, files=len(manifest['files']), mismatches=mismatches,
                                            manifest_sha256=sha((TABLET / name).read_bytes())))
    pkg = read(SOURCE.parent / 'package_manifest.json')
    assert sha(SOURCE.read_bytes()) == pkg['zip_sha256']
    with zipfile.ZipFile(SOURCE) as z:
        assert len(z.namelist()) == len(set(z.namelist())) == 813 and z.testzip() is None
        assert set(z.namelist()) == set(pkg['files'])
        for name, wanted in pkg['files'].items():
            assert sha(z.read(name)) == wanted, name
    report['source_zip'] = dict(entries=813, raw_mismatches=[], sha256=pkg['zip_sha256'])
    old_evidence = read(ROOT / 'docs/active/adaptive_experience_tablet_v0/remote_20261009_evidence_manifest.json')
    assert all(sha((ROOT / name).read_bytes()) == wanted for name, wanted in old_evidence['files'].items())
    report['previous_failure_evidence'] = dict(files=len(old_evidence['files']), raw_mismatches=[], failed_attempts=3)
    report['local_prerequisites'] = dict(ssh_path=shutil.which('ssh'), scp_path=shutil.which('scp'),
                                        existing_key_file=Path('C:/Users/zun24/.ssh/vast_ai').is_file(),
                                        existing_cli_file=Path('C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe').is_file())
    # Read-only OpenSSH known-host lookup. Never connects; public host key is not printed.
    lookup = subprocess.run(['ssh-keygen', '-F', '[ssh9.vast.ai]:26992'], capture_output=True, timeout=5)
    report['local_prerequisites']['cached_host_key_present'] = lookup.returncode == 0 and bool(lookup.stdout)
    if not all(report['local_prerequisites'].values()):
        report['findings'].append('LOCAL_EXECUTION_PREREQUISITE_MISSING')
    report['static_checks_status'] = 'PASS' if not report['findings'] else 'UNRESOLVED'
    report['runtime_validation_status'] = 'NOT_EXECUTED'
    report['limitations'] = ['AST checks are not a complete proof of exception/control behavior',
        'No fake-execution failure injection or remote run', 'Live server/key/runtime/latency not revalidated',
        'Generic guardian plus absolute supervisor is newly composed and unexecuted',
        'No guarantee of OS scheduling, remote outage or successful evidence recovery']
    path = HERE / args.out
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: report[k] for k in ('static_checks_status', 'runtime_validation_status', 'parsed_python_files',
                                          'reused_ast_identical', 'sealed_sources', 'local_prerequisites')}, ensure_ascii=True))


if __name__ == '__main__':
    main()
