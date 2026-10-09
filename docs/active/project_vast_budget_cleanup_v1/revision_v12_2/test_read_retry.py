import subprocess
import pytest
from read_retry import read_retry

def test_timeout_then_same_read_success():
    calls=[]
    def fn(left):
        calls.append(left)
        if len(calls)==1:raise subprocess.TimeoutExpired('TEST_ONLY_READ',left)
        return 'SAME_OWNER'
    assert read_retry(fn,('show','instance',7),timeout=24,absolute_deadline=24,check=lambda:None,now=lambda:0)=='SAME_OWNER'
    assert len(calls)==2

def test_three_failed_reads_stop():
    calls=[]
    def fn(left):calls.append(left);raise subprocess.TimeoutExpired('TEST_ONLY_READ',left)
    with pytest.raises(subprocess.TimeoutExpired):read_retry(fn,('show','instance',7),timeout=24,absolute_deadline=24,check=lambda:None,now=lambda:0)
    assert len(calls)==3

def test_mutation_is_never_retried():
    calls=[]
    def fn(left):calls.append(left);raise subprocess.TimeoutExpired('TEST_ONLY_MUTATION',left)
    with pytest.raises(subprocess.TimeoutExpired):read_retry(fn,('start','instance',7),timeout=24,absolute_deadline=24,check=lambda:None,now=lambda:0)
    assert len(calls)==1

def test_integrity_error_is_never_retried():
    calls=[]
    def fn(left):calls.append(left);raise ValueError('OWNER_CHANGED')
    with pytest.raises(ValueError):read_retry(fn,('show','instance',7),timeout=24,absolute_deadline=24,check=lambda:None,now=lambda:0)
    assert len(calls)==1

def test_absolute_deadline_is_checked_after_read():
    clock=[0];calls=[]
    def fn(left):calls.append(left);clock[0]=10;return 'LATE'
    with pytest.raises(TimeoutError):read_retry(fn,('show','instance',7),timeout=20,absolute_deadline=10,check=lambda:None,now=lambda:clock[0])
    assert calls==[8]
