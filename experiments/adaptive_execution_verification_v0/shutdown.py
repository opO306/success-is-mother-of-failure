"""Vast stop-control prototype with injected transport, never a paid job launcher.

No ps/CPU scan, credentials, subprocess or real network implementation. Actual
Vast transport and external guardian qualification remain explicit prerequisites.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ExclusiveLease:
    instance_id: str
    authorization_reference: str
    exclusive: bool


def stop_owned(lease, transport, *, trigger):
    if not lease.exclusive or not lease.instance_id or not lease.authorization_reference:
        return {"status": "REFUSED_NO_EXCLUSIVE_LEASE", "events": [], "paid_compute_allowed": False}
    if trigger not in ("COMPLETED", "FAILED", "DEADLINE"):
        raise ValueError("UNKNOWN_TRIGGER")
    events = []
    for attempt in range(3):
        try:
            transport.stop(lease.instance_id)
            events.append({"attempt": attempt, "event": "STOP_REQUESTED", "instance_id": lease.instance_id})
        except Exception as error:
            events.append({"attempt": attempt, "event": "STOP_REQUEST_ERROR", "error_type": type(error).__name__})
        # Even a timeout may have delivered stop. Confirm the state independently.
        for _ in range(2):
            try:
                status = transport.status(lease.instance_id)
                if str(status["id"]) != lease.instance_id:
                    return {"status": "REFUSED_INSTANCE_ID_MISMATCH", "events": events, "paid_compute_allowed": False}
                state = status["actual_status"]
                events.append({"event": "STATE_OBSERVED", "state": state})
                if state in ("stopped", "exited"):
                    return {"status": "STOP_CONFIRMED", "events": events, "paid_compute_allowed": False}
            except Exception as error:
                events.append({"event": "STATUS_READ_ERROR", "error_type": type(error).__name__})
    return {"status": "STOP_UNCONFIRMED", "events": events, "paid_compute_allowed": False,
            "required_action": "EXTERNAL_OWNER_STOP_AND_CONFIRM"}
