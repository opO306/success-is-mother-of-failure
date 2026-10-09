"""Stdlib metadata-only final closure. No project imports, tests or network."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASELINE='352f9d1b09c24901a08adc6cf7d0af0a5f63fa5e'
PREFIX=HERE.relative_to(ROOT).as_posix()+'/'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,obj):
    with path.open('xb') as f: f.write((json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


def main():
    syntax=[]
    for path in sorted(HERE.rglob('*.py')):
        ast.parse(path.read_bytes(),filename=str(path)); syntax.append(path.relative_to(ROOT).as_posix())
    assert git('branch','--show-current').decode().strip()=='codex/adaptive-experience-tablet-cpu-route-v0'
    # Compare tracked raw bytes with baseline, preserving the original failure evidence too.
    changes=git('diff','--name-status',BASELINE).decode('utf-8').splitlines()
    for row in changes:
        kind,name=row.split('\t',1)
        assert kind=='A' and name.startswith(PREFIX),(kind,name)
    untracked=git('ls-files','--others','--exclude-standard','-z').decode('utf-8').split('\x00')
    assert all(n.startswith(PREFIX) for n in untracked if n)
    files=sorted(p.relative_to(ROOT).as_posix() for p in HERE.rglob('*') if p.is_file())
    expected=sorted(set(files+[PREFIX+'git_change_manifest.json',PREFIX+'closure_seal.json']))
    write(HERE/'git_change_manifest.json',dict(baseline_commit=BASELINE,scope_preseal_commit='0701d448',
          branch=git('branch','--show-current').decode().strip(),existing_modified_or_deleted=[],
          files=[dict(status='A',path=n) for n in expected],push=False,master_merge=False,
          final_commit='Containing implementation commit; query actual HEAD after commit',
          final_worktree='Query after commit; this record does not predict clean status'))
    bindings=json.loads((HERE/'transport/package_bindings.json').read_bytes())
    write(HERE/'closure_seal.json',dict(schema='PACKAGE_CLOSURE_V1_FINAL_RAW_EVIDENCE',
          status='PACKAGE_CLOSURE_STATIC_READY',dynamic_status='DYNAMIC_VALIDATION_PENDING',mode='NOT_PRODUCTION',
          old_remote_status='REMOTE_TEST_GATE_FAILED / UNRESOLVED',baseline_commit=BASELINE,
          scope_sha256=sha(HERE/'scope_protocol.json'),transport_sha256=sha(HERE/'transport/transport_seal.json'),
          packages=bindings,paid_actions=0,remote_calls=0,project_dynamic_tests=0,new_physics_calls=0,gpu_calls=0,
          syntax_parsed_files=syntax,
          files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}))
    print(json.dumps(dict(changed_files=len(expected),all_additions_in_owned_directory=True,
                         closure_seal_sha256=sha(HERE/'closure_seal.json'),paid_actions=0)))


if __name__=='__main__': main()
