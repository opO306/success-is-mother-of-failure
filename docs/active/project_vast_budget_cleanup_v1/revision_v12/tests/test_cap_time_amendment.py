from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
import campaign
from budget import Ledger
from cleanup import settle_extension_reservations
from admin_revalidation import SafetyStop

def fixture(tmp_path):
    ledger=Ledger(tmp_path/'ledger.jsonl');ledger.append(dict(action='INIT',cap='1',historical_bound='.5'))
    policy=campaign.read(campaign.BASE/'policy.json')
    # Actual sealed authorization bytes, fake private ledger only; no provider.
    event=dict(action='AMEND_CAP',new_cap='2.00',approval_raw_path=str(campaign.BASE/'cap_time_amendment.json'),approval_raw_sha256=policy['cap_time_amendment_sha256'])
    return ledger,event

def test_actual_cap_amendment_preserves_initial_history(tmp_path):
    ledger,event=fixture(tmp_path);before=ledger.path.read_bytes();result=ledger.append(event)
    assert result['cap']==2 and result['spent']==.5 and ledger.path.read_bytes().startswith(before)

def test_duplicate_amendment_refused(tmp_path):
    ledger,event=fixture(tmp_path);ledger.append(event)
    with pytest.raises(ValueError):ledger.append(event)

def test_changed_actual_approval_refused(tmp_path):
    ledger,event=fixture(tmp_path);fake=tmp_path/'approval.json';fake.write_text('NO AUTHORIZATION');event['approval_raw_path']=str(fake)
    with pytest.raises(ValueError):ledger.append(event)
    assert len(ledger.read()[0])==1

@pytest.mark.parametrize('kind',['A','B'])
def test_new_server_keeps_original_twenty_minute_limit(kind):
    historical=campaign.read(campaign.BASE/'policy.json');historical['schema']='HISTORICAL_V8_SCOPE'
    assert campaign.scoped_policy(historical,kind,None)['lease_seconds']==1200

def test_only_exact_existing_b_path_can_extend():
    policy=campaign.read(campaign.BASE/'policy.json');policy['schema']='HISTORICAL_V8_SCOPE';path=Path(policy['private_root'])/'project_v5_2_b_20261009_145216'
    assert campaign.scoped_policy(policy,'B',path)['lease_seconds']==3600
    with pytest.raises(SafetyStop):campaign.scoped_policy(policy,'A',path)
    with pytest.raises(SafetyStop):campaign.scoped_policy(policy,'B',path.parent/'another')

def test_parent_loss_destroy_settles_both_reservations(tmp_path):
    ledger,event=fixture(tmp_path);ledger.append(event)
    ledger.append(dict(action='RESERVE',token='TEST_ONLY',amount='.04'))
    ledger.append(dict(action='RESERVE',token='TEST_ONLY_time_extension_v7',amount='.02'))
    ledger.append(dict(action='SETTLE',token='TEST_ONLY',observed_cost_bound='.04',destroy_confirmed=True))
    owner=dict(instance_id=55040957,machine_id=53859,reservation_token='TEST_ONLY',extension_reservations=[dict(token='TEST_ONLY_time_extension_v7',amount='.02')])
    settle_extension_reservations(ledger,owner)
    assert ledger.balances(ledger.read()[0])['active']=={}
    settle_extension_reservations(ledger,owner)
    assert sum(e['action']=='SETTLE' for e in ledger.read()[0])==2

def test_extension_token_or_amount_drift_preserves_pending(tmp_path):
    ledger,event=fixture(tmp_path);ledger.append(event);ledger.append(dict(action='RESERVE',token='TEST_ONLY_time_extension_v7',amount='.02'))
    owner=dict(instance_id=55040957,machine_id=53859,reservation_token='TEST_ONLY',extension_reservations=[dict(token='TEST_ONLY_time_extension_v7',amount='.01')])
    with pytest.raises(ValueError):settle_extension_reservations(ledger,owner)
    assert ledger.balances(ledger.read()[0])['active']
