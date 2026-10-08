"""Independent evidence reader. Shared V1 RwForce is explicitly not formula independence."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from experiments.adaptive_execution_v1 import checker as CK
from experiments.multiatom_parallel_v1 import scenarios as SC
from .common import HERE, ROOT, canonical, digest, read, raw_hash, write_new, check_seals, ns


def initial_state(N):
    q,p=SC.initial(N)
    return {'q':[[str(x) for x in row] for row in q], 'p':[[str(x) for x in row] for row in p]}


def require(condition,reason):
    if not condition: raise ValueError(reason)


def validate_record(obj,session,replays,*,contract_only=False):
    """Checks one original record, without producer imports or trusting its summary."""
    expected='OFFLINE_CONTRACT_FIXTURE' if contract_only else 'OBSERVED_REAL'
    require(obj['kind']==expected and session['origin']==expected,'REAL_ORIGIN_REQUIRED')
    require(contract_only or not session.get('test_only',False),'TEST_ONLY_SESSION_REFUSED')
    require(obj['session_id']==session['session_id'] and obj['session_sha256']==digest(session),'SESSION_MIX')
    require(obj['code_manifest_sha256']==session['code_manifest_sha256'],'SOURCE_MIX')
    require(obj['state']=='CANDIDATE','EXECUTOR_PROMOTION_REFUSED')
    s=obj['service']; N,T=s['N'],s['T']; env=session['env']
    require((N,T)==(session['N'],session['T']) and s['env_id']==env['env_id'],'REQUEST_OR_ENV_MIX')
    require(env['env_id']==CK.own_env_id(env),'ENV_ID_INTEGRITY')
    require(obj['initial_state']==initial_state(N),'INITIAL_STATE_INTEGRITY')
    require(s['start_decision']['initial_state_digest']==CK.own_initial_digest(N),'ORIGINAL_START_REFUSED')
    require(s['status']=='DECIDED' and s['final_p']==163 and s['p_sequence']==[163] and s['n_passes']==1,'P163_PROFILE_NOT_READY')
    require(len(s['passes'])==1,'PASS_COUNT')
    require(obj['method'] in session['methods'] and obj['goal']==session['goal'],'METHOD_OR_GOAL_MIX')
    allowed={'SERIAL':('CPU_SERIAL',0),'W6':('CPU_PARALLEL',6),'GPU':('GPU_HYBRID',0)}
    wanted=allowed[obj['method']]; costs=[]; errors=[]
    own={}
    for key,replay in replays.items():
        require(replay['origin']==('OFFLINE_CONTRACT_FIXTURE' if contract_only else 'INDEPENDENT_REPLAY'),'REPLAY_ORIGIN_REQUIRED')
        require(replay['session_sha256']==digest(session) and replay['code_manifest_sha256']==session['code_manifest_sha256'],'REPLAY_SESSION_MIX')
        own[tuple(map(int,key.split('/')))]=replay['result']
    for pz in s['passes']:
        require(pz['requested_p']==163 and pz['start']=='ORIGINAL_STATE','PRECISION_OR_RESTART')
        first=pz['attempts'][0]['plan']
        require((first['backend'],first['worker_count'])==wanted,'REQUESTED_METHOD_DIFFERS')
        for attempt in pz['attempts']:
            res=attempt.get('result')
            require(res is not None and res.get('cpu_s') is not None and res.get('wall_s') is not None,'FAILED_ATTEMPT_COST_UNKNOWN')
            require(res.get('status_class')=='OK','FALLBACK_OR_FAILED_MEASUREMENT_NOT_READY')
            costs.append(ns(res['cpu_s']))
            require(attempt['plan']['env_id']==env['env_id'] and attempt['plan']['p']==163,'ATTEMPT_ENV_OR_PRECISION')
            require(res['backend']==attempt['plan']['backend'],'RESULT_BACKEND_MIX')
            for field in CK.FIELDS:
                require(res.get(field)==pz.get(field),'ATTEMPT_RESULT_DIFFERS:'+field)
            if first['backend']=='GPU_HYBRID':
                require(CK.own_gpu_ok(N,T,163,env,False),'GPU_OUTSIDE_SEALED_DOMAIN')
        CK._check_pass(obj['run_id'],s,pz,env,None,False,own,errors)
        require(not errors,'V1_CHECKER:'+repr(errors))
        require(abs(ns(pz['cpu_s'])-sum(ns(a['result']['cpu_s']) for a in pz['attempts']))<=2,'PASS_CPU_ACCOUNTING')
    require(abs(ns(s['service_cpu_s'])-sum(costs))<=2,'SERVICE_CPU_ACCOUNTING')
    observation=obj['observation']; wall,cpu=observation['wall_ns'],observation['cpu_ns']
    require(type(wall) is int and type(cpu) is int and wall>0 and cpu>0,'CLOCK_INVALID')
    require(wall>=ns(s['service_wall_s']),'OUTER_WALL_EXCLUDES_SERVICE')
    require(cpu+max(50_000_000,cpu//100)>=sum(costs),'OBSERVED_CPU_EXCLUDES_ATTEMPTS')
    if not contract_only:
        require(observation['origin']=='OS_MONOTONIC_AND_PROCESS_CPU' and observation['pid']>0,'OBSERVATION_ORIGIN')
        require(observation['end_wall_ns']-observation['start_wall_ns']==wall,'WALL_CLOCK_INTEGRITY')
        require(sum(observation['cpu_deltas_ns'].values())==cpu,'CPU_CLOCK_INTEGRITY')
        require(obj['initial_sha256']==hashlib.sha256(json.dumps(obj['initial_state']).encode()).hexdigest(),'INITIAL_HASH')
        require(session.get('boot_id') and session.get('hostname') and session.get('instance_id') and session.get('machine_id'),'HOST_ID_REQUIRED')
    return {'method':obj['method'],'wall_ns':wall,'cpu_ns':cpu}


def validate_panel(records,session,replays,*,contract_only=False):
    require(len(records)==10,'MISSING_REPEAT')
    samples={method:[] for method in session['methods']}; ids=set(); repeats=set()
    for obj in records:
        require(obj['run_id'] not in ids and (obj['method'],obj['repeat']) not in repeats,'DUPLICATE_RECORD')
        ids.add(obj['run_id']); repeats.add((obj['method'],obj['repeat']))
        samples[obj['method']].append(validate_record(obj,session,replays,contract_only=contract_only))
    rows=[]
    for method,group in sorted(samples.items()):
        require({rep for met,rep in repeats if met==method}==set(range(5)),'REPEAT_IDENTITY')
        for metric in ('wall_ns','cpu_ns'):
            values=[row[metric] for row in group]
            require(min(values)>0 and max(values)*4<=min(values)*5,'SPREAD_NOT_READY:'+method+'/'+metric)
        rows.append(dict(method=method,wall_ns=int(statistics.median(x['wall_ns'] for x in group)),
                         cpu_ns=int(statistics.median(x['cpu_ns'] for x in group)),repeats=5))
    return dict(verdict='CONTRACT_VALIDATED' if contract_only else 'REAL_SESSION_COST_CHECKED',errors=[],
                real_cost_evidence=not contract_only,formula_independence='UNRESOLVED_SHARED_RWFORCE',
                session_sha256=digest(session),code_manifest_sha256=session['code_manifest_sha256'],
                protocol_sha256=raw_hash(HERE/'protocol.json'),goal=session['goal'],rows=rows,
                records_sha256=[digest(obj) for obj in records],replays_sha256=digest(replays),
                scope='OFFLINE_CONTRACT_ONLY' if contract_only else 'RESEARCH_ONLY')


def inspect_directory(directory):
    check_seals(); directory=Path(directory); session=read(directory/'session.json')
    require(session['origin']=='OBSERVED_REAL','REAL_ORIGIN_REQUIRED')
    require(session['code_manifest_sha256']==raw_hash(HERE/'code_seal.json'),'CODE_SEAL_MISMATCH')
    for relative,expected in read(HERE/'code_seal.json')['files'].items():
        require(raw_hash(ROOT/relative)==expected,'SOURCE_INTEGRITY:'+relative)
    paths=sorted((directory/'measurement').glob('*.json')); require(len(paths)==10,'MISSING_REPEAT')
    require(sum(p.stat().st_size for p in paths)<=64*1024*1024,'EVIDENCE_SIZE_CAP')
    replay=read(directory/'replay.json')
    report=validate_panel([read(path) for path in paths],session,replay)
    report['stage']=directory.name
    report['raw_files']={str(path.relative_to(directory)):raw_hash(path) for path in [directory/'session.json',directory/'replay.json',*paths]}
    return report


def main():
    import sys
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from .common import public
    parser=argparse.ArgumentParser(); parser.add_argument('--serve',required=True,type=Path); args=parser.parse_args()
    # The inspector creates and retains its own key before collection. There is no sign-arbitrary-body API.
    check_seals(); key=Ed25519PrivateKey.generate(); root=args.serve.resolve()
    print(json.dumps({'inspector_public_key':public(key.public_key()),'code_manifest_sha256':raw_hash(HERE/'code_seal.json')}),flush=True)
    for line in sys.stdin:
        command=json.loads(line)
        if command=={'operation':'CLOSE'}: return
        target=(root/command['stage']).resolve()
        try:
            require(command['operation'] in ('INSPECT','CHECK_NEXT') and command['stage'] in ('A','B') and target.parent==root,'INSPECTOR_REQUEST_SCOPE')
            if command['operation']=='INSPECT':
                report=inspect_directory(target); output=target/'receipt.json'
            else:
                check_seals(); session=read(target/'session.json'); files=sorted((target/'next_request').glob('*.json'))
                require(len(files)==1,'NEXT_REQUEST_EVIDENCE_COUNT')
                validate_record(read(files[0]),session,read(target/'replay.json'))
                report=dict(verdict='REAL_SESSION_RESULT_CHECKED',session_sha256=digest(session),
                       record_sha256=raw_hash(files[0]),formula_independence='UNRESOLVED_SHARED_RWFORCE'); output=target/'next_request_receipt.json'
            write_new(output,{'body':report,'signature':key.sign(b'REAL_PILOT_RECEIPT\0'+canonical(report)).hex()})
            print(json.dumps({'verdict':report['verdict'],'receipt_sha256':raw_hash(output)}),flush=True)
        except Exception as error:
            write_new(target/'inspector_refused.json',{'verdict':'REFUSED','error':str(error)})
            print(json.dumps({'verdict':'REFUSED','error':str(error)}),flush=True)
            return


if __name__=='__main__': main()
