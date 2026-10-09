"""Approved administrative experiment entry. Verifies candidate inputs; never executes B95/A320."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import resource
import stat
import subprocess
import sys
import time
import zipfile
import psutil
from datetime import datetime,timezone

def sha(raw):return hashlib.sha256(raw).hexdigest()
def put(path,obj):
    with path.open('xb') as f:f.write(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False).encode())

if __name__=='__main__':
    guest,expected,zip_sha,inventory_sha,expected_tests,ticket_sha,armed_sha=sys.argv[1:]
    base=Path(guest)
    ids=[v.split(b'=',1)[1].decode('ascii') for v in Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'CONTAINER_ID=')]
    if ids!=[expected] or sys.version_info[:2]!=(3,12):raise ValueError('ACTUAL_PID1_OR_RUNTIME_MISMATCH')
    if base.parent!=Path('/workspace') or not base.name.startswith('tablet_v0_'):raise ValueError('EXCLUSIVE_ADMIN_ROOT_REQUIRED')
    allowed=sorted(os.sched_getaffinity(0));os.sched_setaffinity(0,{allowed[0]})
    resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    resource.setrlimit(resource.RLIMIT_CPU,(119,120))
    ticket_raw=(base/'admin_ticket.json').read_bytes();armed_raw=(base/'armed.json').read_bytes()
    if sha(ticket_raw)!=ticket_sha or sha(armed_raw)!=armed_sha:raise ValueError('ADMIN_SCOPE_ARM_RAW_HASH')
    ticket=json.loads(ticket_raw);armed=json.loads(armed_raw)
    fixed=dict(schema='HUMAN_PAID_ADMIN_VALIDATION_ONLY_V1',scope='ADMIN_SIMULATION_AND_ACTUAL_TRANSPORT_STOP_ONLY',
        explicit_user_approval=True,instance_id=int(expected),machine_id=150665,country='ES',package_kind='ADMIN',
        expected_tests=int(expected_tests),B95_authorized=False,A320_authorized=False,physics_calls=0,gpu_calls=0,
        allocation_seconds=600,compute_seconds=120,aggregate_cpu_seconds=120,cpu_affinity_count=1,memory_bytes=536870912,
        recovery_deadline_seconds=420,stop_confirmation_seconds=180,hourly_cap_usd='0.25',total_cap_usd='0.05',campaign_total_cap_usd='0.10')
    now=datetime.now(timezone.utc)
    first=datetime.fromisoformat(ticket['allocation_start_utc'])
    arm_time=datetime.fromisoformat(armed['armed_utc'])
    age=(now-first).total_seconds();arm_age=(arm_time-first).total_seconds()
    if (any(ticket.get(k)!=v for k,v in fixed.items()) or armed.get('status')!='ARMED'
        or armed.get('outside_guest') is not True or armed.get('confirmation_seconds')!=180
        or any(armed.get(k)!=ticket[k] for k in ('instance_id','machine_id','country','approval_reference'))
        or armed.get('guardian_sha256')!='2bd2dd3ea6f993c3234d77e963379f317015810d6af825bb74cab190f5750802'
        or ticket.get('armed_sha256')!=armed_sha or not 0<=arm_age
        or arm_age+armed['deadline_seconds']>420 or not 0<=age<150
        or age+140+96>=min(400,arm_age+armed['deadline_seconds'])
        or not 0<armed['deadline_seconds']<=400
        or not datetime.fromisoformat(ticket['approved_utc'])<=now<datetime.fromisoformat(ticket['expires_utc'])
        or not 0<=(now-datetime.fromisoformat(armed['armed_utc'])).total_seconds()<armed['deadline_seconds']-140):
        raise ValueError('ADMIN_APPROVED_SCOPE_OR_GUARDIAN_RESERVE')
    inv_raw=(base/'inventory.json').read_bytes();zip_raw=(base/'source.zip').read_bytes()
    if sha(inv_raw)!=inventory_sha or sha(zip_raw)!=zip_sha:raise ValueError('ADMIN_CANDIDATE_TRANSPORT_HASH_MISMATCH')
    inventory=json.loads(inv_raw)
    if inventory['role']!='UNVALIDATED_ADMIN_CANDIDATE_INPUTS_ONLY' or inventory['B95_executed'] is not False:raise ValueError('ADMIN_ONLY_INPUT_SCOPE_REQUIRED')
    source=base/'source'
    with zipfile.ZipFile(base/'source.zip') as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)!=len(set(n.casefold() for n in names)) or set(names)!=set(inventory['files']):raise ValueError('EXACT_ADMIN_CANDIDATE_MEMBERS')
        if sum(i.file_size for i in z.infolist())!=inventory['uncompressed_bytes'] or inventory['uncompressed_bytes']>5*1024*1024:raise ValueError('ADMIN_PAYLOAD_SIZE_BOUND')
        for i in z.infolist():
            name=i.filename
            if (not name or '\\' in name or ':' in name or '\0' in name or PurePosixPath(name).is_absolute()
                or any(p in ('','.','..') for p in name.split('/')) or i.is_dir() or i.flag_bits&1
                or stat.S_IFMT(i.external_attr>>16) not in (0,stat.S_IFREG)):raise ValueError('ADMIN_ARCHIVE_PATH_OR_MEMBER_TYPE')
            if sha(z.read(name))!=inventory['files'][name]:raise ValueError('ADMIN_MEMBER_CRC_OR_RAW_HASH')
        source.mkdir(exist_ok=False)
        for name in names:
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:f.write(z.read(name))
    put(base/'candidate_verified.json',dict(status='RAW_CANDIDATE_VERIFIED; NOT_READY_SEAL',files=len(names),zip_sha256=zip_sha,inventory_sha256=inventory_sha,actual_container_id=ids[0]))
    runner=source/'docs/active/bounded_admin_recovery_v0/state_contract_v1/run_admin_simulation.py'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',CUDA_VISIBLE_DEVICES='')
    for key in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'):env.pop(key,None)
    started=time.monotonic();self_cpu=time.process_time();me=psutil.Process();peak=0;cpu=0;code=2;error=None;child=None
    try:
        with (base/'suite.stdout').open('xb') as a,(base/'suite.stderr').open('xb') as b:
            child=subprocess.Popen([sys.executable,'-B',str(runner),'--out',str(base/'output'),'--expected',expected_tests],cwd=source,env=env,stdout=a,stderr=b)
            while True:
                processes=[me]
                try:processes+=me.children(recursive=True)
                except psutil.Error:pass
                aggregate_cpu=0;rss=0
                for process in processes:
                    try:
                        t=process.cpu_times();aggregate_cpu+=t.user+t.system;rss+=process.memory_info().rss
                    except psutil.Error:pass
                cpu=max(cpu,aggregate_cpu);peak=max(peak,rss)
                # Aggregate process CPU includes entry startup; it is conservative, never a reset.
                if time.monotonic()-started>=120 or cpu>=120 or peak>536870912:
                    raise TimeoutError('ADMIN_AGGREGATE_WALL_CPU_MEMORY_BOUND')
                if child.poll() is not None:code=child.returncode;break
                time.sleep(.02)
    except BaseException as exc:
        error=repr(exc)
        if child is not None and child.poll() is None:child.kill();child.wait(timeout=2)
    finally:
        put(base/'admin_entry_exit.json',dict(returncode=code,error=error,wall_seconds=time.monotonic()-started,
            aggregate_cpu_seconds=max(cpu,time.process_time()+resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime),
            aggregate_peak_rss_bytes=peak,cpu_affinity=sorted(os.sched_getaffinity(0)),actual_container_id=ids[0],B95_executed=False,A320_executed=False,new_physics_calls=0,gpu_calls=0))
    print(json.dumps(dict(returncode=code,error=error,role='ADMIN_ONLY')))
