from pathlib import Path
import sys,json
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminal_proof import require_terminal

SPEC=dict(expected_tests=95,code_sha256='CODE',protocol_sha256='PROTO')
def complete():
    cases=''.join('<testcase classname="X" name="n%d" />'%n for n in range(95))
    return {'gate_exit.json':json.dumps(dict(returncode=0,error=None)).encode(),
      'output/status.json':json.dumps(dict(status='PASS',tests=95,code_sha256='CODE',protocol_sha256='PROTO',failed=0,errors=0,skipped=0,physics_calls=0,gpu_calls=0,wall_ns=1,cpu_ns=1,process_tree_peak_rss_bytes=1,package_kind='B',benchmark_complete=False)).encode(),
      'output/junit.xml':('<testsuites><testsuite>'+cases+'</testsuite></testsuites>').encode(),
      'output/physics_guard.json':json.dumps(dict(blocked_attempts=[],new_physics_calls=0,gpu_calls=0)).encode()}

def test_byte_valid_partial_snapshot_never_authorizes_destruction():
    with pytest.raises(ValueError,match='WRITER_COMPLETION'):
        require_terminal({'output/tests.log':b'.'*180},writer_completion_verified=False,spec=SPEC)

def test_final_files_missing_even_with_completed_rpc_is_rejected():
    files=complete();del files['output/junit.xml']
    with pytest.raises(ValueError,match='FINAL_FILES_MISSING'):require_terminal(files,writer_completion_verified=True,spec=SPEC)

def test_source_binding_drift_rejected():
    files=complete();s=json.loads(files['output/status.json']);s['code_sha256']='BAD';files['output/status.json']=json.dumps(s).encode()
    with pytest.raises(ValueError,match='SOURCE_BINDING'):require_terminal(files,writer_completion_verified=True,spec=SPEC)

def test_protected_case_identity_mismatch_rejected():
    with pytest.raises(ValueError,match='ORIGINAL_CASE_IDS'):require_terminal(complete(),writer_completion_verified=True,spec=SPEC,original_case_ids=['different'])

def test_guard_unconfirmed_rejected():
    files=complete();files['output/physics_guard.json']=b'{}'
    with pytest.raises(ValueError,match='FINAL_GUARD'):require_terminal(files,writer_completion_verified=True,spec=SPEC)

def test_complete_b_evidence_can_pass_terminal_barrier():
    result=require_terminal(complete(),writer_completion_verified=True,spec=SPEC)
    assert result['writer_completion_verified'] is True and result['final_files_verified'] is True and result['tests']==95


def test_duplicate_final_status_key_does_not_override_stop():
    files=complete();files['output/status.json']=b'{"status":"STOP","status":"PASS"}'
    with pytest.raises(ValueError,match='DUPLICATE'):require_terminal(files,writer_completion_verified=True,spec=SPEC)


def test_nonfinite_final_json_is_rejected():
    files=complete();files['output/status.json']=b'{"wall_ns":NaN}'
    with pytest.raises(ValueError,match='NONFINITE'):require_terminal(files,writer_completion_verified=True,spec=SPEC)
