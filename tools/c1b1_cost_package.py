"""Extend the proven portable package without altering its original objects."""
import gzip
import hashlib
import io
import json
from pathlib import Path,PurePosixPath
import tarfile


def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(data):return json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def portable_name(name):
    p=PurePosixPath(name)
    if not name or p.is_absolute() or '\\' in name or ':' in name or '..' in p.parts or str(p)!=name:
        raise ValueError('nonportable package name')
    return name


def build(base,additional,destination):
    with tarfile.open(base) as tf:
        content={m.name:tf.extractfile(m).read() for m in tf.getmembers()}
    manifest=json.loads(content.pop('manifest.json'))
    for name,data in additional.items():
        portable_name(name)
        if name in content:raise ValueError('cannot replace original package object')
        content[name]=data
        manifest['objects'][name]=dict(sha256=sha(data),bytes=len(data))
    manifest['cost_extension']='new standalone benchmark and seal only'
    content['manifest.json']=encoded(manifest)
    with Path(destination).open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode='w') as tf:
            for name,data in sorted(content.items()):
                item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o644
                tf.addfile(item,io.BytesIO(data))
    return dict(originals=len(manifest['originals']),objects=len(manifest['objects']),bundle_sha256=sha(Path(destination).read_bytes()))
