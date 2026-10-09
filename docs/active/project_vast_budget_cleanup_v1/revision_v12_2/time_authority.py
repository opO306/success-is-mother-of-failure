"""Exact new human time grant; historical paid grant and its one-use counter retained."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,time
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'revision_v12'
PRIVATE=Path('C:/Users/zun24/.codex/evidence/project_vast_budget_cleanup_v1_20261009')
GRANT='623cfc2f2ba0713e9c73480db73b39863bee83bad3bc6a76cbba09e31bbc3f02'
FIRST=190077406000000

def candidate():
    seal=json.loads((HERE/'repair_seal.json').read_bytes())
    for n,h in seal['files'].items():
        if hashlib.sha256((HERE/n).read_bytes()).hexdigest()!=h:raise ValueError('V12_2_SOURCE_CHANGED:'+n)
    for n,h in seal['preserved_sources'].items():
        if hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h:raise ValueError('PRESERVED_SOURCE_CHANGED:'+n)
    return seal

def require_extension():
    candidate()
    value=json.loads((PRIVATE/'v12_2_actual_time_extension.json').read_bytes())
    fixed=dict(accepted=True,instance_id=55069864,machine_id=37055,total_cap_usd='2.00',additional_reservation_usd='0.06',original_grant_sha256=GRANT,original_first_allocation_ns=FIRST,new_rentals=0,A320_execution_limit=1,B95_execution_limit=0,new_window_seconds=1800)
    if any(value.get(k)!=v for k,v in fixed.items()) or not value.get('actual_human_answer') or not value.get('actual_question'):raise ValueError('EXACT_ACTUAL_V12_2_TIME_GRANT_REQUIRED')
    if value['repair_seal_sha256']!=hashlib.sha256((HERE/'repair_seal.json').read_bytes()).hexdigest():raise ValueError('TIME_GRANT_CANDIDATE_BINDING')
    start_ns=value['new_window_start_monotonic_ns'];seconds=value['requested_absolute_maximum_seconds'];end_ns=FIRST+seconds*1000000000
    start=datetime.fromisoformat(value['approved_utc']);end=datetime.fromisoformat(value['absolute_end_utc']);first_utc=datetime.fromisoformat('2026-10-09T18:12:57.932772+00:00')
    if time.monotonic_ns()<start_ns or datetime.now(timezone.utc)<start:raise ValueError('TIME_GRANT_NOT_STARTED')
    if (type(start_ns) is not int or type(seconds) is not int or not 1799<(end_ns-start_ns)/1e9<=1800 or end_ns!=value['absolute_end_monotonic_ns']
        or (end-first_utc).total_seconds()!=seconds or not 1799<(end-start).total_seconds()<=1800 or start.tzinfo is None or end.tzinfo is None
        or abs((time.monotonic_ns()-start_ns)/1e9-(datetime.now(timezone.utc)-start).total_seconds())>2):raise ValueError('SINGLE_IMMUTABLE_APPROVAL_CLOCK_REQUIRED')
    return dict(value,lease_seconds=seconds)

def install():
    import execution_authority as old
    def require(path,expected_sha):
        extension=require_extension()
        if time.monotonic_ns()>=extension['absolute_end_monotonic_ns'] or datetime.now(timezone.utc)>=datetime.fromisoformat(extension['absolute_end_utc']):raise ValueError('ACTUAL_NEW_TIME_WINDOW_EXPIRED')
        path=Path(path)
        if path.resolve()!=(PRIVATE/'v12_actual_bundled_approval.json').resolve() or expected_sha!=GRANT or hashlib.sha256(path.read_bytes()).hexdigest()!=GRANT:raise ValueError('HISTORICAL_APPROVAL_RAW_DRIFT')
        record=json.loads(path.read_bytes())
        fixed=dict(schema='V12_ACTUAL_BUNDLED_PAID_APPROVAL',accepted=True,total_cap_usd='2.00',maximum_lease_seconds=1800,maximum_reservation_usd='0.20',new_instance_limit=1,A320_execution_limit=1,B95_execution_limit=0,local_project_dynamic_tests=False,physics_calls=0,gpu_calls=0)
        if any(record.get(k)!=v for k,v in fixed.items()) or not record.get('actual_human_answer') or not record.get('actual_question'):raise ValueError('HISTORICAL_SCOPE_DRIFT')
        if record['operational_seal_sha256']!=hashlib.sha256((OLD/'operational_seal.json').read_bytes()).hexdigest() or record['implementation_request_sha256']!=hashlib.sha256((OLD/'authorization_request.txt').read_bytes()).hexdigest():raise ValueError('HISTORICAL_SOURCE_AUTHORITY_DRIFT')
        # The historical expiry is retained as history. Only the actual new exact grant authorizes this bounded continuation.
        return record
    old.require_paid_approval=require
