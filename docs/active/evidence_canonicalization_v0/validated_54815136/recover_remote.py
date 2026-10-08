import hashlib,json,zipfile
from pathlib import Path
r=Path('/workspace/evidence_v0_ce36083d_20261008_retry1');files={}
for base in [r/'out']:
 if base.exists():
  for p in sorted(base.rglob('*')):
   if p.is_file():files[p.relative_to(r).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['launch.log','preparation.json','authorization.json','armed.json']:
 p=r/name
 if p.exists():files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
with zipfile.ZipFile(r/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
 for name in files:z.write(r/name,name)
(r/'evidence_manifest.json').write_text(json.dumps(dict(files=files),sort_keys=True))
print('RECOVERY_FILES',len(files))
