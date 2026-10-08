"""Remote-only stored-file/fault tests. No new trajectory, GPU, rental or service."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from experiments.adaptive_execution_real_learning_pilot_v0 import inspector, governance, bridge, runner
from experiments.adaptive_execution_real_learning_pilot_v0.common import ROOT, read, canonical, digest, write_new, public
from experiments.evidence_canonicalization_v0 import fingerprints as FP, history, correction, benchmark


def fixture():
    panel=history.load_originals()
    s=copy.deepcopy(panel['session']); s.update(origin='FORMAT_TEST_ONLY',evidence_version=2,
                  initial_content_version=FP.CONTENT_VERSION,evidence_policy_sha256=FP.policy_hash())
    obj=copy.deepcopy(panel['records'][0]); obj.update(kind='FORMAT_TEST_ONLY',session_sha256=digest(s))
    return FP.stamp(obj),s


def test_content_hash_ignores_mapping_key_order():
    state={'q':[['1','2']], 'p':[['3','4']]}
    assert FP.content_hash(state)==FP.content_hash({'p':state['p'],'q':state['q']})


def test_legacy_hash_exactly_recreates_q_then_p():
    state={'p':[['3','4']],'q':[['1','2']]}
    expected=hashlib.sha256(json.dumps({'q':state['q'],'p':state['p']}).encode()).hexdigest()
    assert FP.legacy_hash(state)==expected


@pytest.mark.parametrize('change',['q','p','atom_order','coordinate_order'])
def test_meaningful_array_or_digit_changes_are_detected(change):
    state={'q':[['1','2'],['5','6']], 'p':[['3','4'],['7','8']]}; bad=copy.deepcopy(state)
    if change in ('q','p'): bad[change][0][0]='9'
    elif change=='atom_order': bad['q'].reverse()
    else: bad['q'][0].reverse()
    assert FP.content_hash(bad)!=FP.content_hash(state)


def test_numeric_strings_are_never_normalized():
    a={'q':[['1.00','-0.0']], 'p':[['1e0','+1']]}; b=copy.deepcopy(a); b['q'][0][0]='1.0'
    assert FP.content_hash(a)!=FP.content_hash(b)
    assert FP.parse_bytes(FP.content_bytes(a))==a


def test_original_fraction_strings_are_exact_and_not_reduced():
    a={'q':[['0','5']], 'p':[['-6/7','-1/7']]}; b=copy.deepcopy(a); b['p'][0][0]='-12/14'
    assert FP.parse_bytes(FP.content_bytes(a))==a
    assert FP.content_hash(a)!=FP.content_hash(b)


def test_zero_denominator_string_is_refused_without_numeric_conversion():
    with pytest.raises(ValueError): FP.content_hash({'q':[['0']], 'p':[['1/000']]})


@pytest.mark.parametrize('raw',[b'{"q":[],"q":[],"p":[]}',b'{"q":[],"p":[],"x":{"a":1,"a":2}}',b'{"q":NaN,"p":[]}'])
def test_duplicate_or_nonfinite_json_is_refused(raw):
    with pytest.raises(ValueError): FP.parse_bytes(raw)


@pytest.mark.parametrize('fault',['missing','extra','number','nonfinite_string','ragged','shape'])
def test_invalid_state_schema_is_refused(fault):
    state={'q':[['1','2']], 'p':[['3','4']]}
    if fault=='missing': del state['p']
    elif fault=='extra': state['precision']=163
    elif fault=='number': state['q'][0][0]=1.0
    elif fault=='nonfinite_string': state['p'][0][0]='NaN'
    elif fault=='ragged': state['q'].append(['1'])
    else: state['p']=[['3']]
    with pytest.raises(ValueError): FP.content_hash(state)


@pytest.mark.parametrize('fault',['missing','downgrade','unknown','content_version','legacy_version'])
def test_live_evidence_cannot_remove_or_downgrade_versions(fault):
    obj,s=fixture()
    if fault=='missing': del obj['evidence_version']
    elif fault=='downgrade': obj['evidence_version']=1
    elif fault=='unknown': obj['evidence_version']=999
    elif fault=='content_version': obj['initial_content_version']='OTHER'
    else: obj['initial_hash_version']='OTHER'
    with pytest.raises(ValueError): FP.validate_saved(obj,obj,s)


def test_real_file_save_reread_checks_both_fingerprints(tmp_path):
    obj,s=fixture(); saved,metrics=FP.save_and_check(tmp_path/'record.json',obj,s,writer=write_new)
    assert saved==read(tmp_path/'record.json')==obj
    assert metrics['raw_sha256']==hashlib.sha256((tmp_path/'record.json').read_bytes()).hexdigest()
    assert metrics['physics_calls']==0 and metrics['independent_replays']==0


def test_raw_file_hash_detects_whitespace_even_when_content_matches(tmp_path):
    obj,s=fixture(); path=tmp_path/'record.json'; saved,m=FP.save_and_check(path,obj,s,writer=write_new)
    changed=path.read_bytes()+b'\n'
    assert FP.parse_bytes(changed)==saved
    assert hashlib.sha256(changed).hexdigest()!=m['raw_sha256']


def test_first_bad_persisted_record_prevents_replay_and_next_calculation(tmp_path,monkeypatch):
    from experiments.adaptive_execution_v1 import environment as ENV,selector as SEL,experience as EXP,service as SVC
    panel=history.load_originals(); calls=[]
    monkeypatch.setattr(ENV,'collect',lambda:copy.deepcopy(panel['session']['env']))
    monkeypatch.setattr(SEL,'cpu_verified',lambda env:True); monkeypatch.setattr(SEL,'placements',lambda env:{'W6':{}})
    monkeypatch.setattr(EXP,'load_store',lambda:None)
    monkeypatch.setattr(runner,'authorize',lambda *a,**kw:None)
    def fake_service(*args,**kw): calls.append('service'); return copy.deepcopy(panel['records'][0]['service'])
    monkeypatch.setattr(SVC,'run_request',fake_service)
    def broken_writer(path,obj):
        bad=copy.deepcopy(obj); bad['initial_state']['q'][0][0]='999'; write_new(path,bad)
    monkeypatch.setattr(bridge,'write_new',broken_writer)
    pilot=object.__new__(runner.Pilot); pilot.root=tmp_path; pilot.code=runner.code_check()
    pilot.ticket={'instance_id':54815136,'machine_id':56006}; pilot.seconds=lambda:120
    pilot.charged=lambda category,fn:fn(); pilot.book=type('Book',(),{'total':lambda self:{'wall_ns':0,'cpu_ns':0},
                       'events':type('Events',(),{'history':lambda self:[]})()})()
    pilot.mgr=type('Manager',(),{'begin':lambda *a:None,'choose':lambda *a:'LEGACY'})()
    pilot.gpu=None; pilot.child=lambda *a,**kw:calls.append('replay')
    with pytest.raises(ValueError): pilot.stage({'id':'A','N':14,'T':1000,'goal':'WALL_MIN','methods':['SERIAL','W6']})
    assert calls==['service']  # First mocked call only; replay and next expensive calls are zero.
    assert list((tmp_path/'A/measurement').glob('*.json'))
    rejection=read(next((tmp_path/'A/measurement/evidence_rejections').glob('*.json')))
    assert rejection['reason']=='LEGACY_INITIAL_HASH'


def test_existing_inspector_has_no_producer_import_or_arbitrary_repair_api():
    source=Path(inspector.__file__).read_text(encoding='utf-8'); tree=ast.parse(source)
    imports=[x.module or '' for x in ast.walk(tree) if isinstance(x,ast.ImportFrom)]
    assert not any(n.endswith(('bridge','runner','service','selector','governance','correction')) for n in imports)
    assert 'sign_arbitrary' not in source


def test_all_original_raw_pins_and_old_failure_are_unchanged():
    p=history.load_originals()
    assert p['original_status']=='REAL_LEARNING_FAIL' and p['original_refusal']['error']=='INITIAL_HASH'
    assert p['verified_raw_files']==68


def test_historical_reader_rederives_all_ten_records_without_physics(monkeypatch):
    monkeypatch.setattr(inspector.CK,'own_pass',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('NEW_PHYSICS_FORBIDDEN')))
    report=inspector.review_historical()
    assert report['verdict']=='VERIFIED_CONTENT' and report['classification']=='FORMAT_EQUIVALENT'
    assert len(report['records'])==10 and report['new_physics_calls']==report['independent_replays']==0
    assert report['original_status']=='REAL_LEARNING_FAIL' and report['scope']=='HISTORICAL_REVIEW_ONLY'


@pytest.mark.parametrize('fault',['unknown_raw','changed_raw','other_session'])
def test_historical_provenance_requires_exact_raw_and_session(fault):
    p=history.load_originals(); obj=copy.deepcopy(p['records'][0]); raw=p['record_raw_hashes'][0]
    if fault=='unknown_raw': raw=None
    elif fault=='changed_raw': raw='0'*64
    else: obj['session_id']='different'
    with pytest.raises(ValueError): inspector.review_original_record(obj,p,raw)


def signed_review():
    judge,ruler=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    roots=governance.Roots(public(judge.public_key()),public(ruler.public_key()),'RESEARCH_ONLY')
    body=inspector.review_historical(); receipt={'body':body,'signature':judge.sign(b'REAL_PILOT_RECEIPT\0'+canonical(body)).hex()}
    return judge,ruler,roots,receipt


@pytest.mark.parametrize('fault',['certificate','signature','wrong_signer','session'])
def test_tampered_correction_or_signature_is_refused(tmp_path,fault):
    judge,ruler,roots,receipt=signed_review(); cert=correction.derive(receipt,roots.inspector)
    if fault=='certificate': cert['body']['records'][0]['content_sha256']='0'*64
    elif fault=='signature': cert['inspector_receipt']['signature']='0'*128
    elif fault=='wrong_signer': cert['inspector_receipt']['signature']=ruler.sign(b'REAL_PILOT_RECEIPT\0'+canonical(receipt['body'])).hex()
    else: cert['body']['session_sha256']='different'
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'witness',roots,ruler)
    with pytest.raises(ValueError): mgr.review_correction(cert)
    assert mgr.rejections.history()


def test_even_signed_false_content_claim_is_rederived_and_rejected(tmp_path):
    judge,ruler,roots,receipt=signed_review()
    receipt['body']['records'][0]['content_sha256']='0'*64
    receipt['signature']=judge.sign(b'REAL_PILOT_RECEIPT\0'+canonical(receipt['body'])).hex()
    cert=correction.derive(receipt,roots.inspector)
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'witness',roots,ruler)
    with pytest.raises(ValueError,match='CORRECTION_RECORD_BINDING'): mgr.review_correction(cert)


def test_explicit_signed_correction_review_keeps_legacy_and_original_failure(tmp_path):
    judge,ruler,roots,receipt=signed_review(); cert=correction.derive(receipt,roots.inspector)
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'witness',roots,ruler)
    review=mgr.review_correction(cert); s=history.load_originals()['session']
    assert review['manager_approval']=='PENDING' and mgr.choose(mgr.begin('WALL_MIN',s),s)=='LEGACY'
    body=mgr.approval_body('LEGACY','WALL_MIN','format-review','TEST_ONLY explicit historical review')
    body['correction_id']=digest(cert)
    mgr.approve_correction(cert,{'body':body,'signature':ruler.sign(b'REAL_PILOT_APPROVAL\0'+canonical(body)).hex()})
    assert mgr.choose(mgr.begin('WALL_MIN',s),s)=='LEGACY'
    assert not list((mgr.directory/'profiles').glob('*.json'))
    assert history.load_originals()['original_status']=='REAL_LEARNING_FAIL'


@pytest.mark.parametrize('fault',['unsigned_manager','wrong_goal','wrong_id','profile_activation','replay'])
def test_bad_manager_correction_approval_is_rejected_and_preserved(tmp_path,fault):
    judge,ruler,roots,receipt=signed_review(); cert=correction.derive(receipt,roots.inspector)
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'witness',roots,ruler)
    body=mgr.approval_body('LEGACY','WALL_MIN','one','TEST_ONLY explicit review'); body['correction_id']=digest(cert)
    if fault=='wrong_goal': body['goal']='CPU_MIN'
    elif fault=='wrong_id': body['correction_id']='0'*64
    elif fault=='profile_activation': body['profile_id']='0'*64
    approval={'body':body,'signature':ruler.sign(b'REAL_PILOT_APPROVAL\0'+canonical(body)).hex()}
    if fault=='unsigned_manager': approval['signature']=''
    if fault=='replay': mgr.approve_correction(cert,approval)
    with pytest.raises(ValueError): mgr.approve_correction(cert,approval)
    assert mgr.rejections.history() and (mgr.directory/'STOP.json').exists()


@pytest.mark.parametrize('fault',['session','source','initial','precision','environment'])
def test_replay_reuse_never_crosses_bound_conditions(fault):
    p=history.load_originals(); s=copy.deepcopy(p['session']); replay=copy.deepcopy(p['replays'])
    if fault=='session': s['session_id']='other'
    elif fault=='source': s['code_manifest_sha256']='0'*64
    elif fault=='initial': p['records'][0]['initial_state']['q'][0][0]='999'
    elif fault=='precision': replay={'14/1000/162':next(iter(replay.values()))}
    else: s['env']['env_id']='other'
    with pytest.raises(ValueError): history.validate_replay_binding(s,replay,p['records'])


def test_overhead_has_actual_file_metrics_and_never_replays(tmp_path):
    obj,s=fixture(); row=benchmark.measure_record(obj,s,tmp_path,repeat=0)
    for field in ('canonical_hash_ns','legacy_hash_ns','save_ns','reread_ns','lightweight_check_ns','total_ns','traced_peak_bytes','rss_delta_bytes','record_bytes','additional_record_bytes'):
        assert type(row[field]) is int and row[field]>=0
    assert row['physics_calls']==row['independent_replays']==0
    assert (tmp_path/'sample_0.json').exists()


def test_mock_bridge_serialized_record_uses_explicit_versions(tmp_path,monkeypatch):
    from experiments.adaptive_execution_v1 import service
    p=history.load_originals(); obj,s=fixture(); s['origin']='OBSERVED_REAL'; s['code_manifest_sha256']=runner.code_check()
    monkeypatch.setattr(bridge,'require_live_session',lambda _:None)
    def mock_service(request,*args,**kw):
        result=copy.deepcopy(p['records'][0]['service']); result['run_id']=result['request_id']=request['id']; return result
    monkeypatch.setattr(service,'run_request',mock_service)
    record=bridge.capture(tmp_path,s,'SERIAL',0,None,reason='MOCK_ONLY')
    assert record==read(tmp_path/'SERIAL_0.json')
    FP.validate_fingerprints(record)


def test_new_source_seal_is_explicit_and_old_seal_is_preserved():
    from experiments.adaptive_execution_real_learning_pilot_v0.common import code_manifest_path,raw_hash
    assert code_manifest_path()!=ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/code_seal.json'
    assert runner.code_check()==raw_hash(code_manifest_path())
    assert history.check_preservation()['original_source_sha256']=='11a4e4495597f0810a39e9c1d665ad69c02f0b2cc4d640e04bdf2256fd9a3309'


def test_old_source_ticket_cannot_authorize_new_live_capture(tmp_path,monkeypatch):
    _,s=fixture(); s['origin']='OBSERVED_REAL'; s['code_manifest_sha256']='11a4e4495597f0810a39e9c1d665ad69c02f0b2cc4d640e04bdf2256fd9a3309'
    monkeypatch.setattr(bridge,'require_live_session',lambda _:None)
    with pytest.raises(ValueError,match='CODE_SEAL'): bridge.capture(tmp_path,s,'SERIAL',0,None)


def test_saved_record_refuses_chain_start_for_fixed_start_request(tmp_path):
    obj,session=fixture(); obj['service']['start_decision']['start']='CHAIN'
    with pytest.raises(ValueError,match='SAVED_INPUT_OR_START'):
        FP.save_and_check(tmp_path/'wrong_start.json',obj,session,writer=write_new)
    assert (tmp_path/'wrong_start.json').exists()
    assert read(tmp_path/'evidence_rejections/wrong_start.json')['reason']=='SAVED_INPUT_OR_START'


@pytest.mark.parametrize('seconds',[0,-1,121,True,'100',None])
def test_retry_budget_cannot_widen_or_remove_limits(seconds):
    from experiments.evidence_canonicalization_v0.offline import gate_seconds
    from experiments.evidence_canonicalization_v0.policy import check_policy
    with pytest.raises(ValueError,match='REMAINING_BUDGET_CANNOT_WIDEN'):
        gate_seconds({'remaining_seconds':seconds},check_policy())


def test_retry_budget_narrows_and_default_preserves_sealed_cap():
    from experiments.evidence_canonicalization_v0.offline import gate_seconds
    from experiments.evidence_canonicalization_v0.policy import check_policy
    assert gate_seconds({'remaining_seconds':100},check_policy())==100
    assert gate_seconds({},check_policy())==120
