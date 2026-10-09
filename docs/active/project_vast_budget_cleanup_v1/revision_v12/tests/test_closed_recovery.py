"""End-to-end local archive checks in the approved REMOTE test process only."""
from pathlib import Path
import hashlib,json,sys,zipfile
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lifecycle
from job_proof import closed_archive,fixture_link_metadata
from test_terminal_finality import complete

def evidence(tmp_path,*,failed=False):
    owner=dict(instance_id=7,machine_id=8,run_id='TEST_ONLY_CLOSED',test_scope='ADMIN_MOCKS_THEN_B95')
    base=Path(lifecycle.__file__).parent;spec=json.loads((base/'transport/package_bindings.json').read_bytes())['B']
    job_spec=dict(instance_id=7,run_id=owner['run_id'],job_id=owner['run_id']+'_gate',guest_root='/workspace/TEST_ONLY',command=['TEST_ONLY'])
    encode=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    digest=hashlib.sha256(encode(job_spec)).hexdigest()
    identity=dict(instance_id=7,run_id=owner['run_id'],job_id=owner['run_id']+'_gate',spec_sha256=digest,boot_id='TEST_ONLY_BOOT',pid=42,pgid=42,startticks=55)
    terminal=dict(identity,returncode=2 if failed else 0,error='TEST_ONLY_FAILURE' if failed else None,all_descendants_reaped=True,remaining_children=[],subreaper_verified=True)
    observation=dict(identity=identity,terminal=terminal,terminal_sha256=hashlib.sha256(encode(terminal)).hexdigest(),state='EXITED_FAILURE' if failed else 'EXITED_SUCCESS',writer_completion_verified=True,**{k:identity[k] for k in ('instance_id','run_id','job_id','spec_sha256','boot_id')})
    data={'job_spec.json':encode(job_spec),'job/identity.json':encode(identity),'job/terminal.json':encode(terminal)}
    if failed:data['output/tests.log']=b'.'*180
    else:
        data.update(complete());status=json.loads(data['output/status.json']);status.update(code_sha256=spec['code_sha256'],protocol_sha256=spec['protocol_sha256']);data['output/status.json']=encode(status)
    absent=[n for n in ('gate_exit.json','output/status.json','output/junit.xml','output/physics_guard.json','output/benchmark.json') if n not in data]
    manifest=dict(instance_id=7,run_id=owner['run_id'],code_sha256=spec['code_sha256'],files={n:hashlib.sha256(v).hexdigest() for n,v in data.items()},writer_completion_verified=True,inventory_stable=True,scope='COMPLETE_EXISTING_FILES_AFTER_WRITERS_EXIT',job_observation=observation,absent_success_files=absent)
    with zipfile.ZipFile(tmp_path/'evidence.zip','x') as z:
        for n,v in data.items():z.writestr(n,v)
        z.writestr('evidence_manifest.json',encode(manifest))
    for n,v in data.items():
        target=tmp_path/'recovered'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(v)
    (tmp_path/'job_spec.json').write_bytes(encode(job_spec));(tmp_path/'job_final_observation.json').write_bytes(encode(observation))
    receipt=dict(zip_sha256=hashlib.sha256((tmp_path/'evidence.zip').read_bytes()).hexdigest(),all_raw_hashes_match=True,writer_completion_verified=True,job_observation=observation,job_spec_sha256=digest)
    (tmp_path/'recovery_verified.json').write_bytes(encode(receipt))
    return owner,spec,receipt

def test_closed_success_archive_retains_original_pass_criteria(tmp_path):
    owner,spec,receipt=evidence(tmp_path)
    result=lifecycle.verified_recovery(tmp_path,owner,True)
    assert result['verified'] is True and result['final_files_verified'] is True

def test_closed_failure_all_raw_is_recovered_without_success_promotion(tmp_path):
    owner,spec,receipt=evidence(tmp_path,failed=True)
    result=lifecycle.verified_recovery(tmp_path,owner,True)
    assert result['verified'] is True and result['execution_passed'] is False
    assert 'output/junit.xml' in result['absent_success_files']
    assert closed_archive(tmp_path,owner,spec['code_sha256'])['outcome']=='EXITED_FAILURE'

def test_hash_valid_archive_with_running_writer_is_not_final(tmp_path):
    owner,spec,receipt=evidence(tmp_path,failed=True);receipt['writer_completion_verified']=False
    (tmp_path/'recovery_verified.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError):closed_archive(tmp_path,owner,spec['code_sha256'])

def test_local_missing_created_original_refuses_even_when_zip_valid(tmp_path):
    owner,spec,receipt=evidence(tmp_path,failed=True);(tmp_path/'recovered/output/tests.log').unlink()
    with pytest.raises((FileNotFoundError,ValueError)):lifecycle.verified_recovery(tmp_path,owner,True)

def test_foreign_job_record_never_passes_recovery(tmp_path):
    owner,spec,receipt=evidence(tmp_path,failed=True);owner['run_id']='ANOTHER_JOB'
    with pytest.raises(ValueError):lifecycle.verified_recovery(tmp_path,owner,True)

def test_admin_fixture_link_preserves_target_string_without_following():
    files={'job_spec.json':b'{"job_role":"ADMIN_TESTS"}'}
    fixture_link_metadata({'admin_fixture_symlink_metadata':{'v12_tmp/testcasecurrent':'/outside/fixture-only'}},files)

@pytest.mark.parametrize('name,role', [('output/research-original','ADMIN_TESTS'),('v12_tmp/testcasecurrent','A320_GUEST'),('../foreign','ADMIN_TESTS')])
def test_link_metadata_cannot_hide_research_or_foreign_raw(name,role):
    files={'job_spec.json':json.dumps({'job_role':role}).encode()}
    with pytest.raises(ValueError):fixture_link_metadata({'admin_fixture_symlink_metadata':{name:'target'}},files)
