"""Remote-only exact package A814/B10 verification; raw pins before extraction."""
import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile


def sha(data): return hashlib.sha256(data).hexdigest()
def read(data):
    def pairs(items):
        out = {}
        for k,v in items:
            if k in out: raise ValueError('DUPLICATE_JSON_KEY')
            out[k] = v
        return out
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def safe(name):
    if (not isinstance(name,str) or not name or '\\' in name or ':' in name or '\x00' in name
            or name.startswith('/') or any(p in ('','.','..') for p in name.split('/'))
            or str(PurePosixPath(name)) != name): raise ValueError('PATH_SCOPE')


if __name__ == '__main__':
    guest, zip_hash, inventory_hash, code_hash, proto_hash, kind = sys.argv[1:]
    base = Path(guest); inv_raw = (base/'inventory.json').read_bytes()
    if sha(inv_raw) != inventory_hash or sha((base/'source.zip').read_bytes()) != zip_hash:
        raise ValueError('APPROVED_NEW_PACKAGE_RAW_PINS')
    inventory = read(inv_raw)
    count = 814 if kind == 'A' else 10 if kind == 'B' else 0
    if count == 0 or inventory['entries'] != count or inventory['zip_sha256'] != zip_hash:
        raise ValueError('APPROVED_EXACT_KIND_ENTRIES')
    with zipfile.ZipFile(base/'source.zip') as z:
        names = z.namelist(); files = inventory['files']
        if (len(names) != count or len(set(names)) != count or len({n.casefold() for n in names}) != count
                or set(names) != set(files) or sum(i.file_size for i in z.infolist()) != inventory['uncompressed_bytes']):
            raise ValueError('EXACT_NEW_PACKAGE_FILE_SET')
        for info in z.infolist():
            safe(info.filename)
            if info.is_dir() or info.flag_bits & 1 or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError('REGULAR_UNENCRYPTED_MEMBERS_ONLY')
        for name,wanted in files.items():
            if sha(z.read(name)) != wanted: raise ValueError('MEMBER_CRC_OR_RAW_HASH:' + name)
        if kind == 'A':
            seal_name = 'experiments/adaptive_experience_tablet_v0/code_seal.json'
            proto_name = 'experiments/adaptive_experience_tablet_v0/protocol.json'
            extra = 'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'
            if code_hash != '18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09':
                raise ValueError('ORIGINAL_TABLET_CODE_SEAL_REQUIRED')
            if sha(z.read(extra)) != 'ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60':
                raise ValueError('EXACT_EXISTING_EXTRA_SEAL')
            manifest = read(z.read(seal_name))
            required = dict(manifest['files'], **{seal_name:code_hash, extra:sha(z.read(extra))})
            if len(manifest['files']) != 812 or required != files: raise ValueError('ORIGINAL_813_PLUS_ONE_ONLY')
        else:
            seal_name = 'admin_policy/source_seal.json'; proto_name = 'admin_policy/protocol.json'
            manifest = read(z.read(seal_name))
            if manifest['expected_tests'] != 95 or dict(manifest['files'], **{seal_name:code_hash}) != files:
                raise ValueError('EXACT_SEPARATE_95_HARNESS')
        if sha(z.read(seal_name)) != code_hash or sha(z.read(proto_name)) != proto_hash:
            raise ValueError('CODE_PROTOCOL_PINS')
        source = base/'source'; source.mkdir(exist_ok=False)
        for name in names:
            path = source/name; path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f: f.write(z.read(name))
    if kind == 'A':
        for relative in ('protocol_seal.json','preservation_manifest.json','code_seal.json'):
            manifest = read((source/'experiments/adaptive_experience_tablet_v0'/relative).read_bytes())
            for name,wanted in manifest['files'].items():
                safe(name)
                if sha((source/name).read_bytes()) != wanted: raise ValueError('EXTRACTED_ORIGINAL_SEAL_HASH')
    modules = ('mpmath','psutil','cryptography','pytest') if kind == 'A' else ('psutil','pytest')
    versions = {n:importlib.metadata.version(n) for n in modules}
    if sys.version_info[:2] != (3,12): raise ValueError('PYTHON_312_REQUIRED')
    backend = None
    if kind == 'A':
        import mpmath
        backend = mpmath.libmp.BACKEND
        if versions['mpmath'] != '1.3.0' or backend != 'python': raise ValueError('ORIGINAL_RUNTIME_BOUNDARY')
    print(json.dumps(dict(status='RAW_SOURCE_VERIFIED', package_kind=kind, entries=count,
          zip_sha256=zip_hash, inventory_sha256=inventory_hash, versions=versions, python=sys.version,
          mpmath_backend=backend)))
