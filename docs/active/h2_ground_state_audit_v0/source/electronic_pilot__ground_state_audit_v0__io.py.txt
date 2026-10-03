"""Portable byte bindings and write-once evidence."""
import hashlib
import json
import os
from pathlib import Path
import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def npy(path, value):
    with Path(path).open('xb') as stream:
        np.save(stream, value, allow_pickle=False)


def array_meta(path):
    value = np.load(path, allow_pickle=False)
    return dict(shape=list(value.shape), dtype=value.dtype.str,
                byte_order='little' if value.dtype.byteorder in ('<', '=') and np.little_endian else 'big',
                file_sha256=sha(path), array_sha256=hashlib.sha256(value.tobytes(order='C')).hexdigest(),
                array_nbytes=value.nbytes)


def binding_path(key, root, main):
    kind, relative = key.split(':', 1)
    if kind == 'worktree':
        return Path(root) / relative
    if kind == 'main':
        return Path(main) / relative
    raise ValueError('unsupported binding '+key)


def verify(bindings, root, main):
    drift = [key for key, expected in bindings.items()
             if not binding_path(key, root, main).is_file() or sha(binding_path(key, root, main)) != expected]
    if drift:
        raise ValueError('BYTE DRIFT: '+repr(drift))
    return len(bindings)


def runtime():
    import platform
    import scipy
    import contextlib
    import io
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        np.show_config()
        scipy.show_config()
    return dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                platform=platform.platform(), libraries=stream.getvalue(),
                threads={x: os.environ.get(x) for x in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})
