"""Fresh authorized one-server administrative transport; no local project imports/tests."""
import hashlib,json,os,pathlib,shlex,subprocess,sys,time,zipfile,math
from datetime import datetime,timezone
from decimal import Decimal

ROOT=pathlib.Path.cwd(); OUT=pathlib.Path(__file__).resolve().parent
INSTANCE=54815136; MACHINE=56006; COUNTRY='FR'
CLI=r'C:\Users\zun24\AppData\Local\Programs\Python\Python312\Scripts\vastai.exe'
KEY='C:/Users/zun24/.ssh/vast_ai'
SSH=['ssh','-i',KEY,'-p','26992','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','root@ssh9.vast.ai']
VENV='/workspace/rlp_A_8d4115e5/venv/bin/python'
GUEST='/workspace/tablet_v0_20261009_sealed_18a76f0e'
SOURCE=ROOT/'docs/active/adaptive_experience_tablet_v0/source_7b264a42/source_7b264a42.zip'
PKG=json.loads((SOURCE.parent/'package_manifest.json').read_bytes())
CODE=PKG['code_seal_sha256']; PROTO='f03bc97a79e1a22ece4964270032d8829f7a208e961c09806c8f7bc10351013c'
GUARD=ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
START=json.loads((OUT/'source_preflight.json').read_bytes())['observed_utc']
REF='2026-10-09 user authorized sealed tablet remote tests and costs; specified ssh -p 26992 root@ssh9.vast.ai; no code changes; 600s/$0.05 cap'
guardian=None; armed=None; remote_created=False; recovered=False; gate_rc=None; primary_error=None

def utc(): return datetime.now(timezone.utc).isoformat()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def age(): return (datetime.now(timezone.utc)-datetime.fromisoformat(START)).total_seconds()
def write(path,obj):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f: f.write(canonical(obj)); f.flush(); os.fsync(f.fileno())
def emit(event,**kw):
    obj=dict(event=event,observed_utc=utc(),allocation_age_s=age(),**kw)
    with (OUT/'events.jsonl').open('ab') as f: f.write(canonical(obj)+b'\n'); f.flush()
    print(json.dumps(obj,ensure_ascii=True),flush=True)
def show(name):
    result=subprocess.run([CLI,'--raw','--retry','1','show','instance',str(INSTANCE)],capture_output=True,timeout=20)
    (OUT/(name+'.stdout')).write_bytes(result.stdout); (OUT/(name+'.stderr')).write_bytes(result.stderr)
    if result.returncode: raise RuntimeError('INSTANCE_QUERY_FAILED')
    obj=json.loads(result.stdout); country=obj.get('country') or obj.get('geolocation','').rsplit(',',1)[-1].strip()
    if int(obj['id'])!=INSTANCE or obj.get('machine_id')!=MACHINE or country!=COUNTRY: raise ValueError('EXACT_SERVER_BINDING')
    rate=Decimal(str(obj['dph_total']))
    if not rate.is_finite() or not 0<=rate<=Decimal('0.25') or rate*600/3600>Decimal('0.05'): raise ValueError('PRICE_CAP')
    if obj.get('ssh_host')!='ssh9.vast.ai' or int(obj.get('ssh_port'))!=26992: raise ValueError('USER_SSH_BINDING')
    return obj
def control():
    if guardian is None or guardian.poll() is not None or (OUT/'guardian/final.json').exists(): raise RuntimeError('OUTSIDE_GUARDIAN_STOPPED')
    if age()>=410: raise TimeoutError('RECOVERY_DEADLINE')
def remote(script,name,*,python='python3',timeout=35,input=None,allow_failure=False):
    control(); command=shlex.quote(python)+' -c '+shlex.quote(script)
    with (OUT/(name+'.stdout')).open('xb') as a,(OUT/(name+'.stderr')).open('xb') as b:
        result=subprocess.run([*SSH,command],input=input,stdout=a,stderr=b,timeout=min(timeout,max(1,410-age())))
    emit('REMOTE_EXIT',phase=name,returncode=result.returncode)
    if result.returncode and not allow_failure: raise RuntimeError('REMOTE_PHASE_FAILED:'+name)
    return result.returncode,(OUT/(name+'.stdout')).read_bytes()
def upload(obj,name):
    path=GUEST+'/'+name
    script="import pathlib,sys,os; p=pathlib.Path(%r); f=p.open('xb'); f.write(sys.stdin.buffer.read()); f.flush(); os.fsync(f.fileno()); f.close()"%path
    return remote(script,'upload_'+name.replace('.','_'),input=canonical(obj))
def recover():
    global recovered
    if not remote_created: return
    script="""
import pathlib,hashlib,json,zipfile
base=pathlib.Path(%r); paths=[p for p in base.rglob('*') if p.is_file() and 'source' not in p.relative_to(base).parts and p.name not in ('source.zip','evidence.zip','evidence_manifest.json')]
files={p.relative_to(base).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
manifest=dict(scope='RAW_REMOTE_TABLET_OFFLINE_OUTPUT',instance_id=%r,code_sha256=%r,files=files)
(base/'evidence_manifest.json').write_bytes(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode())
with zipfile.ZipFile(base/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
 for name in sorted(files):z.writestr(name,(base/name).read_bytes())
 z.writestr('evidence_manifest.json',(base/'evidence_manifest.json').read_bytes())
print(json.dumps(dict(zip_sha256=hashlib.sha256((base/'evidence.zip').read_bytes()).hexdigest(),files=len(files))))
"""%(GUEST,INSTANCE,CODE)
    _,raw=remote(script,'package_output'); description=json.loads(raw)
    local_zip=OUT/'evidence.zip'
    command=['scp','-i',KEY,'-P','26992','-o','BatchMode=yes','-o','ConnectTimeout=10','root@ssh9.vast.ai:'+GUEST+'/evidence.zip',str(local_zip)]
    control(); result=subprocess.run(command,capture_output=True,timeout=min(30,max(1,410-age())))
    (OUT/'download.stdout').write_bytes(result.stdout); (OUT/'download.stderr').write_bytes(result.stderr)
    if result.returncode or sha(local_zip.read_bytes())!=description['zip_sha256']: raise ValueError('RECOVERY_ZIP_HASH')
    dest=OUT/'recovered'; dest.mkdir(exist_ok=False)
    with zipfile.ZipFile(local_zip) as z:
        if z.testzip() is not None or len(z.namelist())!=len(set(z.namelist())): raise ValueError('RECOVERY_ZIP_CRC_OR_DUPLICATE')
        manifest=json.loads(z.read('evidence_manifest.json'))
        for name,wanted in manifest['files'].items():
            path=(dest/name).resolve()
            if not path.is_relative_to(dest.resolve()) or sha(z.read(name))!=wanted: raise ValueError('RECOVERY_ENTRY_HASH')
        z.extractall(dest)
    write(OUT/'recovery_verified.json',dict(status='RAW_HASH_VERIFIED',zip_sha256=description['zip_sha256'],files=len(manifest['files']),mismatches=[],observed_utc=utc()))
    recovered=True; emit('RECOVERED',files=len(manifest['files']),zip_sha256=description['zip_sha256'])

try:
    if sha(SOURCE.read_bytes())!=PKG['zip_sha256'] or age()>=260: raise ValueError('PACKAGE_OR_REMAINING_ALLOCATION')
    host=show('fresh_instance'); write(OUT/'human_authorization.json',dict(scope='OFFLINE_ONLY',explicit_user_approval=True,approval_reference=REF,user_ssh='ssh -p 26992 root@ssh9.vast.ai -L 8080:localhost:8080',instance_id=INSTANCE,machine_id=MACHINE,country=COUNTRY,allocation_start_utc=START,allocation_seconds=600,hourly_cap_usd='0.25',total_cap_usd='0.05',code_sha256=CODE,protocol_sha256=PROTO,zip_sha256=PKG['zip_sha256']))
    if host['actual_status']!='running': raise ValueError('APPROVED_RUNNING_SERVER_REQUIRED_NO_RESTART')
    # Start 10s before the allocation recovery boundary, covering guardian's initial API latency.
    deadline_seconds=math.floor(410-age())
    lease=dict(scope='STOP_CONTROL_ONLY',exclusive=True,explicit_user_approval=True,approval_reference=REF,instance_id=INSTANCE,machine_id=MACHINE,country=COUNTRY,guardian_sha256=sha(GUARD.read_bytes()),completion_marker=str(OUT/'completion.json'),deadline_seconds=deadline_seconds)
    write(OUT/'lease.json',lease)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    guardian=subprocess.Popen([sys.executable,'-B',str(GUARD),'--authorization',str(OUT/'lease.json'),'--out',str(OUT/'guardian'),'--marker',str(OUT/'completion.json'),'--cli',CLI],cwd=ROOT,env=env,stdout=(OUT/'guardian.stdout').open('xb'),stderr=(OUT/'guardian.stderr').open('xb'),creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    write(OUT/'guardian_pid.json',dict(pid=guardian.pid,started_utc=utc()))
    start=time.monotonic()
    while not (OUT/'guardian/armed.json').exists():
        if guardian.poll() is not None or time.monotonic()-start>25: raise RuntimeError('GUARDIAN_NOT_ARMED')
        time.sleep(.25)
    armed=json.loads((OUT/'guardian/armed.json').read_bytes()); write(OUT/'armed.json',armed); emit('GUARDIAN_ARMED',deadline_seconds=armed['deadline_seconds'])
    probe="import os,sys,json,pathlib; print(json.dumps(dict(platform=sys.platform,python=sys.version,container_id=os.environ.get('CONTAINER_ID'),existing_venv=pathlib.Path(%r).exists(),affinity=sorted(os.sched_getaffinity(0)))))"%VENV
    _,raw=remote(probe,'guest_probe'); guest=json.loads(raw); write(OUT/'guest_probe.json',guest)
    if guest['platform']!='linux' or not guest['existing_venv'] or str(guest['container_id'])!=str(INSTANCE): raise ValueError('GUEST_SCOPE_OR_DEPENDENCY_RUNTIME')
    script="import pathlib,sys,os,hashlib; p=pathlib.Path(%r); p.mkdir(exist_ok=False); f=(p/'source.zip').open('xb'); raw=sys.stdin.buffer.read(); f.write(raw); f.flush(); os.fsync(f.fileno()); f.close(); print(hashlib.sha256(raw).hexdigest())"%GUEST
    remote_created=True
    _,raw=remote(script,'source_upload',input=SOURCE.read_bytes(),timeout=40)
    if raw.decode().strip()!=PKG['zip_sha256']: raise ValueError('UPLOAD_RAW_HASH')
    script="""
import pathlib,zipfile,json,hashlib,sys,platform,os
base=pathlib.Path(%r); source=base/'source'; source.mkdir()
with zipfile.ZipFile(base/'source.zip') as z:
 if len(z.namelist())!=813 or len(z.namelist())!=len(set(z.namelist())) or z.testzip() is not None: raise ValueError('ZIP_STRUCTURE')
 for name in z.namelist():
  if not (source/name).resolve().is_relative_to(source.resolve()):raise ValueError('ZIP_ESCAPE')
 z.extractall(source)
for relative in ('experiments/adaptive_experience_tablet_v0/code_seal.json','experiments/adaptive_experience_tablet_v0/preservation_manifest.json','experiments/adaptive_experience_tablet_v0/protocol_seal.json'):
 for name,wanted in json.loads((source/relative).read_bytes())['files'].items():
  if hashlib.sha256((source/name).read_bytes()).hexdigest()!=wanted:raise ValueError('RAW_SOURCE:'+name)
import mpmath,psutil,cryptography,pytest
print(json.dumps(dict(status='RAW_SOURCE_VERIFIED',platform=platform.platform(),python=sys.version,mpmath=mpmath.__version__,backend=mpmath.libmp.BACKEND,psutil=psutil.__version__,cryptography=cryptography.__version__,pytest=pytest.__version__,affinity=sorted(os.sched_getaffinity(0)))))
"""%GUEST
    _,raw=remote(script,'source_verify',python=VENV); write(OUT/'source_upload_verified.json',json.loads(raw))
    upload(armed,'armed.json')
    ticket=dict(gate='ADAPTIVE_EXPERIENCE_TABLET_CPU_ROUTE_V0',scope='OFFLINE_ONLY',explicit_user_approval=True,approval_reference=REF,instance_id=INSTANCE,machine_id=MACHINE,country=COUNTRY,code_sha256=CODE,protocol_sha256=PROTO,physics_calls=0,gpu_calls=0,armed_sha256=sha(canonical(armed)),allocation_start_utc=START,allocation_seconds=600)
    write(OUT/'offline_ticket.json',ticket); upload(ticket,'ticket.json')
    wrapper="""
import pathlib,subprocess,os,json,time
base=pathlib.Path(%r); environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(base/'source'))
with (base/'gate.stdout').open('xb') as a,(base/'gate.stderr').open('xb') as b:
 p=subprocess.run([%r,'-B','-m','experiments.adaptive_experience_tablet_v0.offline','--authorization',str(base/'ticket.json'),'--armed',str(base/'armed.json'),'--out',str(base/'output')],cwd=base/'source',env=environment,stdout=a,stderr=b,timeout=130)
(base/'gate_exit.json').write_text(json.dumps(dict(returncode=p.returncode,observed_ns=time.time_ns())))
print(json.dumps(dict(returncode=p.returncode)))
"""%(GUEST,VENV)
    _,raw=remote(wrapper,'offline_gate',timeout=140); gate_rc=json.loads(raw)['returncode']; emit('OFFLINE_GATE_FINISHED',returncode=gate_rc)
    recover()
except BaseException as error:
    primary_error=repr(error); emit('ADMIN_OR_GATE_ERROR',error=primary_error)
    if remote_created and not recovered and guardian is not None and guardian.poll() is None:
        try: recover()
        except BaseException as recovery_error: emit('RECOVERY_ERROR',error=repr(recovery_error))
finally:
    trigger='COMPLETED' if gate_rc==0 and recovered and primary_error is None else 'FAILED'
    if guardian is not None:
        if not (OUT/'completion.json').exists(): write(OUT/'completion.json',dict(trigger=trigger,observed_utc=utc(),recovered=recovered,gate_returncode=gate_rc,error=primary_error))
        emit('STOP_MARKER',trigger=trigger)
        try: guardian.wait(timeout=max(1,min(190,600-age())))
        except subprocess.TimeoutExpired: emit('GUARDIAN_CONFIRMATION_TIMEOUT')
    try:
        final=show('final_instance'); write(OUT/'final_instance.json',final)
        stopped=final.get('actual_status') in ('exited','stopped')
    except BaseException as error:
        stopped=False; emit('FINAL_STATUS_UNCONFIRMED',error=repr(error))
    write(OUT/'closure.json',dict(gate_returncode=gate_rc,recovery_verified=recovered,primary_error=primary_error,trigger=trigger,actual_stop_confirmed=stopped,allocation_start_utc=START,end_utc=utc(),observed_window_seconds=age(),estimated_window_usd=str(Decimal(str(host['dph_total']))*Decimal(str(age()))/3600) if 'host' in globals() else 'UNKNOWN',billing='THIS_TASK_OBSERVED_WINDOW_ONLY; EARLIER_RUNNING_ALLOCATION_START_AND_INVOICE_UNKNOWN',local_dynamic_tests=0,new_physics=0,gpu_calls=0,github_push=False,master_merge=False))
    emit('CLOSED',actual_stop_confirmed=stopped,recovered=recovered,gate_returncode=gate_rc)
