import json,subprocess
from types import SimpleNamespace
import pytest
from reads import ReadRetryProvider


class Runner:
    """Scripted fake for subprocess.run: each item is an exception, or (returncode, stdout, stderr)."""
    def __init__(self,*script):self.script=list(script);self.calls=[]
    def __call__(self,argv,capture_output,timeout):
        self.calls.append(dict(argv=argv,timeout=timeout))
        step=self.script.pop(0)
        if isinstance(step,BaseException):raise step
        code,out,err=step
        return SimpleNamespace(returncode=code,stdout=out,stderr=err)


ROW=json.dumps(dict(id=1,actual_status='running')).encode()


def provider(tmp_path,runner):return ReadRetryProvider('vastai',tmp_path/'api',runner=runner)


def test_read_timeout_then_success_is_retried_inside_caller_timeout(tmp_path):
    r=Runner(subprocess.TimeoutExpired(['x'],8),(0,ROW,b''))
    assert provider(tmp_path,r).call('show','instance',1,timeout=12)['id']==1
    assert len(r.calls)==2
    assert r.calls[0]['timeout']==8 and 0<r.calls[1]['timeout']<=8  # each attempt <=8 s, never beyond the caller's 12 s


def test_transient_provider_failure_is_retried(tmp_path):
    r=Runner((1,b'',b'requests.exceptions.ConnectionError: Connection reset by peer'),(0,ROW,b''))
    assert provider(tmp_path,r).call('show','instance',1,timeout=12)['id']==1
    assert len(r.calls)==2


def test_authentication_failure_is_not_retried(tmp_path):
    r=Runner((1,b'',b'401 Unauthorized'),(0,ROW,b''))
    with pytest.raises(OSError):provider(tmp_path,r).call('show','instance',1,timeout=12)
    assert len(r.calls)==1


@pytest.mark.parametrize('args',[('stop','instance',1),('start','instance',1),('destroy','instance',1,'--yes'),('create','instance','9'),('search','offers','q')])
def test_mutations_and_search_are_called_exactly_once(tmp_path,args):
    r=Runner(subprocess.TimeoutExpired(['x'],8),(0,b'ok',b''))
    with pytest.raises(subprocess.TimeoutExpired):provider(tmp_path,r).call(*args,json_result=False,timeout=12)
    assert len(r.calls)==1


def test_three_timeouts_stop_and_raise(tmp_path):
    r=Runner(*(subprocess.TimeoutExpired(['x'],1) for _ in range(3)),(0,ROW,b''))
    with pytest.raises(subprocess.TimeoutExpired):provider(tmp_path,r).call('show','instances',timeout=30)
    assert len(r.calls)==3


def test_each_attempt_keeps_its_own_raw_files(tmp_path):
    r=Runner(subprocess.TimeoutExpired(['x'],8),(0,b'[]',b''))
    provider(tmp_path,r).call('show','volumes',timeout=12)
    assert (tmp_path/'api/0001.exception.json').exists() and (tmp_path/'api/0002.stdout').exists()
