"""Standalone OUTSIDE-GUEST controller; fake tests use this exact state machine.

Only show/stop exact leased instance. Never starts/rents/destroys anything.
"""
import argparse
import hashlib
import json
import math
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path
if __package__:
    from . import a_safety
else:
    import a_safety


def hourly_cap(auth):
    """Default unchanged; only the sealed, user-approved offline lease may use 0.28."""
    if 'budget_amendment_sha256' not in auth: return 0.25
    path=Path(__file__).parent/'offline_budget_amendment_52763685.json'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=auth['budget_amendment_sha256']:
        raise ValueError('BUDGET_AMENDMENT_INTEGRITY')
    amendment=json.loads(path.read_bytes())
    if (amendment['explicit_user_approval'] is not True or amendment['scope']!='OFFLINE_ONLY'
            or auth.get('experiment_scope')!='OFFLINE_ONLY'
            or any(auth.get(k)!=amendment[k] for k in ('instance_id','machine_id','country','hourly_cap_usd'))
            or not 1<=int(auth.get('deadline_seconds',0))<=amendment['guardian_deadline_seconds']
            or amendment['hourly_cap_usd']!='0.28' or amendment['physics_calls']!=0 or amendment['gpu_calls']!=0):
        raise ValueError('BUDGET_AMENDMENT_SCOPE_REFUSED')
    return 0.28


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


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--authorization',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path); parser.add_argument('--marker',required=True,type=Path)
    parser.add_argument('--cli',required=True); args=parser.parse_args()
    auth=json.loads(args.authorization.read_bytes())
    if (auth.get('scope')!='STOP_CONTROL_ONLY' or auth.get('exclusive') is not True
            or auth.get('explicit_user_approval') is not True or not auth.get('approval_reference')
            or auth.get('guardian_sha256')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or auth.get('completion_marker')!=str(args.marker)):
        raise ValueError('EXCLUSIVE_LEASE_REFUSED')
    instance=int(auth['instance_id']); deadline=int(auth['deadline_seconds'])
    cap=hourly_cap(auth)
    real_a='safety_policy_sha256' in auth
    p=a_safety.policy() if real_a else None
    if real_a and (auth['safety_policy_sha256']!=a_safety.policy_hash()
            or auth.get('machine_id')!=p['approved_machine_id'] or auth.get('country')!=p['approved_country']
            or auth.get('stages')!=['A'] or deadline!=p['handoff_deadline_seconds']
            or 'budget_amendment_sha256' in auth): raise ValueError('A_CONTROL_LEASE_REFUSED')
    if not 1<=deadline<=(3420 if real_a else 3240): raise ValueError('DEADLINE_BUDGET')
    args.out.mkdir(exist_ok=False,parents=True)
    control=Cli(args.cli,instance)
    def save(name,obj):
        with (args.out/name).open('xb') as stream: stream.write(json.dumps(obj,sort_keys=True).encode())
    def pulse(status,sequence,checked):
        obj=dict(status=status,instance_id=instance,machine_id=auth['machine_id'],country=auth['country'],
                 armed_digest=a_safety.armed_digest(armed),sequence=sequence,
                 observed_utc=datetime.now(timezone.utc).isoformat(),control_checked_utc=checked)
        # Only the administrative guardian updates this mutable status; history is retained.
        raw=json.dumps(obj,sort_keys=True).encode(); tmp=args.out/'heartbeat.tmp'
        tmp.write_bytes(raw); tmp.replace(args.out/'heartbeat.json')
        with (args.out/'heartbeat_history.jsonl').open('ab') as history: history.write(raw+b'\n')
    def confirmation_window():
        if not real_a: return 180
        remaining=p['allocation_seconds']-(a_safety.utc()-a_safety.utc(auth['allocation_start_utc'])).total_seconds()
        return max(1,min(180,int(remaining)))
    sequence=0; checked=datetime.now(timezone.utc).isoformat()
    try:
        state=control.show()
        country=state.get('country') or str(state.get('geolocation','')).rsplit(',',1)[-1].strip()
        price=float(state['dph_total'])
        if int(state['id'])!=instance or not math.isfinite(price) or not 0<=price<=cap or state['actual_status']!='running':
            raise ValueError('INITIAL_INSTANCE_OR_PRICE_REFUSED')
        if state.get('machine_id')!=auth.get('machine_id') or country!=auth.get('country'):
            raise ValueError('INITIAL_MACHINE_OR_COUNTRY_REFUSED')
        armed=dict(status='ARMED',instance_id=instance,outside_guest=True,deadline_seconds=deadline,
                   confirmation_seconds=180,hourly_usd=state['dph_total'],approval_reference=auth['approval_reference'],
                   armed_utc=datetime.now(timezone.utc).isoformat(),guardian_sha256=auth['guardian_sha256'],
                   machine_id=state.get('machine_id'),country=country)
        armed['hourly_cap_usd']=cap
        armed['budget_amendment_sha256']=auth.get('budget_amendment_sha256')
        if real_a:
            armed['safety_policy_sha256']=auth['safety_policy_sha256']
            armed['allocation_start_utc']=auth['allocation_start_utc']
            armed['allocation_start_provenance']=auth.get('allocation_start_provenance','UNCONFIRMED')
            left=a_safety.remaining(armed)
            if left['compute']<=120: raise ValueError('INSUFFICIENT_ALLOCATION_FOR_A_PREPARATION')
            stop_at=time.monotonic()+left['handoff']
        else: stop_at=time.monotonic()+deadline
        save('armed.json',armed); trigger='DEADLINE'; sequence=0; last_check=time.monotonic()
        checked=datetime.now(timezone.utc).isoformat(); last_pulse=-100
        while time.monotonic()<stop_at:
            if args.marker.exists():
                trigger=json.loads(args.marker.read_bytes())['trigger']
                if trigger not in ('COMPLETED','FAILED'): raise ValueError('INVALID_COMPLETION_MARKER')
                break
            if real_a:
                if time.monotonic()-last_check>=p['control_check_seconds']:
                    state=control.show(); country=state.get('country') or str(state.get('geolocation','')).rsplit(',',1)[-1].strip()
                    price=float(state['dph_total'])
                    if (int(state['id'])!=instance or state.get('machine_id')!=auth['machine_id'] or country!=auth['country']
                            or state['actual_status']!='running' or not math.isfinite(price) or not 0<=price<=cap):
                        raise ValueError('ONGOING_INSTANCE_PRICE_OR_CONTROL_LOST')
                    checked=datetime.now(timezone.utc).isoformat(); last_check=time.monotonic()
                if time.monotonic()-last_pulse>=p['heartbeat_seconds']:
                    sequence+=1; pulse('CONTROL_OK',sequence,checked); last_pulse=time.monotonic()
            time.sleep(1)
        if real_a: pulse('CONTROL_STOPPING',sequence+1,checked)
        result=confirm_stop(control,instance,trigger,confirm_seconds=confirmation_window())
    except Exception as error:
        if real_a and (args.out/'armed.json').exists():
            try: pulse('CONTROL_LOST',sequence+1,checked)
            except Exception: pass  # A failed status write must not prevent the stop request.
        result=confirm_stop(control,instance,'FAILED',confirm_seconds=confirmation_window())
        result['control_error_type']=type(error).__name__
    save('final.json',result)
    if result.get('external_warning'):
        save('MANUAL_CONFIRMATION_REQUIRED.json',result)
        print('VAST STOP NOT CONFIRMED: manual exact-instance status confirmation required.',flush=True)
        return 2
    return 0


if __name__=='__main__': raise SystemExit(main())
