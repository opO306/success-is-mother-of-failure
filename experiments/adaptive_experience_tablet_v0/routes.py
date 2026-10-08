"""Existing placement/contract validators, without importing or running calculators."""
from dataclasses import replace
from experiments.adaptive_execution_v1 import selector, adapters
from .host import qualified


def candidates(request, host_info):
    env=qualified(host_info)
    if request.get('goal') not in selector.GOALS: raise ValueError('GOAL_REFUSED')
    if type(request.get('start_p')) is not int or type(request.get('actual_p')) is not int:
        raise ValueError('PRECISION_REFUSED')
    if (request.get('physics')!=env['contracts']['physics'] or request.get('numeric')!=env['contracts']['numeric']):
        raise ValueError('REQUEST_CONTRACT_MISMATCH')
    try: selector.check_request(request['N'],request['T'],env)
    except selector.Refusal as error: raise ValueError(str(error)) from error
    result={}
    for method in selector.placements(env):
        plan=replace(selector.fixed(method,request['N'],request['T'],request['start_p'],env),goal=request['goal'])
        plan.execution_plan()
        violations=adapters.validate_plan(plan,request['N'],request['T'],env,False)
        if violations: raise ValueError('ADAPTER_REFUSED:'+','.join(violations))
        result[method]=plan
    return result


def recheck(plan, request, host_info):
    env=qualified(host_info)
    fresh=candidates(request,host_info)
    if not any(plan==candidate for candidate in fresh.values()): raise ValueError('STALE_OR_ALTERED_PLAN')
    plan.execution_plan()
    violations=adapters.validate_plan(plan,request['N'],request['T'],env,False)
    if violations: raise ValueError('ADAPTER_REFUSED:'+','.join(violations))
    return plan


def check_recorded(plan, runner):
    if not adapters.executed_matches(plan,runner): raise ValueError('RECORDED_PLACEMENT_MISMATCH')
    return True
