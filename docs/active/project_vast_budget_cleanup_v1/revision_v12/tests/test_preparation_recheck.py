"""Remote-only administrative call-boundary cases; never rental or compute."""
from pathlib import Path
import sys
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import campaign

@pytest.mark.parametrize('errors,expected',[(['Connection closed',None],2),(['Connection closed']*4,3),(['Permission denied; Connection closed',None],1)])
def test_preparation_read_recheck_is_finite_and_keeps_all_attempt_raw(tmp_path,errors,expected):
    calls=[]
    def io(out,argv,name,timeout,**kwargs):
        out.mkdir(parents=True);calls.append(timeout)
        message=errors[len(calls)-1]
        (out/(name+'.stderr')).write_text(message or '')
        if message:raise ValueError('ADMIN_TRANSPORT_COMMAND_FAILED:'+name)
        return b'TEST_ONLY_RECHECK_RESULT'
    with patch.object(campaign,'command',side_effect=io):
        if errors[-1] is None and expected==2:assert campaign.command_recheck(tmp_path,['TEST_ONLY_READ'],'recovery',15)==b'TEST_ONLY_RECHECK_RESULT'
        else:
            with pytest.raises(ValueError):campaign.command_recheck(tmp_path,['TEST_ONLY_READ'],'recovery',15)
    assert len(calls)==expected and all(a>=b for a,b in zip(calls,calls[1:]))
    assert len(list(tmp_path.rglob('recovery.stderr')))==expected

def test_termination_control_error_is_not_preparation_retry(tmp_path):
    with patch.object(campaign,'command',side_effect=ValueError('LEASE_WATCHDOG_LOST')) as io:
        with pytest.raises(ValueError,match='LEASE_WATCHDOG_LOST'):campaign.command_recheck(tmp_path,['TEST_ONLY_READ'],'recovery',15)
    assert io.call_count==1

def test_actual_remote_scripts_refuse_wrong_pid1_even_with_python_optimization():
    import ast,subprocess
    sys.path.insert(0,str(campaign.BASE/'transport'))
    import guest_job
    tree=ast.parse((campaign.BASE/'campaign.py').read_text(encoding='utf-8'))
    scripts=[n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)
             and ('PREPARATION_ACTUAL_INSTANCE_MISMATCH' in n.value.value or 'STARTUP_ACTUAL_INSTANCE_MISMATCH' in n.value.value)]
    assert len(scripts)==3
    wrong=str(guest_job.instance()+1)
    for script in scripts:
        args=['/workspace/TEST_ONLY_MUST_NOT_CREATE',wrong] if 'PREPARATION_' in script else [wrong]
        result=subprocess.run([sys.executable,'-B','-O','-c',script,*args],capture_output=True,timeout=5)
        assert result.returncode!=0 and b'ACTUAL_INSTANCE_MISMATCH' in result.stderr and result.stdout==b''
