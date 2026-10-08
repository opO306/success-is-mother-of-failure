"""Information gaps and experiment proposals. A proposal never grants execution."""
def gaps(session,verified_methods=()):
    return {'session_id':session['session_id'],'goal':session['goal'],
            'known':sorted(set(verified_methods)&set(session['methods'])),
            'unknown':sorted(set(session['methods'])-set(verified_methods)),
            'judgment':'CORRECT_LEGACY_CHOICE_IS_NOT_AN_ERROR','state':'UNKNOWN' if set(session['methods'])-set(verified_methods) else 'VERIFIED'}


def value(*,saving_ns=None,confirmed_reuses=None,measurement_ns=None,verification_ns=None,accuracy_in_scope=False,available_ns=None):
    facts=(saving_ns,confirmed_reuses,measurement_ns,verification_ns,available_ns)
    if any(x is None for x in facts): return {'decision':'DEFER_INFORMATION_NEEDED','execution_authorized':False}
    if any(type(x) is not int or x<0 for x in facts): raise ValueError('VALUE_FACT_INVALID')
    cost=measurement_ns+verification_ns
    return {'decision':'PROPOSE_EXPERIMENT' if accuracy_in_scope and cost<=available_ns and saving_ns*confirmed_reuses>cost else 'DEFER_COST_OR_RISK',
            'execution_authorized':False,'expected_gain_ns':saving_ns*confirmed_reuses,'expected_cost_ns':cost}
