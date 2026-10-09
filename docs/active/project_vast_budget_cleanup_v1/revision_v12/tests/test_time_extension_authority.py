from pathlib import Path
import json,hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from preflight import require_time_extension

def packet(tmp_path,**changes):
    # TEST_ONLY fake raw input; never authority for provider actions.
    value=dict(accepted=True,instance_id=55040957,machine_id=53859,requested_absolute_maximum_seconds=3600,actual_human_answer='TEST_ONLY_NOT_AUTHORITY');value.update(changes)
    p=tmp_path/'test_only.json';p.write_text(json.dumps(value))
    return dict(time_extension_path=str(p),time_extension_sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def test_reader_exact_fields_only_test_only(tmp_path):
    require_time_extension(packet(tmp_path))

@pytest.mark.parametrize('changes',[dict(accepted=False),dict(instance_id=1),dict(machine_id=1),dict(requested_absolute_maximum_seconds=3601),dict(actual_human_answer=None)])
def test_pending_or_mutated_extension_refused(tmp_path,changes):
    with pytest.raises(ValueError):require_time_extension(packet(tmp_path,**changes))

def test_time_raw_hash_drift_refused(tmp_path):
    policy=packet(tmp_path);Path(policy['time_extension_path']).write_text('changed')
    with pytest.raises(ValueError):require_time_extension(policy)
