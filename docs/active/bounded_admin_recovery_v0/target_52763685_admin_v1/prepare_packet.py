"""Build a candidate experiment packet, not a readiness or execution-approval seal."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def put(path,obj):
    with path.open('xb') as f:f.write(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False).encode())

if __name__=='__main__':
    paths=list((BASE/'transport').glob('*'))+list((BASE/'fixtures').glob('*.json'))+list((BASE/'tests').glob('*.py'))
    paths += [BASE/n for n in ('run_admin_simulation.py','target_protocol.json','budget_protocol.json')]
    fixed=[
      'docs/active/bounded_admin_recovery_v0/target_54988176_b_v1/transport/controller.py',
      'docs/active/bounded_admin_recovery_v0/target_54988176_b_v1/transport/package_bindings.json',
      'docs/active/bounded_admin_recovery_v0/target_54988176_b_v1/human_approvals/b_95_es_20261009_082647.json',
      'docs/active/bounded_admin_recovery_v0/budget_supplement_v1/remote_result_b_95_20261009_075708/closure.json',
      'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/run_approved_20261009_0130/closure.json',
      'docs/active/bounded_admin_recovery_v0/closure_v1/package_B_v3/admin_policy_95.zip',
      'docs/active/bounded_admin_recovery_v0/closure_v1/package_B_v3/inventory.json',
      'docs/active/bounded_admin_recovery_v0/closure_v1/package_B_v3/source_seal.json',
      'experiments/bounded_admin_recovery_v0/code_seal_v2.json',
      'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py',
      'experiments/adaptive_execution_real_learning_pilot_v0/a_safety.py',
      'experiments/adaptive_execution_real_learning_pilot_v0/offline_budget_amendment_52763685.json']
    paths += [ROOT/n for n in fixed]
    if any(not p.is_file() for p in paths):raise ValueError('REQUIRED_ADMIN_DEPENDENCY_MISSING')
    paths=sorted(set(paths))
    for p in paths:
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    tree=ast.parse((BASE/'tests/test_admin_transport.py').read_text(encoding='utf-8'))
    count=sum(1 for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
    failures=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FAILURES' for t in n.targets))
    expected=count+len(failures.keys)
    if expected!=48:raise ValueError('EXACT_45_PLUS_3_ADMIN_CASES_REQUIRED')
    members={p.relative_to(ROOT).as_posix():p.read_bytes() for p in paths}
    archive=BASE/'candidate_payload.zip'
    if archive.exists():raise ValueError('CANDIDATE_ARCHIVE_ALREADY_EXISTS; NO_REPLACE')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,raw in members.items():z.writestr(name,raw)
    inventory=dict(role='UNVALIDATED_ADMIN_CANDIDATE_INPUTS_ONLY',expected_admin_tests=expected,
        B95_executed=False,A320_executed=False,files={n:sha(raw) for n,raw in members.items()},
        entries=len(members),uncompressed_bytes=sum(map(len,members.values())),zip_sha256=sha(archive.read_bytes()))
    put(BASE/'candidate_inventory.json',inventory)
    put(BASE/'candidate_input_record.json',dict(role='INPUT_BYTE_BINDING_ONLY; NOT_STATIC_READY_OR_SIMULATION_PASS',
        expected_admin_tests=expected,entries=len(members),uncompressed_bytes=inventory['uncompressed_bytes'],
        zip_sha256=inventory['zip_sha256'],inventory_sha256=sha((BASE/'candidate_inventory.json').read_bytes()),
        files=inventory['files']))
    print(json.dumps(dict(expected_admin_tests=expected,entries=len(members),zip_bytes=archive.stat().st_size,zip_sha256=inventory['zip_sha256'])))
