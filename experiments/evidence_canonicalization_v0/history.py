"""Pinned raw/history loader. No trajectory, producer, verdict or signing authority."""
import hashlib
import zipfile
from pathlib import Path
from . import fingerprints as FP
from .policy import HERE,ROOT,raw_hash,check_policy


def read(path): return FP.parse_bytes(Path(path).read_bytes())
def digest(obj): return hashlib.sha256(FP.canonical(obj)).hexdigest()


def check_preservation():
    check_policy()
    active=read(HERE/'code_seal.json')
    pins_path='experiments/evidence_canonicalization_v0/historical_pins.json'
    if raw_hash(ROOT/pins_path)!=active['files'][pins_path]: raise ValueError('HISTORICAL_POLICY_INTEGRITY')
    pins=read(HERE/'historical_pins.json')
    for relative,expected in pins['pins'].items():
        if raw_hash(ROOT/relative)!=expected: raise ValueError('PROVENANCE_UNKNOWN:'+relative)
    base=ROOT/pins['root']; preservation=read(base/'preservation_manifest.json')
    for relative,expected in preservation['files'].items():
        if raw_hash(base/relative)!=expected: raise ValueError('HISTORICAL_ORIGINAL_CHANGED:'+relative)
    # The historical seal continues to describe its ZIP, never the updated checkout.
    old=read(ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/code_seal.json')
    source=ROOT/'docs/active/adaptive_execution_real_learning_pilot_v0/a_source_20261008/source_8d4115e5.zip'
    with zipfile.ZipFile(source) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)!=len(old['files'])+1: raise ValueError('HISTORICAL_SOURCE_ZIP_SCOPE')
        for relative,expected in old['files'].items():
            if hashlib.sha256(z.read(relative)).hexdigest()!=expected: raise ValueError('HISTORICAL_SOURCE_PIN:'+relative)
        seal='experiments/adaptive_execution_real_learning_pilot_v0/code_seal.json'
        if hashlib.sha256(z.read(seal)).hexdigest()!=pins['original_source_sha256']: raise ValueError('HISTORICAL_SOURCE_SEAL')
    return pins


def validate_replay_binding(session,replays,records):
    key=f"{session['N']}/{session['T']}/163"; sh=digest(session)
    if set(replays)!={key}: raise ValueError('REPLAY_REQUEST_MIX')
    replay=replays[key]
    if (replay.get('origin')!='INDEPENDENT_REPLAY' or replay['session_sha256']!=sh
            or replay['code_manifest_sha256']!=session['code_manifest_sha256']): raise ValueError('REPLAY_SESSION_SOURCE_MIX')
    for obj in records:
        if (obj['session_id']!=session['session_id'] or obj['session_sha256']!=sh
                or obj['code_manifest_sha256']!=session['code_manifest_sha256']
                or obj['service']['env_id']!=session['env']['env_id']
                or obj['service']['start_decision']['initial_state_digest']!=FP.legacy_hash(obj['initial_state'])):
            raise ValueError('REPLAY_INITIAL_ENV_BINDING')
    return True


def load_originals():
    pins=check_preservation(); base=ROOT/pins['root']; manifest=read(base/'raw_remote_manifest.json')
    if manifest.get('source_sha256')!=pins['original_source_sha256'] or len(manifest['files'])!=68:
        raise ValueError('ORIGINAL_MANIFEST_SCOPE')
    with zipfile.ZipFile(base/'raw_remote.zip') as z:
        names=z.namelist()
        if len(names)!=69 or len(names)!=len(set(names)) or set(names)!=set(manifest['files'])|{'evidence_manifest.json'}:
            raise ValueError('ORIGINAL_ARCHIVE_SCOPE')
        if z.read('evidence_manifest.json')!=(base/'raw_remote_manifest.json').read_bytes(): raise ValueError('ORIGINAL_ZIP_MANIFEST')
        for relative,expected in manifest['files'].items():
            path=(base/'remote'/relative).resolve()
            if not path.is_relative_to((base/'remote').resolve()): raise ValueError('ORIGINAL_PATH_SCOPE')
            if raw_hash(path)!=expected or hashlib.sha256(z.read(relative)).hexdigest()!=expected:
                raise ValueError('PROVENANCE_UNKNOWN:'+relative)
    root=base/'remote/output_actual/A'; session=read(root/'session.json'); replays=read(root/'replay.json')
    paths=sorted((root/'measurement').glob('*.json')); records=[read(p) for p in paths]
    if len(records)!=10 or session['code_manifest_sha256']!=pins['original_source_sha256']: raise ValueError('ORIGINAL_SESSION_SCOPE')
    original=read(base/'remote/output_actual/report.json'); refusal=read(root/'inspector_refused.json')
    if original['status']!='REAL_LEARNING_FAIL' or refusal!={'verdict':'REFUSED','error':'INITIAL_HASH'}:
        raise ValueError('ORIGINAL_FAILURE_CHANGED')
    validate_replay_binding(session,replays,records)
    return dict(session=session,replays=replays,records=records,record_paths=[str(p.relative_to(ROOT)) for p in paths],
            record_raw_hashes=[raw_hash(p) for p in paths],verified_raw_files=68,original_status=original['status'],
            original_refusal=refusal,origin_root=pins['root'],original_manifest_sha256=raw_hash(base/'raw_remote_manifest.json'),
            original_zip_sha256=raw_hash(base/'raw_remote.zip'),original_source_sha256=pins['original_source_sha256'])
