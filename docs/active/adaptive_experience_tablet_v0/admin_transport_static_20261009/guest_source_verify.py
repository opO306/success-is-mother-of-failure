"""Remote-only raw ZIP validation before extraction or project import."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_name(name):
    parts = PurePosixPath(name).parts
    if (not name or '\\' in name or ':' in name or name.startswith('/')
            or any(p in ('', '.', '..') for p in name.split('/'))
            or PurePosixPath(name).is_absolute() or not parts):
        raise ValueError('ARCHIVE_PATH_SCOPE:' + name)


if __name__ == '__main__':
    guest, zip_hash, code_hash, protocol_hash = sys.argv[1:]
    base = Path(guest)
    actual_zip_hash = sha((base / 'source.zip').read_bytes())
    print(json.dumps(dict(event='UPLOADED_SOURCE_ZIP_HASH', observed_sha256=actual_zip_hash,
                          expected_sha256=zip_hash)), file=sys.stderr, flush=True)
    if actual_zip_hash != zip_hash:
        raise ValueError('SOURCE_ZIP_HASH')
    seal_name = 'experiments/adaptive_experience_tablet_v0/code_seal.json'
    with zipfile.ZipFile(base / 'source.zip') as z:
        names = z.namelist()
        if len(names) != 813 or len(names) != len(set(names)) or z.testzip() is not None:
            raise ValueError('SOURCE_ZIP_STRUCTURE')
        if sum(i.file_size for i in z.infolist()) != 48533194:
            raise ValueError('SOURCE_ZIP_UNCOMPRESSED_SIZE')
        for item in z.infolist():
            safe_name(item.filename)
            if item.is_dir() or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('ARCHIVE_NON_REGULAR_MEMBER')
        seal_raw = z.read(seal_name)
        if sha(seal_raw) != code_hash:
            raise ValueError('SOURCE_CODE_SEAL_HASH')
        seal = json.loads(seal_raw)
        if len(seal['files']) != 812 or set(names) != set(seal['files']) | {seal_name}:
            raise ValueError('SOURCE_ZIP_EXACT_FILE_SET')
        for name, wanted in seal['files'].items():
            if sha(z.read(name)) != wanted:
                raise ValueError('SOURCE_RAW_HASH:' + name)
        if sha(z.read('experiments/adaptive_experience_tablet_v0/protocol.json')) != protocol_hash:
            raise ValueError('PROTOCOL_HASH')
        source = base / 'source'
        source.mkdir(exist_ok=False)
        # No extractall: each member is validated, exclusive, and retains its raw bytes.
        for name in names:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as f:
                f.write(z.read(name))
    for relative in ('protocol_seal.json', 'preservation_manifest.json', 'code_seal.json'):
        manifest = json.loads((source / 'experiments/adaptive_experience_tablet_v0' / relative).read_bytes())
        for name, wanted in manifest['files'].items():
            safe_name(name)
            if sha((source / name).read_bytes()) != wanted:
                raise ValueError('EXTRACTED_RAW_HASH:' + name)
    import importlib.metadata
    import mpmath
    versions = {k: importlib.metadata.version(k) for k in ('mpmath', 'psutil', 'cryptography', 'pytest')}
    if sys.version_info[:2] != (3, 12) or versions['mpmath'] != '1.3.0' or mpmath.libmp.BACKEND != 'python':
        raise ValueError('APPROVED_RUNTIME_DRIFT')
    print(json.dumps(dict(status='RAW_SOURCE_VERIFIED', entries=813, versions=versions,
                         python=sys.version, mpmath_backend=mpmath.libmp.BACKEND)))
