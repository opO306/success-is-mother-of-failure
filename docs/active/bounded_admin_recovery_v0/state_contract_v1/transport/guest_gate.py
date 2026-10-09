"""Remote wrapper: observed PID1 identity and exact A/B ticket, no retry."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone


def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(data): return hashlib.sha256(data).hexdigest()


if __name__ == '__main__':
    guest, runtime, expected, armed_hash, ticket_hash = sys.argv[1:]
    base = Path(guest)
    ids = [v.split(b'=',1)[1].decode('ascii') for v in Path('/proc/1/environ').read_bytes().split(bytes([0]))
           if v.startswith(b'CONTAINER_ID=')]
    if len(ids) != 1 or ids[0] != expected: raise ValueError('ACTUAL_INSTANCE_MISMATCH_BEFORE_GATE')
    actual = ids[0]
    armed = json.loads((base/'armed.json').read_bytes()); raw = (base/'ticket.json').read_bytes(); ticket = json.loads(raw)
    kind = ticket['package_kind']; module = {'A':'experiments.adaptive_experience_tablet_v0.offline', 'B':'admin_policy.offline'}.get(kind)
    if (module is None or sha(canonical(armed)) != armed_hash or sha(raw) != ticket_hash
            or ticket['armed_sha256'] != armed_hash or str(ticket['instance_id']) != actual
            or any(ticket[k] != armed[k] for k in ('instance_id','machine_id','country','approval_reference'))
            or sha((base/'source.zip').read_bytes()) != ticket['zip_sha256']
            or sha((base/'inventory.json').read_bytes()) != ticket['inventory_sha256']):
        raise ValueError('EXACT_NEW_PACKAGE_TICKET_ARM_BINDING')
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(ticket['allocation_start_utc'])).total_seconds()
    arm_age = (datetime.fromisoformat(armed['armed_utc'])-datetime.fromisoformat(ticket['allocation_start_utc'])).total_seconds()
    if not 0 <= age < 200 or age + 130 + 96 >= arm_age + armed['deadline_seconds']:
        raise ValueError('ABSOLUTE_GATE_AND_RECOVERY_TIME_RESERVE')
    env = dict(os.environ,CONTAINER_ID=actual,PYTHONDONTWRITEBYTECODE='1')
    for key in ('PYTHONPATH','PYTEST_ADDOPTS','PYTEST_PLUGINS'): env.pop(key,None)
    env['PYTHONPATH'] = str(base/'source')
    # Refuse unsealed ancestor pytest configuration instead of changing frozen A tests.
    if kind == 'A':
        for ancestor in [base, *base.parents]:
            for filename in ('conftest.py','pytest.ini','.pytest.ini','pyproject.toml','setup.cfg','tox.ini'):
                if (ancestor/filename).is_file(): raise ValueError('UNSEALED_ANCESTOR_PYTEST_CONFIGURATION')
    code = 2; error = None
    try:
        with (base/'gate.stdout').open('xb') as a, (base/'gate.stderr').open('xb') as b:
            result = subprocess.run([runtime,'-B','-m',module,'--authorization',str(base/'ticket.json'),
                       '--armed',str(base/'armed.json'),'--out',str(base/'output')], cwd=base/'source', env=env,
                       stdout=a,stderr=b,timeout=130)
            code = result.returncode
    except BaseException as exc: error = repr(exc)
    finally:
        with (base/'gate_exit.json').open('xb') as f:
            f.write(canonical(dict(returncode=code,error=error,observed_ns=time.time_ns(),package_kind=kind)))
    print(json.dumps(dict(returncode=code,error=error)))
