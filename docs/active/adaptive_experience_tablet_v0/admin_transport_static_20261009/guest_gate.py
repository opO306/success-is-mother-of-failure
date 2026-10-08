"""Remote-only administrative wrapper; frozen offline module is the sole entrypoint."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


if __name__ == '__main__':
    guest, runtime, expected, armed_hash, ticket_hash = sys.argv[1:]
    base = Path(guest)
    values = [v.split(b'=', 1)[1].decode('ascii')
              for v in Path('/proc/1/environ').read_bytes().split(bytes([0]))
              if v.startswith(b'CONTAINER_ID=')]
    if len(values) != 1 or values[0] != expected:
        raise ValueError('ACTUAL_INSTANCE_MISMATCH_BEFORE_GATE')
    actual = values[0]  # Observed and compared, never synthesized from the expected ID.
    armed = json.loads((base / 'armed.json').read_bytes())
    ticket_raw = (base / 'ticket.json').read_bytes()
    ticket = json.loads(ticket_raw)
    if (hashlib.sha256(canonical(armed)).hexdigest() != armed_hash
            or hashlib.sha256(ticket_raw).hexdigest() != ticket_hash
            or ticket['armed_sha256'] != armed_hash
            or str(ticket['instance_id']) != actual
            or any(ticket[k] != armed[k] for k in ('instance_id', 'machine_id', 'country', 'approval_reference'))):
        raise ValueError('REMOTE_TICKET_ARM_BINDING')
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(ticket['allocation_start_utc'])).total_seconds()
    if not 0 <= age < 200:
        raise ValueError('REMOTE_GATE_TIME_RESERVE')
    environment = dict(os.environ, CONTAINER_ID=actual, PYTHONDONTWRITEBYTECODE='1',
                       PYTHONPATH=str(base / 'source'))
    code = 2
    error = None
    try:
        with (base / 'gate.stdout').open('xb') as a, (base / 'gate.stderr').open('xb') as b:
            result = subprocess.run([runtime, '-B', '-m', 'experiments.adaptive_experience_tablet_v0.offline',
                                     '--authorization', str(base / 'ticket.json'), '--armed', str(base / 'armed.json'),
                                     '--out', str(base / 'output')], cwd=base / 'source', env=environment,
                                    stdout=a, stderr=b, timeout=130)
            code = result.returncode
    except BaseException as exc:
        error = repr(exc)
    finally:
        with (base / 'gate_exit.json').open('xb') as f:
            f.write(canonical(dict(returncode=code, error=error, observed_ns=time.time_ns())))
    print(json.dumps(dict(returncode=code, error=error)))
