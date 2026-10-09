"""V12.3 extra remote jobs must be closed and recovered before any automatic delete (parent and watchdog share this)."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
V12_2=HERE.parent/'revision_v12_2'
# (start marker, closed-originals descriptor, local folder, run_id suffix, job role, code archive)
EXTRA_JOBS=(
    ('v12_3_admin_started.json','v12_3_admin_closed_originals.json','v12_3_admin_job','_v12_3_admin','ADMIN_TESTS',V12_2/'admin_payload.zip'),
    ('v12_3_probe_started.json','v12_3_probe_closed_originals.json','v12_3_disconnect_probe','_v12_3_probe','ADMIN_PROBE',V12_2/'admin_payload.zip'),
)


def verify_extra_jobs(out,owner,*,closed_archive=None):
    out=Path(out)
    if closed_archive is None:from job_proof import closed_archive
    for marker,name,folder,suffix,role,archive in EXTRA_JOBS:
        if not (out/marker).exists():continue
        if not (out/name).exists():raise ValueError('V12_3_EXTRA_JOB_UNRECOVERED_PRESERVE:'+folder)
        descriptor=json.loads((out/name).read_bytes())
        bound=descriptor['owner']
        if any(bound.get(k)!=v for k,v in (('instance_id',owner['instance_id']),('machine_id',owner['machine_id']),('run_id',owner['run_id']+suffix))):
            raise ValueError('V12_3_EXTRA_JOB_OWNER_DRIFT:'+folder)
        if Path(descriptor['folder']).resolve()!=(out/folder).resolve():raise ValueError('V12_3_EXTRA_JOB_FOLDER_SCOPE:'+folder)
        if descriptor['code_sha256']!=hashlib.sha256(Path(archive).read_bytes()).hexdigest():raise ValueError('V12_3_EXTRA_JOB_SOURCE_BINDING:'+folder)
        if json.loads((out/folder/'job_spec.json').read_bytes()).get('job_role')!=role:raise ValueError('V12_3_EXTRA_JOB_ROLE:'+folder)
        if closed_archive(descriptor['folder'],bound,descriptor['code_sha256'])!=descriptor['proof']:raise ValueError('V12_3_EXTRA_JOB_RAW_FINALITY:'+folder)
    return True


def install():
    import cleanup
    if getattr(cleanup.verify_admin,'v12_3_wrapped',False):return cleanup
    original=cleanup.verify_admin
    def verify(out,owner):
        verify_extra_jobs(out,owner)
        return original(out,owner)
    verify.v12_3_wrapped=True
    cleanup.verify_admin=verify
    return cleanup
