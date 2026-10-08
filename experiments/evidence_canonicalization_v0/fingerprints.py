"""Explicit content/legacy fingerprints and non-promoting stored-file checks. No physics."""
import hashlib
import json
import os
import re
import time
from pathlib import Path
from .policy import policy_hash

CONTENT_VERSION='INITIAL_STATE_CANON_V2'
LEGACY_VERSION='LEGACY_QP_JSON_V1'
NUMERIC=re.compile(r'(?:[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?|[-+]?[0-9]+/[0-9]+)\Z')
MAX_BYTES=64*1024*1024


def parse_bytes(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES: raise ValueError('JSON_SIZE_OR_TYPE')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: raise ValueError('DUPLICATE_JSON_KEY')
            result[k]=v
        return result
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
             parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf-8')


def validate_state(state):
    if type(state) is not dict or set(state)!= {'q','p'}: raise ValueError('INITIAL_FIELDS')
    shape=None
    for field in ('q','p'):
        rows=state[field]
        if type(rows) is not list or not rows: raise ValueError('INITIAL_ARRAYS')
        dimensions=set()
        for row in rows:
            if type(row) is not list or not row: raise ValueError('INITIAL_COORDINATES')
            dimensions.add(len(row))
            if any(type(x) is not str or NUMERIC.fullmatch(x) is None
                   or ('/' in x and set(x.split('/')[1])=={'0'}) for x in row):
                raise ValueError('EXACT_FINITE_NUMERIC_STRINGS_REQUIRED')
        if len(dimensions)!=1: raise ValueError('INITIAL_RAGGED_ARRAY')
        current=(len(rows),next(iter(dimensions)))
        if shape is not None and current!=shape: raise ValueError('INITIAL_SHAPE')
        shape=current
    return state


def content_bytes(state): return canonical(validate_state(state))
def content_hash(state): return hashlib.sha256(content_bytes(state)).hexdigest()


def legacy_hash(state):
    validate_state(state)
    # Explicit order recreates V1. No reinterpretation of the old initial_sha256 field.
    raw=json.dumps({'q':state['q'],'p':state['p']},ensure_ascii=True,allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def stamp(obj):
    result=dict(obj,evidence_version=2,initial_hash_version=LEGACY_VERSION,initial_content_version=CONTENT_VERSION)
    result['initial_sha256']=legacy_hash(result['initial_state'])
    result['initial_content_sha256']=content_hash(result['initial_state'])
    return result


def validate_fingerprints(obj):
    if (type(obj.get('evidence_version')) is not int or obj['evidence_version']!=2
            or obj.get('initial_hash_version')!=LEGACY_VERSION or obj.get('initial_content_version')!=CONTENT_VERSION):
        raise ValueError('EXPLICIT_EVIDENCE_VERSION_REQUIRED')
    if obj.get('initial_sha256')!=legacy_hash(obj['initial_state']): raise ValueError('LEGACY_INITIAL_HASH')
    if obj.get('initial_content_sha256')!=content_hash(obj['initial_state']): raise ValueError('CONTENT_INITIAL_HASH')
    return True


def validate_saved(saved,expected,session):
    validate_fingerprints(saved)
    if (type(session.get('evidence_version')) is not int or session['evidence_version']!=2
            or session.get('initial_content_version')!=CONTENT_VERSION or session.get('evidence_policy_sha256')!=policy_hash()):
        raise ValueError('SESSION_EVIDENCE_VERSION_OR_POLICY')
    if canonical(saved)!=canonical(expected): raise ValueError('SAVED_MEMORY_CONTENT_MISMATCH')
    from hashlib import sha256
    sh=sha256(canonical(session)).hexdigest()
    if (saved.get('session_id')!=session['session_id'] or saved.get('session_sha256')!=sh
            or saved.get('code_manifest_sha256')!=session['code_manifest_sha256']
            or saved.get('state')!='CANDIDATE' or saved.get('goal')!=session['goal']
            or saved.get('method') not in session['methods']): raise ValueError('SAVED_REQUEST_BINDING')
    service=saved['service']; start=service['start_decision']
    if ((service['N'],service['T'])!=(session['N'],session['T']) or service['env_id']!=session['env']['env_id']
            or service['run_id']!=saved['run_id'] or service['request_id']!=saved['run_id']
            or len(saved['initial_state']['q'])!=session['N'] or start['start']!='FIXED_START:163'
            or start['start_p']!=163 or start['initial_state_digest']!=saved['initial_sha256']):
        raise ValueError('SAVED_INPUT_OR_START')
    if not service.get('passes'): raise ValueError('SAVED_RESULT_MISSING')
    wanted={'SERIAL':('CPU_SERIAL',0),'W6':('CPU_PARALLEL',6),'GPU':('GPU_HYBRID',0)}[saved['method']]
    plan=service['passes'][0]['attempts'][0]['plan']
    if ((plan['backend'],plan['worker_count'])!=wanted or plan['p']!=163
            or plan['env_id']!=session['env']['env_id'] or saved['selection']['plan']!=plan):
        raise ValueError('SAVED_METHOD_OR_PRECISION')
    return True  # Integrity only; never VERIFIED or an inspector approval.


def _exclusive(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(obj)); stream.flush(); os.fsync(stream.fileno())


def write_metrics(path,metrics,*,writer):
    start=time.monotonic_ns(); writer(path,metrics)
    return dict(observer_write_ns=time.monotonic_ns()-start,observer_record_bytes=Path(path).stat().st_size)


def save_and_check(path,obj,session,*,writer):
    path=Path(path); total=time.monotonic_ns(); metrics={}
    import psutil
    proc=psutil.Process(); rss=proc.memory_info().rss
    if any(k in obj for k in ('evidence_version','initial_content_sha256','initial_hash_version')):
        validate_fingerprints(obj)  # Do not silently repair supplied V2 metadata.
    record=dict(obj,evidence_version=2,initial_hash_version=LEGACY_VERSION,initial_content_version=CONTENT_VERSION)
    t=time.monotonic_ns(); record['initial_sha256']=legacy_hash(record['initial_state']); metrics['legacy_hash_ns']=time.monotonic_ns()-t
    t=time.monotonic_ns(); record['initial_content_sha256']=content_hash(record['initial_state']); metrics['canonical_hash_ns']=time.monotonic_ns()-t
    try:
        t=time.monotonic_ns(); writer(path,record); metrics['save_ns']=time.monotonic_ns()-t
        t=time.monotonic_ns(); raw=path.read_bytes(); saved=parse_bytes(raw); metrics['reread_ns']=time.monotonic_ns()-t
        t=time.monotonic_ns(); validate_saved(saved,record,session)
        if raw!=canonical(record): raise ValueError('SAVED_RAW_BYTES_MISMATCH')
        metrics['lightweight_check_ns']=time.monotonic_ns()-t
        metrics.update(raw_sha256=hashlib.sha256(raw).hexdigest(),record_bytes=len(raw),
             additional_record_bytes=max(0,len(raw)-len(canonical(obj))),rss_delta_bytes=max(0,proc.memory_info().rss-rss),
             memory_measurement='RSS_SNAPSHOT_DELTA; TRANSIENT_PEAK_MEASURED_ONLY_IN_BENCHMARK',physics_calls=0,
             independent_replays=0,total_ns=time.monotonic_ns()-total,verdict='SAVED_INTEGRITY_ONLY; NOT_VERIFIED')
        return saved,metrics
    except BaseException as error:
        refusal=path.parent/'evidence_rejections'/(path.stem+'.json')
        if not refusal.exists():
            _exclusive(refusal,dict(verdict='REFUSED',reason=str(error),source_file=path.name,
                      raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
                      next_calculation='STOP',physics_calls=0))
        raise
