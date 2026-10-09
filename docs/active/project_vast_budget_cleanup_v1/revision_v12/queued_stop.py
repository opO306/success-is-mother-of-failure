"""Shared three STOP requests for one known queued-start owner, never reexecutes tests."""
from pathlib import Path
import json

def stop_queued_owned(provider,owner,*,now,sleep,seconds):
    from lifecycle import identity,save_atomic
    path=owner.get('stop_attempt_journal')
    if not isinstance(path,str) or not Path(path).is_absolute():raise ValueError('BOUND_QUEUED_STOP_JOURNAL_REQUIRED')
    folder=Path(path);folder.mkdir(parents=True,exist_ok=True)
    errors=[];start=now();new_attempts=0
    def observations():
        intents=sorted(folder.glob('intent_*.json'));accepted=False
        occupied={p.name.removesuffix('.pending') for p in folder.glob('intent_*.json*')}
        allowed={'intent_%d.json'%n for n in range(1,4)}
        if not occupied.issubset(allowed):raise ValueError('SHARED_STOP_SLOT_NAME_DRIFT')
        if len(occupied)>3:raise ValueError('SHARED_STOP_ATTEMPTS_EXCEEDED')
        for p in intents:
            record=json.loads(p.read_bytes())
            if record.get('instance_id')!=owner['instance_id'] or record.get('machine_id')!=owner['machine_id']:raise ValueError('SHARED_STOP_OWNER_DRIFT')
            ack=p.with_name(p.name.replace('intent_','ack_'))
            if ack.is_file():
                value=json.loads(ack.read_bytes())
                if value.get('instance_id')!=owner['instance_id'] or value.get('machine_id')!=owner['machine_id']:raise ValueError('SHARED_STOP_ACK_OWNER_DRIFT')
                accepted=accepted or value.get('api_accepted') is True
        return len(occupied),accepted
    while now()-start<seconds:
        attempts,accepted=observations()
        try:
            record=identity(provider.call('show','instance',owner['instance_id'],timeout=max(.1,min(15,seconds-(now()-start)))),owner)
            if accepted and record.get('actual_status') in ('exited','stopped') and record.get('intended_status')=='stopped':
                return dict(status='STOP_CONFIRMED',instance_id=owner['instance_id'],attempts=attempts,new_attempts=new_attempts,errors=errors,shared_attempt_limit=3,explicit_api_acceptance=True)
        except ValueError:raise
        except Exception as error:errors.append(repr(error))
        if attempts>=3:return dict(status='STOP_UNCONFIRMED',instance_id=owner['instance_id'],attempts=attempts,new_attempts=new_attempts,errors=errors,shared_attempt_limit=3)
        allocated=None
        for number in range(1,4):
            intent=folder/('intent_%d.json'%number)
            try:save_atomic(intent,dict(instance_id=owner['instance_id'],machine_id=owner['machine_id'],action='STOP_INTENT_BEFORE_PROVIDER_CALL',number=number))
            except FileExistsError:continue
            allocated=number;break
        if allocated is not None:
            new_attempts+=1;api_accepted=False;error=None
            try:
                raw=provider.call('stop','instance',owner['instance_id'],json_result=False,timeout=max(.1,min(15,seconds-(now()-start))))
                api_accepted=raw.strip()==('stopping instance %d.'%owner['instance_id']).encode()
                if not api_accepted:raise ValueError('STOP_API_ACCEPTANCE_UNCONFIRMED')
            except Exception as failure:error=repr(failure);errors.append(error)
            save_atomic(folder/('ack_%d.json'%allocated),dict(instance_id=owner['instance_id'],machine_id=owner['machine_id'],api_accepted=api_accepted,error=error))
        sleep(min(4,max(0,seconds-(now()-start))))
    attempts,_=observations()
    return dict(status='STOP_UNCONFIRMED',instance_id=owner['instance_id'],attempts=attempts,new_attempts=new_attempts,errors=errors,shared_attempt_limit=3)
