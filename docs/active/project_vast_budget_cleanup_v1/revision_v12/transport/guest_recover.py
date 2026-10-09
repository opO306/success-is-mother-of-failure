"""Remote snapshot packer; completed writers and byte-valid partials are distinct."""
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile


def sha(data):return hashlib.sha256(data).hexdigest()
def capture(root,role):
    data={};links={}
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if rel.parts[0]=='.recovery' or rel.as_posix() in ('source.zip','admin.zip'):continue
        if rel.parts[0]=='source' and (len(rel.parts)<2 or rel.parts[1]!='.simulated'):continue
        if path.is_symlink():
            if role!='ADMIN_TESTS' or not (rel.parts[0] in ('v11_tmp','v12_tmp','process_cases') or rel.parts[:2]==('source','.simulated')):raise ValueError('REMOTE_EVIDENCE_SYMLINK')
            # Retain TEST_ONLY fixture link contents as manifest metadata; never follow them.
            links[rel.as_posix()]=os.readlink(path);continue
        if path.is_file():
            before=path.stat();raw=path.read_bytes();after=path.stat()
            if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise ValueError('REMOTE_WRITER_DURING_CAPTURE')
            data[rel.as_posix()]=raw
    return data,links

if __name__=='__main__':
    guest,instance,code,run_id,artifact_id=sys.argv[1:]
    root=Path(guest);sys.path.insert(0,str(root))
    ids=[v.split(b'=',1)[1].decode('ascii') for v in Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'CONTAINER_ID=')]
    if ids!=[instance]:raise ValueError('RECOVERY_ACTUAL_INSTANCE_MISMATCH')
    if not artifact_id.isalnum():raise ValueError('RECOVERY_ARTIFACT_ID')
    if (root/'job_spec.json').is_file():
        from guest_job import observe
        observation=observe(root/'job',instance,run_id+'_gate')
    else:observation=dict(state='NOT_STARTED',writer_completion_verified=False,instance_id=int(instance),run_id=run_id)
    role=json.loads((root/'job_spec.json').read_bytes()).get('job_role') if (root/'job_spec.json').is_file() else None
    data,links=capture(root,role);second,second_links=capture(root,role)
    hashes={name:sha(raw) for name,raw in data.items()}
    if hashes!={name:sha(raw) for name,raw in second.items()} or links!=second_links:raise ValueError('REMOTE_FILE_SET_OR_BYTES_UNSTABLE')
    final=observation.get('writer_completion_verified') is True
    missing=[n for n in ('gate_exit.json','output/status.json','output/junit.xml','output/physics_guard.json','output/benchmark.json') if n not in data]
    manifest=dict(schema='V12_FINAL_OR_PARTIAL_EVIDENCE',instance_id=int(instance),code_sha256=code,run_id=run_id,files=hashes,
                  writer_completion_verified=final,job_observation=observation,scope='COMPLETE_EXISTING_FILES_AFTER_WRITERS_EXIT' if final else 'PARTIAL_SNAPSHOT_ONLY',
                  absent_success_files=missing,inventory_stable=True,admin_fixture_symlink_metadata=links)
    raw=json.dumps(manifest,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    folder=root/'.recovery'/artifact_id;folder.mkdir(parents=True,exist_ok=False)
    tmp=folder/'evidence.zip.pending'
    with zipfile.ZipFile(tmp,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,value in data.items():z.writestr(name,value)
        z.writestr('evidence_manifest.json',raw)
    with tmp.open('rb') as f:os.fsync(f.fileno())
    os.replace(tmp,folder/'evidence.zip')
    print(json.dumps(dict(files=len(data),sha256=sha((folder/'evidence.zip').read_bytes()),remote_archive=str(folder/'evidence.zip'),writer_completion_verified=final,job_observation=observation)))
