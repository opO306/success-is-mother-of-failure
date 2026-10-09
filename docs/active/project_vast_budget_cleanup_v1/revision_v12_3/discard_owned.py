"""Close the stopped V12/V12.2 server 55069864 under an explicit human approval bound to a loss packet.

Why a separate path: V12.2's bridge forces HOLD_BY_USER for its repair owner, and the stopped server can no
longer be inspected, so the automatic closure can never prove "nothing important left remotely". This script
does not pretend otherwise. It records exactly what was verified locally and what remains uninspected on the
remote disk, and destroys only after a human approval that names that exact packet hash.

  prepare  read-only: provider state + local evidence hashes -> packet.json (no mutation)
  execute  approval -> re-check packet and state -> confirmed STOP -> destroy (<=3) -> gone + volumes -> ledger
"""
import argparse
from datetime import datetime,timezone
import hashlib,json,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE)]
import process_bridge
process_bridge.paths()

PRIVATE=Path('C:/Users/zun24/.codex/evidence/project_vast_budget_cleanup_v1_20261009')
PRIOR=PRIVATE/'project_v12_a_20261009_181249'
REPAIR=PRIOR/'administrative_repair_v12_2'
CLI=Path('C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe')
INSTANCE,MACHINE=55069864,37055
EXTENSION_TOKEN='project_v12_a_20261009_181249_v12_2_time_extension'
DECISION='DESTROY_EXACT_OWNED_INSTANCE_ACCEPT_PACKET_LOSS'
UNINSPECTED=[
    dict(path='/workspace/vast_budget_admin_project_v12_a_20261009_181249_disconnect_probe',
         known='V12 probe inputs uploaded; local job_launch_intent.json absent, so no probe job was launched',
         state='UNINSPECTED_REMOTE_INPUT_COPIES'),
    dict(path='/workspace (all other paths)',known='no command beyond setup, V11 10 + ADMIN228 job and probe uploads was issued',
         state='UNINSPECTED_REMOTE'),
]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_bytes())


def write_new(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(obj,f,sort_keys=True,indent=2)


def load_owner(path=REPAIR/'owner.json'):
    owner=read(path)
    if owner.get('instance_id')!=INSTANCE or owner.get('machine_id')!=MACHINE or owner.get('reservation_token')!='project_v12_a_20261009_181249':
        raise ValueError('EXACT_V12_2_OWNER_REQUIRED')
    return owner


def local_evidence(prior=PRIOR,repair=REPAIR,*,closed_archive=None,verify_startup=None):
    """Every claim in the packet is a hash check made here, not a summary."""
    if closed_archive is None:from job_proof import closed_archive
    if verify_startup is None:from lifecycle import verify_startup
    prior,repair=Path(prior),Path(repair)
    close=read(prior/'stage_closeout.json')
    for name,wanted in close['raw_files'].items():
        if sha(prior/name)!=wanted:raise ValueError('PRIOR_RAW_DRIFT:'+name)
    prior_owner=read(prior/'owner.json')
    startup=verify_startup(prior,prior_owner)
    admin=read(prior/'admin_closed_originals.json')
    if closed_archive(admin['folder'],admin['owner'],admin['code_sha256'])!=admin['proof']:raise ValueError('PRIOR_ADMIN_CLOSED_ARCHIVE_DRIFT')
    if (prior/'ssh_disconnect_probe/job_launch_intent.json').exists():raise ValueError('PRIOR_PROBE_LAUNCH_INTENT_PRESENT_NOT_DISCARDABLE')
    files={str(prior/'stage_closeout.json'):sha(prior/'stage_closeout.json')}
    for name in ('owner.json','failure.json','outer_finite_stop.json','outer_finite_disposition.json','repair_closeout.json','restart_intent.json'):
        if (repair/name).exists():files[str(repair/name)]=sha(repair/name)
    for p in sorted((repair/'queued_stop_journal').glob('*.json')):files[str(p)]=sha(p)
    for p in sorted((prior/'ssh_disconnect_probe').rglob('*')):
        if p.is_file():files[str(p)]=sha(p)
    return dict(evidence_files=files,verified=dict(prior_stage_raw_files=len(close['raw_files']),startup=startup['basis'],
        admin_closed_archive=admin['proof'].get('outcome') if isinstance(admin['proof'],dict) else True,probe_launch_intent_absent=True))


def observe(provider,owner):
    from lifecycle import identity
    row=identity(provider.call('show','instance',owner['instance_id'],timeout=24),owner)
    instances=[r['id'] for r in provider.instances(timeout=24)]
    volumes=provider.volumes(timeout=24)
    return dict(actual_status=row.get('actual_status'),intended_status=row.get('intended_status'),dph_total=str(row.get('dph_total')),
                instance_ids=instances,volumes=volumes,observed_utc=utc())


def prepare(provider,owner,out,**kwargs):
    state=observe(provider,owner)
    if state['actual_status'] not in ('exited','stopped') or state['intended_status']!='stopped':raise ValueError('ACTUAL_STOP_REQUIRED_BEFORE_PACKET')
    evidence=local_evidence(**kwargs)
    packet=dict(schema='V12_3_OWNED_DISCARD_LOSS_PACKET',owner=owner,provider_state=state,research_state='ADMIN_TESTS_RECOVERED_A320_NEVER_STARTED',
                uninspected_scope=UNINSPECTED,verified=evidence['verified'],evidence_files=evidence['evidence_files'],
                ledger_tokens=[owner['reservation_token'],EXTENSION_TOKEN],created_utc=utc())
    write_new(Path(out)/'packet.json',packet)
    return Path(out)/'packet.json'


def validate_approval(approval_path,approval_sha256,owner,*,now=None):
    raw=Path(approval_path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=approval_sha256:raise ValueError('DISCARD_APPROVAL_RAW_DRIFT')
    approval=json.loads(raw);packet_path=Path(approval['packet_path'])
    packet=json.loads(packet_path.read_bytes())
    if (approval.get('decision')!=DECISION or approval.get('instance_id')!=owner['instance_id'] or approval.get('accepted') is not True
        or approval.get('packet_sha256')!=sha(packet_path) or not approval.get('actual_human_answer') or not approval.get('actual_question')
        or packet.get('owner')!=owner or approval.get('acknowledged_uninspected_scope')!=packet.get('uninspected_scope')):
        raise ValueError('EXACT_HUMAN_DISCARD_APPROVAL_REQUIRED')
    now=now or datetime.now(timezone.utc)
    start=datetime.fromisoformat(approval['approved_utc']);until=datetime.fromisoformat(approval['valid_until_utc'])
    if start.tzinfo is None or until.tzinfo is None or not start<=now<until or (until-start).total_seconds()>7200:raise ValueError('DISCARD_APPROVAL_TIME_WINDOW')
    for name,wanted in packet['evidence_files'].items():
        if sha(name)!=wanted:raise ValueError('DISCARD_PACKET_EVIDENCE_DRIFT:'+name)
    return approval,packet


def destroy_exact(provider,owner,baseline_volumes,journal,*,now=time.monotonic,sleep=time.sleep,window=100):
    """Same request/observation shape as V12 cleanup._destroy_loop, without its automatic-finality gate (replaced by the human packet approval)."""
    from lifecycle import identity,save
    journal=Path(journal);journal.mkdir(parents=True,exist_ok=True)
    current=identity(provider.call('show','instance',owner['instance_id'],timeout=24),owner)
    if current.get('actual_status') not in ('exited','stopped') or current.get('intended_status')!='stopped':raise ValueError('FRESH_ACTUAL_STOP_REQUIRED_BEFORE_DESTROY')
    existing=sorted(journal.glob('destroy_attempt_*.json'))
    if len(existing)>=3:raise ValueError('DESTROY_JOURNAL_ATTEMPTS_EXCEEDED')
    attempts=len(existing);errors=[];start=now()
    while now()-start<window:
        if attempts<3:
            attempts+=1
            save(journal/('destroy_attempt_%d.json'%attempts),dict(instance_id=owner['instance_id'],action='DESTROY_INTENT_BEFORE_PROVIDER_CALL',observed_utc=utc()))
            try:provider.call('destroy','instance',owner['instance_id'],'--yes',json_result=False,timeout=max(.1,min(15,window-(now()-start))))
            except Exception as error:errors.append(repr(error))
        try:
            records=provider.instances(timeout=max(.1,min(15,window-(now()-start))))
            remaining=[r for r in records if r['id']==owner['instance_id']]
            if not remaining:
                volumes=provider.volumes(timeout=max(.1,min(15,window-(now()-start))))
                if volumes!=baseline_volumes:raise ValueError('RESIDUAL_VOLUME_CHANGE')
                return dict(status='DESTROY_CONFIRMED',instance_id=owner['instance_id'],attempts=attempts,errors=errors,volumes_unchanged=True,
                            remaining_instance_ids=[r['id'] for r in records],basis='HUMAN_APPROVED_LOSS_PACKET')
            identity(remaining[0],owner)
        except ValueError:raise
        except Exception as error:errors.append(repr(error))
        sleep(min(4,max(0,window-(now()-start))))
    return dict(status='DESTROY_UNCONFIRMED',instance_id=owner['instance_id'],attempts=attempts,errors=errors)


def settle(provider,owner,out,ledger_path,destroyed):
    """V12.2 extension token first (same event shape as revision_v12_2/closure_bridge.py), then the unchanged V12 reconcile."""
    from budget import Ledger,money
    from cleanup import reconcile_destroyed
    if destroyed.get('status')!='DESTROY_CONFIRMED' or destroyed.get('instance_id')!=owner['instance_id']:raise ValueError('ACTUAL_OWNED_DESTROY_REQUIRED_FOR_SETTLEMENT')
    ledger=Ledger(ledger_path);balance=ledger.balances(ledger.read()[0])
    if EXTENSION_TOKEN in balance['active']:
        if balance['active'][EXTENSION_TOKEN]!=money('.06'):raise ValueError('EXTENSION_AMOUNT_DRIFT')
        ledger.append(dict(action='SETTLE',token=EXTENSION_TOKEN,instance_id=owner['instance_id'],observed_cost_bound='0.06',destroy_confirmed=True,observed_utc=utc()))
    owner=dict(owner);owner.pop('extension_reservations',None)
    return reconcile_destroyed(provider,owner,out,ledger_path,destroyed,receipt_name='v12_3_discard_reconcile.json')


def main(argv=None):
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='mode',required=True)
    sub.add_parser('prepare')
    e=sub.add_parser('execute');e.add_argument('--approval',required=True,type=Path);e.add_argument('--approval-sha256',required=True)
    args=parser.parse_args(argv)
    import fresh_owned;fresh_owned.verify_seal()
    from reads import ReadRetryProvider
    from lifecycle import stop_owned
    owner=load_owner()
    root=PRIVATE/'v12_3_discard'
    if args.mode=='prepare':
        out=root/('prepare_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
        path=prepare(ReadRetryProvider(CLI,out/'api'),owner,out)
        print(json.dumps(dict(packet=str(path),packet_sha256=sha(path),mutations=0)))
        return 0
    approval,packet=validate_approval(args.approval,args.approval_sha256,owner)
    out=root/('execute_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    out.mkdir(parents=True,exist_ok=False)
    write_new(out/'approval_binding.json',dict(approval_path=str(args.approval.resolve()),approval_sha256=args.approval_sha256,packet_sha256=approval['packet_sha256']))
    provider=ReadRetryProvider(CLI,out/'api')
    state=observe(provider,owner)
    if state['volumes']!=packet['provider_state']['volumes']:raise ValueError('VOLUME_SET_CHANGED_SINCE_PACKET')
    stop=stop_owned(provider,owner,seconds=120);write_new(out/'stop.json',stop)
    if stop['status']!='STOP_CONFIRMED':raise ValueError('STOP_UNCONFIRMED_NO_DESTROY')
    destroyed=destroy_exact(provider,owner,packet['provider_state']['volumes'],out/'destroy_journal');write_new(out/'destroy.json',destroyed)
    if destroyed['status']!='DESTROY_CONFIRMED':
        print(json.dumps(dict(out=str(out),status=destroyed['status'],settled=False)));return 2
    record=settle(provider,owner,out,read(HERE.parent/'revision_v12/policy.json')['ledger_path'],destroyed)
    print(json.dumps(dict(out=str(out),status='DESTROY_CONFIRMED',settled=True,remaining_after_pending=record['remaining_after_pending'],final_invoice=False)))
    return 0


if __name__=='__main__':raise SystemExit(main())
