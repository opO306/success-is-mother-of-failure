"""Actual V3 functions, fake external CLI/file boundaries; remote CPU-only execution."""
import json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preflight import require_tools,before_any_rental
from closure_policy import decide
from cleanup import destroy_with_disposition

OWNER=dict(instance_id=7,machine_id=8,country='KR',label='TEST_ONLY_OWNER')
AUTH=dict(instance_id=7,delete_eligible=True,authorization_verified=True,raw_verified=False,no_remote_project_writes=True,
          accepted_loss_files={'runtime_setup.log':'CREATED_UNRECOVERED'})


class Clock:
    value=0
    def now(self):return self.value
    def sleep(self,n):self.value+=n


class ActualCliBoundary:
    """Reproduce installed CLI's confirmation abort even with exit zero."""
    def __init__(self,scenario):self.scenario=scenario;self.calls=[];self.deleted=False
    def call(self,*args,**kw):
        self.calls.append(args)
        if args[:2]==('destroy','instance'):
            assert args[2]==7
            if '--yes' not in args or self.scenario=='zero_but_present':return b'Aborted.'
            if self.scenario=='request_error':raise OSError('TEST_ONLY_DELETE_FAILED')
            self.deleted=True;return b''
        if self.scenario=='already_deleted':raise OSError('TEST_ONLY_NOT_FOUND')
        return dict(id=99 if self.scenario=='wrong_owner' else 7,machine_id=8,country='KR',label=OWNER['label'],
            actual_status='running' if self.scenario=='running' else 'exited',intended_status='stopped')
    def instances(self,**kw):return [] if self.deleted else [self.call('show','instance',7)]
    def volumes(self,**kw):return [{'id':44}] if self.scenario=='volume_changed' else []


def test_actual_cli_confirmation_abort_counterexample():
    boundary=ActualCliBoundary('normal')
    assert boundary.call('destroy','instance',7)==b'Aborted.' and boundary.deleted is False


def test_shared_actual_destroy_sends_yes_and_verifies_absence(tmp_path):
    p=ActualCliBoundary('normal');clock=Clock()
    result=destroy_with_disposition(p,OWNER,AUTH,[],journal_out=tmp_path/'journal',now=clock.now,sleep=clock.sleep)
    assert result['status']=='DESTROY_CONFIRMED' and result['raw_verified'] is False
    assert [a for a in p.calls if a[:2]==('destroy','instance')]==[('destroy','instance',7,'--yes')]


@pytest.mark.parametrize('scenario',['running','wrong_owner','already_deleted'])
def test_invalid_start_state_has_zero_delete_calls(tmp_path,scenario):
    p=ActualCliBoundary(scenario)
    with pytest.raises((ValueError,OSError)):
        destroy_with_disposition(p,OWNER,AUTH,[],journal_out=tmp_path/'journal')
    assert not any(a[:2]==('destroy','instance') for a in p.calls)


@pytest.mark.parametrize('scenario',['zero_but_present','request_error'])
def test_three_bounded_requests_cannot_claim_deleted_when_still_listed(tmp_path,scenario):
    p=ActualCliBoundary(scenario);clock=Clock()
    r=destroy_with_disposition(p,OWNER,AUTH,[],journal_out=tmp_path/'journal',now=clock.now,sleep=clock.sleep)
    assert r['status']=='DESTROY_UNCONFIRMED' and r['attempts']==3
    assert len([a for a in p.calls if a[:2]==('destroy','instance')])==3


def test_residual_volume_cannot_claim_complete(tmp_path):
    p=ActualCliBoundary('volume_changed')
    with pytest.raises(ValueError,match='RESIDUAL_VOLUME'):
        destroy_with_disposition(p,OWNER,AUTH,[],journal_out=tmp_path/'journal')


def test_scp_o_preflight_does_not_require_or_probe_unused_rsync(tmp_path):
    paths={n:tmp_path/n for n in ['vastai','key','ssh','scp']}
    for p in paths.values():p.write_bytes(b'TEST_ONLY')
    (tmp_path/'key.pub').write_text('ssh-ed25519 TEST_ONLY')
    checked=[]
    def which(name):checked.append(name);return str(paths[name])
    r=require_tools(paths['vastai'],paths['key'],which=which,transfer_mode='SCP_O',
        run=lambda *a,**k:SimpleNamespace(returncode=0,stdout=b'TEST_ONLY_VERSION',stderr=b''))
    assert checked==['ssh','scp'] and 'rsync' not in r['paths']


def test_missing_selected_scp_refused_before_any_version_or_provider(tmp_path):
    for n in ['vastai','key','ssh']:(tmp_path/n).write_bytes(b'TEST_ONLY')
    (tmp_path/'key.pub').write_text('ssh-ed25519 TEST_ONLY')
    with pytest.raises(ValueError,match='MISSING_RECOVERY_TOOL_BEFORE_RENT:scp'):
        before_any_rental(tmp_path/'vastai',tmp_path/'key',{'transfer_mode':'SCP_O'},tmp_path/'out',
            which=lambda n:None if n=='scp' else str(tmp_path/n),
            run=lambda *a,**k:(_ for _ in ()).throw(AssertionError('NO_EXTERNAL_CALL_BEFORE_TOOL_FOUND')))


def test_unnamed_unconfirmed_file_loss_is_not_preapproved():
    r=decide(OWNER,{'runtime_setup.log':{'existence':'UNKNOWN'}},now_utc='2026-10-09T14:00:00+00:00',
        deadline_utc='2026-10-09T13:00:00+00:00',research_state='NO_RESEARCH_COMMANDS_ISSUED_BY_THIS_CONTROLLER',
        important_recovery_verified=True,setup_discard_consent=True)
    assert r['delete_eligible'] is False and r['action']=='WAIT_EXPLICIT_DISCARD_APPROVAL'


def test_created_file_outside_two_named_setup_files_cannot_use_loss_exception():
    r=decide(OWNER,{'actual_junit.xml':{'existence':'CREATED_UNRECOVERED'}},now_utc='2026-10-09T14:00:00+00:00',
        deadline_utc='2026-10-09T13:00:00+00:00',research_state='NO_RESEARCH_COMMANDS_ISSUED_BY_THIS_CONTROLLER',
        important_recovery_verified=True,setup_discard_consent=True)
    assert r['delete_eligible'] is False


def test_direct_writer_marker_without_final_files_has_zero_delete_calls(tmp_path):
    p=ActualCliBoundary('normal');auth=dict(AUTH,no_remote_project_writes=False,writer_completion_verified=True,final_files_verified=False)
    with pytest.raises(ValueError,match='DISPOSITION_FINALITY'):
        destroy_with_disposition(p,OWNER,auth,[],journal_out=tmp_path/'journal')
    assert p.calls==[]
