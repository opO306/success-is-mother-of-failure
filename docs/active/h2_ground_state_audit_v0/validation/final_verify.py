"""Byte provenance, actual JUnit results, source snapshots and document links."""
import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from electronic_pilot.ground_state_audit_v0.io import read, sha, verify, write


def execute(main, output):
    root=Path.cwd()
    package=root/'docs/active/h2_ground_state_audit_v0'
    evidence=package/'evidence'
    seal=read(evidence/'execution_seal.json')
    count=verify(seal['bound_sha256'],root,main)
    raw=read(evidence/'raw_manifest.json')
    for name,record in raw['files'].items():
        path=root/Path(raw['source'])/name
        assert sha(path)==record['sha256']
        if record['committed_as_compact_evidence']:
            assert path.read_bytes()==(evidence/name).read_bytes()
    sources=[]
    for path in sorted((root/'electronic_pilot/ground_state_audit_v0').iterdir()):
        if path.suffix in ('.py','.json','.md'):
            sources.append(path)
    sources+=sorted((root/'tests/h2_ground_state_audit_v0').glob('*.py'))
    for path in sources:
        label=path.relative_to(root).as_posix().replace('/','__')+'.txt'
        assert path.read_bytes()==(package/'source'/label).read_bytes()
    tests={}
    for name,expected in [('related_windows',147),('related_wsl',150)]:
        p=package/'validation'/(name+'.xml')
        tree=ET.parse(p).getroot()
        cases=list(tree.iter('testcase'))
        errors=sum(len(list(tree.iter(tag))) for tag in ('failure','error','skipped'))
        assert len(cases)==expected and errors==0
        tests[name]=dict(passed=len(cases),failure_error_skip=errors,junit_sha256=sha(p))
    allowed={'CURRENT_STATE.md','REPO_MAP.md','docs/README.md','docs/DOCUMENT_STATUS_INDEX.md'}
    changed=subprocess.check_output(['git','diff','HEAD','--name-only'],encoding='utf-8').splitlines()
    preexisting=[p for p in changed if subprocess.run(['git','cat-file','-e',seal['spec']['base_commit']+':'+p],capture_output=True).returncode==0]
    assert set(preexisting)<=allowed,preexisting
    report=root/'docs/active/H2_R04_GROUND_STATE_INDEPENDENT_VALIDATION_V0.md'
    broken=[]
    for name in (report,package/'README.md'):
        for link in re.findall(r'\]\(([^)]+)\)',name.read_text(encoding='utf-8')):
            if '://' not in link and not (name.parent/link.split('#')[0]).exists():
                broken.append(link)
    assert not broken,broken
    write(output,dict(status='VERIFIED',protected_bindings=count,source_snapshots=len(sources),
          raw_and_compact_byte_equality=True,tests=tests,
          preexisting_changed_files=preexisting,existing_execution_shared_contract_fixture_changed=False,
          document_links='MATCH',LOCAL_FULL='omitted; related tests substitute; new isolated analysis/tests/documents only',
          certification='NOT CERTIFIED',designer_decision_required=True))
    print('VERIFIED',count,'bindings;',len(sources),'source snapshots; Windows147/WSL150, skip0',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--main',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    execute(args.main,args.output)
