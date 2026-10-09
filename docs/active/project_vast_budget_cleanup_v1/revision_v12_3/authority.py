"""V12.3 bundled paid approval. Replaces the V12 approval functions in-process only; V12 files stay unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/Users/zun24/.codex/evidence/project_vast_budget_cleanup_v1_20261009')
USE_ROOT=PRIVATE/'v12_3_paid_approval_use'
SCHEMA='V12_3_ACTUAL_BUNDLED_PAID_APPROVAL'
FIXED=dict(schema=SCHEMA,accepted=True,total_cap_usd='2.00',maximum_lease_seconds=1800,maximum_reservation_usd='0.20',
           new_instance_limit=1,A320_execution_limit=1,B95_execution_limit=0,local_project_dynamic_tests=False,
           physics_calls=0,gpu_calls=0)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('DUPLICATE_APPROVAL_KEY')
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs)


def require_paid_approval(path,expected_sha256,*,now=None):
    path=Path(path);content=path.read_bytes()
    if hashlib.sha256(content).hexdigest()!=expected_sha256:raise ValueError('PAID_APPROVAL_RAW_DRIFT')
    record=decode(content)
    if any(record.get(k)!=v for k,v in FIXED.items()) or not record.get('actual_human_answer') or not record.get('actual_question'):
        raise ValueError('NEW_ACTUAL_V12_3_BUNDLED_APPROVAL_REQUIRED')
    if (record.get('implementation_request_sha256')!=sha(HERE/'authorization_request.txt')
        or record.get('operational_seal_sha256')!=sha(HERE/'operational_seal.json')):raise ValueError('PAID_APPROVAL_CANDIDATE_BINDING')
    start=datetime.fromisoformat(record['approved_utc']);end=datetime.fromisoformat(record['expires_utc'])
    now=now or datetime.now(timezone.utc)
    if start.tzinfo is None or end.tzinfo is None or not start<=now<end or not 0<(end-start).total_seconds()<=3600:
        raise ValueError('PAID_APPROVAL_TIME_WINDOW')
    return record


def claim_paid_approval(path,expected_sha256):
    require_paid_approval(path,expected_sha256)
    USE_ROOT.mkdir(parents=True,exist_ok=True);folder=USE_ROOT/expected_sha256
    folder.mkdir(exist_ok=False)  # One use per approval SHA; never a timestamped or alternative folder.
    with (folder/'claim.json').open('x',encoding='utf-8') as f:
        json.dump(dict(approval_sha256=expected_sha256,approval_path=str(Path(path).resolve()),claimed_utc=datetime.now(timezone.utc).isoformat()),f,sort_keys=True)
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


NAMES=('require_paid_approval','claim_paid_approval','require_claim','begin_stage','begin_transport')


def install():
    """V12 code imports these names at call time (`from execution_authority import ...`), so replacing the module attributes is enough."""
    import execution_authority as v12
    for name in NAMES:setattr(v12,name,globals()[name])
    return v12
