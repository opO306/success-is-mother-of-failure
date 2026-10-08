"""Sealed A-only administrative safety; no calculator, selection or signature authority."""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def policy_hash():
    return hashlib.sha256((HERE/'a_safety_policy.json').read_bytes()).hexdigest()


def policy():
    seal=json.loads((HERE/'a_safety_seal.json').read_bytes())
    for relative,expected in seal['files'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
            raise ValueError('A_SAFETY_SEAL_INTEGRITY')
    return json.loads((HERE/'a_safety_policy.json').read_bytes())


def utc(value=None):
    result=datetime.now(timezone.utc) if value is None else datetime.fromisoformat(value)
    if result.tzinfo is None: raise ValueError('UTC_CLOCK_REQUIRED')
    return result


def armed_digest(armed):
    raw=json.dumps(armed,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def remaining(armed,*,now_utc=None):
    p=policy()
    if (armed.get('status')!='ARMED' or armed.get('outside_guest') is not True
            or armed.get('safety_policy_sha256')!=policy_hash()
            or armed.get('deadline_seconds')!=p['handoff_deadline_seconds']):
        raise ValueError('A_DEADLINE_BINDING')
    age=(utc(now_utc)-utc(armed['allocation_start_utc'])).total_seconds()
    if age<0 or age>=p['allocation_seconds']: raise ValueError('A_ALLOCATION_CLOCK')
    return dict(compute=p['compute_seconds']-age,handoff=p['handoff_deadline_seconds']-age,
                allocation=p['allocation_seconds']-age)


def validate_heartbeat(pulse,armed,*,now_utc=None,minimum_sequence=0):
    p=policy(); now=utc(now_utc)
    if (pulse.get('status')!='CONTROL_OK' or pulse.get('armed_digest')!=armed_digest(armed)
            or any(pulse.get(k)!=armed.get(k) for k in ('instance_id','machine_id','country'))
            or type(pulse.get('sequence')) is not int or pulse['sequence']<max(1,minimum_sequence)):
        raise ValueError('EXTERNAL_CONTROL_BINDING_LOST')
    for field in ('observed_utc','control_checked_utc'):
        age=(now-utc(pulse[field])).total_seconds()
        if not -p['future_clock_tolerance_seconds']<=age<=p['heartbeat_ttl_seconds']:
            raise ValueError('EXTERNAL_CONTROL_STALE')
    return pulse['sequence']


def offline_lease(ticket,armed):
    p=policy()
    if (ticket.get('scope')!='OFFLINE_ONLY' or ticket.get('explicit_user_approval') is not True
            or ticket.get('safety_policy_sha256')!=policy_hash()
            or ticket.get('machine_id')!=p['approved_machine_id'] or ticket.get('country')!=p['approved_country']
            or any(ticket.get(k)!=armed.get(k) for k in ('instance_id','machine_id','country','safety_policy_sha256'))
            or ticket.get('hourly_cap_usd')!=p['hourly_cap_usd']
            or ticket.get('physics_calls')!=0 or ticket.get('gpu_calls')!=0
            or armed.get('status')!='ARMED' or armed.get('outside_guest') is not True):
        raise ValueError('A_OFFLINE_SCOPE_REFUSED')
    return True


def allocation_cost(total_ns,baseline_ns,learned_ns,hourly_usd,*,start_known):
    if any(type(x) is not int or x<0 for x in (total_ns,baseline_ns,learned_ns)):
        raise ValueError('UNKNOWN_ALLOCATION_COST')
    rate=Decimal(str(hourly_usd))
    if not rate.is_finite() or not 0<=rate<=Decimal('0.25') or total_ns<baseline_ns+learned_ns:
        raise ValueError('ALLOCATION_COST_OR_PRICE')
    # Imported only for analysis; standalone guardian stays standard-library-only.
    from .costs import recovery
    result=recovery(overhead_ns=total_ns-baseline_ns-learned_ns,baseline_ns=baseline_ns,
                    learned_ns=learned_ns,observed_reuses=1)
    if start_known is not True: result['cost_status']='UNKNOWN_ALLOCATION_START'
    return dict(total_wall_ns=total_ns,cost=result,
                estimated_rental_usd=str(rate*Decimal(total_ns)/Decimal(3600*10**9)),
                billing='UNCONFIRMED',CPU_MIN='OUTSIDE_A_SCOPE')
