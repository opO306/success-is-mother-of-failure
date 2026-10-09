"""Finite setup disposition; legacy important raw verification remains mandatory."""
from pathlib import Path
import hashlib,json,sys,time
from datetime import datetime,timezone,timedelta
V1=Path(__file__).resolve().parent
if str(V1) not in sys.path:sys.path.insert(0,str(V1))
from lifecycle import identity,stop_owned,verified_recovery,verify_admin,verify_startup,save
from closure_policy import file_state,decide
from preflight import require_finite_policy
from budget import Ledger,charge_total,money


def finite_deadline_ns(owner,out,finite_policy):
    deadline=owner['allocation_monotonic_ns']+(finite_policy['lease_seconds']-finite_policy['cleanup_seconds'])*1_000_000_000
    failure=Path(out)/'failure.json'
    if failure.exists():
        try:value=json.loads(failure.read_bytes()).get('recovery_window_start_monotonic_ns')
        except (OSError,ValueError,AttributeError):
            # Preserve malformed raw; a receipt read failure never disarms the absolute lease deadline.
            return deadline
        if type(value) is int and value>=owner['allocation_monotonic_ns']:
            deadline=min(deadline,value+finite_policy['recovery_seconds']*1_000_000_000)
    return deadline


def setup_states(out,owner,*,existence_observation_path=None):
    out=Path(out);names=('runtime_setup.log','runtime_ready')
    states={n:file_state(owner_id=owner['instance_id']) for n in names}
    proof_path=out/'startup_verified.json';result_path=out/'startup_result.json'
    if existence_observation_path is not None:
        packet=json.loads(Path(existence_observation_path).read_bytes())
        if packet.get('owner')!=owner:raise ValueError('EXISTENCE_OBSERVATION_OWNER')
        for path,wanted in packet.get('evidence_files',{}).items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=wanted:raise ValueError('EXISTENCE_OBSERVATION_DRIFT')
        if not packet.get('evidence_files'):raise ValueError('EXISTENCE_OBSERVATION_EMPTY')
        for n in names:
            states[n]=file_state(owner_id=owner['instance_id'],observation=packet.get('files',{}).get(n))
    if not proof_path.exists() or not result_path.exists():return states
    proof=json.loads(proof_path.read_bytes());result=json.loads(result_path.read_bytes())
    if (proof.get('instance_id')!=owner['instance_id'] or result.get('instance_id')!=owner['instance_id']
        or hashlib.sha256(result_path.read_bytes()).hexdigest()!=proof.get('result_sha256')
        or proof.get('files')!=result.get('files') or not set(proof['files']).issubset(names)):
        raise ValueError('STARTUP_OBSERVATION_BINDING_DRIFT')
    writer_closed='runtime_ready' in result['files']
    for n in names:
        if n in result['files']:
            observation=dict(instance_id=owner['instance_id'],read_complete=True,exists=True,
                             content_sha256=result['files'][n],writer_closed=writer_closed)
            states[n]=file_state(owner_id=owner['instance_id'],observation=observation,local_file=out/'startup_raw'/n)
        # Observed absence before writer finishes is not final absence.
    return states


def destroy_with_disposition(provider,owner,disposition,baseline_volumes,*,journal_out=None,now=time.monotonic,sleep=time.sleep):
    """Does not rename accepted loss as verified recovery; target API semantics reused."""
    if (disposition.get('delete_eligible') is not True or disposition.get('instance_id')!=owner['instance_id']
        or disposition.get('authorization_verified') is not True):raise ValueError('VERIFIED_DISPOSITION_AUTHORITY_REQUIRED')
    if journal_out is None:raise ValueError('SHARED_DESTROY_JOURNAL_REQUIRED')
    folder=Path(journal_out);folder.mkdir(parents=True,exist_ok=True)
    lock=folder/'destroy.lock'
    handle=lock.open('xb')
    try:
        return _destroy_loop(provider,owner,disposition,baseline_volumes,folder,now=now,sleep=sleep)
    finally:
        handle.close();lock.unlink()


def _destroy_loop(provider,owner,disposition,baseline_volumes,folder,*,now,sleep):
    if (disposition.get('writer_completion_verified') is not True or disposition.get('final_files_verified') is not True) and disposition.get('no_remote_project_writes') is not True:raise ValueError('DISPOSITION_FINALITY_REQUIRED')
    current=identity(provider.call('show','instance',owner['instance_id']),owner)
    if current.get('actual_status') not in ('exited','stopped') or current.get('intended_status')!='stopped':
        raise ValueError('FRESH_ACTUAL_STOP_REQUIRED_BEFORE_DESTROY')
    start=now();attempts=0;errors=[]
    existing=sorted(folder.glob('destroy_attempt_*.json'))
    if len(existing)>3:raise ValueError('DESTROY_JOURNAL_ATTEMPTS_EXCEEDED')
    for p in existing:
        if json.loads(p.read_bytes()).get('instance_id')!=owner['instance_id']:raise ValueError('DESTROY_JOURNAL_OWNER_DRIFT')
    attempts=len(existing)
    while now()-start<100:
        if attempts<3:
            attempts+=1
            save(folder/('destroy_attempt_%d.json'%attempts),dict(instance_id=owner['instance_id'],
                action='DESTROY_INTENT_BEFORE_PROVIDER_CALL',observed_utc=datetime.now(timezone.utc).isoformat()))
            try:provider.call('destroy','instance',owner['instance_id'],'--yes',json_result=False,timeout=max(.1,min(15,100-(now()-start))))
            except Exception as error:errors.append(repr(error))
        try:
            records=provider.instances(timeout=max(.1,min(15,100-(now()-start))))
            remaining=[r for r in records if r['id']==owner['instance_id']]
            if not remaining:
                if now()-start>=100:break
                volumes=provider.volumes(timeout=max(.1,min(15,100-(now()-start))))
                if volumes!=baseline_volumes:raise ValueError('RESIDUAL_VOLUME_CHANGE')
                return dict(status='DESTROY_CONFIRMED',instance_id=owner['instance_id'],attempts=attempts,errors=errors,
                            raw_verified=disposition.get('raw_verified') is True,accepted_loss=disposition.get('accepted_loss_files',{}),
                            volumes_unchanged=True,remaining_instance_ids=[r['id'] for r in records])
            identity(remaining[0],owner)
        except ValueError:raise
        except Exception as error:errors.append(repr(error))
        sleep(min(4,max(0,100-(now()-start))))
    return dict(status='DESTROY_UNCONFIRMED',instance_id=owner['instance_id'],attempts=attempts,errors=errors)


def close_owned(provider,owner,out,baseline_volumes,finite_policy,*,user_hold=False,receipt_prefix='outer'):
    out=Path(out);stop=stop_owned(provider,owner,seconds=120)
    save(out/(receipt_prefix+'_finite_stop.json'),stop)
    if stop['status']!='STOP_CONFIRMED':raise ValueError('FINITE_STOP_UNCONFIRMED')
    states=setup_states(out,owner)
    started=(out/'admin_started.json').exists() or (out/'transport/remote_writes_started.json').exists()
    important=False;recovery=None;recovery_error=None
    try:
        verify_admin(out,owner)
        recovery=verified_recovery(out/'transport',owner,(out/'transport/remote_writes_started.json').exists())
        important=recovery['verified'] is True
    except Exception as error:recovery_error=repr(error)
    now=datetime.now(timezone.utc)
    deadline=now+timedelta(seconds=(finite_deadline_ns(owner,out,finite_policy)-time.monotonic_ns())/1e9)
    consent=False
    if finite_policy.get('prelease_setup_loss_consent',{}).get('accepted') is True:
        require_finite_policy(finite_policy);consent=True
    user_hold=user_hold or (finite_policy.get('current_instance_user_hold') is True and finite_policy.get('held_instance_id')==owner['instance_id'])
    actual_attempts=1 if (out/'startup_recovery_attempted.json').exists() else 0
    decision=decide(owner,states,now_utc=now.isoformat(),deadline_utc=deadline.isoformat(),
        research_state='IMPORTANT_WRITES_STARTED' if started else 'NO_RESEARCH_COMMANDS_ISSUED_BY_THIS_CONTROLLER',
        important_recovery_verified=important,user_hold=user_hold,setup_discard_consent=consent,
        recovery_attempts=actual_attempts)
    save(out/(receipt_prefix+'_finite_disposition.json'),dict(decision=decision,setup_files=states,recovery=recovery,
        recovery_error=recovery_error,deadline_utc=deadline.isoformat(),observed_utc=now.isoformat()))
    if not decision['delete_eligible']:raise ValueError('FINITE_CLOSURE_REQUIRES_DECISION:'+decision['action'])
    if not important:raise ValueError('IMPORTANT_RECOVERY_NOT_VERIFIED')
    disposition=dict(decision,instance_id=owner['instance_id'],authorization_verified=True,writer_completion_verified=recovery.get('writer_completion_verified') is True,final_files_verified=recovery.get('final_files_verified') is True,no_remote_project_writes=recovery.get('basis')=='NO_REMOTE_PROJECT_WRITES')
    destroyed=destroy_with_disposition(provider,owner,disposition,baseline_volumes,journal_out=out/'destroy_journal')
    save(out/(receipt_prefix+'_finite_destroy.json'),destroyed)
    return stop,recovery,destroyed


def reconcile_destroyed(provider,owner,out,ledger_path,destroyed,*,receipt_name='administrative_reconcile.json'):
    """No re-rent or tests. Consume an actual gone observation into the inherited ledger."""
    if destroyed.get('status')!='DESTROY_CONFIRMED' or destroyed.get('instance_id')!=owner['instance_id']:
        raise ValueError('ACTUAL_OWNED_DESTROY_REQUIRED_FOR_SETTLEMENT')
    if any(r['id']==owner['instance_id'] for r in provider.instances()):raise ValueError('INSTANCE_STILL_LISTED')
    ledger=Ledger(ledger_path);events,_=ledger.read();balance=ledger.balances(events)
    token=owner['reservation_token']
    pages=provider.charges();display,count=charge_total(pages)
    # Preserve the entire pending reserve; account-day observations cover stopped disk.
    if token in balance['active']:
        cost=balance['active'][token]
        ledger.append(dict(action='SETTLE',token=token,instance_id=owner['instance_id'],
            observed_cost_bound=str(cost),destroy_confirmed=True,observed_utc=datetime.now(timezone.utc).isoformat()))
    elif not any(e.get('action')=='SETTLE' and e.get('token')==token for e in events):
        raise ValueError('NO_MATCHING_INHERITED_RESERVATION')
    settle_extension_reservations(ledger,owner)
    observation=display+money('.002')*count+money('.020')
    balance=ledger.append(dict(action='OBSERVE',historical_bound=str(observation),
        observed_utc=datetime.now(timezone.utc).isoformat(),reason='FINITE_OWNED_DESTROY_RECONCILE',instance_id=owner['instance_id']))
    record=dict(instance_id=owner['instance_id'],status='DESTROY_AND_INHERITED_LEDGER_RECONCILED',
        provider_display=str(display),provider_entries=count,spent_bound=str(balance['spent']),
        remaining_after_pending=str(balance['remaining']),final_invoice=False,budget_reset=False)
    save(Path(out)/receipt_name,record)
    if not (Path(out)/'cleanup_done.json').exists():save(Path(out)/'cleanup_done.json',dict(status='OWNED_INSTANCE_GONE',instance_id=owner['instance_id']))
    return record

def settle_extension_reservations(ledger,owner):
    declarations=owner.get('extension_reservations',[])
    if not declarations:return
    if len(declarations)!=1 or owner['instance_id']!=55040957 or owner['machine_id']!=53859:raise ValueError('EXACT_OWNED_EXTENSION_RESERVATION_REQUIRED')
    declaration=declarations[0];token=owner['reservation_token']+'_time_extension_v7'
    if declaration.get('token')!=token or not 0<money(declaration.get('amount'))<=money('.041'):raise ValueError('EXTENSION_AMOUNT_OR_TOKEN_DRIFT')
    events,_=ledger.read();balance=ledger.balances(events)
    if token in balance['active']:
        if balance['active'][token]!=money(declaration['amount']):raise ValueError('EXTENSION_LEDGER_BINDING_DRIFT')
        ledger.append(dict(action='SETTLE',token=token,instance_id=owner['instance_id'],observed_cost_bound=declaration['amount'],destroy_confirmed=True,observed_utc=datetime.now(timezone.utc).isoformat()))
    elif not any(e.get('action')=='SETTLE' and e.get('token')==token and e.get('destroy_confirmed') is True for e in events):raise ValueError('NO_EXTENSION_RESERVATION_OR_SETTLEMENT')
