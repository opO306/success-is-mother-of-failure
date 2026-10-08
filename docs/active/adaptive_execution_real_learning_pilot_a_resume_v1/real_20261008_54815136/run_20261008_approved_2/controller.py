"""Approved one-instance administrative transport. Local code never runs physics/tests."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import uuid
from datetime import datetime,timezone
from decimal import Decimal

ROOT=Path.cwd()
OUT=Path(__file__).resolve().parent
CLI='C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe'
KEY='C:/Users/zun24/.ssh/vast_ai'
INSTANCE=54815136
CODE='ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60'
PROTO='36ca06d984a791e491a25f377f34448a4cb88ad6716a2b09190a4b44d80f22c1'
ZIP_HASH='458a1d9e38964c45021d58ae5c91c1b669e9a3bbbd9782b43d5b6b308b8b2cbd'
PILOT=ROOT/'experiments/adaptive_execution_real_learning_pilot_v0'
SAFETY=hashlib.sha256((PILOT/'a_safety_policy.json').read_bytes()).hexdigest()
GUARD=hashlib.sha256((PILOT/'guardian.py').read_bytes()).hexdigest()
SOURCE=ROOT/'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/source_6c73ad2a/source_6c73ad2a.zip'
REF='2026-10-08 human: 승인 — 같은 서버 재시작 후 제한 시험과 실측 A 진행; code='+CODE
GUEST='/workspace/a_resume_20261008_'+uuid.uuid4().hex[:12]
VENV='/workspace/rlp_A_8d4115e5/venv/bin/python'
events=[]
allocation_ns=None
guardian=None
relay=None
ssh_argv=None
host=None
armed=None

def utc(): return datetime.now(timezone.utc).isoformat()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(canonical(obj)); f.flush(); os.fsync(f.fileno())
def emit(status,**kw):
    obj=dict(status=status,observed_utc=utc(),monotonic_ns=time.monotonic_ns(),**kw)
    events.append(obj)
    with (OUT/'events.jsonl').open('ab') as f:f.write(canonical(obj)+b'\n');f.flush()
    print(json.dumps(obj,ensure_ascii=True),flush=True)
@contextlib.contextmanager
def phase(name):
    start=time.monotonic_ns(); emit('PHASE_BEGIN',phase=name)
    try:yield
    finally:emit('PHASE_END',phase=name,start_ns=start,end_ns=time.monotonic_ns())
def api(*argv):
    result=subprocess.run([CLI,'--raw','--retry','1',*argv],capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError('VAST_API_COMMAND_FAILED:'+argv[0])
    return json.loads(result.stdout) if argv[0]=='show' else {'command_exit_code':0}
def show():
    s=api('show','instance',str(INSTANCE)); country=s.get('country') or str(s.get('geolocation','')).rsplit(',',1)[-1].strip()
    record={k:s.get(k) for k in ('id','machine_id','actual_status','intended_status','dph_total','cpu_name','cpu_cores','cpu_cores_effective','cpu_ram','ssh_host','ssh_port','image_uuid')}
    record['country']=country
    if int(s['id'])!=INSTANCE or s.get('machine_id')!=56006 or country!='FR':raise ValueError('EXACT_INSTANCE_HOST_SCOPE')
    rate=Decimal(str(s['dph_total']))
    if not rate.is_finite() or not 0<=rate<=Decimal('0.25'):raise ValueError('APPROVED_PRICE_CAP')
    return record
def require_control():
    if guardian is None or guardian.poll() is not None or (OUT/'guardian/final.json').exists():raise RuntimeError('OUTSIDE_GUARDIAN_STOPPED')
    pulse=json.loads((OUT/'guardian/heartbeat.json').read_bytes())
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(pulse['control_checked_utc'])).total_seconds()
    if pulse.get('status')!='CONTROL_OK' or not -2<=age<=45:raise RuntimeError('OUTSIDE_CONTROL_NOT_FRESH')
def ssh(command,name,timeout=60,input=None):
    require_control()
    with (OUT/(name+'.stdout')).open('xb') as stdout,(OUT/(name+'.stderr')).open('xb') as stderr:
        result=subprocess.run([*ssh_argv,command],input=input,stdout=stdout,stderr=stderr,timeout=timeout)
    emit('TRANSPORT_EXIT',name=name,returncode=result.returncode)
    if result.returncode:raise RuntimeError('REMOTE_PHASE_FAILED:'+name)
    return (OUT/(name+'.stdout')).read_bytes()
def py(script,name,python='python3',timeout=60):
    return ssh(shlex.quote(python)+' -c '+shlex.quote(script),name,timeout)
def upload(obj,path,name):
    script="import os,sys,pathlib; p=pathlib.Path(sys.argv[1]); r=sys.stdin.buffer.read(); f=p.open('xb'); f.write(r); f.flush(); os.fsync(f.fileno()); f.close()"
    ssh('python3 -c '+shlex.quote(script)+' '+shlex.quote(path),name,input=canonical(obj))
def bounded_background(argv,prefix):
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    proc=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=(OUT/(prefix+'.stdout')).open('xb'),
             stderr=(OUT/(prefix+'.stderr')).open('xb'),creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    write(OUT/(prefix+'_pid.json'),dict(pid=proc.pid,argv=argv,observed_utc=utc()))
    return proc
def module_command(module,args):
    return 'cd '+shlex.quote(GUEST+'/source')+' && env CONTAINER_ID='+str(INSTANCE)+' PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='+shlex.quote(GUEST+'/source')+' '+shlex.quote(VENV)+' -m '+module+' '+args
def recover():
    if ssh_argv is None or armed is None:return
    script="""
from pathlib import Path
import hashlib,json,zipfile
root=Path(%r); files={}
for folder in ('authorization','output_offline','output_actual'):
    if (root/folder).exists():
        for p in (root/folder).rglob('*'):
            if p.is_file():files[p.relative_to(root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
if (root/'preflight.json').exists():files['preflight.json']=hashlib.sha256((root/'preflight.json').read_bytes()).hexdigest()
body={'schema':'A_RESUME_V1_RAW_EVIDENCE_MANIFEST','code_seal_sha256':%r,'instance_id':%r,'files':files}
raw=json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
with (root/'evidence_manifest.json').open('xb') as f:f.write(raw)
with zipfile.ZipFile(root/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(files):z.write(root/rel,rel)
    z.writestr('evidence_manifest.json',raw)
print(json.dumps({'files':len(files),'sha256':hashlib.sha256((root/'evidence.zip').read_bytes()).hexdigest()}))
"""%(GUEST,CODE,INSTANCE)
    package=json.loads(py(script,'package_evidence',timeout=60)); write(OUT/'remote_package.json',package)
    dest=OUT/'evidence.zip'
    result=subprocess.run(['scp','-O','-i',KEY,'-P',str(host['ssh_port']),'-o','BatchMode=yes','-o','ConnectTimeout=5',
          'root@'+host['ssh_host']+':'+GUEST+'/evidence.zip',str(dest)],capture_output=True,timeout=60)
    if result.returncode:raise RuntimeError('RAW_EVIDENCE_DOWNLOAD_FAILED')
    if sha(dest.read_bytes())!=package['sha256']:raise ValueError('RECOVERED_ZIP_INTEGRITY')
    import zipfile
    with zipfile.ZipFile(dest) as z:
        manifest=json.loads(z.read('evidence_manifest.json'))
        if set(z.namelist())!=set(manifest['files'])|{'evidence_manifest.json'}:raise ValueError('RAW_ARCHIVE_SCOPE')
        for rel,wanted in manifest['files'].items():
            raw=z.read(rel)
            if sha(raw)!=wanted:raise ValueError('RAW_RECOVERY_HASH:'+rel)
            path=OUT/'recovered'/rel
            if not path.resolve().is_relative_to((OUT/'recovered').resolve()):raise ValueError('RAW_PATH_SCOPE')
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:f.write(raw)
        with (OUT/'evidence_manifest.json').open('xb') as f:f.write(z.read('evidence_manifest.json'))
    write(OUT/'recovery_verified.json',dict(files=len(manifest['files']),zip_sha256=sha(dest.read_bytes()),all_raw_hashes_match=True))
    emit('RAW_RECOVERY_VERIFIED',files=len(manifest['files']))

def main():
    global allocation_ns,guardian,relay,ssh_argv,host,armed
    # Only raw hashing before paid start; no local project import/test/physics.
    seal_path=ROOT/'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'
    if sha(seal_path.read_bytes())!=CODE or sha(SOURCE.read_bytes())!=ZIP_HASH:raise ValueError('SEALED_SOURCE_PACKAGE')
    seal=json.loads(seal_path.read_bytes())
    for rel,wanted in seal['files'].items():
        if sha((ROOT/rel).read_bytes())!=wanted:raise ValueError('LOCAL_SOURCE_BYTES:'+rel)
    write(OUT/'administrative_controller_seal.json',dict(sha256=sha(Path(__file__).read_bytes()),scope='TRANSPORT_START_STOP_ONLY; NO_LOCAL_TESTS_PHYSICS',source_zip_sha256=ZIP_HASH))
    write(OUT/'human_authorization.json',dict(gate='ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_A_RESUME_V1',explicit_user_approval=True,
        human_answer='승인 — 같은 서버 재시작 후 제한 시험과 실측 A 진행',approval_reference=REF,instance_id=INSTANCE,machine_id=56006,country='FR',
        code_seal_sha256=CODE,resume_protocol_sha256=PROTO,source_zip_sha256=ZIP_HASH,expected_tests=254,
        hourly_cap_usd='0.25',total_rental_cap_usd='0.25',allocation_seconds=3600,compute_seconds=3240,stages=['A'],
        approve_research_profile=True,observed_utc=utc(),physics_scope='N14_T1000_P163_WALL_MIN_ONLY; 10_MEASUREMENTS_1_REPLAY_1_LEARNED; GPU0'))
    initial=show(); write(OUT/'initial_instance.json',initial)
    if initial['actual_status'] not in ('exited','stopped'):raise ValueError('INITIAL_INSTANCE_NOT_EXCLUSIVELY_STOPPED')
    origin=json.loads((OUT.parent/'run_20261008_approved_1/allocation_start.json').read_bytes()); allocation_ns=origin['monotonic_ns']; started_utc=origin['observed_utc']
    write(OUT/'allocation_start.json',dict(monotonic_ns=allocation_ns,observed_utc=started_utc,provenance='BEFORE_AUTHORIZED_RESTART_API_CALL'))
    trigger='FAILED'; reason=None
    try:
        with phase('restart_and_wait'):
            response=api('start','instance',str(INSTANCE))
            write(OUT/'restart_ack.json',dict(command='start instance',instance_id=INSTANCE,acknowledged=True,observed_utc=utc()))
            expiry=time.monotonic()+120
            while time.monotonic()<expiry:
                host=show()
                if host['actual_status']=='running':break
                time.sleep(3)
            else:raise TimeoutError('RESTART_RUNNING_TIMEOUT')
            write(OUT/'running_instance.json',host)
            lease=dict(scope='STOP_CONTROL_ONLY',exclusive=True,explicit_user_approval=True,approval_reference=REF,
                instance_id=INSTANCE,machine_id=56006,country='FR',guardian_sha256=GUARD,
                completion_marker=str(OUT/'completion.json'),deadline_seconds=3420,stages=['A'],safety_policy_sha256=SAFETY,
                allocation_start_utc=started_utc,allocation_start_provenance='BEFORE_AUTHORIZED_RESTART_API_CALL')
            write(OUT/'lease.json',lease)
            guardian=bounded_background([sys.executable,str(PILOT/'guardian.py'),'--authorization',str(OUT/'lease.json'),
                 '--out',str(OUT/'guardian'),'--marker',str(OUT/'completion.json'),'--cli',CLI],'guardian')
            limit=time.monotonic()+30
            while time.monotonic()<limit:
                if (OUT/'guardian/armed.json').exists() and (OUT/'guardian/heartbeat.json').exists():break
                if guardian.poll() is not None:raise RuntimeError('GUARDIAN_ARMING_FAILED')
                time.sleep(0.25)
            else:raise TimeoutError('GUARDIAN_ARM_TIMEOUT')
            armed=json.loads((OUT/'guardian/armed.json').read_bytes()); require_control(); emit('OUTSIDE_GUARDIAN_ARMED',instance_id=INSTANCE)
        ssh_argv=['ssh','-i',KEY,'-p',str(host['ssh_port']),'-o','BatchMode=yes','-o','ConnectTimeout=5',
                  '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','root@'+host['ssh_host']]
        with phase('guest_prepare_and_upload'):
            setup="""
from pathlib import Path
import os,json,sys
actual=next((x.split(b'=',1)[1].decode() for x in Path('/proc/1/environ').read_bytes().split(b'\0') if x.startswith(b'CONTAINER_ID=')),None)
if actual!=%r:raise ValueError('ACTUAL_INSTANCE_MISMATCH')
root=Path(%r);root.mkdir(exist_ok=False);(root/'authorization').mkdir()
if not Path(%r).is_file():raise ValueError('PRESERVED_RUNTIME_MISSING')
print(json.dumps({'actual_container_id':actual,'guest_root':str(root),'python_runtime':%r}))
"""%(str(INSTANCE),GUEST,VENV,VENV)
            write(OUT/'guest_setup.json',json.loads(py(setup,'guest_setup')))
            relay=bounded_background([sys.executable,'-m','experiments.adaptive_execution_real_learning_pilot_a_resume_v1.heartbeat_relay',
                '--guardian-dir',str(OUT/'guardian'),'--guest-heartbeat',GUEST+'/authorization/heartbeat.json','--host',host['ssh_host'],
                '--port',str(host['ssh_port']),'--key',KEY,'--out',str(OUT/'relay.jsonl')],'relay')
            result=subprocess.run(['scp','-O','-i',KEY,'-P',str(host['ssh_port']),'-o','BatchMode=yes','-o','ConnectTimeout=5',
                str(SOURCE),'root@'+host['ssh_host']+':'+GUEST+'/source.zip'],capture_output=True,timeout=120)
            if result.returncode:raise RuntimeError('SOURCE_UPLOAD_FAILED')
            extract="""
from pathlib import Path
import zipfile,json,hashlib
root=Path(%r);archive=root/'source.zip'
if hashlib.sha256(archive.read_bytes()).hexdigest()!=%r:raise ValueError('SOURCE_ZIP_HASH')
with zipfile.ZipFile(archive) as z:
    seal=json.loads(z.read('experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'))
    if len(z.namelist())!=684 or len(z.namelist())!=len(set(z.namelist())):raise ValueError('SOURCE_ZIP_SCOPE')
    for rel,wanted in seal['files'].items():
        if hashlib.sha256(z.read(rel)).hexdigest()!=wanted:raise ValueError('SOURCE_RAW_HASH:'+rel)
    if set(z.namelist())!=set(seal['files'])|{'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'}:raise ValueError('SOURCE_ZIP_FILE_SET')
    for rel in z.namelist():
        if not (root/'source'/rel).resolve().is_relative_to((root/'source').resolve()):raise ValueError('SOURCE_PATH_SCOPE')
    z.extractall(root/'source')
print(json.dumps({'source_raw_files':len(seal['files']),'zip_entries':684,'hashes_match':True}))
"""%(GUEST,ZIP_HASH)
            write(OUT/'source_upload_verified.json',json.loads(py(extract,'source_extract')))
            preflight="""
from pathlib import Path
import os,platform,json,sys,importlib.metadata
import mpmath,psutil
root=Path(%r);sys.path.insert(0,str(root/'source'))
from experiments.adaptive_execution_real_learning_pilot_v0.runner import code_check
from experiments.adaptive_execution_v1 import environment as E,selector as S
env=E.collect();verified=S.cpu_verified(env);placements=S.placements(env)
if code_check()!=%r or not verified or 'W6' not in placements:raise ValueError('SOURCE_CPU_CORRECTNESS_OR_W6_REFUSED')
if env['mpmath_version']!='1.3.0' or env['mpmath_backend']!='python' or env['python']!='3.12.3':raise ValueError('APPROVED_ACCURACY_RUNTIME_DRIFT')
def text(p):
    path=Path(p);return path.read_text().strip() if path.exists() else None
memory_max=text('/sys/fs/cgroup/memory.max');memory_current=text('/sys/fs/cgroup/memory.current')
mem=psutil.virtual_memory();limit=int(memory_max) if memory_max and memory_max!='max' else mem.total
available=min(mem.available,limit-int(memory_current)) if memory_current else min(mem.available,limit)
if limit<2*1024**3 or available<2*1024**3:raise ValueError('TWO_GIB_HEADROOM_NOT_AVAILABLE')
body={'status':'PREFLIGHT_PASS','env':env,'cpu_verified':verified,'placements':placements,'memory_limit_bytes':limit,
      'cgroup_memory_current_bytes':None if memory_current is None else int(memory_current),'available_memory_bytes':available,
      'runtime_versions':{k:importlib.metadata.version(k) for k in ('mpmath','psutil','cryptography','pytest')},
      'boot_id':text('/proc/sys/kernel/random/boot_id'),'physics_calls':0,'gpu_calls':0,'code_seal_sha256':%r}
raw=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
with (root/'preflight.json').open('xb') as f:f.write(raw)
print(raw.decode())
"""%(GUEST,CODE,CODE)
            metadata=json.loads(py(preflight,'preflight',python=VENV));write(OUT/'preflight.json',metadata)
            pulse_expiry=time.monotonic()+15
            while time.monotonic()<pulse_expiry:
                if (OUT/'relay.jsonl').exists() and (OUT/'relay.jsonl').stat().st_size>0:break
                if relay.poll() is not None:raise RuntimeError('PULSE_RELAY_FAILED')
                time.sleep(0.5)
            else:raise TimeoutError('PULSE_RELAY_START_TIMEOUT')
            arm_digest=sha(canonical(armed))
            base=dict(gate='ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_A_RESUME_V1',explicit_user_approval=True,approval_reference=REF,
                  instance_id=INSTANCE,machine_id=56006,country='FR',code_seal_sha256=CODE,resume_protocol_sha256=PROTO,
                  safety_policy_sha256=SAFETY,hourly_cap_usd='0.25',heartbeat_path=GUEST+'/authorization/heartbeat.json',fresh_run_id=arm_digest)
            offline=dict(base,scope='OFFLINE_ONLY',physics_calls=0,gpu_calls=0)
            real=dict(base,scope='REAL_RESEARCH',stages=['A'],hourly_usd='0.25',approve_research_profile=True)
            for name,obj in [('armed.json',armed),('offline.json',offline),('real.json',real),('host.json',host)]:
                write(OUT/name,obj);upload(obj,GUEST+'/authorization/'+name,'upload_'+name)
        with phase('offline_gate'):
            cmd=module_command('experiments.adaptive_execution_real_learning_pilot_a_resume_v1.offline',
                '--authorization '+shlex.quote(GUEST+'/authorization/offline.json')+' --out '+shlex.quote(GUEST+'/output_offline'))
            ssh(cmd,'offline_gate',timeout=145)
            result=json.loads(py("from pathlib import Path;print(Path(%r).read_text())"%(GUEST+'/output_offline/status.json'),'offline_status'))
            write(OUT/'offline_status.json',result)
            if result.get('status')!='PASS' or result.get('tests')!=254 or result.get('failed')!=0 or result.get('skipped')!=0:raise ValueError('EXACT_254_GATE_NOT_PASSED')
            emit('REMOTE_OFFLINE_PASS',tests=254,wall_ns=result['wall_ns'],cpu_ns=result['cpu_ns'])
        with phase('real_A_runner'):
            require_control(); current=show()
            if current['actual_status']!='running':raise ValueError('INSTANCE_NOT_RUNNING_BEFORE_PHYSICS')
            upload(current,GUEST+'/authorization/host_before_actual.json','upload_host_before_actual')
            cmd=module_command('experiments.adaptive_execution_real_learning_pilot_v0.runner',
                '--authorization '+shlex.quote(GUEST+'/authorization/real.json')+' --host-observation '+shlex.quote(GUEST+'/authorization/host_before_actual.json')+
                ' --guardian '+shlex.quote(GUEST+'/authorization/armed.json')+' --offline-checks '+shlex.quote(GUEST+'/output_offline/status.json')+
                ' --out '+shlex.quote(GUEST+'/output_actual'))
            left=3240-(time.monotonic_ns()-allocation_ns)/1e9
            if left<900:raise TimeoutError('INSUFFICIENT_COMPUTE_BUDGET_BEFORE_A')
            ssh(cmd,'actual_A',timeout=left)
            report=json.loads(py("from pathlib import Path;print(Path(%r).read_text())"%(GUEST+'/output_actual/report.json'),'actual_report'))
            write(OUT/'actual_report.json',report);emit('REAL_A_FINISHED',result=report['status'])
            if report['status']!='REAL_LEARNING_LOOP_VALIDATED':raise ValueError('REAL_LOOP_NOT_VALIDATED')
            trigger='COMPLETED'
    except BaseException as error:
        reason=type(error).__name__+':'+str(error);emit('CONTROLLER_STOP',reason=reason)
    finally:
        with phase('recovery_and_hash'):
            try:recover()
            except BaseException as error:
                trigger='FAILED';emit('RECOVERY_FAILED',reason=type(error).__name__+':'+str(error))
        with phase('stop_confirmation'):
            write(OUT/'completion.json',dict(trigger=trigger,observed_utc=utc(),reason=reason))
            if guardian is not None:
                try:guardian.wait(timeout=195)
                except subprocess.TimeoutExpired:emit('GUARDIAN_CONFIRMATION_WAIT_EXPIRED')
            else:
                api('stop','instance',str(INSTANCE))
            if relay is not None:
                try:relay.wait(timeout=20)
                except subprocess.TimeoutExpired:relay.terminate();relay.wait(timeout=10)
            final=show();write(OUT/'final_instance.json',final)
            if final['actual_status'] not in ('exited','stopped'):
                emit('MANUAL_STOP_CONFIRMATION_REQUIRED',actual_status=final['actual_status'])
        total=time.monotonic_ns()-allocation_ns
        write(OUT/'closure.json',dict(controller_trigger=trigger,reason=reason,instance_id=INSTANCE,machine_id=56006,guest_root=GUEST,
            allocation_total_wall_ns=total,allocation_start_utc=started_utc,final_observed_utc=utc(),rate_estimate_only=True,
            estimated_rental_usd=str(Decimal(str(host['dph_total'] if host else initial['dph_total']))*Decimal(total)/Decimal(3600*10**9)),
            actual_shutdown=final['actual_status'],code_seal_sha256=CODE,source_zip_sha256=ZIP_HASH,invoice='UNCONFIRMED'))
        emit('CONTROLLER_CLOSED',trigger=trigger,actual_status=final['actual_status'],allocation_wall_ns=total)
    return 0 if trigger=='COMPLETED' and final['actual_status'] in ('exited','stopped') else 2

if __name__=='__main__':raise SystemExit(main())
