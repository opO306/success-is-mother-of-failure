import json,subprocess,sys,textwrap
from pathlib import Path
import pytest
import process_bridge,closure


def test_dispatch_rewrites_only_the_three_v12_entries(monkeypatch):
    seen=[]
    monkeypatch.setattr(subprocess,'Popen',subprocess.Popen)  # restored after the test
    process_bridge.install_dispatch(previous=lambda argv,*a,**k:seen.append(argv))
    py=sys.executable
    for name,path in process_bridge.TARGETS.items():
        subprocess.Popen([py,'-B',str(path),'--lease','x.json'])
        assert seen[-1]==[py,'-B',str(process_bridge.HERE/'process_bridge.py'),name,'--lease','x.json']
    other=[py,'-B',str(process_bridge.V12/'campaign.py')]
    subprocess.Popen(other);assert seen[-1]==other
    subprocess.Popen('ssh host');assert seen[-1]=='ssh host'
    subprocess.Popen(['ssh']);assert seen[-1]==['ssh']


def test_v12_modules_shadow_v12_2_names():
    """V12.2 has its own preflight/process_bridge; after paths() the V12 and V12.3 ones must win."""
    code=textwrap.dedent(f'''
        import sys;sys.path.insert(0,{str(process_bridge.HERE)!r})
        import process_bridge;process_bridge.paths()
        import importlib.util as u
        print(u.find_spec("preflight").origin);print(u.find_spec("process_bridge").origin);print(u.find_spec("read_retry").origin)''')
    out=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,check=True).stdout.split('\n')
    assert Path(out[0]).parent==process_bridge.V12
    assert Path(out[1]).parent==process_bridge.HERE
    assert Path(out[2]).parent==process_bridge.V12_2


OWNER=dict(instance_id=7,machine_id=8,run_id='project_v12_a_x')


def descriptor(out,marker,name,folder,suffix,role,archive,proof='P'):
    (out/marker).write_text('{}');(out/folder).mkdir()
    (out/folder/'job_spec.json').write_text(json.dumps(dict(job_role=role)))
    (out/name).write_text(json.dumps(dict(owner=dict(OWNER,run_id=OWNER['run_id']+suffix),folder=str(out/folder),
        code_sha256=closure.hashlib.sha256(Path(archive).read_bytes()).hexdigest(),proof=proof)))


def test_no_extra_job_started_needs_nothing(tmp_path):
    assert closure.verify_extra_jobs(tmp_path,OWNER,closed_archive=lambda *a:pytest.fail('not called'))


def test_started_but_unrecovered_extra_job_preserves(tmp_path):
    (tmp_path/'v12_3_admin_started.json').write_text('{}')
    with pytest.raises(ValueError,match='UNRECOVERED_PRESERVE'):closure.verify_extra_jobs(tmp_path,OWNER,closed_archive=lambda *a:'P')


def test_closed_extra_jobs_pass_and_any_drift_preserves(tmp_path):
    for job in closure.EXTRA_JOBS:descriptor(tmp_path,*job)
    assert closure.verify_extra_jobs(tmp_path,OWNER,closed_archive=lambda *a:'P')
    with pytest.raises(ValueError,match='RAW_FINALITY'):closure.verify_extra_jobs(tmp_path,OWNER,closed_archive=lambda *a:'OTHER')
    data=json.loads((tmp_path/'v12_3_probe_closed_originals.json').read_text());data['owner']['run_id']='wrong'
    (tmp_path/'v12_3_probe_closed_originals.json').write_text(json.dumps(data))
    with pytest.raises(ValueError,match='OWNER_DRIFT'):closure.verify_extra_jobs(tmp_path,OWNER,closed_archive=lambda *a:'P')


def test_install_wraps_v12_verify_admin_once(monkeypatch,tmp_path):
    import cleanup
    calls=[]
    monkeypatch.setattr(cleanup,'verify_admin',lambda out,owner:calls.append('original') or 'ok')
    closure.install();closure.install()
    assert cleanup.verify_admin(tmp_path,OWNER)=='ok' and calls==['original']
    (tmp_path/'v12_3_admin_started.json').write_text('{}')
    with pytest.raises(ValueError,match='UNRECOVERED_PRESERVE'):cleanup.verify_admin(tmp_path,OWNER)
    assert calls==['original']  # extra-job refusal happens before the original verifier
