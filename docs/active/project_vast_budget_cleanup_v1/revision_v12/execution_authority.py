"""Fresh bundled paid approval, separate from the V12 implementation request."""
from pathlib import Path
import hashlib
from lifecycle import decode
from datetime import datetime,timezone
import json

BASE=Path(__file__).resolve().parent
USE_ROOT=Path('C:/Users/zun24/.codex/evidence/project_vast_budget_cleanup_v1_20261009/v12_paid_approval_use')

def require_paid_approval(path,expected_sha256):
    path=Path(path);content=path.read_bytes()
    if hashlib.sha256(content).hexdigest()!=expected_sha256:raise ValueError('PAID_APPROVAL_RAW_DRIFT')
    record=decode(content)
    required=dict(schema='V12_ACTUAL_BUNDLED_PAID_APPROVAL',accepted=True,total_cap_usd='2.00',maximum_lease_seconds=1800,
                  maximum_reservation_usd='0.20',new_instance_limit=1,A320_execution_limit=1,B95_execution_limit=0,
                  local_project_dynamic_tests=False,physics_calls=0,gpu_calls=0)
    if any(record.get(k)!=v for k,v in required.items()) or not record.get('actual_human_answer') or not record.get('actual_question'):
        raise ValueError('NEW_ACTUAL_BUNDLED_APPROVAL_REQUIRED')
    if (record.get('implementation_request_sha256')!=hashlib.sha256((BASE/'authorization_request.txt').read_bytes()).hexdigest()
        or record.get('operational_seal_sha256')!=hashlib.sha256((BASE/'operational_seal.json').read_bytes()).hexdigest()):raise ValueError('PAID_APPROVAL_CANDIDATE_BINDING')
    start=datetime.fromisoformat(record['approved_utc']);end=datetime.fromisoformat(record['expires_utc']);now=datetime.now(timezone.utc)
    if start.tzinfo is None or end.tzinfo is None or not start<=now<end or not 0<(end-start).total_seconds()<=3600:raise ValueError('PAID_APPROVAL_TIME_WINDOW')
    return record

def claim_paid_approval(path,expected_sha256):
    require_paid_approval(path,expected_sha256)
    USE_ROOT.mkdir(parents=True,exist_ok=True);folder=USE_ROOT/expected_sha256
    folder.mkdir(exist_ok=False)  # Fixed approval SHA, never timestamp/reset/alternative directory.
    with (folder/'claim.json').open('x',encoding='utf-8') as f:json.dump(dict(approval_sha256=expected_sha256,approval_path=str(Path(path).resolve()),claimed_utc=datetime.now(timezone.utc).isoformat()),f,sort_keys=True)
    return folder

def require_claim(path,expected_sha256):
    require_paid_approval(path,expected_sha256)
    folder=USE_ROOT/expected_sha256
    claim=decode((folder/'claim.json').read_bytes())
    if claim.get('approval_sha256')!=expected_sha256 or claim.get('approval_path')!=str(Path(path).resolve()):raise ValueError('PAID_APPROVAL_USE_BINDING')
    return folder

def begin_stage(path,expected_sha256):
    folder=require_claim(path,expected_sha256)
    with (folder/'stage_started.json').open('x',encoding='utf-8') as f:json.dump(dict(approval_sha256=expected_sha256),f)

def begin_transport(path,expected_sha256):
    folder=require_claim(path,expected_sha256)
    if not (folder/'stage_started.json').is_file():raise ValueError('PAID_STAGE_USE_REQUIRED')
    with (folder/'transport_started.json').open('x',encoding='utf-8') as f:json.dump(dict(approval_sha256=expected_sha256),f)
