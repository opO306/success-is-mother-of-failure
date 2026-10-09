"""Remote administrative regression and writer for the actual SSH disconnection."""
from pathlib import Path
import json,os,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
for key in ('PYTHONOPTIMIZE','PYTEST_ADDOPTS','PYTEST_PLUGINS','PYTHONPATH'):env.pop(key,None)
ini=root/'pytest.ini';ini.write_text('[pytest]\n')
result=subprocess.run([sys.executable,'-B','-m','pytest',str(root/'test_read_retry.py'),'-q','--noconftest','-c',str(ini),'-p','no:cacheprovider','--junitxml='+str(root/'repair_junit.xml')],capture_output=True,timeout=15,env=env)
(root/'repair.stdout').write_bytes(result.stdout);(root/'repair.stderr').write_bytes(result.stderr)
cases=ET.parse(root/'repair_junit.xml').getroot().findall('.//testcase') if (root/'repair_junit.xml').exists() else []
passed=result.returncode==0 and len(cases)==5 and len({c.attrib['classname']+'::'+c.attrib['name'] for c in cases})==5 and not any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped'))
(root/'repair_result.json').write_text(json.dumps(dict(returncode=result.returncode,tests=len(cases),passed=passed)))
if not passed:raise SystemExit(2)
time.sleep(60)
with (root/'probe_written.json').open('x') as f:json.dump(dict(complete=True,scope='ADMIN_ONLY_NO_A_OR_PHYSICS'),f);f.flush();os.fsync(f.fileno())
