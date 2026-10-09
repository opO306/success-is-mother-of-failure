"""V12 administrative repair: same instance/reservation/first deadline; no rental."""
from pathlib import Path
import hashlib,json,os,sys,time,subprocess,shlex,shutil,base64,importlib.util
import psutil
BASE=Path(__file__).resolve().parent
OLD=BASE.parent/'revision_v12'
PRIVATE=Path('C:/Users/zun24/.codex/evidence/project_vast_budget_cleanup_v1_20261009')
PRIOR=PRIVATE/'project_v12_a_20261009_181249'
OUT=PRIOR/'administrative_repair_v12_2'
sys.path.insert(0,str(OLD));sys.path.insert(0,str(OLD/'transport'))
sys.path.insert(0,str(BASE))  # Versioned exact-extension preflight; original files remain sealed.
from lifecycle import Provider,save,identity,verify_admin,verify_startup
from budget import Ledger,money
from cleanup import close_owned,reconcile_destroyed
from execution_authority import require_claim
from read_retry import read_retry
from preflight import require_extension
from time_authority import install as install_time_authority
install_time_authority()
from closure_bridge import install
install()  # Parent and watchdog share exact raw recovery and extension settlement.
import campaign
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
APPROVAL=PRIVATE/'v12_actual_bundled_approval.json'
GRANT='623cfc2f2ba0713e9c73480db73b39863bee83bad3bc6a76cbba09e31bbc3f02'

def main():
    frozen=json.loads((BASE/'repair_seal.json').read_bytes())
    for n,h in frozen['files'].items():
        if SHA(BASE/n)!=h:raise ValueError('REPAIR_SOURCE_CHANGED')
    claim=require_claim(APPROVAL,GRANT)
    extension=require_extension()  # BEFORE API/read/restart/reservation mutation.
    if (claim/'transport_started.json').exists() or (PRIOR/'transport').exists():raise ValueError('A_ALREADY_STARTED_NO_REEXECUTION')
    if SHA(PRIOR/'stage_closeout.json')!='cb0a3d7a254cedd9af157116cacd2c7be7a44124948dc95e0043bb75ddf7e2c8':raise ValueError('PRIOR_FAILURE_RAW_CHANGED')
    prior_close=campaign.read(PRIOR/'stage_closeout.json')
    for n,h in prior_close['raw_files'].items():
        if SHA(PRIOR/n)!=h:raise ValueError('PRIOR_EXECUTION_RAW_CHANGED:'+n)
    if (PRIOR/'ssh_disconnect_probe/job_launch_intent.json').exists():raise ValueError('PRIOR_PROBE_LAUNCH_UNCONFIRMED')
    policy=campaign.read(OLD/'policy.json');campaign.source_preflight(policy)
    policy.update(_paid_approval_path=str(APPROVAL),_paid_approval_sha256=GRANT)
    owner=campaign.read(PRIOR/'owner.json');lease=campaign.read(PRIOR/'watchdog_lease.json')
    if owner['instance_id']!=55069864 or owner['machine_id']!=37055:raise ValueError('EXACT_SAME_OWNER_REQUIRED')
    if (owner['allocation_monotonic_ns']!=190077406000000 or lease['allocation_monotonic_ns']!=190077406000000
        or owner['allocation_start_utc']!='2026-10-09T18:12:57.932772+00:00' or lease['finite_policy']['lease_seconds']!=1800
        or lease['finite_policy']['cleanup_seconds']!=220 or lease['authorization_raw_sha256']!=policy['authorization_raw_sha256']
        or lease['finite_policy']['paid_approval_sha256']!=GRANT or Path(lease['finite_policy']['paid_approval_path']).resolve()!=APPROVAL.resolve()):raise ValueError('EXACT_ORIGINAL_FIRST_CLOCK_REQUIRED')
    lease_seconds=extension['lease_seconds']
    stop_at=owner['allocation_monotonic_ns']/1e9+lease_seconds-220
    if stop_at-time.monotonic()<1500:raise ValueError('UNCHANGED_FIRST_LEASE_INSUFFICIENT')
    old_pid=campaign.read(PRIOR/'watchdog_ready.json')['pid']
    if psutil.pid_exists(old_pid):
        p=psutil.Process(old_pid)
        if p.is_running() and p.status()!=psutil.STATUS_ZOMBIE and str(PRIOR/'watchdog_lease.json') in p.cmdline():raise ValueError('OLD_WATCHDOG_STILL_ARMED_NO_RESTART')
    OUT.mkdir(exist_ok=False)
    save(OUT/'repair_origin.json',dict(original_owner=owner,original_first_allocation_ns=owner['allocation_monotonic_ns'],original_lease_seconds=1800,extended_lease_seconds=lease_seconds,extension_authorization=extension,original_reservation=owner['reservation_token'],grant_sha256=GRANT,repair_seal_sha256=SHA(BASE/'repair_seal.json'),new_rentals=0,A_executions_before_repair=0,B_executions=0,budget_reset=False,actual_failure='ADMIN_API_SHOW_TIMEOUT_BEFORE_PROBE_SPEC_UPLOAD_OR_LAUNCH'))
    verify_startup(PRIOR,owner)
    for n in ('known_hosts','admin_verified.json','admin_result.json','junit.xml','stdout.log','stderr.log','v11_first10.xml','v11_first10.stdout','v11_first10.stderr','admin_started.json'):
        shutil.copyfile(PRIOR/n,OUT/n)
    shutil.copytree(PRIOR/'admin_job_io',OUT/'admin_job_io')
    descriptor=campaign.read(PRIOR/'admin_closed_originals.json');descriptor['folder']=str(OUT/'admin_job_io')
    save(OUT/'admin_closed_originals.json',descriptor)
    owner=dict(owner,local_evidence_destination=str(OUT),v12_2_repair=True,start_request_may_be_queued=True,stop_attempt_journal=str((OUT/'queued_stop_journal').resolve()));save(OUT/'owner.json',owner)
    verify_admin(OUT,owner)  # Validate inherited ADMIN before the bridge's later closure checks.
    ledger=Ledger(policy['ledger_path']);balance=ledger.balances(ledger.read()[0])
    if balance['cap']!=money('2') or set(balance['active'])!={owner['reservation_token']} or str(balance['active'][owner['reservation_token']])!=owner['maximum_cost_usd'] or balance['remaining']<0:raise ValueError('INHERITED_LEDGER_RESERVATION_REQUIRED')
    extra_token=owner['reservation_token']+'_v12_2_time_extension'
    finite=dict(lease['finite_policy'],lease_seconds=lease_seconds,v12_2_exact_extension=True)
    lease=dict(lease,controller_pid=os.getpid(),controller_create_time=psutil.Process().create_time(),out=str(OUT),finite_policy=finite)
    save(OUT/'watchdog_lease.json',lease)
    watch=None
    def check():
        if watch is None or watch.poll() is not None:raise campaign.SafetyStop('INHERITED_LEASE_STOP_CONTROL_LOST')
    class Reads(Provider):
        def call(self,*args,json_result=True,timeout=24):
            check()
            if time.monotonic()>=stop_at:raise campaign.SafetyStop('ABSOLUTE_OUTER_DEADLINE_BEFORE_PROVIDER_COMMAND')
            from read_retry import TemporaryReadFailure,transient_stderr
            def perform(left):
                try:
                    value=super(Reads,self).call(*args,json_result=json_result,timeout=left)
                    if tuple(args[:2])==('show','instance'):identity(value,owner)
                    return value
                except OSError as error:
                    if str(error)!='PROVIDER_COMMAND_FAILED':raise
                    if not transient_stderr((self.out/('%04d.stderr'%self.index)).read_bytes()):raise
                    raise TemporaryReadFailure(str(error)) from error
            return read_retry(perform,args,timeout=timeout,absolute_deadline=stop_at,check=check)
    provider=Reads(lease['cli'],OUT/'api')
    passed=False;failure=None;destroy=None;settled=False
    try:
        ledger.append(dict(action='RESERVE',token=extra_token,amount='0.06',instance_id=owner['instance_id'],reason='ACTUAL_SAME_SERVER_SINGLE_NEW_30_MIN_WINDOW',extension_authorization_sha256=SHA(PRIVATE/'v12_2_actual_time_extension.json')))
        watch=subprocess.Popen([sys.executable,'-B',str(BASE/'watchdog_bridge.py'),'--lease',str(OUT/'watchdog_lease.json')],stdout=(OUT/'watchdog.stdout').open('xb'),stderr=(OUT/'watchdog.stderr').open('xb'),creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
        until=time.monotonic()+10
        while not (OUT/'watchdog_ready.json').exists():
            check()
            if time.monotonic()>=until:raise ValueError('REPAIR_WATCHDOG_NOT_READY')
            time.sleep(.1)
        if campaign.read(OUT/'watchdog_ready.json')['lease_sha256']!=SHA(OUT/'watchdog_lease.json'):raise ValueError('REPAIR_WATCHDOG_RAW_BINDING')
        from budget import charge_total
        display,count=charge_total(provider.charges())
        balance=ledger.append(dict(action='OBSERVE',historical_bound=str(display+money('.002')*count+money('.020')),reason='ACTUAL_PROVIDER_BEFORE_APPROVED_SAME_SERVER_RESTART'))
        if balance['cap']!=money('2') or balance['remaining']<0:raise ValueError('ACTUAL_PROVIDER_COST_EXCEEDS_CAP')
        if stop_at-time.monotonic()<1500:raise ValueError('FULL_EXECUTION_WINDOW_EXHAUSTED_BEFORE_START')
        current=identity(provider.call('show','instance',owner['instance_id']),owner)
        if current['actual_status'] not in ('exited','stopped') or current['intended_status']!='stopped':raise ValueError('ACTUAL_STOP_BEFORE_SAME_SERVER_RESUME')
        if money(current['dph_total'])>money(owner['observed_rate_usd']):raise campaign.SafetyStop('RESERVED_PRICE_CHANGED_BEFORE_RESTART')
        if [r['id'] for r in provider.instances(timeout=24)]!=[owner['instance_id']]:raise ValueError('EXACT_SINGLE_EXISTING_INSTANCE_ONLY')
        # A new rental/stage/approval claim is never entered. Same stopped server starts once.
        save(OUT/'restart_intent.json',dict(instance_id=owner['instance_id'],machine_id=owner['machine_id'],maximum_start_requests=1,queued_stop_journal=owner['stop_attempt_journal']))
        campaign.start_owned_once(provider,owner)
        until=min(time.monotonic()+120,stop_at-900)
        while time.monotonic()<until:
            current=identity(provider.call('show','instance',owner['instance_id']),owner)
            if current.get('actual_status')=='running' and current.get('intended_status')=='running':break
            time.sleep(2)
        else:raise campaign.AdministrativeUnavailable('SAME_SERVER_RESUME_NOT_RUNNING_WITHIN_ORIGINAL_WINDOW')
        ports={r.get('HostPort') for r in current.get('ports',{}).get('22/tcp',[])}
        if current.get('public_ipaddr')!=owner['public_ipaddr'] or ports!={str(owner['direct_ssh_port'])} or money(current['dph_total'])>money(owner['observed_rate_usd']):raise campaign.SafetyStop('SAME_SERVER_MAPPING_OR_PRICE_CHANGED')
        key=Path('C:/Users/zun24/.ssh/vast_ai')
        ssh=['ssh','-T','-i',str(key),'-p',str(owner['direct_ssh_port']),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(OUT/'known_hosts'),'-o','ConnectTimeout=5','root@'+owner['public_ipaddr']]
        fresh=campaign.command_recheck(OUT/'resumed_startup_io',ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',(BASE/'startup_observation.py').read_text(encoding='utf-8'),str(owner['instance_id'])])],'finality',100,watch=watch)
        save(OUT/'resumed_startup_finality.json',json.loads(fresh))
        campaign.collect_startup(OUT,owner,key,watch)
        if campaign.read(OUT/'startup_verified.json')['files']!=json.loads(fresh)['files']:raise campaign.SafetyStop('RESUMED_SETUP_RAW_CHANGED_AFTER_CLOSURE')
        # Recover every file of the abandoned pre-launch probe. A claimed job would refuse.
        audit="import pathlib,sys,json,hashlib,base64\np=pathlib.Path(sys.argv[1]); ids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'CONTAINER_ID=')]\nif ids!=[sys.argv[2]] or (p/'job').exists():raise ValueError('OLD_PROBE_CLAIM_OR_OWNER_UNCONFIRMED')\nfiles={}\nfor q in p.rglob('*'):\n if q.is_symlink():raise ValueError('OLD_PROBE_SYMLINK')\n if q.is_file():files[q.relative_to(p).as_posix()]=base64.b64encode(q.read_bytes()).decode()\nif set(files)-{'guest_probe_writer.py','guest_job.py','job_spec.json'}:raise ValueError('OLD_PROBE_UNKNOWN_GENERATED_RAW')\nprint(json.dumps(files))"
        oldguest='/workspace/vast_budget_admin_'+owner['run_id']+'_disconnect_probe'
        raw=campaign.command_recheck(OUT/'prior_probe_audit',ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',audit,oldguest,str(owner['instance_id'])])],'audit',24,watch=watch)
        packet=json.loads(raw);files={n:base64.b64decode(v,validate=True) for n,v in packet.items()}
        originals={'guest_probe_writer.py':OLD/'transport/guest_probe_writer.py','guest_job.py':OLD/'transport/guest_job.py','job_spec.json':PRIOR/'ssh_disconnect_probe/job_spec.json'}
        for n,v in files.items():
            if hashlib.sha256(v).hexdigest()!=SHA(originals[n]):raise ValueError('PRIOR_PROBE_INPUT_RAW_DRIFT')
            folder=OUT/'prior_probe_raw';folder.mkdir(exist_ok=True);(folder/n).write_bytes(v)
        save(OUT/'prior_probe_closed_prelaunch.json',dict(instance_id=owner['instance_id'],job_claim_absent=True,controller_launch_intent_absent=True,all_existing_files_sha256={n:hashlib.sha256(v).hexdigest() for n,v in files.items()},actual_stopped_before_resume=True,role='CLOSED_PREPARATION_NO_RESEARCH_JOB_STARTED'))
        spec=importlib.util.spec_from_file_location('v12_2_original_transport',OLD/'transport/controller.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure('A')
        io=OUT/'ssh_disconnect_probe';io.mkdir();guest='/workspace/vast_budget_probe_v12_2_'+owner['run_id']
        mkdir="import pathlib,sys\nids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'CONTAINER_ID=')]\nif ids!=[sys.argv[2]]:raise ValueError('REPAIR_ACTUAL_INSTANCE_MISMATCH')\np=pathlib.Path(sys.argv[1])\nif p.parent!=pathlib.Path('/workspace') or p.resolve()!=p or p.exists():raise ValueError('REPAIR_EXCLUSIVE_ROOT')\np.mkdir()"
        campaign.command(io,ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',mkdir,guest,str(owner['instance_id'])])],'mkdir',15,watch=watch)
        save(OUT/'ssh_disconnect_probe_started.json',dict(instance_id=owner['instance_id'],repair_version='V12_2',guest=guest))
        from transport_reads import transport_class
        ReadsTransport=transport_class(m,stop_at,check)
        from process_bridge import install_dispatch
        install_dispatch()
        class Probe(ReadsTransport):
            def py(self,script_name,args,name,timeout=30,phase_deadline=None,required_seconds=None):
                if script_name!='guest_disconnect_launch.py':return super().py(script_name,args,name,timeout,phase_deadline,required_seconds)
                self.control(90+96+8)
                return self.run([*ssh,shlex.join(['/usr/local/bin/python3','-B','-',*map(str,args)])],name,8,input=(BASE/'disconnect_launch.py').read_bytes())
        auth=dict(owner,run_id=owner['run_id']+'_disconnect_probe',ssh_host=owner['public_ipaddr'],ssh_port=owner['direct_ssh_port'],known_hosts_file=str(OUT/'known_hosts'))
        t=Probe(auth,provider.cli,key,io);t.guest=guest;t.remote_created=True;t.identity_verified=True;t.ssh_argv=ssh
        t.evidence_job_role='ADMIN_PROBE';t.evidence_code_sha256=SHA(OLD/'admin_payload.zip');t.start_ns=owner['allocation_monotonic_ns'];t.started_utc=owner['allocation_start_utc'];t.handoff=lambda:lease_seconds-220;t.stop_control_check=check
        def control(required_seconds,phase_deadline=None):
            check();left=stop_at-time.monotonic()
            if left<required_seconds+650:raise campaign.SafetyStop('ORIGINAL_WINDOW_FULL_A_AND_CLEANUP_REQUIRED')
            budget=min(24,left) if phase_deadline is None else min(24,left,phase_deadline-time.monotonic())
            if budget<=0:raise TimeoutError('UNCHANGED_PROBE_RPC_DEADLINE')
            row=identity(provider.call('show','instance',owner['instance_id'],timeout=budget),owner)
            check()
            if phase_deadline is not None and time.monotonic()>=phase_deadline:raise TimeoutError('UNCHANGED_PROBE_RPC_DEADLINE')
            if row['actual_status']!='running' or row['intended_status']!='running' or row.get('public_ipaddr')!=owner['public_ipaddr'] or {r.get('HostPort') for r in row.get('ports',{}).get('22/tcp',[])}!={str(owner['direct_ssh_port'])} or money(row['dph_total'])>money(owner['observed_rate_usd']):raise campaign.SafetyStop('REPAIR_ACTUAL_MAPPING_OR_RATE_DRIFT')
        t.control=control
        # New administrative regression precedes the actual disconnection probe.
        admin_io=OUT/'repair_admin_job';admin_io.mkdir()
        admin_guest='/workspace/vast_budget_admin_v12_2_'+owner['run_id']
        save(OUT/'repair_admin_started.json',dict(instance_id=owner['instance_id'],payload_sha256=SHA(BASE/'admin_payload.zip'),guest=admin_guest))
        control(90+96+40)
        campaign.command(admin_io,ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',mkdir,admin_guest,str(owner['instance_id'])])],'mkdir',15,watch=watch)
        admin_auth=dict(auth,run_id=owner['run_id']+'_repair_admin')
        admin=ReadsTransport(admin_auth,provider.cli,key,admin_io)
        admin.guest=admin_guest;admin.remote_created=True;admin.identity_verified=True;admin.ssh_argv=ssh
        admin.evidence_job_role='ADMIN_TESTS';admin.evidence_code_sha256=SHA(BASE/'admin_payload.zip')
        admin.start_ns=owner['allocation_monotonic_ns'];admin.started_utc=owner['allocation_start_utc'];admin.handoff=lambda:lease_seconds-220;admin.stop_control_check=check;admin.control=control
        admin.upload(BASE/'admin_payload.zip','repair_admin.zip','repair_admin_upload',25)
        extract="import pathlib,sys,hashlib,zipfile,stat\np=pathlib.Path(sys.argv[1]);zpath=p/'repair_admin.zip'\nif hashlib.sha256(zpath.read_bytes()).hexdigest()!=sys.argv[2]:raise ValueError('REPAIR_ADMIN_SOURCE_PIN')\nwith zipfile.ZipFile(zpath) as z:\n if len(z.namelist())!=6 or len(set(z.namelist()))!=6 or z.testzip():raise ValueError('REPAIR_ADMIN_MEMBERS')\n for i in z.infolist():\n  n=i.filename\n  if n not in {'read_retry.py','transport_reads.py','test_read_retry.py','test_transport_reads.py','guest_admin_runner.py','admin_test_inventory.json'} or i.is_dir() or i.flag_bits&1 or stat.S_IFMT(i.external_attr>>16) not in (0,stat.S_IFREG):raise ValueError('REPAIR_ADMIN_SCOPE')\n z.extractall(p)"
        campaign.command(admin_io,ssh+[shlex.join(['/usr/local/bin/python3','-B','-c',extract,admin_guest,admin.evidence_code_sha256])],'extract',15,watch=watch)
        admin_observed=admin.run_remote_job(['/usr/local/bin/python3','-B',admin_guest+'/guest_admin_runner.py','/workspace/vast_budget_admin_'+owner['run_id'],str(owner['instance_id'])],SHA(BASE/'guest_admin_runner.py'),timeout_seconds=90)
        admin.recover_final()
        from job_proof import closed_archive
        admin_closed=closed_archive(admin_io,admin_auth,admin.evidence_code_sha256)
        save(OUT/'repair_admin_closed_originals.json',dict(owner=admin_auth,folder=str(admin_io),code_sha256=admin.evidence_code_sha256,proof=admin_closed))
        admin_result=campaign.read(admin_io/'recovered/repair_result.json');save(OUT/'repair_admin_result.json',admin_result)
        if admin_observed['state']!='EXITED_SUCCESS' or admin_result.get('passed') is not True:raise ValueError('NEW_ADMIN_REGRESSION_FAILED_NO_A_STARTED')
        for n in ('read_retry.py','test_read_retry.py','probe_runner.py'):t.upload(BASE/n,n,'repair_upload_'+n,20)
        observed=t.run_remote_job(['/usr/local/bin/python3','-B',guest+'/probe_runner.py'],SHA(BASE/'probe_runner.py'),timeout_seconds=90,disconnect_probe=True)
        t.recover_final()
        from job_proof import closed_archive
        closed=closed_archive(io,auth,t.evidence_code_sha256)
        save(OUT/'probe_closed_originals.json',dict(owner=auth,folder=str(io),code_sha256=t.evidence_code_sha256,proof=closed))
        result=campaign.read(io/'recovered/repair_result.json')
        if observed['state']!='EXITED_SUCCESS' or result.get('passed') is not True:raise ValueError('REPAIR_ADMIN_AND_DISCONNECT_NOT_PASS')
        events=[json.loads(r) for r in (io/'events.jsonl').read_bytes().splitlines()]
        if not any(e.get('event')=='JOB_STATE_OBSERVED' and e.get('state')=='RUNNING' for e in events):raise ValueError('ACTUAL_LIVE_JOB_AFTER_SSH_DISCONNECTION_NOT_OBSERVED')
        save(OUT/'ssh_disconnect_verified.json',dict(instance_id=owner['instance_id'],job_observation=observed,intentional_client_termination=True,actual_running_after_disconnect=True,actual_status_reconnected=True,scope='ADMIN_PROBE_ONLY_NOT_A320',repair_tests=result))
        verify_admin(OUT,owner)
        B=Path(policy['B_stage_closeout']);binding=campaign.transport_binding(policy,'A',owner,OUT,B);save(OUT/'binding.json',binding)
        checks=m.local_preflight(binding);aout=OUT/'transport';aout.mkdir();save(aout/'source_preflight.json',dict(checks=checks));save(aout/'human_authorization.json',binding)
        if stop_at-time.monotonic()<600:raise ValueError('FULL_ORIGINAL_A_WINDOW_NO_HEADROOM')
        a=ReadsTransport(binding,provider.cli,key,aout)
        passed=a.execute()==0
        if not passed:raise ValueError('ORIGINAL_A320_FAILED_NO_AUTOMATIC_CALCULATION_REEXECUTION')
        save(OUT/'research_success.json',dict(instance_id=owner['instance_id'],actual_original_transport_exit=0,role='PARENT_COMPLETION_NOT_SUBSTITUTE_FOR_RAW_VERIFICATION'))
    except BaseException as error:
        failure=repr(error);save(OUT/'failure.json',dict(error=failure,recovery_window_start_monotonic_ns=time.monotonic_ns(),automatic_physics_retry=False))
    finally:
        try:
            cleanup_provider=Provider(lease['cli'],OUT/'closure_api')
            stop,recovery,destroy=close_owned(cleanup_provider,owner,OUT,lease['baseline_volumes'],lease['finite_policy'],user_hold=not passed)
            save(OUT/'outer_stop.json',stop);save(OUT/'outer_recovery.json',recovery);save(OUT/'outer_destroy.json',destroy)
            if destroy.get('status')=='DESTROY_CONFIRMED':
                reconcile_destroyed(cleanup_provider,owner,OUT,policy['ledger_path'],destroy)
                settled=True
        except BaseException as error:
            failure=(failure+'; ' if failure else '')+'CLEANUP:'+repr(error);save(OUT/'preservation_exception.json',dict(error=repr(error)))
        if settled and watch is not None:
            try:watch.wait(timeout=5)
            except subprocess.TimeoutExpired:watch.terminate();watch.wait(timeout=5)
        save(OUT/'repair_closeout.json',dict(passed=passed and settled,execution_passed=passed,budget_settled=settled,failure=failure,owner=owner,destroy=destroy,first_allocation_monotonic_ns=owner['allocation_monotonic_ns'],lease_seconds=lease_seconds,new_rentals=0,B_reexecutions=0,local_project_dynamic_tests=0,raw_files={p.relative_to(OUT).as_posix():SHA(p) for p in OUT.rglob('*') if p.is_file()}))
    print(json.dumps(dict(repair_out=str(OUT),passed=passed and settled,failure=failure,budget_settled=settled)))
    return 0 if passed and settled else 2

if __name__=='__main__':raise SystemExit(main())
