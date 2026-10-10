"""Build A package revision 2: the sealed tablet_814.zip with exactly one test-order fix (2 members change).

Approved change (designer decision 2026-10-10, relayed): in tests/test_adaptive_experience_tablet_v0.py,
test_only_selected_reference_files_are_opened builds request() BEFORE Path.read_bytes is captured. The assertion
is unchanged. The tablet code_seal.json changes only in that test file's 64-hex hash. Nothing else changes.

Standard library only; no project import. Deterministic: same original zip + zlib 1.3.1 -> same output bytes.
  python -I build_package_v2.py ORIGINAL_ZIP OUT_DIR
Writes OUT_DIR/{tablet_814_v2.zip,inventory.json,revision_manifest.json}; refuses to overwrite.
"""
import hashlib,json,sys,zipfile,zlib
from pathlib import Path

ORIGINAL_ZIP_SHA256='be06c9a7b8cc31c1e414b03f85485a9bb5e9e69226e34f1917553fac2673f4ff'
ORIGINAL_INVENTORY_SHA256='0bb1631ffb6adaaea69eb3c7b15b07a29b19429a8b98b2cfe9c7e5086b4d22b3'
TEST='tests/test_adaptive_experience_tablet_v0.py'
SEAL='experiments/adaptive_experience_tablet_v0/code_seal.json'
ORIGINAL_TEST_SHA256='41b7c97f031ad8f305b94463cf2a90f8feef3181c1127c4430a32acc328add67'
ORIGINAL_SEAL_SHA256='18a76f0e2ea466b7a13e2066367cfc8d52ba6085be66045dacc062490ef08d09'
ARCHIVE='docs/active/project_vast_budget_cleanup_v1/revision_v12_4/package_A_v2/tablet_814_v2.zip'
OLD=(b"def test_only_selected_reference_files_are_opened(archive,monkeypatch):\n"
     b"    tablet,_,_,_=archive; original=Path.read_bytes; accessed=[]\n"
     b"    def capture(path): accessed.append(path); return original(path)\n"
     b"    monkeypatch.setattr(Path,'read_bytes',capture)\n"
     b"    hits=tablet.search(request())\n"
     b"    assert len(hits)==1 and accessed==[]\n")
NEW=(b"def test_only_selected_reference_files_are_opened(archive,monkeypatch):\n"
     b"    tablet,_,_,_=archive; query=request(); original=Path.read_bytes; accessed=[]\n"
     b"    def capture(path): accessed.append(path); return original(path)\n"
     b"    monkeypatch.setattr(Path,'read_bytes',capture)\n"
     b"    hits=tablet.search(query)\n"
     b"    assert len(hits)==1 and accessed==[]\n")
INFO_FIELDS=('filename','date_time','compress_type','create_system','create_version','extract_version','reserved',
             'flag_bits','volume','internal_attr','external_attr','extra','comment')


def sha(data):return hashlib.sha256(data).hexdigest()


def once(data,old,new,label):
    if data.count(old)!=1:raise ValueError('EXACTLY_ONE_OCCURRENCE_REQUIRED:'+label)
    return data.replace(old,new)


def build(original_zip,out_dir):
    original_zip=Path(original_zip);out_dir=Path(out_dir)
    if zlib.ZLIB_RUNTIME_VERSION!='1.3.1':raise ValueError('ZLIB_1_3_1_REQUIRED_FOR_BYTE_REPRODUCTION')
    raw=original_zip.read_bytes()
    if sha(raw)!=ORIGINAL_ZIP_SHA256:raise ValueError('ORIGINAL_PACKAGE_PIN')
    targets={n:out_dir/n for n in ('tablet_814_v2.zip','inventory.json','revision_manifest.json')}
    if any(p.exists() for p in targets.values()):raise ValueError('REFUSE_OVERWRITE')
    out_dir.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(original_zip) as z:
        infos=z.infolist();data={i.filename:z.read(i.filename) for i in infos}
    names=[i.filename for i in infos]
    if len(names)!=814 or len(set(names))!=814:raise ValueError('ORIGINAL_814_MEMBERS')
    if sha(data[TEST])!=ORIGINAL_TEST_SHA256 or sha(data[SEAL])!=ORIGINAL_SEAL_SHA256:raise ValueError('ORIGINAL_MEMBER_PINS')
    new_test=once(data[TEST],OLD,NEW,'test')
    new_seal=once(data[SEAL],ORIGINAL_TEST_SHA256.encode(),sha(new_test).encode(),'seal')
    changed={TEST:new_test,SEAL:new_seal}
    with zipfile.ZipFile(targets['tablet_814_v2.zip'],'x') as w:
        for info in infos:
            copy=zipfile.ZipInfo(info.filename,info.date_time)
            for field in INFO_FIELDS[2:]:setattr(copy,field,getattr(info,field))
            w.writestr(copy,changed.get(info.filename,data[info.filename]))
    v2_raw=targets['tablet_814_v2.zip'].read_bytes()
    with zipfile.ZipFile(targets['tablet_814_v2.zip']) as v2:
        if v2.testzip() is not None or [i.filename for i in v2.infolist()]!=names:raise ValueError('V2_MEMBER_ORDER')
        for old_info,new_info in zip(infos,v2.infolist()):
            if any(getattr(old_info,f)!=getattr(new_info,f) for f in INFO_FIELDS):raise ValueError('V2_HEADER_FIELDS:'+old_info.filename)
            if old_info.filename in changed:
                if v2.read(old_info.filename)!=changed[old_info.filename]:raise ValueError('V2_CHANGED_BYTES')
            elif (old_info.CRC,old_info.compress_size,old_info.file_size)!=(new_info.CRC,new_info.compress_size,new_info.file_size) \
                    or v2.read(old_info.filename)!=data[old_info.filename]:
                raise ValueError('V2_UNCHANGED_MEMBER_DRIFT:'+old_info.filename)
        files={i.filename:sha(v2.read(i.filename)) for i in v2.infolist()}
        size=sum(i.file_size for i in v2.infolist())
    inventory=dict(archive=ARCHIVE,entries=814,files=files,schema='PACKAGE_A_REVISION_2_814',
                   status='RAW_PACKAGE_PREPARED_NOT_EXECUTED',uncompressed_bytes=size,zip_sha256=sha(v2_raw),
                   revision_of_zip_sha256=ORIGINAL_ZIP_SHA256,revision_of_inventory_sha256=ORIGINAL_INVENTORY_SHA256)
    inventory_raw=json.dumps(inventory,sort_keys=True,indent=2).encode()
    targets['inventory.json'].write_bytes(inventory_raw)
    manifest=dict(schema='PACKAGE_A_REVISION_2_MANIFEST',role='STATIC_BYTES_ONLY_NOT_EXECUTION_PASS',
        decision='ONE_TEST_ORDER_FIX_ONLY; VERDICT_ASSERTION_UNCHANGED; OTHER_319_TESTS_AND_PHYSICS_UNCHANGED',
        original=dict(zip_sha256=ORIGINAL_ZIP_SHA256,inventory_sha256=ORIGINAL_INVENTORY_SHA256,code_seal_sha256=ORIGINAL_SEAL_SHA256),
        revision_2=dict(archive=ARCHIVE,zip_sha256=sha(v2_raw),inventory_sha256=sha(inventory_raw),code_seal_sha256=sha(new_seal),
                        uncompressed_bytes=size,zlib=zlib.ZLIB_RUNTIME_VERSION),
        changed_members={TEST:dict(old_sha256=ORIGINAL_TEST_SHA256,new_sha256=sha(new_test),old_block=OLD.decode(),new_block=NEW.decode()),
                         SEAL:dict(old_sha256=ORIGINAL_SEAL_SHA256,new_sha256=sha(new_seal),
                                   change='only files["%s"] value %s -> %s'%(TEST,ORIGINAL_TEST_SHA256,sha(new_test)))},
        unchanged_members=812,unchanged_check='CRC, compress_size, file_size, header fields and raw bytes equal to original')
    manifest_raw=json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False).encode()
    targets['revision_manifest.json'].write_bytes(manifest_raw)
    return dict(zip_sha256=sha(v2_raw),inventory_sha256=sha(inventory_raw),manifest_sha256=sha(manifest_raw),
                code_seal_sha256=sha(new_seal),test_sha256=sha(new_test),uncompressed_bytes=size)


if __name__=='__main__':
    print(json.dumps(build(*sys.argv[1:3]),sort_keys=True))
