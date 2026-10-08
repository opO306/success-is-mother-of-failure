"""Remote-only first-gate, cost and approval faults; originals/mocks, no new physics."""
import copy
import hashlib
import json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from experiments.adaptive_execution_real_learning_pilot_v0 import runner, inspector, governance
from experiments.adaptive_execution_real_learning_pilot_v0.common import canonical, digest, public, read, write_new, raw_hash
from experiments.evidence_canonicalization_v0 import history, fingerprints as FP
from experiments.adaptive_execution_real_learning_pilot_a_resume_v1 import policy, evidence, offline


def saved_fixture(tmp_path,method='SERIAL',repeat=0):
    panel=history.load_originals(); s=copy.deepcopy(panel['session'])
    s.update(evidence_version=2,initial_content_version=FP.CONTENT_VERSION,evidence_policy_sha256=FP.policy_hash(),
             resume_protocol_sha256=policy.protocol_hash(),code_manifest_sha256=raw_hash(runner.code_manifest_path()))
    old=next(x for x in panel['records'] if x['method']==method and x['repeat']==repeat)
    obj=copy.deepcopy(old); obj.update(session_sha256=digest(s),code_manifest_sha256=s['code_manifest_sha256'])
    obj['service']['start_decision'].update(start='FIXED_START:163',start_p=163)
    obj['selection']['requested_method']=method
    obj=FP.stamp(obj); directory=tmp_path/'measurement'; directory.mkdir(exist_ok=True)
    def capture():
        return FP.save_and_check(directory/f'{method}_{repeat}.json',obj,s,writer=write_new)
    record,metrics=capture(); metrics_path=directory/'evidence_metrics'/f'{method}_{repeat}.json'
    metrics['save_reread_cpu_ns']=1; FP.write_metrics(metrics_path,metrics,writer=write_new)
    o=record['observation']; extra=max(metrics['total_ns']+1,1_000_000)
    cost=dict(schema='A_RESUME_FULL_REQUEST_COST_V1',session_sha256=digest(s),code_manifest_sha256=s['code_manifest_sha256'],
              resume_protocol_sha256=policy.protocol_hash(),record_sha256=raw_hash(directory/f'{method}_{repeat}.json'),
              metrics_sha256=raw_hash(metrics_path),run_id=record['run_id'],method=method,repeat=repeat,
              start_wall_ns=o['start_wall_ns']-1,end_wall_ns=o['end_wall_ns']+extra-1,
              wall_ns=o['wall_ns']+extra,cpu_ns=o['cpu_ns']+10,
              cpu_deltas_ns=dict(o['cpu_deltas_ns'],controller=o['cpu_deltas_ns']['controller']+10),
              additional_wall_ns=extra,additional_cpu_ns=10,cost_scope=policy.protocol()['request_cost_scope'],
              light_scope=policy.protocol()['light_cost_scope'])
    cost_path=directory/'request_costs'/f'{method}_{repeat}.json'; write_new(cost_path,cost)
    replay=copy.deepcopy(panel['replays'])
    for r in replay.values(): r.update(session_sha256=digest(s),code_manifest_sha256=s['code_manifest_sha256'])
    write_new(tmp_path/'session.json',s); write_new(tmp_path/'replay.json',replay)
    return record,s,replay,cost_path


def test_full_request_cost_includes_stored_file_work(tmp_path):
    obj,s,_,path=saved_fixture(tmp_path)
    row,files=evidence.read_cost(path.parent.parent,obj,s)
    assert row['wall_ns']>obj['observation']['wall_ns']
    assert row['cpu_ns']>obj['observation']['cpu_ns']
    assert len(files)==3 and path.name in {p.name for p in files}


@pytest.mark.parametrize('fault',['raw','metric_raw','session','source','protocol','clock','cpu','delta','scope','overhead','negative','boolean'])
def test_request_cost_faults_are_refused_and_preserved(tmp_path,fault):
    obj,s,_,path=saved_fixture(tmp_path); bad=read(path)
    fields={'raw':'record_sha256','metric_raw':'metrics_sha256','session':'session_sha256',
            'source':'code_manifest_sha256','protocol':'resume_protocol_sha256'}
    if fault in fields: bad[fields[fault]]='0'*64
    elif fault=='clock': bad['end_wall_ns']+=1
    elif fault=='cpu': bad['cpu_ns']+=1
    elif fault=='delta': bad['additional_cpu_ns']+=1
    elif fault=='scope': bad['cost_scope']='CALCULATOR_ONLY'
    elif fault=='overhead':
        bad['additional_wall_ns']=obj['observation']['wall_ns']//10
        bad['wall_ns']=obj['observation']['wall_ns']+bad['additional_wall_ns']
        bad['end_wall_ns']=bad['start_wall_ns']+bad['wall_ns']
    elif fault=='negative': bad['additional_cpu_ns']=-1
    else: bad['cpu_ns']=True
    path.write_bytes(canonical(bad))
    with pytest.raises(ValueError): evidence.read_cost(path.parent.parent,obj,s)
    assert path.exists() and read(path)==bad


def test_saved_result_tampering_is_refused_by_existing_inspector(tmp_path):
    obj,s,replay,path=saved_fixture(tmp_path)
    record=path.parent.parent/f"{obj['method']}_{obj['repeat']}.json"
    bad=read(record); bad['service']['passes'][0]['cells']=['altered']
    record.write_bytes(canonical(bad))
    with pytest.raises(ValueError): inspector.inspect_first(tmp_path)
    assert record.exists()


def test_first_inspector_reads_one_serial_and_new_session_replay(tmp_path):
    _,s,_,_=saved_fixture(tmp_path)
    result=inspector.inspect_first(tmp_path)
    assert result['verdict']=='REAL_SESSION_FIRST_RESULT_CHECKED'
    assert result['session_sha256']==digest(s) and result['method']=='SERIAL'
    assert result['real_cost_evidence'] is False  # Not a promotable ten-repeat profile.
    assert len(result['raw_files'])==5


@pytest.mark.parametrize('fault',['missing_replay','cross_session','synthetic','extra_file','wrong_method','wrong_precision'])
def test_first_gate_failure_stops_before_w6(tmp_path,fault):
    obj,s,replay,path=saved_fixture(tmp_path); record=path.parent.parent/'SERIAL_0.json'
    if fault=='missing_replay': (tmp_path/'replay.json').rename(tmp_path/'replay.missing_preserved')
    elif fault=='cross_session':
        for r in replay.values(): r['session_sha256']='0'*64
        (tmp_path/'replay.json').write_bytes(canonical(replay))
    elif fault=='synthetic':
        s['origin']='SYNTHETIC_TEST_ONLY'; (tmp_path/'session.json').write_bytes(canonical(s))
    elif fault=='extra_file': write_new(record.parent/'W6_0.json',obj)
    elif fault=='wrong_method': obj['method']='W6'; record.write_bytes(canonical(obj))
    else: obj['service']['final_p']=162; record.write_bytes(canonical(obj))
    calls=[]
    with pytest.raises((ValueError,FileNotFoundError)):
        inspector.inspect_first(tmp_path)
        calls.append('W6')
    assert calls==[] and record.exists()


@pytest.mark.parametrize('fault',['signature','raw','source','session','protocol','verdict','scope'])
def test_first_receipt_wrong_approval_cannot_continue(tmp_path,fault):
    _,s,_,_=saved_fixture(tmp_path); judge=Ed25519PrivateKey.generate()
    body=inspector.inspect_first(tmp_path)
    if fault in ('source','session','protocol'):
        body[{'source':'code_manifest_sha256','session':'session_sha256','protocol':'resume_protocol_sha256'}[fault]]='0'*64
    elif fault=='verdict': body['verdict']='REAL_SESSION_COST_CHECKED'
    elif fault=='scope': body['scope']='PRODUCTION'
    elif fault=='raw': body['raw_files']['measurement/SERIAL_0.json']='0'*64
    receipt=dict(body=body,signature=judge.sign(b'REAL_PILOT_RECEIPT\0'+canonical(body)).hex())
    if fault=='signature': receipt['signature']='0'*128
    with pytest.raises(ValueError): evidence.check_receipt(public(judge.public_key()),receipt,tmp_path,s,'CHECK_FIRST')


def test_correct_first_receipt_is_not_manager_promotion(tmp_path):
    _,s,_,_=saved_fixture(tmp_path); judge,ruler=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    body=inspector.inspect_first(tmp_path)
    receipt=dict(body=body,signature=judge.sign(b'REAL_PILOT_RECEIPT\0'+canonical(body)).hex())
    evidence.check_receipt(public(judge.public_key()),receipt,tmp_path,s,'CHECK_FIRST')
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'witness',
             governance.Roots(public(judge.public_key()),public(ruler.public_key()),'RESEARCH_ONLY'),ruler)
    with pytest.raises(ValueError): mgr.admit(receipt)
    assert mgr.choose(mgr.begin('WALL_MIN',s),s)=='LEGACY'
    assert mgr.rejections.history()


@pytest.mark.parametrize('fault',['old_142','missing_protocol','old_code','skip','old_scope'])
def test_old_or_incomplete_offline_gate_is_refused(fault):
    code='new-code'; n=222
    status=dict(status='PASS',code_seal_sha256=code,resume_protocol_sha256=policy.protocol_hash(),tests=n,
                failed=0,skipped=0,physics_calls=0,gpu_calls=0,mode='OFFLINE_CONTRACT_ONLY')
    if fault=='old_142': status['tests']=142
    elif fault=='missing_protocol': del status['resume_protocol_sha256']
    elif fault=='old_code': status['code_seal_sha256']='old'
    elif fault=='skip': status['skipped']=1
    else: status['mode']='HISTORICAL_REVIEW_ONLY'
    with pytest.raises(ValueError): offline.validate_status(status,code,n)


def test_receipt_raw_binding_detects_later_whitespace_edit(tmp_path):
    _,s,_,path=saved_fixture(tmp_path); judge=Ed25519PrivateKey.generate(); body=inspector.inspect_first(tmp_path)
    receipt=dict(body=body,signature=judge.sign(b'REAL_PILOT_RECEIPT\0'+canonical(body)).hex())
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError): evidence.check_receipt(public(judge.public_key()),receipt,tmp_path,s,'CHECK_FIRST')


def test_resume_protocol_excludes_gpu_and_preserves_old_seals():
    p=policy.protocol(); assert p['stage']['methods']==['SERIAL','W6'] and p['learned_requests']==1
    assert p['order'][0]==['SERIAL',0] and len(p['order'])==10
    assert p['spread_max_ratio']=='1.25' and p['budget']['allocation_seconds']==3600
    policy.check_protocol()


def test_runner_has_explicit_first_gate_before_remaining_samples():
    # Independent of physics, ordering is exercised with stub operations.
    calls=[]
    def capture(method,repeat): calls.append((method,repeat)); return {'method':method,'repeat':repeat}
    def gate(record): calls.append('CHECK_FIRST'); raise ValueError('injected first failure')
    with pytest.raises(ValueError): runner.collect_a(capture,gate,lambda record:None)
    assert calls==[('SERIAL',0),'CHECK_FIRST']


def test_runner_first_success_has_exact_ten_calls_and_one_gate():
    calls=[]; gates=[]
    records=runner.collect_a(lambda m,r:calls.append((m,r)) or dict(method=m,repeat=r),
                             lambda obj:gates.append(obj),lambda obj:None)
    assert calls==[tuple(x) for x in policy.protocol()['order']] and len(records)==10
    assert gates==[records[0]]
