"""Exact owned instance lifecycle; CLI is injectable, no automatic physics retry; administrative revalidation governed by V5 amendment."""
import hashlib
import json
import subprocess
import time
import os
from pathlib import Path


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(json.dumps(obj, sort_keys=True, indent=2, allow_nan=False).encode())


def save_atomic(path,obj):
    """Publish one immutable owner only after bytes and fsync are complete."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    pending=path.with_name(path.name+'.pending')
    with pending.open('xb') as f:
        f.write(json.dumps(obj,sort_keys=True,allow_nan=False).encode());f.flush();os.fsync(f.fileno())
    try:os.link(pending,path)  # atomic no-overwrite on NTFS and Linux
    finally:pending.unlink()


def decode(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('DUPLICATE_PROVIDER_KEY')
            out[k] = v
        return out
    def invalid(value):
        raise ValueError('NONFINITE_PROVIDER_JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


class Provider:
    def __init__(self, cli, out, runner=subprocess.run):
        self.cli, self.out, self.runner = str(cli), Path(out), runner
        self.out.mkdir(parents=True, exist_ok=True)
        self.index = len(list(self.out.glob('*.stdout')))

    def call(self, *args, json_result=True, timeout=15):
        self.index += 1
        prefix = self.out / ('%04d' % self.index)
        save(prefix.with_suffix('.command.json'), dict(argv=[self.cli, '--raw', '--retry', '1', *map(str, args)]))
        try:
            result = self.runner([self.cli, '--raw', '--retry', '1', *map(str, args)],
                                 capture_output=True, timeout=timeout)
        except BaseException as error:
            save(prefix.with_suffix('.exception.json'), dict(error=repr(error)))
            raise
        prefix.with_suffix('.stdout').write_bytes(result.stdout)
        prefix.with_suffix('.stderr').write_bytes(result.stderr)
        save(prefix.with_suffix('.exit.json'), dict(returncode=result.returncode))
        if result.returncode:
            raise OSError('PROVIDER_COMMAND_FAILED')
        return decode(result.stdout) if json_result else result.stdout

    def instances(self, timeout=15):
        data = self.call('show', 'instances', timeout=timeout)
        if not isinstance(data, list) or any(not isinstance(x, dict) or type(x.get('id')) is not int for x in data):
            raise ValueError('INSTANCE_LIST_REQUIRED')
        if len({x['id'] for x in data}) != len(data):
            raise ValueError('DUPLICATE_INSTANCE')
        return data

    def volumes(self, timeout=15):
        data = self.call('show', 'volumes', timeout=timeout)
        if not isinstance(data, list):
            raise ValueError('VOLUME_LIST_REQUIRED')
        return data

    def charges(self):
        pages = []
        token = None
        seen = set()
        for _ in range(20):
            args = ['show', 'invoices-v1', '--charges', '--start-date', '2026-10-09',
                    '--end-date', '2026-10-10', '--limit', '100', '--format', 'tree', '--verbose']
            if token:
                args += ['--next-token', token]
            page = self.call(*args)
            if not isinstance(page, dict) or 'next_token' not in page:
                raise ValueError('BILLING_PAGE_REQUIRED')
            pages.append(page)
            token = page['next_token']
            if token is None:
                return pages
            if not isinstance(token, str) or token in seen:
                raise ValueError('BILLING_PAGINATION_CYCLE')
            seen.add(token)
        raise ValueError('BILLING_PAGINATION_LIMIT')


def identity(record, owner):
    country = record.get('country') or str(record.get('geolocation', '')).rsplit(',', 1)[-1].strip()
    if (type(record.get('id')) is not int or record['id'] != owner['instance_id']
            or record.get('machine_id') != owner['machine_id'] or country != owner['country']
            or record.get('label') != owner['label']):
        raise ValueError('OWNED_INSTANCE_IDENTITY_MISMATCH')
    return record


def stop_owned(provider, owner, *, now=time.monotonic, sleep=time.sleep, seconds=120):
    if owner.get('start_request_may_be_queued') is True:
        from queued_stop import stop_queued_owned
        return stop_queued_owned(provider,owner,now=now,sleep=sleep,seconds=seconds)
    start = now()
    attempts = 0
    errors = []
    while now()-start < seconds:
        try:
            record = identity(provider.call('show', 'instance', owner['instance_id'],timeout=max(.1,min(15,seconds-(now()-start)))), owner)
            if record.get('actual_status') in ('exited', 'stopped') and record.get('intended_status') == 'stopped':
                return dict(status='STOP_CONFIRMED', instance_id=owner['instance_id'], attempts=attempts, errors=errors)
        except Exception as error:
            # The exact ID comes from the saved creation/owner binding. Observation
            # loss must never prevent an already-authorized stop of that ID.
            errors.append(repr(error))
        if attempts < 3:
            if now()-start>=seconds:break
            attempts += 1
            try:
                provider.call('stop', 'instance', owner['instance_id'], json_result=False,timeout=max(.1,min(15,seconds-(now()-start))))
            except Exception as error:
                errors.append(repr(error))
        sleep(min(4, max(0, seconds-(now()-start))))
    return dict(status='STOP_UNCONFIRMED', instance_id=owner['instance_id'], attempts=attempts, errors=errors)


def destroy_owned(provider, owner, recovery, stopped, baseline_volumes, *, now=time.monotonic, sleep=time.sleep):
    if (recovery.get('verified') is not True or recovery.get('instance_id') != owner['instance_id']
            or stopped.get('status') != 'STOP_CONFIRMED' or stopped.get('instance_id') != owner['instance_id']):
        raise ValueError('DESTROY_REQUIRES_LOCAL_RAW_AND_ACTUAL_STOP')
    if recovery.get('basis')!='NO_REMOTE_PROJECT_WRITES' and (recovery.get('writer_completion_verified') is not True or recovery.get('final_files_verified') is not True):raise ValueError('DESTROY_REQUIRES_TERMINAL_WRITER_AND_FINAL_FILES')
    current = identity(provider.call('show', 'instance', owner['instance_id']), owner)
    if current.get('actual_status') not in ('exited', 'stopped') or current.get('intended_status') != 'stopped':
        raise ValueError('FRESH_ACTUAL_STOP_REQUIRED_BEFORE_DESTROY')
    start = now()
    attempts = 0
    errors = []
    while now()-start < 100:
        # Fresh list observation after every destroy request, including timeout.
        if attempts < 3:
            attempts += 1
            try:
                provider.call('destroy', 'instance', owner['instance_id'], '--yes', json_result=False,timeout=max(.1,min(15,100-(now()-start))))
            except Exception as error:
                errors.append(repr(error))
        try:
            records = provider.instances(timeout=max(.1,min(15,100-(now()-start))))
            remaining = [x for x in records if x['id'] == owner['instance_id']]
            if not remaining:
                if now()-start>=100:break
                volumes = provider.volumes(timeout=max(.1,min(15,100-(now()-start))))
                if volumes != baseline_volumes:
                    raise ValueError('RESIDUAL_VOLUME_CHANGE')
                return dict(status='DESTROY_CONFIRMED', instance_id=owner['instance_id'], attempts=attempts,
                            errors=errors, raw_verified=True, volumes_unchanged=True,
                            remaining_instance_ids=[x['id'] for x in records])
            identity(remaining[0], owner)
        except ValueError:
            raise
        except Exception as error:
            errors.append(repr(error))
        sleep(min(4,max(0,100-(now()-start))))
    return dict(status='DESTROY_UNCONFIRMED', instance_id=owner['instance_id'], attempts=attempts, errors=errors)


def verified_recovery(out, owner, remote_writes_started):
    out = Path(out)
    proof = out/'recovery_verified.json'
    if not remote_writes_started:
        return dict(verified=True, instance_id=owner['instance_id'], basis='NO_REMOTE_PROJECT_WRITES', files=0)
    if not proof.is_file():
        raise ValueError('IMPORTANT_REMOTE_RAW_UNRECOVERED')
    receipt = decode(proof.read_bytes())
    archive = out/'evidence.zip'
    if receipt.get('all_raw_hashes_match') is not True or hashlib.sha256(archive.read_bytes()).hexdigest() != receipt.get('zip_sha256'):
        raise ValueError('RECOVERY_RECEIPT_OR_ZIP_DRIFT')
    import zipfile
    with zipfile.ZipFile(archive) as z:
        manifest = decode(z.read('evidence_manifest.json'))
        if (manifest.get('instance_id') != owner['instance_id'] or manifest.get('run_id')!=owner['run_id']
            or len(z.namelist())!=len(set(z.namelist())) or len(z.namelist())!=len({n.casefold() for n in z.namelist()})
            or z.testzip() or set(z.namelist()) != set(manifest['files'])|{'evidence_manifest.json'}):
            raise ValueError('RECOVERY_OWNER_OR_FILE_SET')
        for name, wanted in manifest['files'].items():
            from pathlib import PurePosixPath
            if (not name or '\\' in name or ':' in name or '\x00' in name or PurePosixPath(name).is_absolute()
                    or any(part in ('', '.', '..') for part in name.split('/'))):
                raise ValueError('LOCAL_RECOVERY_MEMBER_PATH')
            if (hashlib.sha256(z.read(name)).hexdigest() != wanted
                    or hashlib.sha256((out/'recovered'/name).read_bytes()).hexdigest() != wanted):
                raise ValueError('LOCAL_RECOVERY_MEMBER_DRIFT')
    from terminal_proof import require_terminal
    bindings=decode((Path(__file__).resolve().parent/'transport/package_bindings.json').read_bytes())
    scope=owner.get('test_scope')
    if scope=='A320_THEN_ORIGINAL_SEARCH_BENCHMARK':kind='A'
    elif scope=='ADMIN_MOCKS_THEN_B95':kind='B'
    else:raise ValueError('IMPORTANT_FINAL_PACKAGE_SCOPE_REQUIRED')
    with zipfile.ZipFile(archive) as z:final_bytes={name:z.read(name) for name in manifest['files']}
    from job_proof import completed_job,fixture_link_metadata
    fixture_link_metadata(manifest,final_bytes)
    if (final_bytes.get('job_spec.json')!=(out/'job_spec.json').read_bytes()
        or manifest.get('job_observation')!=decode((out/'job_final_observation.json').read_bytes())):raise ValueError('LOCAL_JOB_INTENT_AND_FINAL_OBSERVATION_BINDING')
    job=completed_job(final_bytes,owner,job_observation=receipt.get('job_observation',{}),expected_spec_sha256=receipt.get('job_spec_sha256'))
    if (manifest.get('writer_completion_verified') is not True or manifest.get('inventory_stable') is not True
        or manifest.get('scope')!='COMPLETE_EXISTING_FILES_AFTER_WRITERS_EXIT' or manifest.get('job_observation')!=receipt.get('job_observation')):raise ValueError('FINAL_REMOTE_INVENTORY_OR_JOB_PROOF')
    # Failure recovery proves the closed existing file set, never the normal PASS gate.
    if job['outcome']=='EXITED_FAILURE':
        absent=[n for n in ('gate_exit.json','output/status.json','output/junit.xml','output/physics_guard.json','output/benchmark.json') if n not in final_bytes]
        if manifest.get('absent_success_files')!=absent:raise ValueError('FAILURE_MISSING_FILE_CLASSIFICATION')
        return dict(verified=True,instance_id=owner['instance_id'],files=len(manifest['files']),zip_sha256=receipt['zip_sha256'],
                    basis='CLOSED_FAILED_JOB_ALL_EXISTING_RAW_RECOVERED_NOT_PASS',writer_completion_verified=True,final_files_verified=True,
                    execution_passed=False,absent_success_files=absent,job_id=job['job_id'])
    ids=decode((Path(__file__).resolve().parent/'transport/case_inventory_320.json').read_bytes())['ids'] if kind=='A' else None
    terminal=require_terminal(final_bytes,writer_completion_verified=receipt.get('writer_completion_verified'),spec=bindings[kind],original_case_ids=ids)
    return dict(verified=True, instance_id=owner['instance_id'], files=len(manifest['files']),
                zip_sha256=receipt['zip_sha256'], basis='TERMINAL_WRITER_EXACT_FINAL_FILES_AND_RAW_SHA256',writer_completion_verified=terminal['writer_completion_verified'],final_files_verified=terminal['final_files_verified'])


def verify_admin(out,owner):
    out=Path(out)
    if not (out/'admin_started.json').exists():
        if (out/'admin_io/tests.command.json').exists():raise ValueError('ADMIN_EXECUTION_MARKER_MISSING_PRESERVE')
        return dict(verified=True,basis='ADMIN_TEST_COMMAND_NOT_ISSUED')
    if owner.get('v12_owned_job') is True:
        from job_proof import closed_archive
        for name,suffix in [('admin_closed_originals.json','_admin'),('probe_closed_originals.json','_disconnect_probe')]:
            if name=='probe_closed_originals.json' and not (out/'ssh_disconnect_probe_started.json').exists():continue
            descriptor=decode((out/name).read_bytes())
            expected=dict(owner,run_id=owner['run_id']+suffix)
            bound=descriptor['owner']
            if any(bound.get(k)!=expected[k] for k in ('instance_id','machine_id','run_id')):raise ValueError('ADMIN_OR_PROBE_CLOSED_OWNER_DRIFT')
            expected_folder=out/('admin_job_io' if name=='admin_closed_originals.json' else 'ssh_disconnect_probe')
            if Path(descriptor['folder']).resolve()!=expected_folder.resolve():raise ValueError('ADMIN_OR_PROBE_LOCAL_FOLDER_SCOPE')
            expected_code=decode((Path(__file__).parent/'operational_seal.json').read_bytes())['files']['admin_payload.zip']
            if descriptor['code_sha256']!=expected_code:raise ValueError('ADMIN_OR_PROBE_SOURCE_BINDING')
            role=decode((expected_folder/'job_spec.json').read_bytes()).get('job_role')
            if role!=('ADMIN_TESTS' if name=='admin_closed_originals.json' else 'ADMIN_PROBE'):raise ValueError('ADMIN_OR_PROBE_JOB_ROLE')
            checked=closed_archive(descriptor['folder'],bound,descriptor['code_sha256'])
            if checked!=descriptor['proof']:raise ValueError('ADMIN_OR_PROBE_COMPLETE_RAW_PROOF_DRIFT')
        if decode((out/'admin_closed_originals.json').read_bytes())['proof']['outcome']=='EXITED_FAILURE':
            return dict(verified=True,passed=False,basis='CLOSED_ADMIN_FAILURE_ALL_EXISTING_RAW_NOT_PASS')
    proof=decode((out/'admin_verified.json').read_bytes())
    required={'stdout.log','stderr.log','junit.xml','admin_result.json'}
    if proof.get('instance_id')!=owner['instance_id'] or set(proof.get('raw_files',{}))!=required:
        raise ValueError('ADMIN_RAW_PROOF_OWNER_AND_FILE_SET')
    for name,wanted in proof['raw_files'].items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=wanted:raise ValueError('ADMIN_LOCAL_RAW_DRIFT')
    result=decode((out/'admin_result.json').read_bytes())
    if result.get('instance_id')!=owner['instance_id'] or not result.get('source_zip_sha256'):
        raise ValueError('ADMIN_RAW_RESULT_OWNER')
    import xml.etree.ElementTree as ET
    cases=ET.parse(out/'junit.xml').getroot().findall('.//testcase')
    if len(cases)!=proof.get('tests'):raise ValueError('ADMIN_JUNIT_COUNT_DRIFT')
    # Failed cases remain recoverable raw evidence; this function never promotes PASS.
    return dict(verified=True,files=len(required),basis='ADMIN_RAW_LOCAL_HASHES',passed=proof.get('passed') is True)


def verify_startup(out,owner):
    out=Path(out)
    proof=decode((out/'startup_verified.json').read_bytes())
    if proof.get('instance_id')!=owner['instance_id'] or not isinstance(proof.get('files'),dict):
        raise ValueError('STARTUP_RAW_OWNER_PROOF')
    if set(proof['files'])!={'runtime_setup.log','runtime_ready'}:raise ValueError('STARTUP_FINAL_COMPLETION_NOT_PROVEN_PRESERVE_RAW')
    for name,wanted in proof['files'].items():
        if hashlib.sha256((out/'startup_raw'/name).read_bytes()).hexdigest()!=wanted:raise ValueError('STARTUP_RAW_HASH')
    result=decode((out/'startup_result.json').read_bytes())
    if (result.get('instance_id')!=owner['instance_id'] or result.get('files')!=proof['files']
        or hashlib.sha256((out/'startup_result.json').read_bytes()).hexdigest()!=proof.get('result_sha256')):
        raise ValueError('STARTUP_RAW_RESULT_BINDING')
    return dict(verified=True,instance_id=owner['instance_id'],files=len(proof['files']),basis='STARTUP_LOG_CLOSED_BEFORE_READY_MARKER')
