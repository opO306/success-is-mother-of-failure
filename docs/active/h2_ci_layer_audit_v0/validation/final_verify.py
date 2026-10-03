import hashlib,json,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

root=Path.cwd();audit=Path('runs/h2_ci_layer_audit_v0/audit_v0')
sealed=json.loads((audit/'execution_seal.json').read_text(encoding='utf-8'))
def mapped(name):
    return Path('C:/'+name.removeprefix('/mnt/c/')) if name.startswith('/mnt/c/') else Path(name)
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
changed=[name for name,digest in sealed['bound_sha256'].items() if sha(mapped(name))!=digest]
assert not changed,changed
post=Path('docs/active/h2_ci_layer_audit_v0/evidence/postprocess_seal.json')
record=json.loads(post.read_text(encoding='utf-8'))
assert sha(Path('electronic_pilot/ci_layer_audit_summary_v0.py'))==record['source_sha256']
results={}
for label in ['windows_passed','wsl_passed']:
    tree=ET.parse(Path('runs/h2_ci_layer_audit_v0')/(label+'.xml'))
    cases=list(tree.iter('testcase'))
    assert cases and not any(list(case) and any(child.tag in ('failure','error','skipped') for child in case) for case in cases)
    results[label]=len(cases)
report=Path('docs/active/H2_R04_CI_LAYER_MICRO_AUDIT_V0.md').read_text(encoding='utf-8')
import re
links=[]
for target in re.findall(r'\]\(([^)]+)\)',report):
    if target.startswith('http'):continue
    p=Path('docs/active')/target
    assert p.exists(),p
    links.append(target)
out=dict(binding_count=len(sealed['bound_sha256']),changed=changed,postprocess_source_unchanged=True,
         tests=results,report_local_links=len(links),
         head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         changed_tracked=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines(),
         no_physical_rerun=True,no_eigensolver=True,no_push=True)
Path('runs/h2_ci_layer_audit_v0/final_verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
