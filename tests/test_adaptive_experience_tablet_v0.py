"""Remote-only contract faults. No calculator, GPU, paid execution or authority creation.

Mutation targets: granting another session authority, trusting index metadata, allowing
SMT/unknown/quota-invalid placement, forgetting recorded placement or cost uncertainty.
Real historical signatures and records are used; altered copies stay in tmp_path.
"""
import copy
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from experiments.adaptive_execution_real_learning_pilot_v0 import governance
from experiments.adaptive_execution_real_learning_pilot_v0.common import canonical, digest, public, read, write_new
from experiments.adaptive_execution_v1 import environment as ENV
from experiments.adaptive_experience_tablet_v0 import catalog, host, routes, policy, offline

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / 'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/run_20261008_approved_3/recovered/output_actual'
PROFILE = 'b775509603dc3f07e578ccce4aea11021cee013c7eea8feb8268f01a8e91482f'


def environment(cores=6, cpus=None):
    env = copy.deepcopy(read(ORIGINAL / 'A/session.json')['env'])
    cpus = list(range(cores)) if cpus is None else cpus
    env.update(allowed_cpus=cpus, core_of_cpu={str(c): f'0:{i}' for i,c in enumerate(cpus)},
               physical_cores=cores, logical_cpus=len(cpus), cpu_quota=None, gpu=None)
    env['env_id'] = ENV.env_id(env)
    return env


def request(env=None):
    env = environment() if env is None else env
    return dict(N=14,T=1000,start_p=163,actual_p=163,goal='WALL_MIN',
                physics=env['contracts']['physics'],numeric=env['contracts']['numeric'],
                source_sha256=read(ORIGINAL/'A/session.json')['code_manifest_sha256'])


def qualified(env):
    return host.describe(env, quota_observation='OBSERVED_UNLIMITED' if env['cpu_quota'] is None else 'OBSERVED_FINITE',
                         core_classes='HOMOGENEOUS', provenance='OFFLINE_LITERAL_FIXTURE')


@pytest.fixture
def archive(tmp_path):
    target=tmp_path/'originals'; shutil.copytree(ORIGINAL,target)
    roots=governance.Roots(**read(target/'manager/roots.json'))
    tablet=catalog.Tablet(tmp_path/'tablet',target,roots)
    entry=tablet.register('A',PROFILE,'manager/events/event_000000.json')
    return tablet,target,roots,entry


@pytest.mark.parametrize('cores,want',[(1,['SERIAL']),(2,['SERIAL']),(4,['SERIAL','W3']),
                                    (5,['SERIAL','W3','W4']),(6,['SERIAL','W3','W4','W6'])])
def test_route_candidates_obey_physical_core_needs(cores,want):
    assert list(routes.candidates(request(),qualified(environment(cores)))) == want


def test_smt_siblings_do_not_supply_six_physical_cores():
    env=environment(6); env['core_of_cpu']['5']='0:0'; env['env_id']=ENV.env_id(env)
    assert list(routes.candidates(request(),qualified(env))) == ['SERIAL','W3','W4']


def test_noncontiguous_affinity_and_w6_main_sharing_are_preserved():
    plans=routes.candidates(request(),qualified(environment(6,[2,7,11,19,23,31])))
    plan=plans['W6']; assert plan.main_cpu==2 and plan.worker_cpus==(7,11,19,23,31,2)
    assert plan.execution_plan().shares_main_core()


@pytest.mark.parametrize('quota,want',[(0.5,[]),(3.9,['SERIAL']),(4,['SERIAL','W3']),
                                     (5,['SERIAL','W3','W4']),(6,['SERIAL','W3','W4','W6'])])
def test_quota_is_not_rounded_up(quota,want):
    env=environment(); env['cpu_quota']=quota; env['env_id']=ENV.env_id(env)
    assert list(routes.candidates(request(),qualified(env)))==want


def test_changed_affinity_invalidates_previous_plan():
    env=environment(); plan=routes.candidates(request(),qualified(env))['W6']
    env['allowed_cpus']=[0,1,2,3,4]; env['env_id']=ENV.env_id(env)
    with pytest.raises(ValueError): routes.recheck(plan,request(),qualified(env))


@pytest.mark.parametrize('fault',['missing_core','unknown_quota','hybrid','other_os','forged_env','missing_attestation'])
def test_unqualified_host_refuses_optimistic_routes(fault):
    env=environment(); info=qualified(env)
    if fault=='missing_core':
        env['core_of_cpu']['5']=None; env['env_id']=ENV.env_id(env); info=qualified(env)
    elif fault=='unknown_quota': info=host.describe(env,core_classes='HOMOGENEOUS',provenance='fixture')
    elif fault=='hybrid': info=host.describe(env,quota_observation='OBSERVED_UNLIMITED',core_classes='HETEROGENEOUS',provenance='fixture')
    elif fault=='other_os':
        env['platform']='win32'; env['env_id']=ENV.env_id(env); info=qualified(env)
    elif fault=='forged_env': info['env']['allowed_cpus']=[99]
    else: info=host.describe(env)
    with pytest.raises(ValueError): routes.candidates(request(),info)


def test_actual_recorded_placement_mismatch_is_refused():
    plan=routes.candidates(request(),qualified(environment()))['W6']
    runner=dict(plan=json.loads(plan.execution_plan().to_json()),main_affinity=[0],worker_affinity=[[i] for i in (1,2,3,4,5,0)])
    routes.check_recorded(plan,runner)
    runner['worker_affinity'][0]=[2]
    with pytest.raises(ValueError): routes.check_recorded(plan,runner)


def test_unknown_hardware_details_stay_unknown_without_changing_env_id():
    env=environment(); before=copy.deepcopy(env); info=qualified(env)
    assert info['cache']=='UNKNOWN' and info['numa']=='UNKNOWN' and info['isa']=='UNKNOWN'
    assert env==before and info['env']['env_id']==before['env_id']


def test_signed_original_is_searchable_but_foreign_session_is_hint(archive):
    tablet,root,_,entry=archive; hits=tablet.search(request())
    assert len(hits)==1 and hits[0]['profile_id']==PROFILE
    experience=tablet.load(hits[0]); session=read(root/'A/session.json'); session['session_id']='new-session'
    state=policy.classify(experience,request(),qualified(session['env']),session)
    assert state=='TRANSFER_HINT_ONLY'
    assert entry['repeats']=={'SERIAL':5,'W6':5}


@pytest.mark.parametrize('fault',['raw','receipt_signature','approval_signature','profile','session','wrong_root'])
def test_corrupt_evidence_cannot_become_a_trusted_hit(archive,fault):
    tablet,root,roots,entry=archive
    if fault=='raw':
        path=root/'A/measurement/SERIAL_0.json'; bad=read(path); bad['service']['final_p']=162
    elif fault=='receipt_signature':
        path=root/'manager/profiles'/f'{PROFILE}.json'; bad=read(path); bad['receipt']['signature']='00'*64
    elif fault=='approval_signature':
        path=root/'manager/events/event_000000.json'; bad=read(path); bad['payload']['signature']='00'*64
    elif fault=='profile':
        path=root/'manager/profiles'/f'{PROFILE}.json'; bad=read(path); bad['rows'][1]['wall_ns']=1
    elif fault=='session':
        path=root/'A/session.json'; bad=read(path); bad['session_id']='forged'
    else:
        key=Ed25519PrivateKey.generate(); tablet=catalog.Tablet(tablet.directory,root,replace(roots,inspector=public(key.public_key())))
        with pytest.raises(ValueError): tablet.load(entry)
        return
    path.write_bytes(canonical(bad))
    with pytest.raises(ValueError): tablet.load(entry)
    assert read(path)==bad


@pytest.mark.parametrize('change',['same_env_new_session','same_model_new_env','no_snapshot'])
def test_same_cpu_or_env_never_automatically_grants_current_authority(archive,change):
    tablet,root,_,entry=archive; exp=tablet.load(entry); session=read(root/'A/session.json')
    if change=='same_env_new_session': session['session_id']='different'
    elif change=='same_model_new_env':
        session['env']['allowed_cpus']=list(range(6)); session['env']['env_id']=ENV.env_id(session['env'])
    assert policy.classify(exp,request(),qualified(session['env']),session) in ('TRANSFER_HINT_ONLY','NEEDS_CALIBRATION')


@pytest.mark.parametrize('field,value',[('goal','CPU_MIN'),('start_p',164),('actual_p',164),
                                      ('physics','different'),('numeric','different'),('source_sha256','different'),('T',100)])
def test_problem_contract_and_goal_mixing_are_refused(archive,field,value):
    tablet,root,_,entry=archive; req=request(); req[field]=value
    assert not tablet.search(req)
    assert policy.classify(tablet.load(entry),req,qualified(environment()),read(root/'A/session.json'))=='REFUSED'


def test_unavailable_w6_is_incompatible(archive):
    tablet,root,_,entry=archive
    assert policy.classify(tablet.load(entry),request(),qualified(environment(4)),read(root/'A/session.json'),method='W6')=='INCOMPATIBLE'


def test_gpu_experience_cannot_be_applied_to_cpu(archive):
    tablet,root,_,entry=archive
    assert policy.classify(tablet.load(entry),request(),qualified(environment()),read(root/'A/session.json'),method='GPU')=='INCOMPATIBLE'


def test_duplicate_experience_does_not_inflate_count(archive):
    tablet,_,_,entry=archive
    tablet.register('A',PROFILE,'manager/events/event_000000.json')
    assert len(tablet.search(request()))==1
    assert tablet.search(request())[0]['repeats']=={'SERIAL':5,'W6':5}


def test_corrupt_index_stops_and_explicit_rebuild_preserves_originals(archive):
    tablet,root,roots,_=archive; original=(root/'A/session.json').read_bytes()
    index=tablet.index_path; bad=read(index); bad['entries'][0]['key']['N']=99; index.write_bytes(canonical(bad))
    with pytest.raises(ValueError): catalog.Tablet(tablet.directory,root,roots)
    catalog.Tablet.rebuild(tablet.directory,root,roots)
    restored=catalog.Tablet(tablet.directory,root,roots)
    assert len(restored.search(request()))==1 and (root/'A/session.json').read_bytes()==original


def test_bad_reference_is_preserved_and_rebuild_never_approves_it(archive):
    tablet,root,roots,entry=archive; ref=tablet.directory/'references'/f"{entry['reference_id']}.json"
    original=ref.read_bytes(); ref.write_bytes(b'corrupt')
    result=catalog.Tablet.rebuild(tablet.directory,root,roots)
    assert result['refused'] and ref.read_bytes()==b'corrupt'
    assert catalog.Tablet(tablet.directory,root,roots).search(request())==[]
    assert original!=ref.read_bytes()


def test_supplied_index_metadata_is_not_authority(archive):
    tablet,_,_,entry=archive; bad=copy.deepcopy(entry); bad['key']['actual_p']=64
    with pytest.raises(ValueError): tablet.load(bad)


def test_search_result_mutation_does_not_change_live_index(archive):
    tablet,_,_,_=archive; hits=tablet.search(request()); hits[0]['key']['N']=99
    assert tablet.search(request())[0]['key']['N']==14


def test_only_selected_reference_files_are_opened(archive,monkeypatch):
    tablet,_,_,_=archive; original=Path.read_bytes; accessed=[]
    def capture(path): accessed.append(path); return original(path)
    monkeypatch.setattr(Path,'read_bytes',capture)
    hits=tablet.search(request())
    assert len(hits)==1 and accessed==[]


def test_rollback_and_old_snapshot_remain_existing_manager_semantics(tmp_path):
    judge,ruler=Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()
    roots=governance.Roots.for_contract(judge.public_key(),ruler.public_key())
    manager=governance.Manager(tmp_path/'manager',tmp_path/'witness',roots,ruler)
    session=read(ORIGINAL/'A/session.json'); session['origin']='OFFLINE_CONTRACT_ONLY'
    old=manager.begin('WALL_MIN',session)
    from experiments.adaptive_execution_real_learning_pilot_v0.common import HERE, raw_hash
    body=dict(verdict='CONTRACT_VALIDATED',errors=[],formula_independence='UNRESOLVED_SHARED_RWFORCE',
              real_cost_evidence=False,goal='WALL_MIN',protocol_sha256=raw_hash(HERE/'protocol.json'),
              session_sha256=digest(session),rows=[dict(method='SERIAL',wall_ns=100,cpu_ns=100),dict(method='W6',wall_ns=20,cpu_ns=110)])
    profile=manager.admit(dict(body=body,signature=judge.sign(b'REAL_PILOT_RECEIPT\0'+canonical(body)).hex()))
    approval=manager.approval_body(profile['id'],'WALL_MIN','activate','fixture')
    manager.activate(dict(body=approval,signature=ruler.sign(b'REAL_PILOT_APPROVAL\0'+canonical(approval)).hex()))
    snapshot=manager.begin('WALL_MIN',session)
    assert manager.choose(old,session)=='LEGACY' and manager.choose(snapshot,session)=='W6'
    approval=manager.approval_body('LEGACY','WALL_MIN','rollback','fixture')
    manager.rollback(dict(body=approval,signature=ruler.sign(b'REAL_PILOT_APPROVAL\0'+canonical(approval)).hex()))
    assert manager.choose(manager.begin('WALL_MIN',session),session)=='LEGACY'
    assert manager.choose(snapshot,session)=='W6'


def test_tablet_does_not_activate_or_select_w6_without_current_snapshot(archive):
    tablet,root,_,entry=archive; exp=tablet.load(entry); session=read(root/'A/session.json')
    plans=routes.candidates(request(),qualified(session['env']))
    assert policy.safe_method('CPU_MIN',plans)=='SERIAL'
    assert policy.safe_method('WALL_MIN',plans,experience=exp,request=request(),host_info=qualified(session['env']),session=session)=='SERIAL'


@pytest.mark.parametrize('fault',['unknown_reuses','unknown_risk','unverified_baseline','budget_short'])
def test_learning_information_or_budget_gap_never_executes(fault):
    args=dict(baseline_ns=100,candidate_upper_ns=20,reuses=10,measurement_ns=100,verification_ns=100,
              available_ns=500,rental_upper_usd='0.01',budget_usd='0.02',risk_bounded=True,baseline_verified=True)
    if fault=='unknown_reuses': args['reuses']=None
    elif fault=='unknown_risk': args['risk_bounded']=None
    elif fault=='unverified_baseline': args['baseline_verified']=False
    else: args['budget_usd']='0.001'
    result=policy.study_value(**args)
    assert result['decision'].startswith('DEFER_') and result['execution_authorized'] is False


def test_positive_learning_value_is_only_a_proposal():
    result=policy.study_value(baseline_ns=100,candidate_upper_ns=20,reuses=10,measurement_ns=100,
          verification_ns=100,available_ns=500,rental_upper_usd='0.01',budget_usd='0.02',risk_bounded=True,baseline_verified=True)
    assert result['decision']=='PROPOSE_EXPERIMENT' and result['execution_authorized'] is False


def test_no_evidence_means_calibration_needed():
    assert policy.classify(None,request(),qualified(environment()),{})=='NEEDS_CALIBRATION'


@pytest.mark.parametrize('fault',['skipped','failed','error','wrong_count','wrong_code','physics','missing_benchmark'])
def test_offline_status_cannot_claim_validation_without_all_gates(fault):
    status=dict(status='PASS',tests=99,failed=0,errors=0,skipped=0,physics_calls=0,gpu_calls=0,
                code_sha256='sealed',protocol_sha256=offline.protocol_hash(),benchmark_complete=True)
    if fault in ('skipped','failed'): status[fault]=1
    elif fault=='error': status['errors']=1
    elif fault=='wrong_count': status['tests']=98
    elif fault=='wrong_code': status['code_sha256']='old'
    elif fault=='physics': status['physics_calls']=1
    else: status['benchmark_complete']=False
    with pytest.raises(ValueError): offline.validate_status(status,'sealed',99)
