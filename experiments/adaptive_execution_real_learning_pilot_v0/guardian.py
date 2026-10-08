"""Standalone OUTSIDE-GUEST controller; fake tests use this exact state machine.

Only show/stop exact leased instance. Never starts/rents/destroys anything.
"""
import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path


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
                control.stop(); events.append({'event':'STOP_REQUEST','attempt':requests,'elapsed':now()-start})
            except Exception as error: events.append({'event':'STOP_REQUEST_ERROR','error_type':type(error).__name__})
            requests+=1; next_stop=start+requests*60
        try:
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
    def __init__(self,path,instance): self.path,self.instance=path,str(instance)
    def call(self,*args,decode=True):
        result=subprocess.run([self.path,'--raw','--retry','1',*args,self.instance],capture_output=True,text=True,timeout=12)
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
    if not 1<=deadline<=3240: raise ValueError('DEADLINE_BUDGET')
    args.out.mkdir(exist_ok=False,parents=True)
    control=Cli(args.cli,instance)
    def save(name,obj):
        with (args.out/name).open('xb') as stream: stream.write(json.dumps(obj,sort_keys=True).encode())
    try:
        state=control.show()
        country=state.get('country') or str(state.get('geolocation','')).rsplit(',',1)[-1].strip()
        if int(state['id'])!=instance or float(state['dph_total'])>cap or state['actual_status']!='running':
            raise ValueError('INITIAL_INSTANCE_OR_PRICE_REFUSED')
        if state.get('machine_id')!=auth.get('machine_id') or country!=auth.get('country'):
            raise ValueError('INITIAL_MACHINE_OR_COUNTRY_REFUSED')
        armed=dict(status='ARMED',instance_id=instance,outside_guest=True,deadline_seconds=deadline,
                   confirmation_seconds=180,hourly_usd=state['dph_total'],approval_reference=auth['approval_reference'],
                   armed_utc=datetime.now(timezone.utc).isoformat(),guardian_sha256=auth['guardian_sha256'],
                   machine_id=state.get('machine_id'),country=country)
        armed['hourly_cap_usd']=cap
        armed['budget_amendment_sha256']=auth.get('budget_amendment_sha256')
        save('armed.json',armed); stop_at=time.monotonic()+deadline; trigger='DEADLINE'
        while time.monotonic()<stop_at:
            if args.marker.exists():
                trigger=json.loads(args.marker.read_bytes())['trigger']
                if trigger not in ('COMPLETED','FAILED'): raise ValueError('INVALID_COMPLETION_MARKER')
                break
            time.sleep(1)
        result=confirm_stop(control,instance,trigger)
    except Exception as error:
        result=confirm_stop(control,instance,'FAILED')
        result['control_error_type']=type(error).__name__
    save('final.json',result)
    if result.get('external_warning'):
        save('MANUAL_CONFIRMATION_REQUIRED.json',result)
        print('VAST STOP NOT CONFIRMED: manual exact-instance status confirmation required.',flush=True)
        return 2
    return 0


if __name__=='__main__': raise SystemExit(main())
