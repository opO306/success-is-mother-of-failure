"""Remote Linux only. Actual sealed job wrapper, real child processes, no A/B compute."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,sys,time
import pytest

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'transport'))
import guest_job

@pytest.fixture
def job(tmp_path):
    artifact=Path(os.environ['V12_TEST_ARTIFACT_ROOT'])/tmp_path.name
    artifact.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(BASE/'transport/guest_job.py',artifact/'guest_job.py')
    instance=guest_job.instance();job_id=tmp_path.name+'_gate'
    def create(body,timeout=2):
        writer=artifact/'writer.py';writer.write_text(body,encoding='utf-8')
        spec=dict(instance_id=instance,run_id=tmp_path.name,job_id=job_id,guest_root=str(artifact),wrapper_sha256=hashlib.sha256((artifact/'guest_job.py').read_bytes()).hexdigest(),
                  command=[sys.executable,'-B',str(writer)],command_script_sha256=hashlib.sha256(writer.read_bytes()).hexdigest(),timeout_seconds=timeout)
        (artifact/'job_spec.json').write_bytes(guest_job.raw(spec))
    yield artifact,instance,job_id,create
    # Every launched process has a sealed finite timeout; no cleanup deletion of its raw.

def final(job,seconds=12):
    root,instance,job_id,_=job;end=time.monotonic()+seconds
    while time.monotonic()<end:
        state=guest_job.observe(root/'job',instance,job_id)
        if state['state'] in ('EXITED_SUCCESS','EXITED_FAILURE'):return state
        time.sleep(.05)
    raise AssertionError('REMOTE_JOB_NOT_TERMINAL:'+json.dumps(state))

def test_real_normal_exit_and_same_claim_never_relaunch(job):
    root,instance,job_id,create=job
    create("from pathlib import Path\np=Path(__file__).parent/'once';p.open('x').write('once')\n")
    first=guest_job.launch(root/'job',instance,job_id);done=final(job)
    second=guest_job.launch(root/'job',instance,job_id)
    assert done['state']=='EXITED_SUCCESS' and second['identity']==done['identity']
    assert done['writer_completion_verified'] is True and (root/'once').read_text()=='once'

def test_real_disconnect_then_running_then_completed(job):
    root,instance,job_id,create=job
    create("import time\nfrom pathlib import Path\ntime.sleep(3)\n(Path(__file__).parent/'written').write_text('complete')\n",timeout=6)
    client=subprocess.Popen([sys.executable,'-B',str(BASE/'transport/guest_disconnect_launch.py'),str(root),str(instance),job_id],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        with pytest.raises(subprocess.TimeoutExpired):client.communicate(timeout=1)
    finally:
        client.kill();client.communicate(timeout=2)
    running=guest_job.observe(root/'job',instance,job_id)
    assert running['state']=='RUNNING' and running['writer_completion_verified'] is False
    assert final(job)['state']=='EXITED_SUCCESS' and (root/'written').read_text()=='complete'

def test_real_setsid_descendant_writer_is_waited_not_group_assumed(job):
    root,instance,job_id,create=job
    create("import subprocess,sys\nsubprocess.Popen([sys.executable,'-c',\"import time;from pathlib import Path;time.sleep(.4);Path('descendant').write_text('closed')\"],start_new_session=True)\n",timeout=3)
    guest_job.launch(root/'job',instance,job_id);done=final(job)
    assert done['state']=='EXITED_SUCCESS' and done['terminal']['all_descendants_reaped'] is True
    assert (root/'descendant').read_text()=='closed'

def test_real_failure_is_closed_failure_not_success(job):
    root,instance,job_id,create=job;create("raise SystemExit(7)\n")
    guest_job.launch(root/'job',instance,job_id);done=final(job)
    assert done['state']=='EXITED_FAILURE' and done['terminal']['returncode']==7 and done['writer_completion_verified'] is True

def test_real_timeout_stops_child_and_does_not_claim_success(job):
    root,instance,job_id,create=job;create("import time;time.sleep(20)\n",timeout=1)
    guest_job.launch(root/'job',instance,job_id);done=final(job)
    assert done['state']=='EXITED_FAILURE' and done['terminal']['remaining_children']==[]

def test_unknown_claim_without_process_identity_never_relaunch(job):
    root,instance,job_id,create=job;create("raise AssertionError('MUST_NOT_RUN')\n")
    folder=root/'job';folder.mkdir();spec=guest_job.read(root/'job_spec.json')
    guest_job.atomic(folder/'claim.json',dict(spec_sha256=guest_job.sha(guest_job.raw(spec)),boot_id=guest_job.boot()))
    assert guest_job.launch(folder,instance,job_id)['state']=='CLAIMED_UNKNOWN_PID'
    assert not (folder/'identity.json').exists()

def test_other_job_id_is_refused_without_process_start(job):
    root,instance,job_id,create=job;create("raise AssertionError('MUST_NOT_RUN')\n")
    with pytest.raises(ValueError,match='OWNER_BINDING'):guest_job.launch(root/'job',instance,job_id+'_different')
    assert not (root/'job').exists()

def test_pid_reuse_is_refused_even_with_terminal(job,monkeypatch):
    root,instance,job_id,create=job;create("pass\n")
    guest_job.launch(root/'job',instance,job_id);done=final(job);identity=done['identity']
    monkeypatch.setattr(guest_job,'census',lambda:{identity['pid']:dict(identity,ppid=1,session=identity['pid'],state='R',startticks=identity['startticks']+1)})
    with pytest.raises(ValueError,match='PID_REUSED'):guest_job.observe(root/'job',instance,job_id)
