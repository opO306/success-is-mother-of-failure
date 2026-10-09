"""Stdlib-only local metadata writer. No imports of project/transport, no execution grant."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
T = HERE / 'transport'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())
def rel(path): return Path(path).relative_to(ROOT).as_posix()
def write(path, obj):
    raw=(json.dumps(obj, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    if Path(path).exists():
        if Path(path).read_bytes()!=raw: raise FileExistsError('IMMUTABLE_METADATA_ALREADY_EXISTS:'+str(path))
        return
    with Path(path).open('xb') as f:
        f.write(raw)


def main():
    original_cases = ROOT / 'docs/active/bounded_admin_recovery_v0/original_320_case_inventory.json'
    if (T/'case_inventory_320.json').exists():
        if (T/'case_inventory_320.json').read_bytes()!=original_cases.read_bytes(): raise ValueError('CASE_INVENTORY_DRIFT')
    else:
        with (T/'case_inventory_320.json').open('xb') as f: f.write(original_cases.read_bytes())
    A = read(HERE/'package_A/inventory.json'); B = read(HERE/'package_B_v3/inventory.json')
    originals = ['experiments/bounded_admin_recovery_v0/'+n for n in ('__init__.py','package_gate.py','planning.py','protocol.json')]
    originals.append('tests/bounded_admin_recovery_v0/test_bounded_admin_recovery_v0.py')
    bindings = {}
    for kind, inv, path, expected in [('A',A,HERE/'package_A/inventory.json',320),('B',B,HERE/'package_B_v3/inventory.json',95)]:
        bindings[kind] = dict(archive=inv['archive'], zip_sha256=inv['zip_sha256'], inventory=rel(path),
                             inventory_sha256=sha(path), entries=inv['entries'], expected_tests=expected,
                             uncompressed_bytes=inv['uncompressed_bytes'])
    bindings['A'].update(code_sha256=sha(ROOT/'experiments/adaptive_experience_tablet_v0/code_seal.json'),
                         protocol_sha256=sha(ROOT/'experiments/adaptive_experience_tablet_v0/protocol.json'),
                         case_inventory=rel(T/'case_inventory_320.json'), case_inventory_sha256=sha(original_cases),
                         original_zip_sha256=read(HERE/'preservation_before.json')['original_zip_sha256'],
                         original_files_preserved=813, extra_files=1,
                         addition_path='experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json',
                         addition_sha256='ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60',
                         comparison=rel(HERE/'package_A/member_comparison.json'), comparison_sha256=sha(HERE/'package_A/member_comparison.json'))
    bindings['B'].update(code_sha256=sha(HERE/'package_B_v3/source_seal.json'),
                         protocol_sha256=sha(HERE/'package_B_v3/harness_protocol.json'),
                         local_code_seal=rel(HERE/'package_B_v3/source_seal.json'), original_policy_files=originals,
                         runtime_status='NOT_EXECUTED;95_EXPECTED;0_OFFICIAL_PASSES')
    write(T/'package_bindings.json',bindings)
    source_files = ['controller.py','supervisor.py','guest_probe.py','guest_recover.py','guest_source_verify.py',
                    'guest_gate.py','package_bindings.json','case_inventory_320.json','reuse_origin.json']
    guardian = ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
    write(T/'transport_seal.json',dict(schema='PACKAGE_CLOSURE_TRANSPORT_STATIC_SEAL_V1',
          scope_sha256=sha(HERE/'scope_protocol.json'), guardian_sha256=sha(guardian),
          files={name:sha(T/name) for name in source_files}, execution_authorized=False,
          runtime_validation='PENDING', packages=bindings))
    for kind in ('B','A'):
        spec=bindings[kind]
        auth=dict(schema='PACKAGE_CLOSURE_V1_NEW_WINDOW_HUMAN_APPROVAL', explicit_user_approval=False,
                  new_window_separately_authorized=False,restart_exact_instance_authorized=False,exclusive=False,
                  approval_reference=None,human_approval_text=None,approved_utc=None,expires_utc=None,run_id=None,
                  prior_failed_attempts=3,prior_tablet_gate_attempts=1,
                  prior_closed_window_sha256=sha(ROOT/'docs/active/adaptive_experience_tablet_v0/remote_20261009_attempt3/closure.json'),
                  closed_failed_gate_sha256=sha(ROOT/'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009/run_approved_20261009_0130/closure.json'),
                  transport_seal_sha256=sha(T/'transport_seal.json'),scope_protocol_sha256=sha(HERE/'scope_protocol.json'),
                  instance_id=54815136,machine_id=56006,country='FR',ssh_host='ssh9.vast.ai',ssh_port=26992,
                  scope='OFFLINE_ONLY',package_kind=kind,code_sha256=spec['code_sha256'],protocol_sha256=spec['protocol_sha256'],
                  zip_sha256=spec['zip_sha256'],inventory_sha256=spec['inventory_sha256'],package_entries=spec['entries'],
                  expected_tests=spec['expected_tests'],allocation_seconds=600,compute_seconds=120,
                  recovery_deadline_seconds=420,stop_confirmation_seconds=180,hourly_cap_usd='0.25',total_cap_usd='0.05',
                  campaign_total_cap_usd='0.05',
                  physics_calls=0,gpu_calls=0,
                  live_readonly_preflight='PENDING; historical target and SSH are proposal only',
                  approval_status='UNAPPROVED_TEMPLATE; no new or renewed budget is granted')
        if kind=='A': auth.update(policy_gate_receipt=None,policy_gate_receipt_sha256=None)
        write(T/f'approval_UNAPPROVED_{kind}.json',auth)
    write(HERE/'packages_final_summary.json',dict(status='PACKAGE_CLOSURE_STATIC_READY',A=bindings['A'],B=bindings['B'],
          transport_seal_sha256=sha(T/'transport_seal.json'),official_new_policy_passes=0,official_new_tablet_passes=0,
          remote_execution='NOT_AUTHORIZED; NOT_EXECUTED', old_remote_status='REMOTE_TEST_GATE_FAILED / UNRESOLVED',
          historical_B_drafts_preserved=['package_B','package_B_v2'],combined_budget_proven=False))
    print(json.dumps(dict(A_entries=A['entries'], B_entries=B['entries'], A_inventory_sha256=sha(HERE/'package_A/inventory.json'),
                         B_inventory_sha256=sha(HERE/'package_B_v3/inventory.json'),transport_seal_sha256=sha(T/'transport_seal.json'))))


if __name__=='__main__': main()
