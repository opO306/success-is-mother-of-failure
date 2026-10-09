"""Remote bounded observation of restarted setup writers and exact runtime."""
from pathlib import Path
import sys,time,json,hashlib,importlib.metadata as m
expected=sys.argv[1]
ids=[v.split(b'=',1)[1].decode() for v in Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'CONTAINER_ID=')]
if ids!=[expected]:raise ValueError('RESUMED_ACTUAL_INSTANCE')
def snapshot():
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:a=p.read_bytes().split(b'\0')
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        if b'pip' in a and b'install' in a:return None
        if b'-c' in a and any(v.startswith(b'mkdir -p /workspace && touch /root/.no_auto_tmux') for v in a):return None
    files={}
    for n in ('runtime_setup.log','runtime_ready'):
        p=Path('/workspace')/n
        if not p.is_file() or p.is_symlink() or p.stat().st_size>8388608:return None
        files[n]=hashlib.sha256(p.read_bytes()).hexdigest()
    if (Path('/workspace/runtime_ready').stat().st_mtime_ns<Path('/workspace/runtime_setup.log').stat().st_mtime_ns):return None
    return files
until=time.monotonic()+90
while time.monotonic()<until:
    first=snapshot();time.sleep(1);second=snapshot()
    if first is not None and first==second:break
else:raise TimeoutError('RESUMED_SETUP_WRITER_NOT_CLOSED')
versions={n:m.version(n) for n in ('pytest','psutil','mpmath','cryptography')}
if sys.version_info[:2]!=(3,12) or versions!={'pytest':'8.3.5','psutil':'6.1.1','mpmath':'1.3.0','cryptography':'44.0.1'}:raise ValueError('RESUMED_RUNTIME_NOT_PINNED')
print(json.dumps(dict(instance_id=int(expected),writers_absent=True,files=second,versions=versions,stable_snapshots=2)))
