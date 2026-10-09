"""TEST_ONLY new binding/adoption tests; no authority or paid I/O."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
import pytest
from budget import Ledger
from lifecycle import verify_admin
import campaign
import test_transport_paths as scaffold


@pytest.mark.parametrize('scenario,success',[('normal',True),('supervisor_not_ready',False),('container_mismatch',False),('gate_failure',False),('recovery_corrupt',False)])
def test_actual_delegated_running_transport_no_restart(tmp_path,scenario,success):
    m=scaffold.configured();clock=scaffold.Clock();out=tmp_path/'transport';out.mkdir()
    a=scaffold.auth();a.update(schema='PROJECT_VAST_DELEGATED_INSTANCE_BINDING_V1',scope='OFFLINE_ONLY',
        allocation_mode='ADOPT_RUNNING',exclusive=True,explicit_user_approval=True)
    b=scaffold.Backend(m,out,scenario,clock);b.state='running';original=b.api
    def api(phase):
        if phase=='initial_instance':return scaffold.raw('running')
        return original(phase)
    b.api=api
    with patch.object(m,'subprocess',b.shim()),patch.object(m,'time',clock),patch.object(m,'datetime',clock.datetime_type()),patch.object(m,'guardian_alive',lambda pid:True),patch.object(m,'local_preflight',return_value=['TEST_ONLY_EXTERNAL_AUTHORITY_BOUNDARY']),patch('execution_authority.begin_transport',return_value=None):
        t=m.Transport(a,'mock_vast','mock_key',out);result=t.execute()
    assert (result==0)==success
    assert b.starts==0
    assert b.gates<=1
    assert not any('destroy' in c['argv'] for c in b.commands)


def fixture(tmp_path):
    m=scaffold.configured();base=tmp_path/'binding_version';(base/'transport').mkdir(parents=True)
    for name in ('authorization_request.txt','budget.py','transport/controller.py','transport/package_bindings.json'):
        dest=base/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(campaign.BASE/name,dest)
    policy=campaign.read(campaign.BASE/'policy.json');policy['ledger_path']=str(base/'ledger.jsonl');policy.update(_paid_approval_path='TEST_ONLY_FAKE_BOUNDARY',_paid_approval_sha256='TEST_ONLY')
    campaign.save(base/'policy.json',policy)
    files={name:campaign.sha(base/name) for name in ('authorization_request.txt','budget.py','policy.json','transport/controller.py','transport/package_bindings.json')}
    campaign.save(base/'operational_seal.json',dict(files=files,role='TEST_ONLY_FIXTURE_NOT_EXECUTION_AUTHORITY'))
    ledger=Ledger(base/'ledger.jsonl');ledger.append(dict(action='INIT',cap='1',historical_bound='.364'))
    ledger.append(dict(action='RESERVE',token='TEST_ONLY_RESERVATION',amount='.05'))
    stage=tmp_path/'stage';stage.mkdir();(stage/'known_hosts').write_bytes(b'TEST_ONLY_HOST_KEY_NOT_REMOTE')
    campaign.save(stage/'watchdog_ready.json',dict(pid=12345))
    old=scaffold.auth()
    owner=dict(instance_id=old['instance_id'],machine_id=old['machine_id'],country=old['country'],run_id='test_only_delegated_binding',
        api_ssh_host=old['api_ssh_host'],api_ssh_port=old['api_ssh_port'],public_ipaddr=old['ssh_host'],direct_ssh_port=old['ssh_port'],
        reservation_token='TEST_ONLY_RESERVATION',observed_rate_usd='.1',authorization_raw_sha256=policy['authorization_raw_sha256'])
    campaign.save(stage/'owner.json',owner)
    with patch.object(campaign,'BASE',base):binding=campaign.transport_binding(policy,'B',owner,stage,None)
    import execution_authority
    actual=m.local_preflight
    def with_mock_paid_authority(value):
        # New paid guard has its own negative tests; legacy fixtures exercise their existing boundaries.
        with patch.object(execution_authority,'require_claim',return_value={'role':'TEST_ONLY_NO_PAID_IO'}):return actual(value)
    m.local_preflight=with_mock_paid_authority
    m.HERE=base/'transport'
    return m,base,stage,ledger,binding


def test_actual_new_delegation_preflight_with_real_package_hashes(tmp_path):
    m,base,stage,l,binding=fixture(tmp_path)
    checks=m.local_preflight(binding)
    assert checks[-1]['entries']==10


@pytest.mark.parametrize('field,value',[('explicit_user_approval',False),('authorization_raw_sha256','0'*64),
    ('scope','PHYSICS'),('transport_ssh_host','WRONG_HOST'),('machine_id',999),('allocation_seconds',601)])
def test_new_delegation_mutation_refused_before_io(tmp_path,field,value):
    m,base,stage,l,binding=fixture(tmp_path);binding[field]=value
    with patch.object(m.subprocess,'run',side_effect=AssertionError('NO_IO_BEFORE_VALID_AUTH')):
        with pytest.raises(ValueError):m.local_preflight(binding)


def test_new_delegation_requires_still_reserved_cost(tmp_path):
    m,base,stage,l,binding=fixture(tmp_path)
    l.append(dict(action='SETTLE',token='TEST_ONLY_RESERVATION',observed_cost_bound='.05',destroy_confirmed=True))
    with pytest.raises(ValueError):m.local_preflight(binding)


def test_declared_B_pass_without_mandatory_raw_refuses_A(tmp_path):
    m,base,stage,l,binding=fixture(tmp_path)
    l.append(dict(action='SETTLE',token='TEST_ONLY_RESERVATION',observed_cost_bound='.05',destroy_confirmed=True))
    close=dict(package_kind='B',passed=True,destroy={'status':'DESTROY_CONFIRMED'},stop={'status':'STOP_CONFIRMED'},
        recovery={'verified':True},budget_settled=True,authorization_raw_sha256=campaign.read(campaign.BASE/'policy.json')['B_origin_authorization_raw_sha256'],
        owner={'reservation_token':'TEST_ONLY_RESERVATION'},raw_files={})
    path=stage/'stage_closeout.json';campaign.save(path,close)
    binding.update(B_stage_closeout=str(path),B_stage_closeout_sha256=campaign.sha(path))
    with pytest.raises(ValueError,match='MANDATORY'):m.validate_policy_receipt(binding)


def test_fresh_provider_increase_reduces_actual_remaining(tmp_path):
    l=Ledger(tmp_path/'l.jsonl');l.append(dict(action='INIT',cap='1',historical_bound='.364'))
    l.append(dict(action='RESERVE',token='B',amount='.05'))
    l.append(dict(action='SETTLE',token='B',observed_cost_bound='.05',destroy_confirmed=True))
    balance=l.append(dict(action='OBSERVE',historical_bound='.982'))
    assert str(balance['remaining'])=='0.018'
    with pytest.raises(ValueError):l.append(dict(action='RESERVE',token='A',amount='.05'))


@pytest.mark.parametrize('data',[b'',b'{}',b'{"instance_id":7,"raw_files":{}}'])
def test_watchdog_uses_hash_verified_admin_evidence(tmp_path,data):
    (tmp_path/'admin_started.json').write_bytes(b'{}');(tmp_path/'admin_verified.json').write_bytes(data)
    with pytest.raises(Exception):verify_admin(tmp_path,{'instance_id':7})
