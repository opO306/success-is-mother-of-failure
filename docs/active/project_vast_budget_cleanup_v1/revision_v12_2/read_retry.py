"""Only bounded administrative reads. Never retry a mutation or an integrity error."""
import subprocess,time

class TemporaryReadFailure(Exception):
    """Raised only from the actual failed read's preserved transient stderr."""

def transient_stderr(raw):
    text=raw.decode('utf-8',errors='replace').lower()
    if any(s in text for s in ('unauthorized','forbidden','permission denied','host key','authentication','invalid api key','401','403')):return False
    return any(s in text for s in ('connecttimeout','readtimeout','connectionerror','connection reset','connection aborted','temporary failure in name resolution','502 bad gateway','503 service unavailable','504 gateway timeout','remote end closed connection'))

def read_retry(perform,args,*,timeout,absolute_deadline,check,now=None):
    now=time.monotonic if now is None else now
    if tuple(args[:2]) not in (('show','instance'),('show','instances'),('show','volumes'),('show','invoices-v1')):
        return perform(timeout)
    deadline=min(absolute_deadline,now()+timeout)
    for attempt in range(1,4):
        check();left=deadline-now()
        if left<=0:raise TimeoutError('UNCHANGED_ADMIN_READ_DEADLINE')
        try:result=perform(min(8,left))
        except (subprocess.TimeoutExpired,TemporaryReadFailure):
            check()
            if attempt==3 or now()>=deadline:raise
            continue
        check()
        if now()>=deadline:raise TimeoutError('UNCHANGED_ADMIN_READ_DEADLINE')
        return result
