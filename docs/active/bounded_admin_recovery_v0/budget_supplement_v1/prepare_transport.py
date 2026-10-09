"""Local stdlib raw copy and preservation check only; never import or run transport."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=HERE.parent/'closure_v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())
def write(path,obj):
    with path.open('xb') as f: f.write((json.dumps(obj,sort_keys=True,indent=2)+'\n').encode())


def main():
    protocol=read(HERE/'budget_protocol.json')
    assert sha(OLD/'closure_seal.json')==protocol['previous_closure_seal_sha256']
    original=read(OLD/'closure_seal.json')
    for name,wanted in original['files'].items(): assert sha(ROOT/name)==wanted,name
    preservation=[]
    for item in read(OLD/'preservation_before.json')['checks']:
        manifest=ROOT/item['manifest']; assert sha(manifest)==item['raw_sha256']
        anchor=manifest.parent if manifest.name=='transport_seal_v3.json' else ROOT
        for name,wanted in read(manifest)['files'].items(): assert sha(anchor/name)==wanted,name
        preservation.append(dict(manifest=item['manifest'],files=item['files'],mismatches=[]))
    old_seal=OLD/'transport/transport_seal.json'
    assert sha(old_seal)==protocol['previous_transport_seal_sha256']
    target=HERE/'transport'; target.mkdir(exist_ok=False)
    reused={}
    for name,wanted in read(old_seal)['files'].items():
        source=OLD/'transport'/name; assert sha(source)==wanted
        with (target/name).open('xb') as f: f.write(source.read_bytes())
        reused[name]=dict(original_path=source.relative_to(ROOT).as_posix(),original_sha256=wanted,
                          action='COPY_RAW_THEN_VERSION_CONTROLLER_ONLY' if name=='controller.py' else 'COPY_RAW_UNCHANGED')
    write(HERE/'preservation_before.json',dict(previous_closure_files=len(original['files']),checks=preservation,
          previous_closure_seal_sha256=sha(OLD/'closure_seal.json'),previous_transport_seal_sha256=sha(old_seal),
          old_package_A_and_B_unchanged=True,local_project_tests=0,paid_actions=0,source_copies=reused))
    print(json.dumps(dict(previous_closure_files=len(original['files']),copied_transport_files=len(reused),paid_actions=0)))


if __name__=='__main__': main()
