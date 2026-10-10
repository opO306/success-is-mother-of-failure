"""Write operational_seal.json: exact bytes of V12.5 sources (incl. A package revision 2) and every V12/V12.2 file
it depends on, plus the V12 files package_v2 attaches to. Static only."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
V12_2_USED=('read_retry.py','transport_reads.py','admin_payload.zip','admin_test_inventory.json','guest_admin_runner.py',
            'probe_runner.py','test_read_retry.py','test_transport_reads.py','disconnect_launch.py')
V12_PINNED=('operational_seal.json','policy.json','finite_policy.json','campaign.py','lifecycle.py','terminal_proof.py','cleanup.py',
            'watchdog.py','transport/controller.py','transport/guest_source_verify.py','transport/package_bindings.json')
PACKAGE_V2=('revision_v12_4/package_A_v2/tablet_814_v2.zip','revision_v12_4/package_A_v2/inventory.json',
            'revision_v12_4/package_A_v2/revision_manifest.json','revision_v12_4/package_A_v2/build_package_v2.py')


def files():
    names=[p.relative_to(BASE).as_posix() for p in sorted(HERE.rglob('*'))
           if p.is_file() and p.name!='operational_seal.json' and '__pycache__' not in p.parts and p.suffix in ('.py','.txt','.md','.json')]
    names+=list(PACKAGE_V2)+['revision_v12_2/'+n for n in V12_2_USED]+['revision_v12/'+n for n in V12_PINNED]
    return {n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in names}


def main():
    seal=dict(schema='V12_5_OPERATIONAL_SEAL',role='STATIC_BYTES_ONLY_NOT_EXECUTION_PASS',files=files())
    raw=json.dumps(seal,sort_keys=True,indent=2).encode()
    (HERE/'operational_seal.json').write_bytes(raw)
    print(json.dumps(dict(files=len(seal['files']),seal_sha256=hashlib.sha256(raw).hexdigest())))


if __name__=='__main__':sys.exit(main())
