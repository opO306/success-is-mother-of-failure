"""Bounded same-instance readiness and transient transfer recovery; no test execution."""
import json,time
from pathlib import Path

class SafetyStop(RuntimeError):pass
class AdministrativeUnavailable(RuntimeError):pass

def transient_connection(stderr):
    value=stderr.lower()
    if any(marker in value for marker in ('host key verification failed','remote host identification has changed',
            'permission denied','safety_instance_id_mismatch','lease_watchdog_lost','outside_stop_control_lost')):
        return False
    return any(marker in value for marker in ('connection closed','connection refused','connection reset','connection timed out','closed by remote host'))

def ready_on_same_instance(owner,deadline,out,operation,check_control,*,now=time.monotonic,sleep=time.sleep,maximum_attempts=3):
    """One unchanged absolute deadline; all three probes bind the exact same owner."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if maximum_attempts not in (1,2,3):raise ValueError('READINESS_ATTEMPT_BOUND')
    for attempt in range(1,maximum_attempts+1):
        check_control()
        left=deadline-now()
        if left<2:raise AdministrativeUnavailable('ABSOLUTE_PREPARATION_DEADLINE')
        folder=out/('attempt_'+str(attempt));folder.mkdir(exist_ok=False)
        try:
            result=operation(folder,min(100,left))
        except SafetyStop:raise
        except Exception as error:
            stderr=(folder/'runtime_probe.stderr').read_text(encoding='utf-8',errors='replace') if (folder/'runtime_probe.stderr').is_file() else ''
            if not transient_connection(stderr):raise
            result=dict(status='CONNECTING',error=repr(error))
        check_control()
        if now()>=deadline:raise AdministrativeUnavailable('ABSOLUTE_PREPARATION_DEADLINE')
        if result.get('actual_container_id') is not None and str(result['actual_container_id'])!=str(owner['instance_id']):
            raise SafetyStop('SAFETY_INSTANCE_ID_MISMATCH')
        if result.get('status')=='READY':
            if str(result.get('actual_container_id'))!=str(owner['instance_id']):raise SafetyStop('SAFETY_INSTANCE_ID_MISSING')
            (folder/'readiness.json').write_text(json.dumps(result,sort_keys=True),encoding='utf-8')
            return result
        if result.get('status') not in ('WAITING','CONNECTING'):raise SafetyStop('UNCLASSIFIED_READINESS_RESULT')
        (folder/'readiness.json').write_text(json.dumps(result,sort_keys=True),encoding='utf-8')
        if attempt==maximum_attempts:break
        until=min(deadline,now()+30)
        while now()<until:
            check_control();sleep(min(.5,until-now()))
    raise AdministrativeUnavailable('THREE_SAME_INSTANCE_PREPARATION_ATTEMPTS_EXHAUSTED')


def transfer_on_same_instance(deadline,out,operation,check_control,check_identity,*,maximum_attempts=3,now=time.monotonic):
    if type(maximum_attempts) is not int or not 1<=maximum_attempts<=3:raise ValueError('TRANSFER_ATTEMPT_BOUND')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for attempt in range(1,maximum_attempts+1):
        check_control();left=deadline-now()
        if left<2:raise AdministrativeUnavailable('ADMIN_UPLOAD_ABSOLUTE_DEADLINE')
        check_identity(left);check_control();left=deadline-now()
        if left<2:raise AdministrativeUnavailable('ADMIN_UPLOAD_ABSOLUTE_DEADLINE')
        folder=out/('upload_attempt_'+str(attempt));folder.mkdir(exist_ok=False)
        try:operation(folder,left)
        except SafetyStop:raise
        except Exception:
            stderr=(folder/'upload.stderr').read_text(encoding='utf-8',errors='replace') if (folder/'upload.stderr').is_file() else ''
            if attempt==maximum_attempts or not transient_connection(stderr):raise
            continue
        check_control()
        if now()>=deadline:raise AdministrativeUnavailable('ADMIN_UPLOAD_ABSOLUTE_DEADLINE')
        return attempt
