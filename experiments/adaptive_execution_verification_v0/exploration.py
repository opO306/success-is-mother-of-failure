"""Objective-specific bounded experiment proposals. Never launches anything."""


def assess(goal, gain_lower_ns=None, reuse_count=None, measurement_upper_ns=None,
           verification_upper_ns=None, risk=None, eligible=False):
    if goal not in ("WALL_MIN", "CPU_MIN"):
        raise ValueError("UNSUPPORTED_GOAL")
    if risk == "MISMATCH":
        return {"decision": "STOP", "reason": "CORRECTNESS_MISMATCH", "launch": False}
    data = {"gain_lower_ns": gain_lower_ns, "reuse_count": reuse_count,
            "measurement_upper_ns": measurement_upper_ns, "verification_upper_ns": verification_upper_ns}
    missing = [name for name, value in data.items() if value is None]
    if risk is None:
        missing.append("risk")
    if missing:
        return {"decision": "DEFER_INFORMATION_NEEDED", "missing": missing, "launch": False}
    if any(type(value) is not int or value < 0 for value in data.values()):
        raise ValueError("NONNEGATIVE_INTEGER_BOUNDS_REQUIRED")
    net = gain_lower_ns * reuse_count - measurement_upper_ns - verification_upper_ns
    reason = "RISK_OR_ELIGIBILITY" if risk != "LOW" or not eligible else "NET_GAIN_NOT_POSITIVE"
    return {"decision": "PROPOSE" if risk == "LOW" and eligible and net > 0 else "DEFER",
            "reason": "BOUNDED_POSITIVE_NET_GAIN" if risk == "LOW" and eligible and net > 0 else reason,
            "net_gain_lower_ns": net, "goal": goal, "launch": False, "authorization": "REQUIRED"}
