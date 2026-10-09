"""One-time exclusive evidence preparation. Stdlib/raw-byte/AST only.

No imports of project modules or the proposed planner, no test execution,
no archive extraction/mutation, no network, no signing or approval issuance.
"""
import ast
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(data): return hashlib.sha256(data).hexdigest()
def read(name): return json.loads((ROOT / name).read_bytes())
def raw_hash(name): return sha((ROOT / name).read_bytes())
def write(name, obj):
    body = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True).encode() + b'\n'
    if (OUT / name).exists():
        if (OUT / name).read_bytes() != body:
            raise ValueError('EXCLUSIVE_EVIDENCE_ALREADY_EXISTS_WITH_DIFFERENT_BYTES:' + name)
        return
    with (OUT / name).open('xb') as f:
        f.write(body)


def main():
    prefix = 'experiments/'
    tablet = prefix + 'adaptive_experience_tablet_v0/'
    pilot = prefix + 'adaptive_execution_real_learning_pilot_v0/'
    resume = prefix + 'adaptive_execution_real_learning_pilot_a_resume_v1/'
    evidence = prefix + 'evidence_canonicalization_v0/'
    learning = prefix + 'adaptive_execution_learning_v1/'
    verification = prefix + 'adaptive_execution_verification_v0/'
    source = 'docs/active/adaptive_experience_tablet_v0/source_7b264a42/'
    ip = source + 'package_manifest.json'
    inventory = read(ip)
    manifest_names = ([tablet + n for n in ('protocol_seal.json', 'preservation_manifest.json', 'code_seal.json')]
                      + [resume + n for n in ('protocol_seal.json', 'protected_history.json', 'code_seal.json')]
                      + [pilot + n for n in ('protocol_seal.json', 'protected_manifest.json',
                                           'offline_budget_amendment_seal.json', 'a_safety_seal.json')]
                      + [evidence + n for n in ('protocol_seal.json', 'numeric_string_amendment_seal.json')]
                      + [learning + n for n in ('protocol_seal.json', 'preservation_manifest.json')]
                      + [verification + 'protocol_seal.json'])
    callsites = [tablet + 'offline.py', tablet + 'catalog.py', pilot + 'common.py', pilot + 'runner.py',
                 pilot + 'a_safety.py', resume + 'policy.py', evidence + 'policy.py', learning + 'core.py',
                 verification + 'common.py', verification + 'verifier.py']
    tests = read(tablet + 'protocol.json')['offline']['test_files']
    required = {name: raw_hash(name) for name in callsites + tests}
    contract = dict(schema='BOUNDED_ADMIN_PACKAGE_DEPENDENCIES_V0', baseline='394d16c9',
                    original_inventory=ip, original_inventory_sha256=raw_hash(ip),
                    original_zip_sha256=inventory['zip_sha256'], required_files=required,
                    runtime_manifests={name: raw_hash(name) for name in manifest_names},
                    scope='REVIEWED_EXECUTION_SEALS_AND_THEIR_FILES; DYNAMIC_COMPLETENESS_NOT_PROVEN',
                    review='A_SOURCE_HISTORICAL_MANIFEST_IS_NOT_AN_EXECUTION_SEAL', test_files=tests)
    write('dependency_contract.json', contract)
    missing = resume + 'code_seal.json'
    old_seal = read(missing)
    old_authority = ('docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/'
                     'run_20261008_approved_3/recovered/output_offline/authorization_used.json')
    with zipfile.ZipFile(ROOT / inventory['archive']) as z:
        zipped = set(z.namelist())
        failures = [k for k, v in inventory['files'].items() if sha(z.read(k)) != v]
        refs_missing = sorted(set(old_seal['files']) - zipped)
        refs_mismatch = [k for k, v in old_seal['files'].items() if k in zipped and sha(z.read(k)) != v]
    junit = ('docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/'
             'run_approved_20261009_0130/recovered/output/junit.xml')
    cases = ET.parse(ROOT / junit).getroot().findall('.//testcase')
    ids = [c.attrib['classname'] + '::' + c.attrib['name'] for c in cases]
    write('original_320_case_inventory.json', dict(status='HISTORICAL_FAILED_SUITE_IDENTIFIERS_ONLY',
                                                 source=junit, source_sha256=raw_hash(junit),
                                                 count=len(ids), unique=len(set(ids)), ids=sorted(ids)))
    parsed = []
    module = ROOT / 'experiments/bounded_admin_recovery_v0'
    for path in [*module.glob('*.py'), ROOT / 'tests/bounded_admin_recovery_v0/test_bounded_admin_recovery_v0.py', Path(__file__)]:
        tree = ast.parse(path.read_bytes(), filename=str(path))
        functions = []
        count = 0
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith('test_'): continue
            expansion = 1
            for deco in node.decorator_list:
                if (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)
                        and deco.func.attr == 'parametrize'):
                    if not isinstance(deco.args[1], (ast.List, ast.Tuple)):
                        raise ValueError('STATIC_PARAMETRIZATION_LIST_REQUIRED:' + node.name)
                    expansion *= len(deco.args[1].elts)
            functions.append(dict(name=node.name, prepared_cases=expansion)); count += expansion
        parsed.append(dict(path=str(path.relative_to(ROOT)).replace('\\', '/'), raw_sha256=sha(path.read_bytes()),
                           syntax='AST_PARSE_ONLY', test_functions=functions, prepared_cases=count))
    protected = []
    for name in ('protocol_seal.json', 'preservation_manifest.json', 'code_seal.json'):
        bindings = read(tablet + name)['files']
        protected.append(dict(manifest=tablet + name, raw_sha256=raw_hash(tablet + name), files=len(bindings),
                              mismatches=[k for k, v in bindings.items() if raw_hash(k) != v]))
    transport_dir = 'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/'
    transport = read(transport_dir + 'transport_seal_v3.json')
    protected.append(dict(manifest=transport_dir + 'transport_seal_v3.json',
                          raw_sha256=raw_hash(transport_dir + 'transport_seal_v3.json'), files=len(transport['files']),
                          mismatches=[k for k, v in transport['files'].items() if raw_hash(transport_dir + k) != v]))
    write('static_preparation_evidence_v4.json', dict(
        status='STATIC_PREPARATION_ONLY; DYNAMIC_FAULT_TESTS_NOT_RUN',
        original_zip_sha256=raw_hash(inventory['archive']), original_zip_member_mismatches=failures,
        missing_seal=missing, missing_seal_raw_sha256=raw_hash(missing),
        historical_success_authority=old_authority, historical_authority_raw_sha256=raw_hash(old_authority),
        historical_authority_code_sha256=read(old_authority)['code_seal_sha256'],
        old_seal_references=len(old_seal['files']), old_seal_references_missing=refs_missing,
        old_seal_reference_mismatches=refs_mismatch, independent_new_recovery_verification='NOT_PERFORMED',
        protected_checks=protected, ast_checks=parsed,
        prepared_test_cases=sum(p['prepared_cases'] for p in parsed),
        dynamic_tests=0, project_imports=0, paid_executions=0, package_repairs=0,
        prior_admin_failures=3, historical_status='REMOTE_TEST_GATE_FAILED / UNRESOLVED'))
    print(json.dumps(dict(contract_sha256=raw_hash(str((OUT/'dependency_contract.json').relative_to(ROOT))),
                          ast_files=len(parsed), prepared_test_cases=sum(p['prepared_cases'] for p in parsed),
                          protected_mismatches=sum(len(p['mismatches']) for p in protected))))


if __name__ == '__main__': main()
