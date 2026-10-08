"""Request cost evidence and signed-gate bindings. No calculator or key creation."""
import time
from pathlib import Path
from . import policy
from experiments.evidence_canonicalization_v0 import fingerprints as FP
from experiments.adaptive_execution_real_learning_pilot_v0.common import digest, raw_hash, write_new, verify


def strict_read(path): return FP.parse_bytes(Path(path).read_bytes())


def require(condition,reason):
    if not condition: raise ValueError(reason)


def capture_cost(directory,session,method,repeat,capture,clock):
    """The sidecar's own write is charged by the enclosing management ledger/allocation."""
    start_cpu=clock(); start=time.monotonic_ns()
    obj=capture()  # Already the strict, saved-file reread returned by existing bridge.
    end=time.monotonic_ns(); end_cpu=clock(); directory=Path(directory)
    deltas={k:end_cpu[k]-start_cpu[k] for k in start_cpu}
    o=obj['observation']; wall=end-start; cpu=sum(deltas.values())
    record=directory/f'{method}_{repeat}.json'; metrics=directory/'evidence_metrics'/record.name
    p=policy.protocol()
    sidecar=dict(schema='A_RESUME_FULL_REQUEST_COST_V1',session_sha256=digest(session),
       code_manifest_sha256=session['code_manifest_sha256'],resume_protocol_sha256=policy.protocol_hash(),
       record_sha256=raw_hash(record),metrics_sha256=raw_hash(metrics),run_id=obj['run_id'],method=obj['method'],repeat=repeat,
       start_wall_ns=start,end_wall_ns=end,wall_ns=wall,cpu_ns=cpu,cpu_deltas_ns=deltas,
       additional_wall_ns=wall-o['wall_ns'],additional_cpu_ns=cpu-o['cpu_ns'],
       cost_scope=p['request_cost_scope'],light_scope=p['light_cost_scope'])
    write_new(directory/'request_costs'/record.name,sidecar)
    read_cost(directory,obj,session)  # Refuse before any subsequent expensive action.
    return obj


def read_cost(directory,obj,session):
    """Read actual raw files; costs are OS-clock evidence, not hardware attestation."""
    directory=Path(directory); record=directory/f"{obj['method']}_{obj['repeat']}.json"
    metric=directory/'evidence_metrics'/record.name; path=directory/'request_costs'/record.name
    cost=strict_read(path); metrics=strict_read(metric); original=strict_read(record); p=policy.protocol()
    require(digest(original)==digest(obj),'COST_RECORD_CONTENT')
    require(cost.get('schema')=='A_RESUME_FULL_REQUEST_COST_V1','COST_SCHEMA')
    require(cost.get('session_sha256')==digest(session) and cost.get('code_manifest_sha256')==session['code_manifest_sha256']
            and cost.get('resume_protocol_sha256')==policy.protocol_hash()==session.get('resume_protocol_sha256'),'COST_SESSION_SOURCE_POLICY')
    require(cost.get('record_sha256')==metrics.get('raw_sha256')==raw_hash(record)
            and cost.get('metrics_sha256')==raw_hash(metric),'COST_RAW_BINDING')
    require((cost.get('run_id'),cost.get('method'),cost.get('repeat'))==(obj['run_id'],obj['method'],obj['repeat']),'COST_REQUEST_BINDING')
    require(obj['run_id']==session['session_id']+'/'+obj['method']+'/'+str(obj['repeat']),'COST_RUN_ID_SESSION_METHOD_REPEAT')
    require(cost.get('cost_scope')==p['request_cost_scope'] and cost.get('light_scope')==p['light_cost_scope'],'COST_SCOPE')
    values=('start_wall_ns','end_wall_ns','wall_ns','cpu_ns','additional_wall_ns','additional_cpu_ns')
    require(all(type(cost.get(k)) is int and cost[k]>=0 for k in values),'COST_CLOCK_TYPE')
    deltas=cost.get('cpu_deltas_ns',{}); o=obj['observation']
    require(set(deltas)==set(o['cpu_deltas_ns']) and all(type(v) is int and v>=0 for v in deltas.values())
            and sum(deltas.values())==cost['cpu_ns'],'COST_CPU_CLOCK')
    require(cost['start_wall_ns']<=o['start_wall_ns'] and cost['end_wall_ns']>=o['end_wall_ns']
            and cost['end_wall_ns']-cost['start_wall_ns']==cost['wall_ns'],'COST_WALL_CLOCK')
    require(cost['wall_ns']-o['wall_ns']==cost['additional_wall_ns']
            and cost['cpu_ns']-o['cpu_ns']==cost['additional_cpu_ns'],'COST_DELTA')
    require(all(deltas[k]>=v for k,v in o['cpu_deltas_ns'].items()),'COST_CPU_COMPONENT')
    require(type(metrics.get('total_ns')) is int and 0<=metrics['total_ns']<=cost['additional_wall_ns']
            and type(metrics.get('save_reread_cpu_ns')) is int and 0<=metrics['save_reread_cpu_ns']<=cost['additional_cpu_ns']
            and metrics.get('physics_calls')==0 and metrics.get('independent_replays')==0,'LIGHT_METRIC_SCOPE')
    require(cost['additional_wall_ns']*100<=o['wall_ns']*p['light_wall_percent_max'],'LIGHT_OVERHEAD_EXCEEDS_ONE_PERCENT')
    return dict(method=obj['method'],wall_ns=cost['wall_ns'],cpu_ns=cost['cpu_ns']),[record,metric,path]


VERDICTS={'CHECK_FIRST':'REAL_SESSION_FIRST_RESULT_CHECKED','INSPECT':'REAL_SESSION_COST_CHECKED','CHECK_NEXT':'REAL_SESSION_RESULT_CHECKED'}
RECEIPTS={'CHECK_FIRST':'first_result_receipt.json','INSPECT':'receipt.json','CHECK_NEXT':'next_request_receipt.json'}


def check_receipt(inspector_key,receipt,directory,session,operation):
    verify(inspector_key,b'REAL_PILOT_RECEIPT\0',receipt); b=receipt['body']; directory=Path(directory).resolve()
    require(b.get('verdict')==VERDICTS[operation] and b.get('scope')=='RESEARCH_ONLY'
            and b.get('session_sha256')==digest(session) and b.get('code_manifest_sha256')==session['code_manifest_sha256']
            and b.get('resume_protocol_sha256')==session['resume_protocol_sha256']==policy.protocol_hash()
            and b.get('formula_independence')=='UNRESOLVED_SHARED_RWFORCE' and not b.get('errors'),'SIGNED_GATE_BINDING')
    require(bool(b.get('raw_files')),'SIGNED_GATE_RAW_REQUIRED')
    for relative,wanted in b['raw_files'].items():
        path=(directory/relative).resolve()
        require(path.is_relative_to(directory) and raw_hash(path)==wanted,'SIGNED_GATE_RAW_INTEGRITY')
    expected=[directory/'session.json',directory/'replay.json']
    location='next_request' if operation=='CHECK_NEXT' else 'measurement'
    records=sorted((directory/location).glob('*.json'))
    require(len(records)==(10 if operation=='INSPECT' else 1),'SIGNED_GATE_RECORD_COUNT')
    for record in records:
        expected.extend([record,record.parent/'evidence_metrics'/record.name,record.parent/'request_costs'/record.name])
    require(set(b['raw_files'])=={p.relative_to(directory).as_posix() for p in expected},'SIGNED_GATE_REQUIRED_FILES')
    if operation=='CHECK_FIRST': require(b.get('method')=='SERIAL' and b.get('repeat')==0
                  and b.get('real_cost_evidence') is False,'SIGNED_FIRST_SCOPE')
    return b
