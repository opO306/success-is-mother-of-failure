"""Remote Linux administrative mock tests; raw stdout/JUnit returned on SSH stdout."""
import base64
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import zipfile

if __name__=='__main__':
    root,expected,archive_sha=sys.argv[1:]
    root=Path(root)
    ids=[part.split(b'=',1)[1] for part in Path('/proc/1/environ').read_bytes().split(b'\0') if part.startswith(b'CONTAINER_ID=')]
    if ids!=[expected.encode()] or sys.platform!='linux':raise ValueError('ADMIN_ACTUAL_INSTANCE_MISMATCH')
    archive=root/'admin.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=archive_sha:raise ValueError('ADMIN_PAYLOAD_RAW_HASH')
    source=root/'source';source.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if name.startswith('/') or '\\' in name or ':' in name or any(p in ('','.','..') for p in name.split('/')):raise ValueError('ADMIN_MEMBER_PATH')
        z.extractall(source)
    base=source/'docs/active/project_vast_budget_cleanup_v1/revision_v12'
    previous=source/'docs/active/project_vast_budget_cleanup_v1/revision_v11'
    ini=root/'pytest.ini';ini.write_text('[pytest]\n')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    env['V12_TEST_ARTIFACT_ROOT']=str(root/'process_cases')
    for key in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'):env.pop(key,None)
    start=time.monotonic_ns()
    first=subprocess.run([sys.executable,'-B','-m','pytest',str(previous/'tests/test_terminal_finality.py'),
        str(previous/'tests/test_operations.py')+'::test_direct_destroy_without_final_files_has_zero_provider_calls',
        str(previous/'tests/test_known_transport_faults.py')+'::test_direct_writer_marker_without_final_files_has_zero_delete_calls',
        '-q','--noconftest','-c',str(ini),'-p','no:cacheprovider','--basetemp='+str(root/'v11_tmp'),'--junitxml='+str(root/'v11_first10.xml')],cwd=source,env=env,capture_output=True,timeout=30)
    (root/'v11_first10.stdout').write_bytes(first.stdout);(root/'v11_first10.stderr').write_bytes(first.stderr)
    import xml.etree.ElementTree as ET
    cases=ET.parse(root/'v11_first10.xml').getroot().findall('.//testcase') if (root/'v11_first10.xml').is_file() else []
    first_ok=first.returncode==0 and len(cases)==10 and len({c.attrib['classname']+'::'+c.attrib['name'] for c in cases})==10 and not any(c.find(t) is not None for c in cases for t in ('failure','error','skipped'))
    if first_ok:
        result=subprocess.run([sys.executable,'-B','-m','pytest',str(base/'tests'),'-q','--noconftest',
            '-c',str(ini),'-p','no:cacheprovider','--basetemp='+str(root/'v12_tmp'),'--junitxml='+str(root/'junit.xml')],cwd=source,env=env,capture_output=True,timeout=90)
    else:
        result=subprocess.CompletedProcess([],2,first.stdout,first.stderr)
        if (root/'v11_first10.xml').exists():(root/'junit.xml').write_bytes((root/'v11_first10.xml').read_bytes())
    (root/'stdout.log').write_bytes(result.stdout);(root/'stderr.log').write_bytes(result.stderr)
    payload=dict(returncode=result.returncode,wall_ns=time.monotonic_ns()-start,instance_id=int(expected),
        stdout_b64=base64.b64encode(result.stdout).decode(),stderr_b64=base64.b64encode(result.stderr).decode(),
        junit_b64=base64.b64encode((root/'junit.xml').read_bytes()).decode() if (root/'junit.xml').is_file() else None,
        source_zip_sha256=archive_sha,role='TEST_ONLY_ADMIN_MOCKS_NOT_B95_OR_A320')
    payload.update(v11_first10_passed=first_ok,v11_first10_returncode=first.returncode,
        v11_first10_junit_b64=base64.b64encode((root/'v11_first10.xml').read_bytes()).decode() if (root/'v11_first10.xml').exists() else None,
        v11_first10_stdout_b64=base64.b64encode(first.stdout).decode(),v11_first10_stderr_b64=base64.b64encode(first.stderr).decode())
    (root/'result.json').write_text(json.dumps(payload,sort_keys=True))
    print(json.dumps(payload,sort_keys=True))
