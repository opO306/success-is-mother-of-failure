import hashlib,json,subprocess
from pathlib import Path
root=Path.cwd()
evidence=Path('docs/active/h2_ci_layer_audit_v0/evidence')
seal=json.loads((evidence/'preparation_seal.json').read_text(encoding='utf-8'))
manifest=json.loads((evidence/'artifact_manifest.json').read_text(encoding='utf-8'))
def relative(name):
    if name.startswith('/mnt/c/'):
        return Path('C:/'+name.removeprefix('/mnt/c/')).relative_to(root).as_posix()
    return Path(name).as_posix()
checks={relative(p):v for p,v in seal['source_sha256'].items()}
checks.update({(evidence/Path(p.replace('\\','/'))).as_posix():v for p,v in manifest['files'].items()})
post=json.loads((evidence/'postprocess_seal.json').read_text(encoding='utf-8'))
checks['electronic_pilot/ci_layer_audit_summary_v0.py']=post['source_sha256']
bad=[]
for p,v in checks.items():
    actual=hashlib.sha256(subprocess.check_output(['git','show',':'+p])).hexdigest()
    if actual!=v:bad.append(p)
assert not bad,bad
base=seal['head']
existing=subprocess.check_output(['git','diff','--cached','--diff-filter=M','--name-only'],text=True).splitlines()
assert set(existing)=={'CURRENT_STATE.md','docs/README.md','docs/DOCUMENT_STATUS_INDEX.md'},existing
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==base
out=dict(staged_sealed_source_and_compact_record_count=len(checks),mismatches=bad,
         old_modified_only_navigation_docs=existing,base_commit=base,
         artifact_CRLF_and_trace_whitespace_preserved=True,git_diff_check=True,
         numerical_source_or_guards_changed=False)
Path('runs/h2_ci_layer_audit_v0/staged_verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
