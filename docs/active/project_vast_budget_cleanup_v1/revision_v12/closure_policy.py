"""Explicit file existence/recovery classes and finite setup-only closure decisions."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone

UNKNOWN='UNKNOWN'
ABSENT='ABSENT_OBSERVED_AFTER_STOP'
CREATED='CREATED_UNRECOVERED'
RECOVERED='CREATED_RECOVERED'


def file_state(*,owner_id,observation=None,local_file=None):
    """Observation comes from exact owner-bound successful reads, never missing local proof."""
    if not observation:return dict(existence=UNKNOWN,recovery='UNRECOVERED',finality='UNKNOWN')
    if observation.get('instance_id')!=owner_id or observation.get('read_complete') is not True:
        raise ValueError('FILE_OBSERVATION_NOT_COMPLETE_OR_WRONG_OWNER')
    existence=observation.get('exists')
    if existence is False:
        if observation.get('after_actual_stop') is not True:return dict(existence=UNKNOWN,recovery='UNRECOVERED',finality='UNKNOWN')
        return dict(existence=ABSENT,recovery='NOT_APPLICABLE',finality='FINAL')
    if existence is not True:return dict(existence=UNKNOWN,recovery='UNRECOVERED',finality='UNKNOWN')
    finality='FINAL' if observation.get('after_actual_stop') is True or observation.get('writer_closed') is True else 'SNAPSHOT'
    if local_file is None:return dict(existence=CREATED,recovery='UNRECOVERED',finality=finality)
    wanted=observation.get('content_sha256')
    if not wanted or hashlib.sha256(Path(local_file).read_bytes()).hexdigest()!=wanted:
        raise ValueError('FILE_RECOVERY_HASH_MISSING_OR_DRIFT')
    return dict(existence=RECOVERED,recovery='VERIFIED',finality=finality)


def decide(owner,files,*,now_utc,deadline_utc,research_state,important_recovery_verified,
           user_hold=False,setup_discard_consent=False,recovery_attempts=0):
    """Only a decision; no I/O, no loss of evidence, no manufactured recovery success."""
    if type(owner.get('instance_id')) is not int or not files:raise ValueError('OWNER_AND_NONEMPTY_FILE_CLASSIFICATION_REQUIRED')
    if not 0<=recovery_attempts<=3:raise ValueError('RECOVERY_ATTEMPTS_BOUND')
    due=datetime.fromisoformat(now_utc)>=datetime.fromisoformat(deadline_utc)
    if research_state not in ('NO_RESEARCH_COMMANDS_ISSUED_BY_THIS_CONTROLLER','IMPORTANT_WRITES_STARTED','UNKNOWN'):
        raise ValueError('RESEARCH_STATE_REQUIRED')
    complete=all(f.get('existence')==ABSENT or
        (f.get('existence')==RECOVERED and f.get('recovery')=='VERIFIED' and f.get('finality')=='FINAL') for f in files.values())
    if user_hold:return dict(action='HOLD_BY_USER',delete_eligible=False,deadline_reached=due)
    if research_state!='NO_RESEARCH_COMMANDS_ISSUED_BY_THIS_CONTROLLER' and important_recovery_verified is not True:
        return dict(action='PRESERVE_IMPORTANT_RAW',delete_eligible=False,deadline_reached=due)
    if complete:return dict(action='DELETE_ELIGIBLE_RECOVERED',delete_eligible=True,raw_verified=True)
    if not due and recovery_attempts<3:return dict(action='BOUNDED_RECOVERY_WINDOW',delete_eligible=False,deadline_reached=False)
    if setup_discard_consent is True and due and (set(files)-{'runtime_setup.log','runtime_ready'} or any(f.get('existence')==UNKNOWN for f in files.values())):
        return dict(action='WAIT_EXPLICIT_DISCARD_APPROVAL',delete_eligible=False,deadline_reached=True)
    if setup_discard_consent is True and due:
        return dict(action='DELETE_ELIGIBLE_SETUP_WAIVER',delete_eligible=True,raw_verified=False,
                    accepted_loss_files={n:f['existence'] for n,f in files.items() if f.get('existence')!=ABSENT},deadline_reached=due)
    return dict(action='WAIT_UNTIL_PREAPPROVED_DEADLINE' if setup_discard_consent is True else 'WAIT_EXPLICIT_DISCARD_APPROVAL',delete_eligible=False,deadline_reached=due,
                accepted_loss_files={},automatic_restart=False)


def validate_exact_discard_approval(approval,packet_path,owner,*,now_utc):
    """Approval is a separate human instruction bound to an immutable loss packet."""
    packet_path=Path(packet_path);raw=packet_path.read_bytes();packet=json.loads(raw)
    raw_approval=Path(approval['raw_path']).read_bytes()
    if (approval.get('decision')!='DESTROY_EXACT_OWNED_INSTANCE_ACCEPT_PACKET_LOSS'
        or approval.get('instance_id')!=owner['instance_id']
        or approval.get('packet_sha256')!=hashlib.sha256(raw).hexdigest()
        or approval.get('raw_sha256')!=hashlib.sha256(raw_approval).hexdigest()
        or packet.get('owner')!=owner):raise ValueError('EXACT_HUMAN_DISCARD_APPROVAL_REQUIRED')
    now=datetime.fromisoformat(now_utc);until=datetime.fromisoformat(approval['valid_until_utc'])
    if now.tzinfo is None or until.tzinfo is None or now>=until:raise ValueError('DISCARD_APPROVAL_EXPIRED_OR_UNTIMED')
    if approval.get('acknowledged_file_states')!=packet.get('setup_files'):
        raise ValueError('DISCARD_LOSS_SET_NOT_ACKNOWLEDGED')
    if approval.get('acknowledged_uninspected_scope')!=packet.get('uninspected_scope'):
        raise ValueError('UNINSPECTED_SCOPE_LOSS_NOT_ACKNOWLEDGED')
    if packet.get('research_state')!='NO_RESEARCH_COMMANDS_ISSUED_BY_THIS_CONTROLLER':
        raise ValueError('IMPORTANT_OR_UNKNOWN_RESEARCH_NOT_SETUP_WAIVER')
    for name,wanted in packet.get('evidence_files',{}).items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=wanted:raise ValueError('DISCARD_PACKET_EVIDENCE_DRIFT')
    if not packet.get('evidence_files'):raise ValueError('EMPTY_DISCARD_EVIDENCE_PACKET')
    return packet
