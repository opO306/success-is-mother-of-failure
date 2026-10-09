"""Local stdlib metadata writer; no API, SSH, project imports or approval grant."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=HERE.parent/'closure_v1'
T=HERE/'transport'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())
def write(path,obj):
    with path.open('xb') as f: f.write((json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


def main():
    protocol_hash=sha(HERE/'budget_protocol.json')
    assert protocol_hash==read(HERE/'protocol_seal.json')['files']['budget_protocol.json']
    write(T/'B_cost_confirmation_UNCONFIRMED.json',dict(schema='B_POST_STOP_PROVIDER_EXECUTION_COST_CONFIRMATION_V1',
          package_kind='B',human_confirmed=False,confirmation_reference=None,human_confirmation_text=None,
          confirmed_utc=None,budget_protocol_sha256=protocol_hash,policy_gate_receipt_sha256=None,
          closure_sha256=None,final_instance_sha256=None,cost_basis='PROVIDER_REPORTED_EXECUTION_FEE',
          actual_execution_fee_usd=None,billing_scope='EXECUTION_ONLY',raw_files={},
          independent_provider_authentication=False,full_invoice_verified=False,
          status='UNCONFIRMED_TEMPLATE; copy to exact B run after stop and human cost review; not execution authority'))
    prior=read(OLD/'transport/transport_seal.json')
    names=sorted(list(prior['files'])+['B_cost_confirmation_UNCONFIRMED.json'])
    write(T/'transport_seal.json',dict(schema='PACKAGE_CLOSURE_BUDGET_SUPPLEMENT_TRANSPORT_SEAL_V1',
          budget_protocol_sha256=protocol_hash,original_scope_sha256=prior['scope_sha256'],
          previous_transport_seal_sha256=sha(OLD/'transport/transport_seal.json'),
          guardian_sha256=prior['guardian_sha256'],files={n:sha(T/n) for n in names},
          campaign_total_cap_usd='0.10',each_total_cap_usd='0.05',execution_authorized=False,
          runtime_validation='PENDING',packages=read(T/'package_bindings.json')))
    for kind in ('B','A'):
        auth=read(OLD/f'transport/approval_UNAPPROVED_{kind}.json')
        auth.update(schema='PACKAGE_CLOSURE_BUDGET_SUPPLEMENT_V1_NEW_WINDOW_HUMAN_APPROVAL',
                    campaign_total_cap_usd='0.10',budget_protocol_sha256=protocol_hash,
                    aggregate_cpu_seconds=120,cpu_affinity_count=1,memory_bytes=536870912,
                    previous_transport_seal_sha256=sha(OLD/'transport/transport_seal.json'),
                    transport_seal_sha256=sha(T/'transport_seal.json'),
                    approval_status='BUDGET_SUPPLEMENT_TEMPLATE_ONLY; paid restart/execution requires separate explicit human approval')
        if kind=='A': auth.update(B_cost_confirmation=None,B_cost_confirmation_sha256=None)
        write(T/f'approval_UNAPPROVED_{kind}.json',auth)
    print(json.dumps(dict(budget_protocol_sha256=protocol_hash,transport_seal_sha256=sha(T/'transport_seal.json'),
                         campaign_cap='0.10',each_cap='0.05',paid_actions=0)))


if __name__=='__main__': main()
