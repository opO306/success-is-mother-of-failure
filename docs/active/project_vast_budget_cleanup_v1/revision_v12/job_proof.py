"""Local administrative proof of completed writers, never a test PASS shortcut."""
import hashlib
from pathlib import Path,PurePosixPath
import stat,zipfile
from lifecycle import decode

def fixture_link_metadata(manifest,files):
    links=manifest.get('admin_fixture_symlink_metadata',{})
    if not isinstance(links,dict):raise ValueError('FIXTURE_LINK_METADATA_TYPE')
    if not links:return
    if decode(files['job_spec.json']).get('job_role')!='ADMIN_TESTS':raise ValueError('FIXTURE_LINK_ROLE')
    for name,target in links.items():
        if not isinstance(name,str) or not isinstance(target,str) or not name or '\\' in name or ':' in name or '\0' in name or PurePosixPath(name).is_absolute() or any(p in ('','.','..') for p in name.split('/')):raise ValueError('FIXTURE_LINK_PATH')
        parts=PurePosixPath(name).parts
        if name in files or not (parts[0] in ('v11_tmp','v12_tmp','process_cases') or parts[:2]==('source','.simulated')):raise ValueError('FIXTURE_LINK_SCOPE')

def completed_job(files,owner,*,job_observation,expected_spec_sha256):
    observed=job_observation
    if (observed.get('state') not in ('EXITED_SUCCESS','EXITED_FAILURE') or observed.get('writer_completion_verified') is not True
        or observed.get('instance_id')!=owner['instance_id'] or observed.get('run_id')!=owner['run_id']
        or observed.get('job_id')!=owner['run_id']+'_gate' or observed.get('spec_sha256')!=expected_spec_sha256):raise ValueError('JOB_FINAL_OBSERVATION_REQUIRED')
    identity=decode(files['job/identity.json']);terminal=decode(files['job/terminal.json']);spec=decode(files['job_spec.json'])
    if any(identity.get(k)!=observed.get(k) for k in ('instance_id','run_id','job_id','spec_sha256','boot_id')):raise ValueError('JOB_IDENTITY_BINDING')
    canonical=lambda v:__import__('json').dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if hashlib.sha256(canonical(spec)).hexdigest()!=expected_spec_sha256:raise ValueError('JOB_SPEC_RAW_BINDING')
    if observed.get('identity')!=identity or observed.get('terminal')!=terminal or hashlib.sha256(files['job/terminal.json']).hexdigest()!=observed.get('terminal_sha256'):raise ValueError('JOB_FINAL_RAW_BINDING')
    if any(terminal.get(k)!=identity.get(k) for k in ('instance_id','run_id','job_id','spec_sha256','boot_id','pid','startticks','pgid')):raise ValueError('JOB_TERMINAL_OWNER_DRIFT')
    if (terminal.get('all_descendants_reaped') is not True or terminal.get('remaining_children')!=[] or terminal.get('subreaper_verified') is not True
        or type(terminal.get('returncode')) is not int or identity.get('pgid')!=identity.get('pid')):raise ValueError('JOB_FINAL_CHILDREN_REQUIRED')
    return dict(writer_completion_verified=True,outcome=observed['state'],job_id=observed['job_id'],terminal_sha256=observed['terminal_sha256'])

def closed_archive(folder,owner,expected_code):
    folder=Path(folder);receipt=decode((folder/'recovery_verified.json').read_bytes());archive=folder/'evidence.zip'
    if receipt.get('all_raw_hashes_match') is not True or receipt.get('writer_completion_verified') is not True or hashlib.sha256(archive.read_bytes()).hexdigest()!=receipt.get('zip_sha256'):raise ValueError('CLOSED_ARCHIVE_RECEIPT_HASH')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();manifest=decode(z.read('evidence_manifest.json'))
        if (len(names)!=len(set(names)) or len(names)!=len({n.casefold() for n in names}) or z.testzip()
            or set(names)!=set(manifest['files'])|{'evidence_manifest.json'} or manifest.get('instance_id')!=owner['instance_id']
            or manifest.get('run_id')!=owner['run_id'] or manifest.get('code_sha256')!=expected_code):raise ValueError('CLOSED_ARCHIVE_SCOPE')
        data={}
        for info in z.infolist():
            name=info.filename
            if not name or '\\' in name or ':' in name or '\0' in name or PurePosixPath(name).is_absolute() or any(p in ('','.','..') for p in name.split('/')) or info.is_dir() or info.flag_bits&1 or stat.S_IFMT(info.external_attr>>16) not in (0,stat.S_IFREG):raise ValueError('CLOSED_ARCHIVE_REGULAR_MEMBER')
            if name!='evidence_manifest.json':
                value=z.read(name);wanted=manifest['files'][name]
                if hashlib.sha256(value).hexdigest()!=wanted or hashlib.sha256((folder/'recovered'/name).read_bytes()).hexdigest()!=wanted:raise ValueError('CLOSED_ARCHIVE_MEMBER_HASH')
                data[name]=value
    if (manifest.get('writer_completion_verified') is not True or manifest.get('inventory_stable') is not True or manifest.get('scope')!='COMPLETE_EXISTING_FILES_AFTER_WRITERS_EXIT'
        or manifest.get('job_observation')!=receipt.get('job_observation') or data.get('job_spec.json')!=(folder/'job_spec.json').read_bytes()
        or manifest.get('job_observation')!=decode((folder/'job_final_observation.json').read_bytes())):raise ValueError('CLOSED_ARCHIVE_FINALITY')
    fixture_link_metadata(manifest,data)
    result=completed_job(data,owner,job_observation=receipt['job_observation'],expected_spec_sha256=receipt['job_spec_sha256'])
    return dict(result,files=len(data),zip_sha256=receipt['zip_sha256'],all_existing_raw_verified=True)
