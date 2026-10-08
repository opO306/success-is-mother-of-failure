"""OUTSIDE-GUEST administrative relay only. No tests, physics, rental or start API."""
import argparse
import json
import re
import shlex
import subprocess
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    for name in ('guardian','identity','remote','host','port','log'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args(); directory=Path(args.guardian)
    if not re.fullmatch(r'/workspace/[A-Za-z0-9_/-]+\.json',args.remote): raise ValueError('REMOTE_PATH_SCOPE')
    if not re.fullmatch(r'[A-Za-z0-9.-]+',args.host) or not 1<=int(args.port)<=65535: raise ValueError('SSH_SCOPE')
    remote=shlex.quote(args.remote); tmp=shlex.quote(args.remote+'.relaytmp')
    command='umask 077; cat > '+tmp+' && mv -- '+tmp+' '+remote
    with Path(args.log).open('xb') as log:
        while not (directory/'final.json').exists():
            try:
                raw=(directory/'heartbeat.json').read_bytes(); pulse=json.loads(raw)
                result=subprocess.run(['ssh','-i',args.identity,'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
                         '-o','ConnectTimeout=8','-p',args.port,'root@'+args.host,command],
                         input=raw,capture_output=True,timeout=10)
                event=dict(sequence=pulse['sequence'],status=pulse['status'],returncode=result.returncode,
                           observed_utc=pulse['observed_utc'])
            except Exception as error: event=dict(status='RELAY_UNCONFIRMED',error_type=type(error).__name__)
            log.write(json.dumps(event,sort_keys=True).encode()+b'\n'); log.flush()
            time.sleep(5)


if __name__=='__main__': main()
