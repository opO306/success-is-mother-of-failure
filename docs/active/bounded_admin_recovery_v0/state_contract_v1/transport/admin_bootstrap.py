"""One explicitly approved paid ADMIN window. Reuses Transport lifecycle; never invokes B95/A320."""
import argparse
from decimal import Decimal
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import controller as c

HERE=Path(__file__).resolve().parent
BASE=HERE.parent

class AdminTransport(c.Transport):
    def execute_payload(self):
        self.upload(c.SOURCE,'source.zip','admin_source_upload',40)
        self.upload(c.INVENTORY,'inventory.json','admin_inventory_upload',12)
        c.write(self.out/'admin_ticket.json',dict(self.auth,allocation_start_utc=self.started_utc,
            armed_sha256=c.sha((self.out/'armed.json').read_bytes())))
        self.upload(self.out/'admin_ticket.json','admin_ticket.json','admin_scope_upload',12)
        self.upload(self.out/'armed.json','armed.json','admin_arm_upload',12)
        if self.age()>=150 or self.age()+140+96>=self.handoff():
            raise TimeoutError('ADMIN_FULL_TEST_RECOVERY_RESERVE_REQUIRED')
        response=c.decode(self.py('remote_admin_entry.py',
            [self.guest,self.auth['instance_id'],c.ZIP_HASH,c.INVENTORY_HASH,c.EXPECTED,
             c.sha((self.out/'admin_ticket.json').read_bytes()),c.sha((self.out/'armed.json').read_bytes())],
            'admin_simulation',140))
        self.payload_returncode=response.get('returncode')
        # Exactly one attempt; failed outputs are still recovered before stop when safe.
        self.recover()
        if response.get('role')!='ADMIN_ONLY' or response.get('returncode')!=0 or response.get('error') is not None:
            raise ValueError('ADMIN_REMOTE_SIMULATION_FAILED:'+repr(response))
        self.validate_result()
        return 0

    def validate_result(self):
        root=self.out/'recovered'
        if ((root/'admin_ticket.json').read_bytes()!=(self.out/'admin_ticket.json').read_bytes()
            or (root/'armed.json').read_bytes()!=(self.out/'armed.json').read_bytes()):
            raise ValueError('ADMIN_RAW_SCOPE_AND_ARM_BINDING')
        status=c.load(root/'output/status.json');entry=c.load(root/'admin_entry_exit.json')
        if (status.get('role')!='ADMIN_TRANSPORT_CPU_SIMULATION_ONLY; NOT_B95_OR_A320'
            or status.get('status')!='PASS' or status.get('tests')!=c.EXPECTED
            or status.get('expected_tests')!=c.EXPECTED or status.get('error') is not None
            or status.get('blocked_attempts')!=[]
            or any(status.get(k)!=0 for k in ('failed','errors','skipped','new_physics_calls','gpu_calls',
                'real_provider_calls_inside_simulation','real_subprocess_calls_inside_simulation'))
            or any(status.get(k) is not False for k in ('B95_executed','A320_executed','independent_authority_certification'))
            or not 0<=status['wall_ns']<=120*10**9 or not 0<=status['cpu_ns']<=120*10**9
            or not 0<=status['peak_rss_bytes']<=536870912 or len(status['cpu_affinity'])!=1
            or entry.get('returncode')!=0 or entry.get('error') is not None
            or entry.get('actual_container_id')!=str(self.auth['instance_id'])
            or any(entry.get(k) is not False for k in ('B95_executed','A320_executed'))
            or entry.get('new_physics_calls')!=0 or entry.get('gpu_calls')!=0
            or not 0<=entry['wall_seconds']<=120 or not 0<=entry['aggregate_cpu_seconds']<=120
            or not 0<=entry['aggregate_peak_rss_bytes']<=536870912 or len(entry['cpu_affinity'])!=1):
            raise ValueError('ADMIN_ACTUAL_CASE_OR_RESOURCE_GATE')
        cases=ET.parse(root/'output/junit.xml').getroot().findall('.//testcase')
        ids=[x.attrib['name'] for x in cases]
        rows=c.load(root/'output/case_results.json')['cases']
        if (len(cases)!=c.EXPECTED or len(set(ids))!=c.EXPECTED or len(rows)!=c.EXPECTED
            or set(ids)!={r['id'] for r in rows} or any(r['outcome']!='PASS' for r in rows)
            or any(x.find(tag) is not None for x in cases for tag in ('failure','error','skipped'))):
            raise ValueError('ADMIN_JUNIT_AND_RAW_CASE_GATE')
        c.write(self.out/'admin_result_verified.json',dict(status='PASS',tests=c.EXPECTED,
            failed=0,errors=0,skipped=0,B95_passed=False,A320_passed=False,
            independent_authority_certification=False,status_sha256=c.sha((root/'output/status.json').read_bytes()),
            case_results_sha256=c.sha((root/'output/case_results.json').read_bytes())))
        return status

def preflight(a):
    # This independent admin authority cannot satisfy controller.local_preflight's B authority.
    fixed=dict(schema='HUMAN_PAID_ADMIN_VALIDATION_ONLY_V1',explicit_user_approval=True,
        new_window_separately_authorized=True,restart_exact_instance_authorized=True,exclusive=True,
        scope='ADMIN_SIMULATION_AND_ACTUAL_TRANSPORT_STOP_ONLY',package_kind='ADMIN',
        instance_id=54988176,machine_id=150665,country='ES',ssh_host='188.245.20.75',ssh_port=40470,
        api_ssh_host='ssh5.vast.ai',api_ssh_port=23876,runtime='/usr/bin/python3',
        allocation_seconds=600,compute_seconds=120,aggregate_cpu_seconds=120,cpu_affinity_count=1,
        memory_bytes=536870912,recovery_deadline_seconds=420,stop_confirmation_seconds=180,
        hourly_cap_usd='0.25',total_cap_usd='0.05',campaign_total_cap_usd='0.10',
        physics_calls=0,gpu_calls=0,B95_authorized=False,A320_authorized=False,
        prior_failed_attempts=3,prior_B_failed_windows=1,prior_tablet_gate_attempts=1,
        prior_local_invocation_failures=1,prior_B_prestart_failures=1,auto_retry=False,field_code_changes=False)
    if any(a.get(k)!=v for k,v in fixed.items()) or not a.get('approval_reference') or not a.get('human_approval_text'):
        raise ValueError('EXPLICIT_ADMIN_ONLY_SCOPE_REQUIRED')
    if not c.re.fullmatch(r'admin_[a-z0-9_]{4,42}',a['run_id']):raise ValueError('ADMIN_EXCLUSIVE_RUN_ID')
    stamp=c.datetime.fromisoformat(a['approved_utc']);expires=c.datetime.fromisoformat(a['expires_utc'])
    if stamp.tzinfo is None or expires.tzinfo is None or not stamp<=c.datetime.now(c.timezone.utc)<expires:
        raise ValueError('ADMIN_APPROVAL_TIME_INVALID')
    record=c.load(BASE/'candidate_input_record.json')
    if (a['candidate_input_record_sha256']!=c.sha((BASE/'candidate_input_record.json').read_bytes())
        or record['role']!='INPUT_BYTE_BINDING_ONLY; NOT_STATIC_READY_OR_SIMULATION_PASS'
        or a['expected_tests']!=record['expected_admin_tests']):raise ValueError('ADMIN_CANDIDATE_BINDING')
    for name,wanted in record['files'].items():
        c.safe_name(name)
        if c.sha((c.ROOT/name).read_bytes())!=wanted:raise ValueError('ADMIN_CANDIDATE_RAW_DRIFT:'+name)
    if c.sha(c.SOURCE.read_bytes())!=record['zip_sha256'] or c.sha(c.INVENTORY.read_bytes())!=record['inventory_sha256']:
        raise ValueError('ADMIN_CANDIDATE_ZIP_OR_INVENTORY_DRIFT')
    preserved=c.load(BASE/'preservation_before.json')
    for name,wanted in preserved['files'].items():
        if c.sha((c.ROOT/name).read_bytes())!=wanted:raise ValueError('FROZEN_SOURCE_OR_FAILURE_DRIFT:'+name)
    c.safe_name(a['budget_ledger_file'])
    budget=c.load(BASE/a['budget_ledger_file'])
    if a['budget_ledger_sha256']!=c.sha((BASE/a['budget_ledger_file']).read_bytes()):raise ValueError('ADMIN_BUDGET_RAW_PIN')
    spent=Decimal(budget['conservative_spent_bound_usd'])
    budget_time=c.datetime.fromisoformat(budget['observed_utc'])
    if (budget.get('role')!='CURRENT_PROVIDER_READONLY_AND_PRESERVED_COST_BOUND'
        or budget.get('campaign_total_cap_usd')!='0.10' or not budget.get('provider_raw_sha256')
        or budget.get('provider_query_complete') is not True or budget_time.tzinfo is None
        or not 0<=(c.datetime.now(c.timezone.utc)-budget_time).total_seconds()<=300
        or not spent.is_finite() or spent<0 or spent+Decimal('.25')*600/3600>Decimal('.10')):
        raise ValueError('ACTUAL_CURRENT_BUDGET_RESERVE_REFUSED')
    c.PRIOR_POLICY_FEE_BOUND=spent
    return dict(preserved_files=len(preserved['files']),candidate_files=len(record['files']),
        B95_authorized=False,A320_authorized=False,campaign_reserve_checked=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--approval',type=Path,required=True)
    p.add_argument('--cli',type=Path,required=True);p.add_argument('--key',type=Path,required=True)
    args=p.parse_args();a=c.load(args.approval);record=c.load(BASE/'candidate_input_record.json')
    c.KIND='ADMIN';c.CODE=c.sha((HERE/'controller.py').read_bytes());c.PROTO=c.sha((BASE/'PLAN.md').read_bytes())
    c.SOURCE=BASE/'candidate_payload.zip';c.INVENTORY=BASE/'candidate_inventory.json'
    c.ZIP_HASH=record['zip_sha256'];c.INVENTORY_HASH=record['inventory_sha256'];c.EXPECTED=record['expected_admin_tests']
    checked=preflight(a)
    out=HERE/('run_'+a['run_id']);out.mkdir(exist_ok=False)
    c.write(out/'admin_authorization.json',a);c.write(out/'preflight_verified.json',checked)
    print(str(out),flush=True)
    return AdminTransport(a,args.cli,args.key,out).execute()

if __name__=='__main__':raise SystemExit(main())
