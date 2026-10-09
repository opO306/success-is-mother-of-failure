"""Local stdlib evidence sealing only; no project imports, dynamic tests or network."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASELINE='d77e08d28fabdfd39a0615f5a76aaa4944208e67'
PREFIX=HERE.relative_to(ROOT).as_posix()+'/'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,obj):
    with path.open('xb') as f: f.write((json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


def main():
    syntax=[]
    for p in HERE.rglob('*.py'):
        ast.parse(p.read_bytes(),filename=str(p)); syntax.append(p.relative_to(ROOT).as_posix())
    branch=git('branch','--show-current').decode().strip()
    assert branch=='codex/adaptive-experience-tablet-cpu-route-v0'
    tracked=git('diff','--name-status','-z',BASELINE).decode('utf-8').strip('\0').split('\0')
    for i in range(0,len(tracked),2): assert tracked[i]=='A' and tracked[i+1].startswith(PREFIX)
    untracked=git('ls-files','--others','--exclude-standard','-z').decode('utf-8').split('\0')
    assert all(n.startswith(PREFIX) for n in untracked if n)
    paths=sorted(p.relative_to(ROOT).as_posix() for p in HERE.rglob('*') if p.is_file())
    expected=sorted(set(paths+[PREFIX+'git_change_manifest.json',PREFIX+'evidence_seal.json']))
    write(HERE/'git_change_manifest.json',dict(baseline=BASELINE,branch=branch,scope_preseal_commit='527ea32c',
          files=[dict(status='A',path=n) for n in expected],existing_modified_or_deleted=[],push=False,master_merge=False))
    write(HERE/'evidence_seal.json',dict(schema='BUDGET_SUPPLEMENT_V1_RAW_EVIDENCE_SEAL',
          status='BUDGET_SUPPLEMENT_STATIC_READY',dynamic_validation='PENDING',mode='NOT_PRODUCTION',
          budget_protocol_sha256=sha(HERE/'budget_protocol.json'),transport_seal_sha256=sha(HERE/'transport/transport_seal.json'),
          original_remote_status='REMOTE_TEST_GATE_FAILED / UNRESOLVED',
          campaign_execution_fee_cap_usd='0.10',each_execution_fee_cap_usd='0.05',
          paid_actions=0,local_project_dynamic_tests=0,remote_calls=0,physics_calls=0,gpu_calls=0,
          syntax_parsed_files=sorted(syntax),files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}))
    print(json.dumps(dict(new_files=len(expected),evidence_seal_sha256=sha(HERE/'evidence_seal.json'),old_edits=0,paid_actions=0)))


if __name__=='__main__': main()
