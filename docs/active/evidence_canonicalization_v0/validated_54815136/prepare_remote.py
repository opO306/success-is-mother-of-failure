import hashlib,json,os,platform,zipfile
from pathlib import Path
from importlib.metadata import version
r=Path('/workspace/evidence_v0_ce36083d_20261008_retry1')
env=dict(x.split(b'=',1) for x in Path('/proc/1/environ').read_bytes().split(b'\0') if b'=' in x)
assert env[b'CONTAINER_ID']==b'54815136','ACTUAL_INSTANCE'
assert platform.python_version().startswith('3.12.'),'PYTHON_VERSION'
versions={n:version(n) for n in ['mpmath','psutil','cryptography','pytest']}
assert versions['mpmath']=='1.3.0','MPMATH_VERSION'
import mpmath.libmp
assert mpmath.libmp.BACKEND=='python','MPMATH_BACKEND'
src=r/'src';src.mkdir(exist_ok=False)
with zipfile.ZipFile(r/'source_ce36083d.zip') as z:
 for name in z.namelist():
  assert not Path(name).is_absolute() and '..' not in Path(name).parts
 z.extractall(src)
seal=json.loads((src/'experiments/evidence_canonicalization_v0/code_seal.json').read_bytes())
for name,expected in seal['files'].items():
 assert hashlib.sha256((src/name).read_bytes()).hexdigest()==expected,name
meta=dict(instance_id=54815136,versions=versions,python=platform.python_version(),platform=platform.platform(),sealed_files=len(seal['files']),mpmath_backend=mpmath.libmp.BACKEND,new_physics_calls=0,gpu_calls=0,remaining_seconds=100)
(r/'preparation.json').write_text(json.dumps(meta,sort_keys=True))
print(json.dumps(meta,sort_keys=True))
