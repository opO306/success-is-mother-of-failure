"""Non-promoting classifications and cost proposals; manager retains all authority."""
from decimal import Decimal, InvalidOperation
from experiments.adaptive_execution_real_learning_pilot_v0 import knowledge
from experiments.adaptive_execution_real_learning_pilot_v0.common import canonical,digest
from experiments.adaptive_execution_real_learning_pilot_a_resume_v1 import evidence
from experiments.evidence_canonicalization_v0.fingerprints import parse_bytes
from .catalog import Experience,problem_key
from . import routes


def _current_method(experience,request,host_info,session,manager,snapshot):
    if manager is None or snapshot is None: return None
    meta=experience.metadata
    if (meta['session_sha256']!=digest(session) or meta['env_id']!=host_info['env']['env_id']
            or experience.session_bytes!=canonical(session)
            or experience.root_fingerprint!=digest(manager.roots.__dict__)
            or snapshot.session_sha256!=digest(session) or snapshot.goal!=request['goal']
            or snapshot.profile_bytes!=experience.profile_bytes): return None
    method=manager.choose(snapshot,session)  # Existing signed-manager behavior, never tablet approval.
    if method=='LEGACY': return None
    profile=parse_bytes(snapshot.profile_bytes); stage=profile['receipt']['body']['stage']
    if stage not in ('A','B'): return None
    original=evidence.strict_read(manager.directory.parent/stage/'measurement/SERIAL_0.json')
    exact=problem_key(dict(N=session['N'],T=session['T'],start_p=original['service']['start_decision']['start_p'],
          actual_p=original['service']['final_p'],goal=session['goal'],physics=session['env']['contracts']['physics'],
          numeric=session['env']['contracts']['numeric'],source_sha256=session['code_manifest_sha256']))
    if problem_key(request)!=exact: return None
    return method if method in ('SERIAL','W6') else None


def classify(experience,request,host_info,session,*,method=None,manager=None,snapshot=None):
    try:
        plans=routes.candidates(request,host_info)
        if experience is None: return 'NEEDS_CALIBRATION' if plans else 'INCOMPATIBLE'
        if not isinstance(experience,Experience): return 'REFUSED'
        meta=experience.metadata
        if problem_key(request)!=meta['key']: return 'REFUSED'
        if method is not None and method not in plans: return 'INCOMPATIBLE'
        if method is not None and method not in meta['repeats']: return 'NEEDS_CALIBRATION'
        if not any(kind in plans for kind in meta['repeats']): return 'INCOMPATIBLE'
        current=_current_method(experience,request,host_info,session,manager,snapshot)
        if current is not None: return 'CURRENT_SESSION_VERIFIED'
        if meta['session_sha256']!=digest(session) or meta['env_id']!=host_info['env']['env_id']: return 'TRANSFER_HINT_ONLY'
        return 'NEEDS_CALIBRATION'
    except (ValueError,KeyError,TypeError,OSError): return 'REFUSED'


def safe_method(goal,plans,*,experience=None,request=None,host_info=None,session=None,manager=None,snapshot=None):
    if goal not in ('CPU_MIN','WALL_MIN') or 'SERIAL' not in plans: raise ValueError('NO_SAFE_EXISTING_POLICY')
    if goal=='CPU_MIN': return 'SERIAL'
    if not all(x is not None for x in (experience,request,host_info,session,manager,snapshot)): return 'SERIAL'
    if request['goal']!=goal: raise ValueError('GOAL_MIX')
    if classify(experience,request,host_info,session,manager=manager,snapshot=snapshot)!='CURRENT_SESSION_VERIFIED': return 'SERIAL'
    chosen=_current_method(experience,request,host_info,session,manager,snapshot)
    if chosen not in plans: raise ValueError('CURRENT_METHOD_NO_LONGER_EXECUTABLE')
    routes.recheck(plans[chosen],request,host_info)
    return chosen


def study_value(*,baseline_ns=None,candidate_upper_ns=None,reuses=None,measurement_ns=None,verification_ns=None,
                available_ns=None,rental_upper_usd=None,budget_usd=None,risk_bounded=None,baseline_verified=False):
    facts=(baseline_ns,candidate_upper_ns,reuses,measurement_ns,verification_ns,available_ns,rental_upper_usd,budget_usd,risk_bounded)
    if any(x is None for x in facts) or baseline_verified is not True:
        return dict(decision='DEFER_INFORMATION_NEEDED',execution_authorized=False)
    for val in facts[:6]:
        if type(val) is not int or val<0: raise ValueError('VALUE_FACT_INVALID')
    try: cost,budget=Decimal(rental_upper_usd),Decimal(budget_usd)
    except (InvalidOperation,TypeError,ValueError) as error: raise ValueError('BUDGET_INVALID') from error
    if not cost.is_finite() or not budget.is_finite() or min(cost,budget)<0: raise ValueError('BUDGET_INVALID')
    if risk_bounded is not True or cost>budget: return dict(decision='DEFER_COST_OR_RISK',execution_authorized=False)
    return knowledge.value(saving_ns=max(0,baseline_ns-candidate_upper_ns),confirmed_reuses=reuses,
                           measurement_ns=measurement_ns,verification_ns=verification_ns,
                           accuracy_in_scope=True,available_ns=available_ns)
