"""Versioned closure bindings shared by parent and unchanged V12 watchdog."""
from pathlib import Path
import hashlib,json
from preflight import require_extension
from budget import money

def install():
    import cleanup
    original_verify=cleanup.verify_admin
    original_settle=cleanup.settle_extension_reservations
    original_close=cleanup.close_owned
    def close(provider,owner,out,baseline_volumes,finite_policy,**kwargs):
        # Both parent and watchdog preserve an administrative failure for same-window repair.
        if owner.get('v12_2_repair') is True and not (Path(out)/'research_success.json').exists():kwargs['user_hold']=True
        return original_close(provider,owner,out,baseline_volumes,finite_policy,**kwargs)
    def verify(out,owner):
        out=Path(out)
        if owner.get('v12_2_repair') is True:
            proof=json.loads((out/'prior_probe_closed_prelaunch.json').read_bytes())
            if (proof.get('instance_id')!=55069864 or owner['machine_id']!=37055
                or proof.get('job_claim_absent') is not True or proof.get('controller_launch_intent_absent') is not True):raise ValueError('OLD_PROBE_UNRECOVERED_PRESERVE')
            actual={p.relative_to(out/'prior_probe_raw').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'prior_probe_raw').rglob('*') if p.is_file()}
            if actual!=proof['all_existing_files_sha256'] or set(actual)-{'guest_probe_writer.py','guest_job.py','job_spec.json'}:raise ValueError('OLD_PROBE_RAW_DRIFT')
            startup=json.loads((out/'resumed_startup_finality.json').read_bytes())
            current=json.loads((out/'startup_verified.json').read_bytes())
            if startup.get('instance_id')!=owner['instance_id'] or startup.get('writers_absent') is not True or startup.get('files')!=current['files']:raise ValueError('RESUMED_STARTUP_UNCLOSED_PRESERVE')
            if (out/'repair_admin_started.json').exists():
                from job_proof import closed_archive
                descriptor=json.loads((out/'repair_admin_closed_originals.json').read_bytes())
                expected_owner=dict(owner,run_id=owner['run_id']+'_repair_admin')
                if any(descriptor['owner'].get(k)!=expected_owner[k] for k in ('instance_id','machine_id','run_id')) or Path(descriptor['folder']).resolve()!=(out/'repair_admin_job').resolve():raise ValueError('REPAIR_ADMIN_EXACT_OWNER_OR_FOLDER')
                wanted=hashlib.sha256((Path(__file__).parent/'admin_payload.zip').read_bytes()).hexdigest()
                if descriptor['code_sha256']!=wanted or json.loads((out/'repair_admin_job/job_spec.json').read_bytes()).get('job_role')!='ADMIN_TESTS':raise ValueError('REPAIR_ADMIN_INPUT_OR_ROLE')
                if closed_archive(descriptor['folder'],descriptor['owner'],wanted)!=descriptor['proof']:raise ValueError('REPAIR_ADMIN_ALL_RAW_FINALITY')
        return original_verify(out,owner)
    def settle(ledger,owner):
        original_settle(ledger,owner)
        if owner.get('v12_2_repair') is not True:return
        require_extension()
        token=owner['reservation_token']+'_v12_2_time_extension'
        if owner['instance_id']!=55069864 or owner['machine_id']!=37055 or owner['allocation_monotonic_ns']!=190077406000000:raise ValueError('EXTENSION_EXACT_OWNER')
        events,_=ledger.read();balance=ledger.balances(events)
        def already(rows):
            return any(e.get('action')=='SETTLE' and e.get('token')==token and e.get('instance_id')==55069864 and e.get('destroy_confirmed') is True and money(e.get('observed_cost_bound'))==money('.06') for e in rows)
        if token not in balance['active']:
            if not already(events):raise ValueError('EXTENSION_PENDING_OR_SETTLED_REQUIRED')
            return
        if balance['active'][token]!=money('.06'):raise ValueError('EXTENSION_AMOUNT_DRIFT')
        try:ledger.append(dict(action='SETTLE',token=token,instance_id=55069864,observed_cost_bound='0.06',destroy_confirmed=True))
        except ValueError:
            if not already(ledger.read()[0]):raise
    cleanup.verify_admin=verify
    cleanup.settle_extension_reservations=settle
    cleanup.close_owned=close
    return cleanup
