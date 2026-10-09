"""Seal NEW preparation files only; rehash historical evidence, no execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def relative(path): return path.relative_to(ROOT).as_posix()
def write(path, obj):
    data = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True).encode() + b'\n'
    if path.exists():
        if path.read_bytes() != data: raise ValueError('EXISTING_EVIDENCE_BYTES_DIFFER:' + str(path))
        return
    with path.open('xb') as f:
        f.write(data)


def main():
    history = []
    for name in ('docs/active/adaptive_experience_tablet_v0/remote_20261009_evidence_manifest.json',
                 'docs/active/adaptive_experience_tablet_v0/remote_results_20261009_0130/evidence_manifest.json'):
        manifest = json.loads((ROOT / name).read_bytes())
        bad = [k for k, v in manifest['files'].items() if sha(ROOT / k) != v]
        history.append(dict(manifest=name, manifest_sha256=sha(ROOT/name), files=len(manifest['files']), mismatches=bad))
        if bad: raise ValueError('HISTORICAL_RAW_EVIDENCE_CHANGED')
    write(OUT / 'historical_preservation_check.json', dict(status='AUTHOR_RAW_HASH_CHECK_ONLY', checks=history,
                                                        resets=0, new_independent_verification=False))
    module = ROOT / 'experiments/bounded_admin_recovery_v0'
    tests = ROOT / 'tests/bounded_admin_recovery_v0'
    design = OUT / 'BOUNDED_ADMIN_RECOVERY_V0.md'
    report = OUT / 'BOUNDED_ADMIN_RECOVERY_V0_PREPARATION_2026-10-09.md'
    protocol_files = [module/'protocol.json', design, OUT/'dependency_contract.json', OUT/'original_320_case_inventory.json']
    write(module/'protocol_seal_v2.json', dict(schema='BOUNDED_ADMIN_RECOVERY_V0_PREPARATION_PROTOCOL_SEAL',
          baseline='394d16c9', execution_authorized=False, files={relative(p):sha(p) for p in protocol_files}))
    owned_code = [p for base in (module, tests) for p in base.rglob('*') if p.is_file()]
    owned_code += [design, report, OUT/'dependency_contract.json', OUT/'original_320_case_inventory.json',
                   OUT/'prepare_static.py', Path(__file__)]
    write(module/'code_seal_v2.json', dict(schema='BOUNDED_ADMIN_RECOVERY_V0_PREPARATION_CODE_SEAL', baseline='394d16c9',
          status='STATIC_PREPARATION_ONLY; DYNAMIC_FAULT_TESTS_NOT_RUN', execution_authorized=False,
          prepared_tests=95, files={relative(p):sha(p) for p in sorted(owned_code)}))
    all_files = sorted(set(p for base in (module, tests, OUT) for p in base.rglob('*') if p.is_file()))
    pending = [OUT/'change_inventory_v2.json', OUT/'evidence_manifest_v2.json']
    write(OUT/'change_inventory_v2.json', dict(baseline='394d16c9', branch='codex/adaptive-experience-tablet-cpu-route-v0',
          modified_existing_files=[], added_files=sorted(relative(p) for p in all_files+pending),
          added_count=len(all_files)+len(pending), paid_actions=0, project_dynamic_tests=0,
          local_commit_only=True, github_push=False, master_merge=False))
    all_files.append(OUT/'change_inventory_v2.json')
    write(OUT/'evidence_manifest_v2.json', dict(schema='BOUNDED_ADMIN_RECOVERY_V0_PREPARATION_EVIDENCE',
          status='PREPARED_NOT_EXECUTION_VALIDATED', files={relative(p):sha(p) for p in sorted(all_files)}))
    print(json.dumps(dict(added_files=len(all_files)+1, raw_evidence_files=len(all_files),
          policy_sha256=sha(module/'protocol.json'), new_code_seal_sha256=sha(module/'code_seal_v2.json'),
          historical_files_checked=sum(x['files'] for x in history))))


if __name__ == '__main__': main()
