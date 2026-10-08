"""Remote-only contract/fault tests. Historical fixture is never real-session evidence."""
import ast
import copy
import json
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from experiments.adaptive_execution_real_learning_pilot_v0 import guardian, inspector, governance, costs, bridge
from experiments.adaptive_execution_real_learning_pilot_v0.common import ROOT, canonical, digest, read, write_new, check_seals
from experiments.adaptive_execution_real_learning_pilot_v0.fixtures import contract_panel


class Clock:
    def __init__(self): self.t = 0
    def now(self): return self.t
    def sleep(self, dt): self.t += dt


class Control:
    def __init__(self, clock, delay=70, fail=False, wrong=False):
        self.clock, self.delay, self.fail, self.wrong = clock, delay, fail, wrong
        self.stops, self.first_stop = 0, None
    def show(self):
        if self.fail: raise OSError("mock network failure")
        exited = self.first_stop is not None and self.clock.t - self.first_stop >= self.delay
        return dict(id=999 if self.wrong else 123, actual_status="exited" if exited else "running",
                    intended_status="stopped" if self.stops else "running", dph_total=0.2)
    def stop(self):
        self.stops += 1
        if self.first_stop is None: self.first_stop = self.clock.t
        return True


@pytest.mark.parametrize("trigger", ["COMPLETED", "FAILED", "DEADLINE"])
def test_guardian_late_actual_exit_confirmed(trigger):
    clock=Clock(); control=Control(clock)
    result=guardian.confirm_stop(control, 123, trigger, confirm_seconds=180, now=clock.now, sleep=clock.sleep)
    assert result["status"] == "STOP_CONFIRMED" and clock.t >= 70
    assert any(x.get("actual_status") == "running" and x.get("intended_status") == "stopped" for x in result["events"])
    assert control.stops <= 3


@pytest.mark.parametrize("fault", ["timeout", "network", "wrong_instance"])
def test_guardian_never_claims_unconfirmed_success(fault):
    clock=Clock(); control=Control(clock, delay=999, fail=fault=="network", wrong=fault=="wrong_instance")
    result=guardian.confirm_stop(control, 123, "FAILED", confirm_seconds=180, now=clock.now, sleep=clock.sleep)
    assert result["status"] != "STOP_CONFIRMED" and result["manual_confirmation_required"]
    assert result["external_warning"] and clock.t <= 180


def test_original_sources_and_replay_boundary():
    check_seals()
    tree=ast.parse(Path(inspector.__file__).read_text(encoding="utf-8"))
    names=[node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(any(name.endswith(x) for x in ("bridge", "governance", "service", "selector", "adapters")) for name in names)


def test_fixture_validates_only_as_contract():
    records, session, replays=contract_panel()
    report=inspector.validate_panel(records, session, replays, contract_only=True)
    assert report["verdict"] == "CONTRACT_VALIDATED"
    assert report["real_cost_evidence"] is False
    with pytest.raises(ValueError, match="REAL_ORIGIN_REQUIRED"):
        inspector.validate_panel(records, session, replays)


@pytest.mark.parametrize("fault", ["session", "synthetic", "precision", "placement", "GPU_N14", "result", "failed_cpu", "initial", "source", "repeat", "clock", "replay_origin"])
def test_bad_real_evidence_contract_refused(fault):
    records, session, replays=contract_panel()
    obj=records[-1]; service=obj["service"]; pz=service["passes"][0]; result=pz["attempts"][0]["result"]
    if fault=="session": obj["session_id"]="other"
    elif fault=="synthetic": obj["kind"]="SYNTHETIC_TEST_ONLY"
    elif fault=="precision": result["effective_p"]=162
    elif fault=="placement": pz["attempts"][0]["plan"]["worker_cpus"]=[999]*6
    elif fault=="GPU_N14": pz["attempts"][0]["plan"]["backend"]="GPU_HYBRID"
    elif fault=="result": result["cells"]=["wrong"]
    elif fault=="failed_cpu":
        extra=copy.deepcopy(pz["attempts"][0]); extra["result"]["cpu_s"]=1; extra["result"]["outcome"]="UNDECIDED_AT_PRECISION"
        pz["attempts"].insert(0,extra)
    elif fault=="initial": obj["initial_state"]["q"][0][0]="999"
    elif fault=="source": obj["code_manifest_sha256"]="0"*64
    elif fault=="repeat": records.pop()
    elif fault=="clock": obj["observation"]["wall_ns"]=1
    else: replays["14/1000/163"]["origin"]="SYNTHETIC_TEST_ONLY"
    with pytest.raises(ValueError): inspector.validate_panel(records, session, replays, contract_only=True)


def test_signed_contract_profile_next_request_and_rollback(tmp_path):
    judge, ruler=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    records, session, replays=contract_panel()
    report=inspector.validate_panel(records,session,replays,contract_only=True)
    roots=governance.Roots.for_contract(judge.public_key(),ruler.public_key())
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'controller_witness',roots,ruler)
    before=mgr.begin("WALL_MIN",session)
    receipt={"body":report,"signature":judge.sign(b"REAL_PILOT_RECEIPT\0"+canonical(report)).hex()}
    profile=mgr.admit(receipt)
    body=mgr.approval_body(profile["id"],"WALL_MIN","a","contract test explicit approval")
    mgr.activate({"body":body,"signature":ruler.sign(b"REAL_PILOT_APPROVAL\0"+canonical(body)).hex()})
    assert mgr.choose(mgr.begin("WALL_MIN",session),session)=="W6"
    assert mgr.choose(before,session)=="LEGACY"
    other=dict(session,session_id="other")
    assert mgr.choose(mgr.begin("WALL_MIN",other),other)=="LEGACY"
    body=mgr.approval_body("LEGACY","WALL_MIN","back","rollback")
    mgr.rollback({"body":body,"signature":ruler.sign(b"REAL_PILOT_APPROVAL\0"+canonical(body)).hex()})
    assert mgr.choose(mgr.begin("WALL_MIN",session),session)=="LEGACY"
    with pytest.raises(ValueError): bridge.require_live_session(session)


@pytest.mark.parametrize("fault", ["unsigned", "wrong_key", "goal", "root", "tail", "failed_rollback", "snapshot"])
def test_authority_and_journal_faults_stop(tmp_path,fault):
    judge,ruler=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    records,session,replays=contract_panel(); report=inspector.validate_panel(records,session,replays,contract_only=True)
    roots=governance.Roots.for_contract(judge.public_key(),ruler.public_key())
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'witness',roots,ruler)
    receipt={"body":report,"signature":judge.sign(b"REAL_PILOT_RECEIPT\0"+canonical(report)).hex()}
    if fault=='unsigned':
        receipt['signature']=''
        with pytest.raises(ValueError): mgr.admit(receipt)
        return
    profile=mgr.admit(receipt)
    body=mgr.approval_body(profile['id'],'WALL_MIN','first','test')
    key=judge if fault=='wrong_key' else ruler
    if fault=='goal': body['goal']='CPU_MIN'
    approval={'body':body,'signature':key.sign(b'REAL_PILOT_APPROVAL\0'+canonical(body)).hex()}
    if fault in ('wrong_key','goal'):
        with pytest.raises(ValueError): mgr.activate(approval)
        return
    mgr.activate(approval)
    if fault=='root': (mgr.directory/'roots.json').write_bytes(canonical({'forged':True}))
    elif fault=='tail':
        # Truncation simulation retains removed bytes; no source deletion.
        path=sorted(mgr.events.directory.glob('event_*.json'))[-1]
        path.rename(path.with_suffix('.truncated_evidence'))
    elif fault=='failed_rollback':
        body=mgr.approval_body('missing','WALL_MIN','back','bad rollback')
        with pytest.raises(ValueError): mgr.rollback({'body':body,'signature':ruler.sign(b'REAL_PILOT_APPROVAL\0'+canonical(body)).hex()})
    else:
        from dataclasses import replace
        snap=mgr.begin('WALL_MIN',session)
        obj=json.loads(snap.profile_bytes); obj['rows'][0]['cpu_ns']=1
        with pytest.raises(ValueError): mgr.choose(replace(snap,profile_bytes=canonical(obj)),session)
        return
    with pytest.raises(ValueError): mgr.begin('WALL_MIN',session)


def test_learning_cost_not_recovered_after_one_reuse():
    out=costs.recovery(overhead_ns=1000,baseline_ns=100,learned_ns=20,observed_reuses=1)
    assert out['break_even_reuses']==13
    assert out['realized_net_ns']==-920 and out['cost_status']=='COST_NOT_YET_RECOVERED'
    assert out['future_net_profit']=='UNCONFIRMED'
    assert costs.recovery(overhead_ns=10,baseline_ns=100,learned_ns=20,observed_reuses=1)['cost_status']=='RECOVERED_FOR_OBSERVED_REUSES'


def test_pilot_requires_stage_and_machine_authorization():
    from experiments.adaptive_execution_real_learning_pilot_v0.runner import authorize
    with pytest.raises(ValueError): authorize({},'A','code',instance_id='123',platform_name='Linux')
    ticket=dict(gate='ADAPTIVE_EXECUTION_REAL_LEARNING_PILOT_V0',scope='REAL_RESEARCH',explicit_user_approval=True,
                approval_reference='test',instance_id='123',machine_id=1234,country='US',stages=['A'],code_seal_sha256='code',hourly_usd='0.2')
    assert authorize(ticket,'A','code',instance_id='123',platform_name='Linux')['machine_id']==1234
    with pytest.raises(ValueError): authorize(ticket,'B','code',instance_id='123',platform_name='Linux')
    with pytest.raises(ValueError): authorize(ticket,'A','code',instance_id='123',platform_name='Windows')


def test_information_gap_does_not_relabel_correct_slow_choice():
    from experiments.adaptive_execution_real_learning_pilot_v0.knowledge import gaps,value
    _,session,_=contract_panel()
    gap=gaps(session,['SERIAL'])
    assert gap['unknown']==['W6'] and gap['judgment']=='CORRECT_LEGACY_CHOICE_IS_NOT_AN_ERROR'
    assert value(saving_ns=10)['decision']=='DEFER_INFORMATION_NEEDED'
    proposal=value(saving_ns=100,confirmed_reuses=5,measurement_ns=200,verification_ns=100,accuracy_in_scope=True,available_ns=1000)
    assert proposal['decision']=='PROPOSE_EXPERIMENT' and not proposal['execution_authorized']


def test_cpu_min_historical_contract_is_separate_goal(tmp_path):
    records,session,replays=contract_panel(N=12,goal='CPU_MIN')
    report=inspector.validate_panel(records,session,replays,contract_only=True)
    judge,ruler=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    roots=governance.Roots.for_contract(judge.public_key(),ruler.public_key())
    mgr=governance.Manager(tmp_path/'manager',tmp_path/'witness',roots,ruler)
    profile=mgr.admit({'body':report,'signature':judge.sign(b'REAL_PILOT_RECEIPT\0'+canonical(report)).hex()})
    body=mgr.approval_body(profile['id'],'CPU_MIN','cpu','historical contract only')
    mgr.activate({'body':body,'signature':ruler.sign(b'REAL_PILOT_APPROVAL\0'+canonical(body)).hex()})
    assert mgr.choose(mgr.begin('CPU_MIN',session),session)=='GPU'
    assert mgr.choose(mgr.begin('WALL_MIN',session),session)=='LEGACY'
    assert report['real_cost_evidence'] is False


@pytest.mark.parametrize('fault',['attempt_cost','service_cost','negative_clock','initial_digest'])
def test_secondary_evidence_integrity(fault):
    records,session,replays=contract_panel(); obj=records[-1]; s=obj['service']
    if fault=='attempt_cost': s['passes'][0]['attempts'][0]['result']['cpu_s']=None
    elif fault=='service_cost': s['service_cpu_s']=1
    elif fault=='negative_clock': obj['observation']['cpu_ns']=-1
    else: s['start_decision']['initial_state_digest']='0'*64
    with pytest.raises(ValueError): inspector.validate_panel(records,session,replays,contract_only=True)


def test_actual_controller_has_no_inspector_private_key_or_arbitrary_sign_api():
    from experiments.adaptive_execution_real_learning_pilot_v0 import runner
    source=Path(runner.__file__).read_text(encoding='utf-8')
    assert 'self.judge' not in source and 'private_bytes' not in source
    assert "'INSPECT'" in source and "'CHECK_NEXT'" in source
    checker=Path(inspector.__file__).read_text(encoding='utf-8')
    assert 'key=Ed25519PrivateKey.generate()' in checker
    assert 'from_private_bytes' not in checker


def test_completion_bridge_mock_only_candidate_is_not_real_evidence(tmp_path,monkeypatch):
    from experiments.adaptive_execution_v1 import service
    from experiments.adaptive_execution_real_learning_pilot_v0.common import raw_hash,HERE,ns,code_manifest_path
    from experiments.evidence_canonicalization_v0.fingerprints import CONTENT_VERSION,policy_hash
    records,oldsession,replays=contract_panel(); original=copy.deepcopy(records[-1]['service'])
    original['run_id']=original['request_id']=oldsession['session_id']+'/W6/0'
    # This mock answers capture's FIXED_START request, not the historical CHAIN request.
    original['start_decision']['start']='FIXED_START:163'
    session=dict(oldsession,origin='OBSERVED_REAL',test_only=True,boot_id='MOCK_BOOT',
                 code_manifest_sha256=raw_hash(code_manifest_path()),evidence_version=2,
                 initial_content_version=CONTENT_VERSION,evidence_policy_sha256=policy_hash())
    with pytest.raises(ValueError): bridge.require_live_session(session)
    # Test explicitly bypasses ONLY execution authorization; no calculator runs, no receipts are signed.
    monkeypatch.setattr(bridge,'require_live_session',lambda _:None)
    monkeypatch.setattr(service,'run_request',lambda *args,**kwargs:copy.deepcopy(original))
    clocks=iter([{'controller':0,'waited_children':0,'live_gpu':0},
                 {'controller':1,'waited_children':ns(original['service_cpu_s']),'live_gpu':0}])
    monkeypatch.setattr(bridge,'cpu_clock',lambda gpu=None:next(clocks))
    record=bridge.capture(tmp_path,session,'W6',0,None,reason='MOCK_TEST_ONLY; NOT_NEW_EXPERIENCE')
    assert record['state']=='CANDIDATE' and (tmp_path/'W6_0.json').exists()
    assert record['service']==original and record['initial_state']==records[-1]['initial_state']
    with pytest.raises(ValueError,match='TEST_ONLY_SESSION_REFUSED'):
        inspector.validate_record(record,session,replays)


def approved_offline_lease():
    from experiments.adaptive_execution_real_learning_pilot_v0.common import HERE,raw_hash
    return dict(experiment_scope='OFFLINE_ONLY',instance_id=52763685,machine_id=3448,country='NO',
                deadline_seconds=240,hourly_cap_usd='0.28',budget_amendment_sha256=raw_hash(HERE/'offline_budget_amendment_52763685.json'))


def test_guardian_default_price_limit_remains_sealed():
    assert guardian.hourly_cap({})==0.25


def test_guardian_user_approved_offline_exception_only():
    assert guardian.hourly_cap(approved_offline_lease())==0.28


@pytest.mark.parametrize('fault',['instance','scope','hash','cap','deadline'])
def test_guardian_budget_exception_refuses_widening(fault):
    auth=approved_offline_lease()
    if fault=='instance': auth['instance_id']=54645489
    elif fault=='scope': auth['experiment_scope']='REAL_RESEARCH'
    elif fault=='hash': auth['budget_amendment_sha256']='0'*64
    elif fault=='cap': auth['hourly_cap_usd']='0.29'
    else: auth['deadline_seconds']=3240
    with pytest.raises(ValueError): guardian.hourly_cap(auth)


def a_armed():
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    return dict(status='ARMED',outside_guest=True,instance_id=123,machine_id=56006,country='FR',
                armed_utc='2026-10-08T00:00:00+00:00',allocation_start_utc='2026-10-08T00:00:00+00:00',
                safety_policy_sha256=a_safety.policy_hash(),deadline_seconds=3420)


def test_a_absolute_budget_has_three_separate_deadlines():
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    assert a_safety.remaining(a_armed(),now_utc='2026-10-08T00:10:00+00:00')==dict(compute=2640,handoff=2820,allocation=3000)


@pytest.mark.parametrize('fault',['policy','future_start','deadline','expired'])
def test_a_budget_refuses_invalid_origin_or_extension(fault):
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    armed=a_armed(); now='2026-10-08T00:10:00+00:00'
    if fault=='policy': armed['safety_policy_sha256']='0'*64
    elif fault=='future_start': armed['allocation_start_utc']='2026-10-09T00:00:00+00:00'
    elif fault=='deadline': armed['deadline_seconds']=3600
    else: now='2026-10-08T01:00:00+00:00'
    with pytest.raises(ValueError): a_safety.remaining(armed,now_utc=now)


def a_heartbeat(armed):
    from experiments.adaptive_execution_real_learning_pilot_v0.common import digest
    return dict(status='CONTROL_OK',instance_id=123,machine_id=56006,country='FR',armed_digest=digest(armed),
                sequence=2,observed_utc='2026-10-08T00:10:00+00:00',control_checked_utc='2026-10-08T00:09:50+00:00')


def test_a_heartbeat_validates_current_outside_control():
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    armed=a_armed()
    assert a_safety.validate_heartbeat(a_heartbeat(armed),armed,now_utc='2026-10-08T00:10:05+00:00',minimum_sequence=1)==2


@pytest.mark.parametrize('fault',['status','instance','machine','armed','stale','future','sequence','control_stale'])
def test_a_heartbeat_faults_stop_before_new_compute(fault):
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    armed=a_armed(); pulse=a_heartbeat(armed)
    if fault=='status': pulse['status']='CONTROL_LOST'
    elif fault=='instance': pulse['instance_id']=999
    elif fault=='machine': pulse['machine_id']=999
    elif fault=='armed': pulse['armed_digest']='0'*64
    elif fault=='stale': pulse['observed_utc']='2026-10-08T00:08:00+00:00'
    elif fault=='future': pulse['observed_utc']='2026-10-08T00:11:00+00:00'
    elif fault=='sequence': pulse['sequence']=0
    else: pulse['control_checked_utc']='2026-10-08T00:08:00+00:00'
    with pytest.raises(ValueError): a_safety.validate_heartbeat(pulse,armed,now_utc='2026-10-08T00:10:05+00:00',minimum_sequence=1)


def test_a_whole_allocation_cost_never_claims_runner_only_recovery():
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    result=a_safety.allocation_cost(1000,100,20,'0.2',start_known=True)
    assert result['cost']['break_even_reuses']==11 and result['cost']['cost_status']=='COST_NOT_YET_RECOVERED'
    assert result['billing']=='UNCONFIRMED' and result['CPU_MIN']=='OUTSIDE_A_SCOPE'
    assert a_safety.allocation_cost(1000,100,20,'0.2',start_known=False)['cost']['cost_status']=='UNKNOWN_ALLOCATION_START'


@pytest.mark.parametrize('fault',['negative','missing_time','price','interval'])
def test_a_allocation_accounting_rejects_invalid_cost(fault):
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    total,baseline,learned,price=1000,100,20,'0.2'
    if fault=='negative': total=-1
    elif fault=='missing_time': total=None
    elif fault=='price': price='NaN'
    else: total=10
    with pytest.raises(ValueError): a_safety.allocation_cost(total,baseline,learned,price,start_known=True)


def test_a_preparatory_offline_ticket_cannot_authorize_physics():
    from experiments.adaptive_execution_real_learning_pilot_v0 import a_safety
    ticket=dict(scope='OFFLINE_ONLY',instance_id=123,machine_id=56006,country='FR',explicit_user_approval=True,
                safety_policy_sha256=a_safety.policy_hash(),hourly_cap_usd='0.25',physics_calls=0,gpu_calls=0)
    assert a_safety.offline_lease(ticket,a_armed())
    ticket['physics_calls']=1
    with pytest.raises(ValueError): a_safety.offline_lease(ticket,a_armed())
