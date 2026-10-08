"""OUTSIDE-GUEST pulse transport only. No rental, restart, physics or signing API."""
import argparse
import hashlib
import json
import shlex
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety


def guest_target(value):
    path=PurePosixPath(value)
    if not path.is_absolute() or '..' in path.parts or len(path.parts)<4 or path.parts[1]!='workspace':
        raise ValueError('RELAY_PATH_SCOPE')
    if path.name!='heartbeat.json': raise ValueError('RELAY_HEARTBEAT_NAME')
    return str(path)


def forward(argv,target,raw,run=subprocess.run):
    # Only the task's named status file is replaced. Its history is kept by the guardian.
    script="import os,sys,pathlib; p=pathlib.Path(sys.argv[1]); r=sys.stdin.buffer.read(); t=p.with_suffix('.relay.tmp'); t.write_bytes(r); os.replace(t,p)"
    remote='python3 -c '+shlex.quote(script)+' '+shlex.quote(guest_target(target))
    result=run([*argv,remote],input=raw,capture_output=True,timeout=12)
    if result.returncode: raise OSError('HEARTBEAT_RELAY_TRANSPORT_FAILED')


def main():
    parser=argparse.ArgumentParser()
    for name in ('guardian_dir','guest_heartbeat','host','port','key','out'):
        parser.add_argument('--'+name.replace('_','-'),required=True)
    args=parser.parse_args(); root=Path(args.guardian_dir); output=Path(args.out)
    target=guest_target(args.guest_heartbeat)
    armed=json.loads((root/'armed.json').read_bytes()); sequence=0; started=time.monotonic()
    argv=['ssh','-i',args.key,'-p',args.port,'-o','BatchMode=yes','-o','ConnectTimeout=5',
          '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','root@'+args.host]
    with output.open('xb') as log:
        while not (root/'final.json').exists() and time.monotonic()-started<3600:
            raw=(root/'heartbeat.json').read_bytes(); pulse=json.loads(raw)
            try:
                if pulse.get('status')!='CONTROL_OK': break
                sequence=a_safety.validate_heartbeat(pulse,armed,minimum_sequence=sequence)
                forward(argv,target,raw)
                entry=dict(status='FORWARDED',sequence=sequence,raw_sha256=hashlib.sha256(raw).hexdigest())
            except Exception as error:
                entry=dict(status='RELAY_FAILED',sequence=sequence,error_type=type(error).__name__)
                log.write(json.dumps(dict(entry,observed_utc=datetime.now(timezone.utc).isoformat())).encode()+b'\n'); log.flush()
                raise  # Guest watcher stops on expired pulse; external guardian still controls the lease.
            log.write(json.dumps(dict(entry,observed_utc=datetime.now(timezone.utc).isoformat())).encode()+b'\n'); log.flush()
            time.sleep(5)


if __name__=='__main__': main()
