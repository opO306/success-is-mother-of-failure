"""Rebuildable index; immutable references to originals; public roots only.

Registration uses the existing manager's admission checks. Normal selected loads use
the existing signed resume gate (32 bound files), not a scan of the source universe.
No private key, signer, manager instance creation, activation or calculator entrypoint.
"""
import copy
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from experiments.adaptive_execution_real_learning_pilot_v0 import governance
from experiments.adaptive_execution_real_learning_pilot_v0.common import canonical,digest,raw_hash,write_new,verify,Ledger
from experiments.adaptive_execution_real_learning_pilot_a_resume_v1 import evidence
from experiments.evidence_canonicalization_v0.fingerprints import parse_bytes

KEYS=('N','T','start_p','actual_p','goal','physics','numeric','source_sha256')


def read(path): return parse_bytes(Path(path).read_bytes())


def problem_key(request):
    key={k:request[k] for k in KEYS}
    if any(type(key[k]) is not int or key[k]<=0 for k in ('N','T','start_p','actual_p')):
        raise ValueError('INVALID_PROBLEM_KEY')
    if key['goal'] not in ('WALL_MIN','CPU_MIN') or any(not isinstance(key[k],str) or not key[k] for k in ('physics','numeric','source_sha256')):
        raise ValueError('INVALID_PROBLEM_KEY')
    return key


def bucket_key(request): return canonical(problem_key(request)).decode('ascii')


@dataclass(frozen=True)
class Experience:
    metadata_bytes: bytes
    session_bytes: bytes
    profile_bytes: bytes
    root_fingerprint: str
    @property
    def metadata(self): return parse_bytes(self.metadata_bytes)
    @property
    def session(self): return parse_bytes(self.session_bytes)


class _AdmissionReader:
    """Read-only subset of the existing manager; intentionally no key or writer API."""
    _receipt=governance.Manager._receipt
    _profile=governance.Manager._profile
    _check=governance.Manager._check
    def __init__(self,directory,roots):
        self.directory,self.roots=directory,roots
        if not (directory/'events').is_dir(): raise ValueError('MANAGER_LEDGER_REQUIRED')
        self.events=Ledger(directory/'events')
        self.head=directory.parent/'controller_witness/signed_head.json'
    def _stop(self,reason):
        # Existing manager may write STOP; this read-only adapter only reports it.
        raise ValueError('MANAGER_HISTORY_REFUSED:'+reason)


class Tablet:
    def __init__(self,directory,archive_root,roots):
        if not isinstance(roots,governance.Roots) or roots.mode not in ('RESEARCH_ONLY','OFFLINE_CONTRACT_ONLY'):
            raise ValueError('PUBLIC_ROOTS_REQUIRED')
        if roots.inspector==roots.manager: raise ValueError('AUTHORITIES_MUST_DIFFER')
        self.directory=Path(directory); self.archive_root=Path(archive_root).resolve(); self.roots=roots
        self.directory.mkdir(parents=True,exist_ok=True)
        (self.directory/'references').mkdir(exist_ok=True)
        self._index=self._read_index()
        self._build_buckets()

    def _path(self,relative):
        if not isinstance(relative,str) or Path(relative).is_absolute(): raise ValueError('ARCHIVE_PATH_REFUSED')
        path=(self.archive_root/relative).resolve()
        if not path.is_relative_to(self.archive_root): raise ValueError('ARCHIVE_PATH_ESCAPE')
        return path

    def _read_index(self):
        head=self.directory/'index_head.json'
        if not head.exists():
            if any((self.directory/'references').glob('*.json')): raise ValueError('STOP_INDEX_MISSING_REBUILD_REQUIRED')
            self.index_path=None
            return dict(schema='TABLET_V0_INDEX',entries=[],refused=[])
        identifier=read(head).get('id')
        if not isinstance(identifier,str) or len(identifier)!=64 or any(c not in '0123456789abcdef' for c in identifier):
            raise ValueError('STOP_INDEX_HEAD_INTEGRITY')
        self.index_path=self.directory/f'index_{identifier}.json'
        try:
            raw=self.index_path.read_bytes(); obj=parse_bytes(raw)
            if hashlib.sha256(raw).hexdigest()!=identifier or obj.get('schema')!='TABLET_V0_INDEX': raise ValueError('INDEX_INTEGRITY')
            seen=set(); sessions=set()
            for entry in obj['entries']:
                problem_key(entry['key'])
                if entry['profile_id'] in seen: raise ValueError('INDEX_DUPLICATE')
                identity=(entry['session_sha256'],entry['key']['goal'])
                if identity in sessions: raise ValueError('INDEX_DUPLICATE_SESSION')
                seen.add(entry['profile_id'])
                sessions.add(identity)
            return obj
        except (OSError,ValueError,KeyError,TypeError) as error: raise ValueError('STOP_INDEX_INTEGRITY') from error

    def _build_buckets(self):
        self._buckets={}
        for entry in self._index['entries']:
            self._buckets.setdefault(bucket_key(entry['key']),[]).append(entry)

    def _publish(self,index):
        raw=canonical(index); identifier=hashlib.sha256(raw).hexdigest(); path=self.directory/f'index_{identifier}.json'
        if path.exists():
            if path.read_bytes()!=raw: raise ValueError('STOP_INDEX_SNAPSHOT_INTEGRITY')
        else: write_new(path,index)
        pending=self.directory/'index_head.pending'
        write_new(pending,dict(id=identifier))
        os.replace(pending,self.directory/'index_head.json')
        self.index_path=path; self._index=copy.deepcopy(index); self._build_buckets()

    def _derive(self,reference, *, admission=False):
        stage=self._path(reference['stage']); manager_dir=stage.parent/'manager'
        profile_path=manager_dir/'profiles'/f"{reference['profile_id']}.json"
        if not profile_path.resolve().is_relative_to(self.archive_root): raise ValueError('ARCHIVE_PROFILE_ESCAPE')
        session=read(stage/'session.json'); profile=read(profile_path)
        if read(manager_dir/'roots.json')!=self.roots.__dict__: raise ValueError('PROVISIONED_ROOT_MISMATCH')
        if self.roots.mode!='RESEARCH_ONLY': raise ValueError('TEST_EVIDENCE_IMPORT_ADAPTER_NOT_IMPLEMENTED')
        # Admission's deep checks are never repeated over all sources during index search.
        reader=_AdmissionReader(manager_dir,self.roots); history=reader._check()
        if admission: reader._profile(reference['profile_id'])
        body=evidence.check_receipt(self.roots.inspector,profile['receipt'],stage,session,'INSPECT')
        if (profile.get('id')!=reference['profile_id'] or digest({k:v for k,v in profile.items() if k!='id'})!=profile['id']
                or profile.get('mode')!='RESEARCH_ONLY' or profile.get('state')!='VERIFIED'
                or profile.get('rows')!=body['rows'] or profile.get('goal')!=body['goal']
                or profile.get('session_sha256')!=digest(session)):
            raise ValueError('PROFILE_BINDING_REFUSED')
        approval_path=self._path(reference['approval']); event=read(approval_path)
        envelope=event.get('payload',event); verify(self.roots.manager,b'REAL_PILOT_APPROVAL\0',envelope)
        approval=envelope['body']
        if envelope not in [event['payload'] for event in history]: raise ValueError('APPROVAL_NOT_IN_WITNESSED_HISTORY')
        if (approval.get('profile_id')!=profile['id'] or approval.get('mode')!=profile['mode']
                or approval.get('goal')!=profile['goal'] or not approval.get('reason') or not approval.get('decision_id')):
            raise ValueError('MANAGER_APPROVAL_BINDING_REFUSED')
        if session.get('origin')!='OBSERVED_REAL' or session['env'].get('env_id') is None:
            raise ValueError('REAL_SESSION_REQUIRED')
        records=[read(stage/'measurement'/f'{method}_{repeat}.json') for method in ('SERIAL','W6') for repeat in range(5)]
        p0=records[0]['service']['start_decision']['start_p']; actual=records[0]['service']['final_p']
        if any((o['service']['start_decision']['start_p'],o['service']['final_p'])!=(p0,actual) for o in records):
            raise ValueError('MIXED_PRECISION_REFUSED')
        if set(row['method'] for row in profile['rows'])!={'SERIAL','W6'} or any(row.get('repeats')!=5 for row in profile['rows']):
            raise ValueError('FIVE_REPEATS_PER_METHOD_REQUIRED')
        key=problem_key(dict(N=session['N'],T=session['T'],start_p=p0,actual_p=actual,goal=session['goal'],
                            physics=session['env']['contracts']['physics'],numeric=session['env']['contracts']['numeric'],
                            source_sha256=session['code_manifest_sha256']))
        placements={method:next(o['selection']['plan'] for o in records if o['method']==method) for method in ('SERIAL','W6')}
        stats={}
        for method in ('SERIAL','W6'):
            costs=[read(stage/'measurement/request_costs'/f'{method}_{i}.json') for i in range(5)]
            stats[method]={metric:dict(min=min(c[metric] for c in costs),max=max(c[metric] for c in costs)) for metric in ('wall_ns','cpu_ns')}
        metadata=dict(profile_id=profile['id'],session_sha256=digest(session),session_id=session['session_id'],key=key,
                      env_id=session['env']['env_id'],cpu_model=session['env'].get('cpu_model'),mode=profile['mode'],
                      repeats={row['method']:row['repeats'] for row in profile['rows']},rows=profile['rows'],placements=placements,
                      stats=stats,load=[o['observation'].get('host_load_before','UNKNOWN') for o in records],
                      correctness_scope='SIGNED_REAL_SESSION_REPLAY; UNRESOLVED_SHARED_RWFORCE',
                      approval_decision=approval['decision_id'],
                      rollback_history=[dict(index=event['index'],profile_id=event['payload']['body']['profile_id'],
                             goal=event['payload']['body']['goal'],decision_id=event['payload']['body']['decision_id']) for event in history])
        files={str(profile_path.relative_to(self.archive_root).as_posix()):raw_hash(profile_path),
               reference['approval']:raw_hash(approval_path),
               str((manager_dir/'roots.json').relative_to(self.archive_root).as_posix()):raw_hash(manager_dir/'roots.json')}
        files.update({str((stage/n).relative_to(self.archive_root).as_posix()):h for n,h in body['raw_files'].items()})
        for path in [reader.head,*sorted((manager_dir/'events').glob('event_*.json'))]:
            files[path.relative_to(self.archive_root).as_posix()]=raw_hash(path)
        return metadata,session,profile,files

    def register(self,stage,profile_id,approval):
        if not isinstance(profile_id,str) or len(profile_id)!=64 or any(c not in '0123456789abcdef' for c in profile_id):
            raise ValueError('PROFILE_ID_REFUSED')
        descriptor=dict(stage=stage,profile_id=profile_id,approval=approval)
        meta,_,_,files=self._derive(descriptor,admission=True)
        for entry in self._index['entries']:
            if entry['profile_id']==profile_id:
                self.load(entry)
                return copy.deepcopy(entry)
            if (entry['session_sha256'],entry['key']['goal'])==(meta['session_sha256'],meta['key']['goal']):
                raise ValueError('DUPLICATE_SESSION_EVIDENCE_REFUSED')
        capsule=dict(schema='TABLET_V0_REFERENCE',descriptor=descriptor,metadata=meta,files=files,
                     root_fingerprint=digest(self.roots.__dict__))
        identifier=digest(capsule); path=self.directory/'references'/f'{identifier}.json'
        if path.exists():
            if path.read_bytes()!=canonical(capsule): raise ValueError('REFERENCE_INTEGRITY')
        else: write_new(path,capsule)
        entry=dict(profile_id=profile_id,reference_id=identifier,session_sha256=meta['session_sha256'],key=meta['key'],
                   repeats=meta['repeats'],env_id=meta['env_id'],cpu_model=meta['cpu_model'])
        index=copy.deepcopy(self._index); index['entries'].append(entry); self._publish(index)
        return copy.deepcopy(entry)

    def search(self,request,limit=64):
        if type(limit) is not int or not 1<=limit<=64: raise ValueError('MATCH_LIMIT_REFUSED')
        return copy.deepcopy(self._buckets.get(bucket_key(request),[])[:limit])

    def load(self,entry):
        identifier=entry.get('reference_id')
        if not isinstance(identifier,str) or len(identifier)!=64 or any(c not in '0123456789abcdef' for c in identifier):
            raise ValueError('REFERENCE_ID_REFUSED')
        path=self.directory/'references'/f'{identifier}.json'
        if path.stat().st_size>1048576: raise ValueError('REFERENCE_SIZE_REFUSED')
        raw=path.read_bytes(); capsule=parse_bytes(raw)
        if (hashlib.sha256(raw).hexdigest()!=identifier or capsule.get('schema')!='TABLET_V0_REFERENCE'
                or capsule.get('root_fingerprint')!=digest(self.roots.__dict__)):
            raise ValueError('REFERENCE_INTEGRITY_OR_ROOTS')
        for relative,wanted in capsule['files'].items():
            if raw_hash(self._path(relative))!=wanted: raise ValueError('SOURCE_INTEGRITY')
        meta,session,profile,files=self._derive(capsule['descriptor'])
        wanted=dict(profile_id=meta['profile_id'],reference_id=identifier,session_sha256=meta['session_sha256'],key=meta['key'],
                    repeats=meta['repeats'],env_id=meta['env_id'],cpu_model=meta['cpu_model'])
        if meta!=capsule['metadata'] or files!=capsule['files'] or entry!=wanted: raise ValueError('INDEX_METADATA_NOT_AUTHORITY')
        return Experience(canonical(meta),canonical(session),canonical(profile),digest(self.roots.__dict__))

    @classmethod
    def rebuild(cls,directory,archive_root,roots):
        # Bypass the damaged derivative index only; every original reference is revalidated.
        obj=object.__new__(cls); obj.directory=Path(directory); obj.archive_root=Path(archive_root).resolve(); obj.roots=roots
        head=obj.directory/'index_head.json'
        index=dict(schema='TABLET_V0_INDEX',entries=[],refused=[],
                   rebuilt_from_head_sha256=raw_hash(head) if head.exists() else 'MISSING',
                   prior_snapshot_count=len(list(obj.directory.glob('index_*.json')))); seen=set()
        for path in sorted((obj.directory/'references').glob('*.json')):
            try:
                if path.stat().st_size>1048576: raise ValueError('REFERENCE_SIZE_REFUSED')
                capsule=read(path); meta=capsule['metadata']
                entry=dict(profile_id=meta['profile_id'],reference_id=path.stem,session_sha256=meta['session_sha256'],key=meta['key'],
                           repeats=meta['repeats'],env_id=meta['env_id'],cpu_model=meta['cpu_model'])
                obj.load(entry)
                identity=(meta['session_sha256'],meta['key']['goal'])
                if identity in seen: raise ValueError('DUPLICATE_SESSION_EVIDENCE_REFUSED')
                seen.add(identity); index['entries'].append(entry)
            except (ValueError,OSError,KeyError,TypeError) as error:
                index['refused'].append(dict(reference=path.name,reason=str(error)))
        obj._publish(index)
        return copy.deepcopy(index)
