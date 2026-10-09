"""Administrative absolute deadline supervisor; existing guardian and verbatim fallback state machine."""
import json
from state_contract import CheckedCli
import subprocess
import time

def confirm_stop(control, instance, trigger, *, confirm_seconds=180, now=time.monotonic, sleep=time.sleep):
    if trigger not in ('COMPLETED','FAILED','DEADLINE') or not 1<=confirm_seconds<=180:
        raise ValueError('CONTROL_SCOPE_REFUSED')
    start=now(); events=[]; requests=0; next_stop=start
    while now()-start<confirm_seconds:
        if requests<3 and now()>=next_stop:
            try:
                if hasattr(control,'timeout_seconds'): control.timeout_seconds=max(0.1,min(12,confirm_seconds-(now()-start)))
                control.stop(); events.append({'event':'STOP_REQUEST','attempt':requests,'elapsed':now()-start})
            except Exception as error: events.append({'event':'STOP_REQUEST_ERROR','error_type':type(error).__name__})
            requests+=1; next_stop=start+requests*60
        if now()-start>=confirm_seconds: break
        try:
            if hasattr(control,'timeout_seconds'): control.timeout_seconds=max(0.1,min(12,confirm_seconds-(now()-start)))
            state=control.show()
            if int(state['id'])!=instance: raise ValueError('WRONG_INSTANCE')
            events.append({'event':'OBSERVED','actual_status':state['actual_status'],'intended_status':state['intended_status'],'elapsed':now()-start})
            if state['actual_status'] in ('exited','stopped'):
                return dict(status='STOP_CONFIRMED',trigger=trigger,instance_id=instance,events=events,
                            manual_confirmation_required=False,external_warning=False)
        except Exception as error: events.append({'event':'OBSERVATION_ERROR','error_type':type(error).__name__})
        sleep(min(5,max(0,confirm_seconds-(now()-start))))
    return dict(status='STOP_UNCONFIRMED',trigger=trigger,instance_id=instance,events=events,
                manual_confirmation_required=True,external_warning=True)

class Cli:
    def __init__(self,path,instance): self.path,self.instance=path,str(instance); self.timeout_seconds=12
    def call(self,*args,decode=True):
        result=subprocess.run([self.path,'--raw','--retry','1',*args,self.instance],capture_output=True,text=True,timeout=self.timeout_seconds)
        if result.returncode: raise OSError('CONTROL_CLI_FAILURE')
        return json.loads(result.stdout) if decode else True
    def show(self): return self.call('show','instance')
    def stop(self): return self.call('stop','instance',decode=False)

# Appended below verbatim Cli/confirm_stop from the sealed generic guardian.
import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def write_new(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
        f.flush()
        os.fsync(f.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--lease', type=Path, required=True)
    args = parser.parse_args(argv)
    lease = json.loads(args.lease.read_bytes())
    root = Path(lease['repo_root'])
    out = Path(lease['out'])
    marker = out / 'completion.json'
    guardian_path = root / 'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py'
    if (lease['scope'] != 'STOP_CONTROL_ONLY' or lease['exclusive'] is not True
            or lease['explicit_user_approval'] is not True or not lease['approval_reference']
            or lease['prior_failed_attempts'] != 3 or lease['new_window_separately_authorized'] is not True
            or lease['guardian_sha256'] != hashlib.sha256(guardian_path.read_bytes()).hexdigest()
            or lease['supervisor_sha256'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or lease['state_contract_sha256'] != hashlib.sha256((Path(__file__).parent/'state_contract.py').read_bytes()).hexdigest()
            or lease['guardian_driver_sha256'] != hashlib.sha256((Path(__file__).parent/'guardian_driver.py').read_bytes()).hexdigest()):
        raise ValueError('SUPERVISOR_APPROVAL_BINDING')
    start_ns = lease['allocation_monotonic_ns']
    start_utc = datetime.fromisoformat(lease['allocation_start_utc'])
    def age():
        return (time.monotonic_ns() - start_ns) / 1e9
    def clock_fault():
        return abs(age() - (datetime.now(timezone.utc) - start_utc).total_seconds()) > 2
    guardian = None
    failure = None
    try:
        write_new(out / 'supervisor_ready.json', dict(status='STOP_WATCH_READY', instance_id=lease['instance_id'],
                  lease_sha256=hashlib.sha256(args.lease.read_bytes()).hexdigest(), observed_utc=datetime.now(timezone.utc).isoformat()))
        while age() < 400:
            if clock_fault():
                raise ValueError('SUPERVISOR_ALLOCATION_CLOCK_DRIFT')
            if marker.exists():
                break
            if (out / 'running_instance.json').exists() and guardian is None:
                # Reserve 20 seconds for the guardian's <=12 second initial API plus scheduling.
                deadline = min(240,int(400 - age() - 20)) if lease.get('hourly_cap_usd')=='0.28' else int(400 - age() - 20)
                if deadline < 1:
                    raise ValueError('NO_GUARDIAN_ARM_RESERVE')
                generic = {k: lease[k] for k in ('scope', 'exclusive', 'explicit_user_approval', 'approval_reference',
                            'instance_id', 'machine_id', 'country', 'guardian_sha256')}
                if lease.get('hourly_cap_usd')=='0.28':
                    protocol=root/'docs/active/bounded_admin_recovery_v0/target_52763685_admin_v1/target_protocol.json'
                    data=json.loads(protocol.read_bytes())
                    if (hashlib.sha256(protocol.read_bytes()).hexdigest()!=lease.get('admin_target_protocol_sha256')
                        or data.get('explicit_user_approval') is not True or data.get('exclusive_stop_authorized') is not True
                        or data.get('approval_reference')!=lease.get('approval_reference')
                        or any(lease.get(k)!=data.get(k) for k in ('instance_id','machine_id','country','hourly_cap_usd'))):raise ValueError('CURRENT_NO_BUDGET_APPROVAL_BINDING')
                    generic.update(hourly_cap_usd='0.28',experiment_scope='OFFLINE_ONLY',
                        budget_amendment_sha256=data['original_offline_hourly_amendment_sha256'],admin_target_protocol_sha256=lease['admin_target_protocol_sha256'])
                generic.update(completion_marker=str(marker), deadline_seconds=deadline)
                write_new(out / 'guardian_lease.json', generic)
                guardian = subprocess.Popen([sys.executable, '-B', str(Path(__file__).parent/'guardian_driver.py'),
                    '--guardian', str(guardian_path), '--authorization',
                    str(out / 'guardian_lease.json'), '--out', str(out / 'guardian'), '--marker', str(marker),
                    '--cli', lease['cli']], cwd=root,
                    env=dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1'),
                    stdout=(out / 'guardian.stdout').open('xb'), stderr=(out / 'guardian.stderr').open('xb'),
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
                write_new(out / 'guardian_pid.json', dict(pid=guardian.pid))
            if guardian is not None and guardian.poll() is not None:
                break
            time.sleep(.25)
    except BaseException as exc:
        failure = repr(exc)
    finally:
        if not marker.exists():
            try:
                write_new(marker, dict(trigger='FAILED', reason=failure or 'ABSOLUTE_HANDOFF_DEADLINE',
                                      observed_utc=datetime.now(timezone.utc).isoformat()))
            except FileExistsError:
                pass  # Controller and absolute watchdog may finish at the same instant.
            except BaseException as exc:
                failure = 'COMPLETION_MARKER_WRITE_FAILED:' + repr(exc)
        final = None
        if guardian is not None:
            try:
                guardian.wait(timeout=max(.1, min(181, 590 - age())))
            except subprocess.TimeoutExpired:
                failure = 'GENERIC_GUARDIAN_CONFIRMATION_TIMEOUT'
            if (out / 'guardian/final.json').exists():
                try:
                    final = json.loads((out / 'guardian/final.json').read_bytes())
                except BaseException as exc:
                    failure = 'GENERIC_STOP_RECEIPT_UNREADABLE:' + repr(exc)
                    final = None
        if not final or final.get('status') != 'STOP_CONFIRMED' or final.get('instance_id') != lease['instance_id']:
            # Reuse the exact guardian stop state machine, never start/rent/destroy.
            remaining = int(min(180, 590 - age()))
            if remaining >= 1:
                final = confirm_stop(CheckedCli(lease['cli'], lease['instance_id'], lease), lease['instance_id'], 'FAILED',
                                     confirm_seconds=remaining)
            else:
                final = dict(status='STOP_UNCONFIRMED', instance_id=lease['instance_id'],
                             manual_confirmation_required=True, external_warning=True)
        write_new(out / 'supervisor_final.json', dict(result=final, failure=failure,
                  allocation_age_s=age(), observed_utc=datetime.now(timezone.utc).isoformat()))
    return 0 if final['status'] == 'STOP_CONFIRMED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
