"""Remote-only evidence packer derived from successful A-resume recovery."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile


if __name__ == '__main__':
    guest, instance, code, run_id = sys.argv[1:]
    root = Path(guest)
    files = {}
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if rel.parts[0] == 'source' or rel.as_posix() in ('source.zip', 'evidence.zip', 'evidence_manifest.json'):
            continue
        if path.is_symlink():
            raise ValueError('REMOTE_EVIDENCE_SYMLINK')
        if path.is_file():
            files[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = dict(schema='TABLET_RAW_EVIDENCE', instance_id=int(instance), code_sha256=code,
                    run_id=run_id, files=files)
    raw = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    with (root / 'evidence_manifest.json').open('xb') as f:
        f.write(raw)
    with zipfile.ZipFile(root / 'evidence.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            z.write(root / rel, rel)
        z.writestr('evidence_manifest.json', raw)
    print(json.dumps(dict(files=len(files), sha256=hashlib.sha256((root / 'evidence.zip').read_bytes()).hexdigest())))
