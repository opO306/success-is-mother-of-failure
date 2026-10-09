"""Read fixed local originals and export an allow-listed API projection; no network/imports/tests."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIVATE = Path(r'C:\Users\zun24\.codex\evidence\bounded_admin_recovery_v0\target_54988176_b_v1')
FIELDS = ('id','machine_id','geolocation','country','actual_status','intended_status','dph_total',
          'ssh_host','ssh_port','public_ipaddr','ports')
RAW = {
 'running': ('readonly_instance.json','f0f3f08c45b6ea95648b0c2ead523090af4e0f1b175e895e76a2cdeffb879fb1'),
 'stopping': ('preparation_stopped_instance.json','8d0e1d650751a083cb36874f02a2e67ca6f4f26ffb84a67cda3714a5afed60ec'),
 'stopped': ('preparation_final_instance.json','7e8970417a9e8d5133b8e8c0c856002de23845512c3ec8eee82e7e9348701fa7'),
 'final_stopped': ('external_final_instance.json','d844024c65120adef4bbb51ceaeddeab9f6c0fde79154fcabc638701062b2c77'),
}

def digest(raw): return hashlib.sha256(raw).hexdigest()
def put(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        f.write(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False).encode())

if __name__ == '__main__':
    inventory={}
    for label,(name,wanted) in RAW.items():
        path=PRIVATE/name; raw=path.read_bytes()
        if digest(raw)!=wanted: raise ValueError('FIXED_ORIGINAL_CHANGED:'+name)
        data=json.loads(raw)
        projected={k:data[k] for k in FIELDS if k in data}
        out=HERE/'fixtures'/f'{label}.json'
        put(out,projected)
        inventory[label]=dict(role='ACTUAL_API_FIELD_PROJECTION',original_path=str(path),original_sha256=wanted,
            fixture=out.relative_to(HERE).as_posix(),fixture_sha256=digest(out.read_bytes()),
            fields_present=list(projected),fields_omitted=sorted(set(data)-set(projected)),
            omission_preserved='ports' not in data)
    # Record privacy-sensitive omitted keys by name only. Never export original tokens/values.
    put(HERE/'fixtures'/'provenance.json',dict(schema='FIXED_ACTUAL_API_PROJECTIONS_V1',records=inventory,
        actual_starting_snapshot_available=False,starting_evidence='UNCONFIRMED; synthetic inputs will be labelled',
        source_policy='Allow-listed exact values; absent fields remain absent; original bytes remain private'))
    old=ROOT/'docs/active/bounded_admin_recovery_v0/target_54988176_b_v1'
    seal=json.loads((old/'preparation_seal.json').read_bytes())
    preserved={}
    for name,wanted in seal['files'].items():
        path=old/name
        if digest(path.read_bytes())!=wanted: raise ValueError('OLD_PREPARATION_CHANGED:'+name)
        preserved[path.relative_to(ROOT).as_posix()]=wanted
    failure=old/'result_b_95_es_20261009_082647'
    failseal=json.loads((failure/'result_evidence_seal.json').read_bytes())
    for name,wanted in failseal['files'].items():
        path=failure/name
        if digest(path.read_bytes())!=wanted: raise ValueError('OLD_FAILURE_CHANGED:'+name)
        preserved[path.relative_to(ROOT).as_posix()]=wanted
    for relative in ('experiments/adaptive_experience_tablet_v0/code_seal.json',
        'experiments/adaptive_experience_tablet_v0/preservation_manifest.json',
        'experiments/bounded_admin_recovery_v0/code_seal_v2.json'):
        path=ROOT/relative; manifest=json.loads(path.read_bytes())
        preserved[relative]=digest(path.read_bytes())
        for name,wanted in manifest['files'].items():
            if digest((ROOT/name).read_bytes())!=wanted: raise ValueError('FROZEN_SOURCE_CHANGED:'+name)
            preserved[name]=wanted
    put(HERE/'preservation_before.json',dict(baseline_commit='3090460280219b8964097caafc25a54861906121',
        files=preserved,mismatches=[],scope='Original seals, sources, failed transport and receipts; no readiness claim'))
    print(json.dumps(dict(fixtures=len(inventory),preserved_files=len(preserved),status='INPUTS_FIXED_ONLY; NO_TEST_EXECUTION')))
