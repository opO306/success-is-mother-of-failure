"""Outside guest: watches one reserved owned lease from before creation to cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import psutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cleanup import close_owned,finite_deadline_ns,reconcile_destroyed
from lifecycle import Provider, save, stop_owned, destroy_owned, verified_recovery, identity, verify_admin,verify_startup


def main():
    p=argparse.ArgumentParser();p.add_argument('--lease',type=Path,required=True);a=p.parse_args()
    raw=a.lease.read_bytes();lease=json.loads(raw);out=a.lease.parent
    provider=Provider(lease['cli'],out/'watchdog_api')
    if lease['authorization_raw_sha256']!=hashlib.sha256(Path(lease['request_path']).read_bytes()).hexdigest():
        raise ValueError('WATCHDOG_USER_DELEGATION_RAW_PIN')
    save(out/'watchdog_ready.json',dict(lease_sha256=hashlib.sha256(raw).hexdigest(),pid=psutil.Process().pid))
    owner=None
    while True:
        if (out/'cleanup_done.json').is_file():return 0
        for name in ('owner.json','created_owner.json'):
            if (out/name).is_file():
                try:owner=json.loads((out/name).read_bytes());break
                except Exception:pass  # Partial ownership never disables deadline fallback.
        try:
            process=psutil.Process(lease['controller_pid'])
            alive=process.is_running() and abs(process.create_time()-lease['controller_create_time'])<.001
        except psutil.NoSuchProcess:alive=False
        age=(time.monotonic_ns()-lease['allocation_monotonic_ns'])/1e9
        finite_due=time.monotonic_ns()>=finite_deadline_ns(owner or lease,out,lease['finite_policy'])
        if not alive and not finite_due and owner is not None:
            # Stop once on parent loss; remain armed until the sealed finite deadline.
            if not (out/'watchdog_parent_lost_stop.json').exists():
                save(out/'watchdog_parent_lost_stop.json',stop_owned(provider,owner,seconds=120))
            time.sleep(.5)
            continue
        if not alive or finite_due:
            if owner is None:
                matches=None
                for attempt in range(3):
                    try:
                        matches=[r for r in provider.instances() if r.get('label')==lease['label'] and r.get('machine_id')==lease['machine_id']]
                        break
                    except Exception as error:
                        save(out/('watchdog_discovery_error_%d.json'%attempt),dict(error=repr(error)));time.sleep(2)
                if matches is None:return 2
                if len(matches)==1:
                    owner=dict(lease,instance_id=matches[0]['id'],run_id=lease['run_id'])
                    identity(matches[0],owner)
                elif matches:raise ValueError('AMBIGUOUS_CREATED_INSTANCE')
            if owner:
                if not alive and not finite_due:
                    # Discovery after an interrupted create is also deadline-owned.
                    if not (out/'watchdog_discovered_owner.json').exists():
                        save(out/'watchdog_discovered_owner.json',owner)
                    if not (out/'watchdog_parent_lost_stop.json').exists():
                        save(out/'watchdog_parent_lost_stop.json',stop_owned(provider,owner,seconds=120))
                    time.sleep(.5)
                    continue
                try:
                    _,_,destroyed=close_owned(provider,owner,out,lease['baseline_volumes'],lease['finite_policy'],receipt_prefix='watchdog')
                    if destroyed['status']=='DESTROY_CONFIRMED':
                        reconcile_destroyed(provider,owner,out,lease['ledger_path'],destroyed,receipt_name='watchdog_reconcile.json')
                except Exception as error:save(out/'watchdog_preservation_exception.json',dict(error=repr(error)))
            else:save(out/'watchdog_no_owned_instance.json',dict(observed_no_instance=True))
            return 2
        time.sleep(.5)


if __name__=='__main__':raise SystemExit(main())
