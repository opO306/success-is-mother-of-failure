"""Short remote job wrapper. No project imports. One claim, detached session, subreaper.

PID/startticks/boot identity; terminal is committed only after wait of all children.
No retry of a claimed launch. Not an OS authority boundary against hostile root.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone


def raw(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('DUPLICATE_JOB_KEY')
            out[key]=value
        return out
    def invalid(value):raise ValueError('NONFINITE_JOB_JSON')
    return json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=invalid)

def atomic(path,obj):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.pending')
    with tmp.open('xb') as f:f.write(raw(obj));f.flush();os.fsync(f.fileno())
    if path.exists():raise ValueError('IMMUTABLE_JOB_RECORD_EXISTS')
    os.replace(tmp,path)
    fd=os.open(str(path.parent),os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def instance():
    ids=[v.split(b'=',1)[1].decode('ascii') for v in Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'CONTAINER_ID=')]
    if len(ids)!=1 or not ids[0].isdigit():raise ValueError('JOB_PID1_ID_REQUIRED')
    return int(ids[0])

def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

def proc(pid):
    try:
        fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return dict(pid=int(pid),state=fields[0],ppid=int(fields[1]),pgid=int(fields[2]),session=int(fields[3]),startticks=int(fields[19]))
    except FileNotFoundError:return None

def census():
    rows={}
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            row=proc(int(path.name))
            if row is not None:rows[row['pid']]=row
    return rows

def descendants(rows,parent):
    result=set();front={parent}
    while front:
        front={pid for pid,row in rows.items() if row['ppid'] in front and pid not in result}
        result.update(front)
    return [rows[pid] for pid in sorted(result)]

def context(folder,expected,job_id):
    folder=Path(folder)
    if not folder.is_absolute() or not folder.resolve().is_relative_to(Path('/workspace')) or folder.resolve()!=folder or folder.name!='job':raise ValueError('JOB_FOLDER_SCOPE')
    if instance()!=int(expected):raise ValueError('JOB_ACTUAL_INSTANCE_MISMATCH')
    spec=read(folder.parent/'job_spec.json')
    if spec.get('guest_root')!=str(folder.parent):raise ValueError('JOB_ROOT_BINDING')
    if spec.get('instance_id')!=int(expected) or spec.get('job_id')!=job_id or not spec.get('run_id'):raise ValueError('JOB_OWNER_BINDING')
    if sha(Path(__file__).read_bytes())!=spec.get('wrapper_sha256'):raise ValueError('JOB_WRAPPER_SOURCE_DRIFT')
    return folder,spec

def observe(folder,expected,job_id):
    folder,spec=context(folder,expected,job_id)
    base=dict(schema='V12_JOB_OBSERVATION',instance_id=int(expected),run_id=spec['run_id'],job_id=job_id,spec_sha256=sha(raw(spec)),boot_id=boot())
    if not folder.exists():return dict(base,state='NOT_CLAIMED',writer_completion_verified=False)
    claim=read(folder/'claim.json')
    if claim.get('spec_sha256')!=base['spec_sha256'] or claim.get('boot_id')!=base['boot_id']:raise ValueError('JOB_CLAIM_IDENTITY_DRIFT')
    if not (folder/'identity.json').is_file():return dict(base,state='CLAIMED_UNKNOWN_PID',writer_completion_verified=False)
    identity=read(folder/'identity.json')
    if any(identity.get(k)!=base[k] for k in ('instance_id','run_id','job_id','spec_sha256','boot_id')):raise ValueError('JOB_PROCESS_IDENTITY_DRIFT')
    rows=census();leader=rows.get(identity['pid']);members=[r for r in rows.values() if r['pgid']==identity['pgid']]
    if leader is not None and leader['startticks']!=identity['startticks']:raise ValueError('JOB_PID_REUSED')
    if leader is not None and leader['state']!='Z':
        if leader['session']!=identity['pid'] or leader['pgid']!=identity['pid']:raise ValueError('JOB_SESSION_CHANGED')
        return dict(base,state='FINALIZING' if (folder/'terminal.json').exists() else 'RUNNING',identity=identity,members=members,descendants=descendants(rows,identity['pid']),writer_completion_verified=False)
    active=[r for r in members if r['pid']!=identity['pid'] or r['state']!='Z']
    if active or not (folder/'terminal.json').is_file():return dict(base,state='UNKNOWN_WRITERS',identity=identity,members=members,writer_completion_verified=False)
    terminal=read(folder/'terminal.json')
    if (any(terminal.get(k)!=identity.get(k) for k in ('instance_id','run_id','job_id','spec_sha256','boot_id','pid','startticks','pgid'))
        or terminal.get('all_descendants_reaped') is not True or terminal.get('remaining_children')!=[]
        or terminal.get('subreaper_verified') is not True or type(terminal.get('returncode')) is not int):raise ValueError('JOB_TERMINAL_IDENTITY_OR_WRITERS')
    return dict(base,state='EXITED_SUCCESS' if terminal['returncode']==0 and terminal.get('error') is None else 'EXITED_FAILURE',identity=identity,members=members,writer_completion_verified=True,terminal=terminal,terminal_sha256=sha((folder/'terminal.json').read_bytes()))

def launch(folder,expected,job_id):
    folder,spec=context(folder,expected,job_id)
    if folder.exists():return observe(folder,expected,job_id)
    folder.mkdir(exist_ok=False)
    atomic(folder/'claim.json',dict(spec_sha256=sha(raw(spec)),boot_id=boot(),instance_id=int(expected),job_id=job_id,claimed_utc=datetime.now(timezone.utc).isoformat()))
    # consume precedes fork: response loss or a dead launcher cannot rerun this job.
    with (folder/'wrapper.stdout').open('xb') as a,(folder/'wrapper.stderr').open('xb') as b:
        subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'run',str(folder),str(expected),job_id],stdin=subprocess.DEVNULL,stdout=a,stderr=b,start_new_session=True,close_fds=True)
    return observe(folder,expected,job_id)

def run_job(folder,expected,job_id):
    folder,spec=context(folder,expected,job_id)
    row=proc(os.getpid())
    if row is None or row['session']!=os.getpid() or row['pgid']!=os.getpid():raise ValueError('JOB_DETACHED_SESSION_REQUIRED')
    libc=ctypes.CDLL(None,use_errno=True)
    enabled=ctypes.c_int(0)
    if libc.prctl(36,1,0,0,0)!=0 or libc.prctl(37,ctypes.byref(enabled),0,0,0)!=0 or enabled.value!=1:raise ValueError('JOB_SUBREAPER_UNAVAILABLE')
    # Ignore SSH session hangup; TERM/timeout is recorded and ends all descendants.
    signal.signal(signal.SIGHUP,signal.SIG_IGN)
    stopping=[]
    signal.signal(signal.SIGTERM,lambda signum,frame:stopping.append('SIGTERM'))
    identity=dict(instance_id=int(expected),run_id=spec['run_id'],job_id=job_id,spec_sha256=sha(raw(spec)),boot_id=boot(),pid=os.getpid(),pgid=os.getpid(),startticks=row['startticks'],started_utc=datetime.now(timezone.utc).isoformat())
    atomic(folder/'identity.json',identity)
    if type(spec.get('timeout_seconds')) is not int or not 1<=spec['timeout_seconds']<=150:raise ValueError('JOB_TIMEOUT_BOUND')
    command=spec['command']
    if not isinstance(command,list) or not command or any(not isinstance(t,str) or '\0' in t for t in command):raise ValueError('JOB_COMMAND_ARGV')
    script=Path(command[2]) if len(command)>2 and command[1]=='-B' else None
    if script is None or script.parent!=folder.parent or sha(script.read_bytes())!=spec['command_script_sha256']:raise ValueError('JOB_COMMAND_SCRIPT_PIN')
    deadline=time.monotonic()+spec['timeout_seconds'];rc=2;error=None;child=None;timeout=False
    try:
        with (folder/'payload.stdout').open('xb') as a,(folder/'payload.stderr').open('xb') as b:
            child=subprocess.Popen(command,cwd=folder.parent,stdin=subprocess.DEVNULL,stdout=a,stderr=b,close_fds=True)
            while True:
                result=child.poll()
                # Only reap adopted descendants after Popen has waited for its own child.
                if result is not None:
                    rc=result
                    while True:
                        try:
                            pid,status=os.waitpid(-1,os.WNOHANG)
                            if pid==0:break
                        except ChildProcessError:break
                rows=census();children=descendants(rows,os.getpid())
                if result is not None and not children:break
                if stopping or time.monotonic()>=deadline:
                    timeout=True;error='JOB_TIME_OR_SIGNAL_STOP';break
                time.sleep(.05)
    except BaseException as exc:error=repr(exc)
    if timeout or error:
        # A setsid descendant is still a descendant/adopted child of this subreaper.
        until=time.monotonic()+8
        while time.monotonic()<until:
            if child is not None:child.poll()
            for row in reversed(descendants(census(),os.getpid())):
                current=proc(row['pid'])
                if current is not None and current['startticks']==row['startticks']:
                    try:os.kill(row['pid'],signal.SIGKILL)
                    except ProcessLookupError:pass
            if child is not None and child.poll() is not None:
                while True:
                    try:
                        pid,status=os.waitpid(-1,os.WNOHANG)
                        if pid==0:break
                    except ChildProcessError:break
            if not descendants(census(),os.getpid()):break
            time.sleep(.05)
        if child is not None and child.returncode is not None:rc=child.returncode
        if rc==0:rc=2
    remaining=descendants(census(),os.getpid())
    if remaining:raise ValueError('JOB_WRITERS_STILL_LIVE_NO_TERMINAL')
    atomic(folder/'terminal.json',dict(identity,returncode=rc,error=error,subreaper_verified=True,all_descendants_reaped=True,remaining_children=[],finished_utc=datetime.now(timezone.utc).isoformat()))
    # No stdout/stderr/file write after the terminal commit. Actual exit is separately observed.
    return 0

if __name__=='__main__':
    action,folder,expected,job_id=sys.argv[1:]
    if action=='run':raise SystemExit(run_job(folder,expected,job_id))
    result=launch(folder,expected,job_id) if action=='launch' else observe(folder,expected,job_id) if action=='status' else None
    if result is None:raise ValueError('JOB_ACTION')
    print(json.dumps(result,sort_keys=True,allow_nan=False))
