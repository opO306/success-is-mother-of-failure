"""Run the guest source verifiers (v2 and original) as the server does: script on stdin, fake guest folder.
Stdlib + the verifier's own runtime checks only. Not the official gate.
  python -I guest_verify_scenarios.py CLEANUP_DIR ROOT WORK
"""
import hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path

B,ROOT,WORK=(Path(a) for a in sys.argv[1:4])
WORK.mkdir(parents=True,exist_ok=False)
old=json.loads((B/'revision_v12/transport/package_bindings.json').read_bytes())['A']
new=json.loads((B/'revision_v12_4/package_bindings_v2.json').read_bytes())['A']
V2=B/'revision_v12_4/guest_source_verify_v2.py';V1=B/'revision_v12/transport/guest_source_verify.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def args(spec,z=None,i=None):return [sha(z) if z else spec['zip_sha256'],sha(i) if i else spec['inventory_sha256'],spec['code_sha256'],spec['protocol_sha256'],'A']
def run(name,script,zip_path,inv_path,argv):
    g=WORK/name;g.mkdir();shutil.copyfile(zip_path,g/'source.zip');shutil.copyfile(inv_path,g/'inventory.json')
    r=subprocess.run([sys.executable,'-B','-',str(g),*argv],input=Path(script).read_bytes(),capture_output=True,cwd=g)
    text=(r.stdout+r.stderr).decode(errors='replace').strip().splitlines()
    return dict(returncode=r.returncode,last=text[-1] if text else '')
# forged: one unchanged member edited, inventory made consistent (stored zip)
forged=WORK/'forged.zip'
with zipfile.ZipFile(ROOT/new['archive']) as z,zipfile.ZipFile(forged,'x',zipfile.ZIP_STORED) as w:
    for info in z.infolist():
        data=z.read(info.filename)
        w.writestr(info.filename,data+b'\n' if info.filename=='a_numeric/exp.py' else data)
with zipfile.ZipFile(forged) as z:files={i.filename:hashlib.sha256(z.read(i.filename)).hexdigest() for i in z.infolist()};size=sum(i.file_size for i in z.infolist())
inv=dict(json.loads((ROOT/new['inventory']).read_bytes()),files=files,uncompressed_bytes=size,zip_sha256=sha(forged))
forged_inv=WORK/'forged_inventory.json';forged_inv.write_bytes(json.dumps(inv,sort_keys=True,indent=2).encode())
O=(ROOT/old['archive'],ROOT/old['inventory']);N=(ROOT/new['archive'],ROOT/new['inventory'])
cases=[('v2_accepts_revision_2',V2,*N,args(new),'"status": "RAW_SOURCE_VERIFIED"',0),
       ('v2_refuses_original_package',V2,*O,args(old),'APPROVED_REVISION_2_TABLET_CODE_SEAL_REQUIRED',1),
       ('v2_refuses_swapped_upload',V2,*O,args(new),'APPROVED_NEW_PACKAGE_RAW_PINS',1),
       ('v2_refuses_tampered_member',V2,forged,forged_inv,args(new,forged,forged_inv),'REVISION_2_813_PLUS_ONE_ONLY',1),
       ('original_verifier_refuses_revision_2',V1,*N,args(new),'ORIGINAL_TABLET_CODE_SEAL_REQUIRED',1)]
out={}
for name,script,z,i,argv,expect,fail in cases:
    r=run(name,script,z,i,argv);r['expected']=expect;r['as_expected']=(expect in r['last']) and ((r['returncode']!=0)==bool(fail))
    out[name]=r
(WORK/'scenarios.json').write_text(json.dumps(out,indent=1,sort_keys=True))
print(json.dumps({k:[v['as_expected'],v['returncode'],v['last'][-90:]] for k,v in out.items()},indent=1))
print('ALL_AS_EXPECTED',all(v['as_expected'] for v in out.values()))
