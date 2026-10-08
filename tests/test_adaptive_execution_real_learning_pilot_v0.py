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
