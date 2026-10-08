"""Objective-specific bounded learning proposal. Never launches or authorizes anything."""
def assess(*, goal, gain_lower_ns=None, reuse_count=None, measurement_upper_ns=None,
           verification_upper_ns=None, learning_upper_ns=None, risk=None, correctness_eligible=None,
           resource_allowance_ns=None, resource_required_ns=None):
    if goal not in ("WALL_MIN", "CPU_MIN"):
        raise ValueError("INVALID_GOAL")
    facts = dict(gain_lower_ns=gain_lower_ns, reuse_count=reuse_count, measurement_upper_ns=measurement_upper_ns,
                 verification_upper_ns=verification_upper_ns, learning_upper_ns=learning_upper_ns,
                 risk=risk, correctness_eligible=correctness_eligible, resource_allowance_ns=resource_allowance_ns,
                 resource_required_ns=resource_required_ns)
    out = {"goal": goal, "execution_authorized": False, "actual_net_profit": "UNCONFIRMED",
           "missing": [key for key, val in facts.items() if val is None]}
    if out["missing"]:
        return dict(out, status="DEFER_INFORMATION_NEEDED")
    for key, val in facts.items():
        if key not in ("risk", "correctness_eligible") and (type(val) is not int or val < 0):
            raise ValueError("INVALID_COST_FACT:" + key)
    if type(correctness_eligible) is not bool:
        raise ValueError("INVALID_ELIGIBILITY")
    net = gain_lower_ns * reuse_count - measurement_upper_ns - verification_upper_ns - learning_upper_ns
    if risk == "MISMATCH": status = "STOP"
    elif risk != "LOW" or not correctness_eligible: status = "DEFER_RISK_OR_ELIGIBILITY"
    elif (resource_required_ns > resource_allowance_ns
          or resource_required_ns < measurement_upper_ns + verification_upper_ns + learning_upper_ns): status = "DEFER_BUDGET"
    elif net <= 0: status = "DEFER_NO_NET_GAIN"
    else: status = "PROPOSE_ONLY"
    return dict(out, status=status, estimated_net_gain_lower_ns=net)
