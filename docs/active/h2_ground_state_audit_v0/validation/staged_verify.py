"""Check new physically sealed source/evidence bytes survive the Git index."""
import hashlib
import json
import subprocess
from pathlib import Path

root=Path.cwd()
new_roots=('electronic_pilot/ground_state_audit_v0/','tests/h2_ground_state_audit_v0/',
           'docs/active/h2_ground_state_audit_v0/')
paths=subprocess.check_output(['git','diff','--cached','--name-only','-z']).decode('utf-8').split('\0')
paths=[p for p in paths if p and p.startswith(new_roots)]
batch=''.join(':'+p+'\n' for p in paths).encode('utf-8')
output=subprocess.check_output(['git','cat-file','--batch'],input=batch)
offset=0;checked={}
for path in paths:
    end=output.index(b'\n',offset)
    header=output[offset:end].split()
    assert header[1]==b'blob',header
    size=int(header[2]);start=end+1;contents=output[start:start+size];offset=start+size+1
    local=(root/path).read_bytes()
    assert contents==local,'STAGED BYTE DRIFT: '+path
    checked[path]=hashlib.sha256(contents).hexdigest()
assert offset==len(output)
destination=root/'docs/active/h2_ground_state_audit_v0/validation/staged_verification.json'
assert not destination.exists()
destination.write_text(json.dumps({'status':'STAGED_BYTE_IDENTICAL','checked_files':len(checked),
                      'sha256':checked,'not_certified':True},indent=2)+'\n',encoding='utf-8')
print('STAGED BYTE IDENTICAL',len(checked),'new files')
