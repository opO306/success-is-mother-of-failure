"""Actual remote administrative tests only; original archived inputs reused, A not run."""
from pathlib import Path,PurePosixPath
import json,sys,hashlib,zipfile,stat,os,subprocess,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
original_root=Path(sys.argv[1]);expected=sys.argv[2]
ids=[v.split(b'=',1)[1].decode() for v in Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'CONTAINER_ID=')]
if ids!=[expected]:raise ValueError('ADMIN_ACTUAL_INSTANCE_ID')
archive=original_root/'admin.zip'
if hashlib.sha256(archive.read_bytes()).hexdigest()!='d2c0f490dcf3f2676304f68ece3bd23cb8abae2fe56b1b36138b0f3833777199':raise ValueError('ORIGINAL_ADMIN_INPUT_ARCHIVE_PIN')
source=root/'process_cases/regression_inputs';source.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(archive) as z:
    names=z.namelist()
    if len(names)!=999 or len(set(names))!=999 or len(set(n.casefold() for n in names))!=999 or z.testzip():raise ValueError('EXACT_ADMIN_INPUT_MEMBERS')
    for i in z.infolist():
        n=i.filename
        if PurePosixPath(n).is_absolute() or '\\' in n or ':' in n or any(p in ('','.','..') for p in n.split('/')) or i.is_dir() or i.flag_bits&1 or stat.S_IFMT(i.external_attr>>16) not in (0,stat.S_IFREG):raise ValueError('ADMIN_MEMBER_SCOPE')
    z.extractall(source)
base=source/'docs/active/project_vast_budget_cleanup_v1/revision_v12'
metadata=json.loads((root/'admin_test_inventory.json').read_bytes())
ini=root/'pytest.ini';ini.write_text('[pytest]\n')
env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',V12_2_ORIGINAL_BASE=str(base))
for key in ('PYTHONOPTIMIZE','PYTEST_ADDOPTS','PYTEST_PLUGINS','PYTHONPATH'):env.pop(key,None)
paths=[str(root/'test_read_retry.py'),str(root/'test_transport_reads.py')]+[str(base/'tests'/n) for n in metadata['original_test_files']]
r=subprocess.run([sys.executable,'-B','-m','pytest',*paths,'-q','--noconftest','-c',str(ini),'-p','no:cacheprovider','--basetemp='+str(root/'v12_tmp'),'--junitxml='+str(root/'repair_junit.xml')],cwd=source,env=env,capture_output=True,timeout=70)
(root/'repair.stdout').write_bytes(r.stdout);(root/'repair.stderr').write_bytes(r.stderr)
cases=ET.parse(root/'repair_junit.xml').getroot().findall('.//testcase') if (root/'repair_junit.xml').exists() else []
names={c.attrib['name'].split('[',1)[0] for c in cases}
passed=r.returncode==0 and len(cases)>0 and len({c.attrib['classname']+'::'+c.attrib['name'] for c in cases})==len(cases) and set(metadata['required_functions']).issubset(names) and not any(c.find(t) is not None for c in cases for t in ('failure','error','skipped'))
(root/'repair_result.json').write_text(json.dumps(dict(returncode=r.returncode,tests=len(cases),passed=passed,required_functions_verified=passed,scope='TEST_ONLY_ADMIN_NOT_A320',original_test_files=metadata['original_test_files'])))
raise SystemExit(0 if passed else 2)
