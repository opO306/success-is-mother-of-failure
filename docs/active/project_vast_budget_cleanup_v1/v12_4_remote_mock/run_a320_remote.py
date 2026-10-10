"""Free remote-PC check (aic-2DESK-TOP): extract an A package byte-exact and run the protocol's offline test files.

Mirrors experiments/adaptive_experience_tablet_v0/offline.py's pytest command (same test files, -p no:cacheprovider,
physics guard plugin, junit) and guest_gate.py's environment (PYTHONPATH=source, cwd=source), pinned to ONE CPU like
offline.py's sched_setaffinity. Not the official gate: Windows, no ticket/guardian, no 120 s resource monitor.
  python -I run_a320_remote.py ZIP ZIP_SHA256 DEST OUT CASE_INVENTORY [--only NODEID]
"""
import argparse,hashlib,json,os,subprocess,sys,time,zipfile
from pathlib import Path,PurePosixPath
import xml.etree.ElementTree as ET
import psutil


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for name in ('zip','zip_sha256','dest','out','case_inventory'):p.add_argument(name)
    p.add_argument('--only');a=p.parse_args()
    raw=Path(a.zip).read_bytes()
    if sha(raw)!=a.zip_sha256:raise ValueError('ZIP_PIN')
    dest,out=Path(a.dest),Path(a.out)
    dest.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(a.zip) as z:
        for name in z.namelist():
            if name.startswith('/') or '..' in PurePosixPath(name).parts or '\\' in name:raise ValueError('PATH_SCOPE')
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(z.read(name))
    here=dest/'experiments/adaptive_experience_tablet_v0'
    for seal in ('protocol_seal.json','preservation_manifest.json','code_seal.json'):
        for rel,wanted in json.loads((here/seal).read_bytes())['files'].items():
            if sha((dest/rel).read_bytes())!=wanted:raise ValueError('EXTRACTED_SEAL:'+rel)
    files=json.loads((here/'protocol.json').read_bytes())['offline']['test_files']
    targets=[a.only] if a.only else files
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONPATH=str(dest),
             EVIDENCE_PHYSICS_GUARD_REPORT=str(out.resolve()/'physics_guard.json'))
    for key in ('PYTEST_ADDOPTS','PYTEST_PLUGINS'):env.pop(key,None)
    me=psutil.Process();cpus=me.cpu_affinity();me.cpu_affinity([min(cpus)])
    start=time.monotonic_ns()
    with (out/'tests.log').open('xb') as log:
        proc=subprocess.run([sys.executable,'-B','-m','pytest',*targets,'-q','-p','no:cacheprovider','-p',
                             'experiments.evidence_canonicalization_v0.physics_guard','--junitxml='+str(out.resolve()/'junit.xml')],
                            cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
    wall=time.monotonic_ns()-start
    cases=ET.parse(out/'junit.xml').getroot().findall('.//testcase')
    ids=[c.attrib['classname']+'::'+c.attrib['name'] for c in cases]
    bad={t:[i for c,i in zip(cases,ids) if c.find(t) is not None] for t in ('failure','error','skipped')}
    expected=json.loads(Path(a.case_inventory).read_bytes())['ids']
    guard=json.loads((out/'physics_guard.json').read_bytes()) if (out/'physics_guard.json').exists() else None
    result=dict(role='FREE_REMOTE_PC_MOCK_NOT_OFFICIAL_GATE',zip_sha256=a.zip_sha256,only=a.only,returncode=proc.returncode,
                tests=len(cases),unique=len(set(ids)),failed=bad['failure'],errors=bad['error'],skipped=bad['skipped'],
                ids_equal_case_inventory=(set(ids)==set(expected)) if not a.only else None,wall_seconds=wall/1e9,
                cpu_affinity=me.cpu_affinity(),cpu_count=os.cpu_count(),python=sys.version,
                guard_blocked_attempts=None if guard is None else guard.get('blocked_attempts'),
                junit_sha256=sha((out/'junit.xml').read_bytes()),tests_log_sha256=sha((out/'tests.log').read_bytes()))
    (out/'result.json').write_bytes(json.dumps(result,sort_keys=True,indent=2).encode())
    print(json.dumps({k:result[k] for k in ('returncode','tests','failed','errors','skipped','ids_equal_case_inventory','wall_seconds')}))


if __name__=='__main__':main()
