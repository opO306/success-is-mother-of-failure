"""Administrative transport/control only; every test executes on the approved guest."""
import hashlib,json,os,subprocess,sys,time,zipfile
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CLI=Path('C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe')
KEY=Path('C:/Users/zun24/.ssh/vast_ai')
INSTANCE=54815136
APPROVAL='user_reply_call_795c1551452041189ec0e4a9f50ece0d_approval_20261008'
REMOTE='/workspace/evidence_v0_d4b65b00_20261008_approved'
VENV='/workspace/rlp_A_8d4115e5/venv/bin/python'
SOURCE=ROOT/'docs/active/evidence_canonicalization_v0/source_d4b65b00/source_d4b65b00.zip'
GUARD=ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
SSH=['ssh','-i',str(KEY),'-p','26992','-o','BatchMode=yes','-o','ConnectTimeout=5',
     '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','root@ssh9.vast.ai']
SCP=['scp','-i',str(KEY),'-P','26992','-o','BatchMode=yes','-o','ConnectTimeout=5']
FIELDS=('id','machine_id','actual_status','intended_status','geolocation','dph_total','ssh_host','ssh_port','label')

def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,obj):
    with (HERE/name).open('xb') as stream:stream.write(json.dumps(obj,indent=2,sort_keys=True).encode())
def progress(message):print(utc()+' '+message,flush=True)
def call(argv,timeout):return subprocess.run([str(x) for x in argv],capture_output=True,timeout=timeout)
def show():
    result=call([CLI,'--raw','--retry','1','show','instance',str(INSTANCE)],12)
    if result.returncode:raise RuntimeError('CONTROL_SHOW_FAILED')
    obj=json.loads(result.stdout)
    if obj.get('instances'):obj=obj['instances']
    if obj['id']!=INSTANCE or obj['machine_id']!=56006 or obj['geolocation']!='France, FR':raise RuntimeError('EXACT_INSTANCE_MISMATCH')
    rate=Decimal(str(obj['dph_total']))
    if not rate.is_finite() or not Decimal(0)<=rate<=Decimal('0.25'):raise RuntimeError('PRICE_REFUSED')
    return {field:obj.get(field) for field in FIELDS}
def remote(command,name,timeout):
    result=call(SSH+[command],timeout)
    (HERE/name).write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('REMOTE_PHASE_FAILED:'+name+':'+str(result.returncode))
    return result

def recover():
    remote(VENV+' '+REMOTE+'/recover_remote.py','recovery.log',30)
    for name in ('evidence.zip','evidence_manifest.json'):
        result=call(SCP+['root@ssh9.vast.ai:'+REMOTE+'/'+name,str(HERE/name)],30)
        if result.returncode:raise RuntimeError('EVIDENCE_TRANSFER_FAILED:'+name)
    manifest=json.loads((HERE/'evidence_manifest.json').read_bytes())
    recovered=HERE/'recovered';recovered.mkdir(exist_ok=False)
    with zipfile.ZipFile(HERE/'evidence.zip') as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(manifest['files']):raise RuntimeError('RECOVERY_ZIP_NAMES')
        for name,expected in manifest['files'].items():
            path=Path(name)
            if path.is_absolute() or '..' in path.parts:raise RuntimeError('RECOVERY_PATH')
            raw=z.read(name)
            if hashlib.sha256(raw).hexdigest()!=expected:raise RuntimeError('RECOVERY_RAW_HASH')
            target=recovered/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    save('recovery_verified.json',dict(files=len(manifest['files']),zip_sha256=sha(HERE/'evidence.zip'),
         manifest_sha256=sha(HERE/'evidence_manifest.json'),verified_utc=utc(),scope='ADMIN_RAW_BYTES_ONLY'))
    return recovered

guard=None;begin=None;gate_rc=None;recovery_ok=False;failure=None
try:
    if sha(SOURCE)!='a9ca1b08451e915205d6c2a0c0b5da57e26a349e0cd38c94fd068bc0e80037ab':raise RuntimeError('SOURCE_ZIP_HASH')
    seal=ROOT/'experiments/evidence_canonicalization_v0/code_seal.json'
    if sha(seal)!='8ad79b9e4655ef29ea1ab14f94cfa863db8f7c3214e39ebdea201d341f6e79de':raise RuntimeError('CODE_SEAL_HASH')
    for name,expected in json.loads(seal.read_bytes())['files'].items():
        if sha(ROOT/name)!=expected:raise RuntimeError('SOURCE_FILE_HASH:'+name)
    initial=show();save('initial_instance.json',initial)
    if initial['actual_status'] not in ('exited','stopped') or initial['label']!='adaptive-A-20261008-8d4115e5':raise RuntimeError('RESTART_EXCLUSIVITY_REFUSED')
    allocation=utc();begin=time.monotonic()
    save('restart_authorization.json',dict(explicit_user_approval=True,approval_reference=APPROVAL,instance_id=INSTANCE,
         machine_id=56006,country='FR',allocation_start_utc=allocation,scope='EVIDENCE_OFFLINE_ONLY',physics_calls=0,gpu_calls=0,
         total_cap_usd='0.10',hourly_cap_usd='0.25',allocation_seconds=600))
    result=call([CLI,'--raw','--retry','1','start','instance',str(INSTANCE)],15)
    save('restart_result.json',dict(returncode=result.returncode,observed_utc=utc(),raw_response_omitted=True))
    if result.returncode:raise RuntimeError('START_FAILED')
    progress('APPROVED_INSTANCE_START_REQUESTED')
    while time.monotonic()-begin<42:
        state=show()
        if state['actual_status']=='running':break
        time.sleep(1)
    else:raise RuntimeError('START_NOT_RUNNING_WITHIN_ARM_BUDGET')
    save('running_instance.json',state)
    lease=dict(scope='STOP_CONTROL_ONLY',exclusive=True,explicit_user_approval=True,approval_reference=APPROVAL,
         guardian_sha256=sha(GUARD),completion_marker=str(HERE/'completion.json'),instance_id=INSTANCE,
         machine_id=56006,country='FR',deadline_seconds=300,allocation_start_utc=allocation,
         experiment_scope='EVIDENCE_OFFLINE_ONLY',hourly_cap_usd='0.25',total_cap_usd='0.10')
    save('lease.json',lease)
    guard=subprocess.Popen([sys.executable,str(GUARD),'--authorization',str(HERE/'lease.json'),'--out',str(HERE/'guardian'),
         '--marker',str(HERE/'completion.json'),'--cli',str(CLI)],stdout=(HERE/'guardian_stdout.log').open('xb'),
         stderr=(HERE/'guardian_stderr.log').open('xb'),creationflags=subprocess.CREATE_NO_WINDOW)
    save('guardian_pid.json',dict(pid=guard.pid))
    while time.monotonic()-begin<60 and not (HERE/'guardian/armed.json').exists():
        if guard.poll() is not None:raise RuntimeError('GUARDIAN_NOT_ARMED')
        time.sleep(.2)
    if not (HERE/'guardian/armed.json').exists():raise RuntimeError('ARM_WITHIN_START_60_FAILED')
    armed=json.loads((HERE/'guardian/armed.json').read_bytes())
    arm_time=datetime.fromisoformat(armed['armed_utc'])
    if not 0<=(arm_time-datetime.fromisoformat(allocation)).total_seconds()<=60:raise RuntimeError('ARM_ORIGIN_BUDGET')
    (HERE/'armed.json').write_bytes((HERE/'guardian/armed.json').read_bytes())
    progress('EXTERNAL_GUARDIAN_ARMED; NO_NEW_PHYSICS_OR_GPU')
    ticket=dict(gate='EVIDENCE_CANONICALIZATION_AND_LIGHTWEIGHT_VERIFICATION_V0',scope='EVIDENCE_OFFLINE_ONLY',
         explicit_user_approval=True,approval_reference=APPROVAL,instance_id=INSTANCE,machine_id=56006,country='FR',
         allocation_start_utc=allocation,code_seal_sha256=sha(seal),policy_sha256=sha(ROOT/'experiments/evidence_canonicalization_v0/protocol.json'),
         physics_calls=0,gpu_calls=0)
    save('authorization.json',ticket)
    prepare="""import hashlib,json,os,platform,zipfile\nfrom pathlib import Path\nfrom importlib.metadata import version\nr=Path(%r)\nenv=dict(x.split(b'=',1) for x in Path('/proc/1/environ').read_bytes().split(b'\\0') if b'=' in x)\nassert env[b'CONTAINER_ID']==b'54815136','ACTUAL_INSTANCE'\nassert platform.python_version().startswith('3.12.'),'PYTHON_VERSION'\nversions={n:version(n) for n in ['mpmath','psutil','cryptography','pytest']}\nassert versions['mpmath']=='1.3.0','MPMATH_VERSION'\nimport mpmath.libmp\nassert mpmath.libmp.BACKEND=='python','MPMATH_BACKEND'\nsrc=r/'src';src.mkdir(exist_ok=False)\nwith zipfile.ZipFile(r/'source_d4b65b00.zip') as z:\n for name in z.namelist():\n  assert not Path(name).is_absolute() and '..' not in Path(name).parts\n z.extractall(src)\nseal=json.loads((src/'experiments/evidence_canonicalization_v0/code_seal.json').read_bytes())\nfor name,expected in seal['files'].items():\n assert hashlib.sha256((src/name).read_bytes()).hexdigest()==expected,name\nmeta=dict(instance_id=54815136,versions=versions,python=platform.python_version(),platform=platform.platform(),sealed_files=len(seal['files']),mpmath_backend=mpmath.libmp.BACKEND,new_physics_calls=0,gpu_calls=0)\n(r/'preparation.json').write_text(json.dumps(meta,sort_keys=True))\nprint(json.dumps(meta,sort_keys=True))\n"""%REMOTE
    (HERE/'prepare_remote.py').write_text(prepare,encoding='utf-8')
    recovery="""import hashlib,json,zipfile\nfrom pathlib import Path\nr=Path(%r);files={}\nfor base in [r/'out']:\n if base.exists():\n  for p in sorted(base.rglob('*')):\n   if p.is_file():files[p.relative_to(r).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()\nfor name in ['launch.log','preparation.json','authorization.json','armed.json']:\n p=r/name\n if p.exists():files[name]=hashlib.sha256(p.read_bytes()).hexdigest()\nwith zipfile.ZipFile(r/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:\n for name in files:z.write(r/name,name)\n(r/'evidence_manifest.json').write_text(json.dumps(dict(files=files),sort_keys=True))\nprint('RECOVERY_FILES',len(files))\n"""%REMOTE
    (HERE/'recover_remote.py').write_text(recovery,encoding='utf-8')
    remote('mkdir '+REMOTE,'mkdir.log',12)
    result=call(SCP+[str(SOURCE),str(HERE/'prepare_remote.py'),str(HERE/'recover_remote.py'),str(HERE/'authorization.json'),
           str(HERE/'armed.json'),'root@ssh9.vast.ai:'+REMOTE+'/'],30)
    (HERE/'upload.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('SOURCE_UPLOAD_FAILED')
    remote(VENV+' '+REMOTE+'/prepare_remote.py','preparation.log',20)
    if (datetime.now(timezone.utc)-arm_time).total_seconds()>55:raise RuntimeError('GUEST_START_ARM_AGE_BUDGET')
    command='cd '+REMOTE+'/src && CONTAINER_ID=54815136 PYTHONDONTWRITEBYTECODE=1 '+VENV+' -m experiments.evidence_canonicalization_v0.offline --authorization '+REMOTE+'/authorization.json --out '+REMOTE+'/out > '+REMOTE+'/launch.log 2>&1'
    progress('REMOTE_194_TEST_GATE_STARTED')
    result=call(SSH+[command],140)
    (HERE/'gate_transport.log').write_bytes(result.stdout+result.stderr)
    gate_rc=result.returncode;save('gate_exit.json',dict(returncode=gate_rc,observed_utc=utc()))
    progress('REMOTE_GATE_EXIT '+str(gate_rc)+'; RECOVERING_IMMUTABLE_OUTPUT')
    recovered=recover();recovery_ok=True
    status_path=recovered/'out/status.json'
    status=json.loads(status_path.read_bytes()) if status_path.exists() else {'status':'NO_STATUS'}
    save('remote_status_snapshot.json',status)
    progress('RECOVERY_RAW_VERIFIED; STATUS '+status['status'])
except BaseException as error:
    failure=str(error);save('controller_failure.json',dict(error_type=type(error).__name__,reason=failure,observed_utc=utc()))
    progress('ADMIN_OR_GATE_FAILURE '+failure)
    if guard is not None and not recovery_ok and (HERE/'prepare_remote.py').exists():
        try:recover();recovery_ok=True
        except BaseException as recovery_error:save('recovery_failure.json',dict(error_type=type(recovery_error).__name__,reason=str(recovery_error)))
finally:
    if begin is not None:
        trigger='COMPLETED' if gate_rc==0 and recovery_ok and failure is None else 'FAILED'
        if guard is not None:
            if not (HERE/'completion.json').exists():save('completion.json',dict(trigger=trigger,created_utc=utc(),recovery_verified=recovery_ok))
            while guard.poll() is None and time.monotonic()-begin<590:time.sleep(1)
        else:
            result=call([CLI,'--raw','--retry','1','stop','instance',str(INSTANCE)],12)
            save('fallback_stop.json',dict(returncode=result.returncode,trigger=trigger))
            stop_start=time.monotonic()
            while time.monotonic()-stop_start<180:
                state=show()
                if state['actual_status'] in ('exited','stopped'):break
                time.sleep(5)
        try:
            final=show();save('final_instance.json',final)
            elapsed=Decimal(str(time.monotonic()-begin));rate=Decimal(str(final['dph_total']))
            confirmed=final['actual_status'] in ('exited','stopped')
            save('closure.json',dict(stop_confirmed=confirmed,trigger=trigger,allocation_window_seconds=str(elapsed),
                 time_charge_upper_estimate_usd=str(elapsed*rate/Decimal(3600)),invoice_verified=False,
                 transfer_storage_fees_verified=False,recovery_verified=recovery_ok,gate_returncode=gate_rc,
                 source_zip_sha256=sha(SOURCE),new_physics_calls=0,gpu_calls=0))
            progress('FINAL_ACTUAL '+final['actual_status']+'; WINDOW_SECONDS '+str(elapsed))
        except BaseException as close_error:
            save('closure_error.json',dict(error_type=type(close_error).__name__,manual_confirmation_required=True))
            progress('STOP_CONFIRMATION_NEEDS_ATTENTION')
sys.exit(0 if gate_rc==0 and recovery_ok and failure is None else 2)
