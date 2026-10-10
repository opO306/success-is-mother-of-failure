"""V12.4 = V12.3 + A package revision 2 (one test-order fix; designer decision 2026-10-10, package_v2.py).

Everything below is the V12.3 description; the only V12.4 additions are the package_v2 attachment points
(controller configure/verify/guest verifier, campaign source_preflight/transport_binding, terminal_proof) and a
pre-approval package gate in main(). Original V12.3 text:

V12.3: run the unchanged V12 fresh-rental stage with the V12.2 read repairs attached.

Only the server-acquisition/administration layer changes. A320 cases, verdicts, search 3x31, physics and
budget accounting are the sealed V12 originals. Attachment points (all in-process, V12 files unchanged):
  campaign.Provider        -> ReadRetryProvider (reads only, inside caller timeout)
  controller Transport     -> V12.2 transport_class (A320 transport show/control reads)
  watchdog/supervisor/guardian subprocesses -> process_bridge (same reads, V12.3 approval, closure guard)
  campaign.remote_admin    -> + read-only fingerprint, then original V12 admin/probe, then V12.2 new admin
                              regression and actual SSH-disconnect probe (all before A320)
  execution_authority      -> V12.3 approval schema bound to this folder's seal
  cleanup.verify_admin     -> also requires the V12.3 extra jobs' closed originals before any delete
"""
import argparse
from datetime import datetime,timezone
import hashlib,importlib.util,json,shlex,sys,time,types
from pathlib import Path

HERE=Path(__file__).resolve().parent
V12=HERE.parent/'revision_v12'
V12_2=HERE.parent/'revision_v12_2'
CONTROLLER=(V12/'transport/controller.py').resolve()
PRIVATE=Path('C:/Users/zun24/.codex/evidence/project_vast_budget_cleanup_v1_20261009')
CLI=Path('C:/Users/zun24/AppData/Local/Programs/Python/Python312/Scripts/vastai.exe')
KEY=Path('C:/Users/zun24/.ssh/vast_ai')
PY='/usr/local/bin/python3'

sys.path[:0]=[str(HERE)]
import process_bridge
process_bridge.paths()
import package_v2


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_seal(base=HERE.parent):
    seal=json.loads((HERE/'operational_seal.json').read_bytes())
    for relative,wanted in seal['files'].items():
        if sha(base/relative)!=wanted:raise ValueError('V12_3_SOURCE_DRIFT:'+relative)
    return seal


def transport_loader_shim(wrap):
    """campaign.stage/remote_admin load controller.py by file path each time; wrap Transport right after exec."""
    real=importlib.util
    class Loader:
        def __init__(self,inner):self.inner=inner
        def create_module(self,spec):return self.inner.create_module(spec)
        def exec_module(self,module):
            self.inner.exec_module(module)
            wrap(module)
    def spec_from_file_location(name,location,*args,**kwargs):
        spec=real.spec_from_file_location(name,location,*args,**kwargs)
        if Path(location).resolve()==CONTROLLER:spec.loader=Loader(spec.loader)
        return spec
    return types.SimpleNamespace(util=types.SimpleNamespace(spec_from_file_location=spec_from_file_location,module_from_spec=real.module_from_spec))


FINGERPRINT=r'''import json,os,pathlib,platform,sys
expected=sys.argv[1]
ids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'CONTAINER_ID=')]
if ids!=[expected]:raise ValueError('FINGERPRINT_ACTUAL_INSTANCE')
def r(p):
    try:return pathlib.Path(p).read_text(errors='replace')[:262144]
    except Exception as e:return 'UNREADABLE:'+repr(e)
try:affinity=sorted(os.sched_getaffinity(0))
except Exception as e:affinity='UNREADABLE:'+repr(e)
print(json.dumps(dict(instance_id=int(expected),role='READ_ONLY_FINGERPRINT_NOT_A_VERDICT_INPUT',cpuinfo=r('/proc/cpuinfo'),
    cpu_online=r('/sys/devices/system/cpu/online'),cgroup_cpu_max=r('/sys/fs/cgroup/cpu.max'),meminfo=r('/proc/meminfo')[:4096],
    uname=list(platform.uname()),python=sys.version,cpu_count=os.cpu_count(),affinity=affinity)))'''


def fingerprint(campaign,out,ssh,owner,watch):
    """Read-only record for later machine comparison. Never a verdict input; failure is recorded, not hidden."""
    try:
        campaign.command(out/'v12_3_fingerprint_io',ssh+[shlex.join([PY,'-B','-c',FINGERPRINT,str(owner['instance_id'])])],'fingerprint',20,watch=watch)
    except Exception as error:
        if watch.poll() is not None:raise
        campaign.save(out/'v12_3_fingerprint_failure.json',dict(error=repr(error),affects_verdict=False))


MKDIR=("import pathlib,sys\nids=[v.split(b'=',1)[1].decode() for v in pathlib.Path('/proc/1/environ').read_bytes().split(b'\\0') if v.startswith(b'CONTAINER_ID=')]\n"
       "if ids!=[sys.argv[2]]:raise ValueError('V12_3_ACTUAL_INSTANCE_MISMATCH')\np=pathlib.Path(sys.argv[1])\n"
       "if p.parent!=pathlib.Path('/workspace') or p.resolve()!=p or p.exists():raise ValueError('V12_3_EXCLUSIVE_ROOT')\np.mkdir()")
EXTRACT=("import pathlib,sys,hashlib,zipfile,stat\np=pathlib.Path(sys.argv[1]);zpath=p/'repair_admin.zip'\n"
         "if hashlib.sha256(zpath.read_bytes()).hexdigest()!=sys.argv[2]:raise ValueError('REPAIR_ADMIN_SOURCE_PIN')\n"
         "with zipfile.ZipFile(zpath) as z:\n if len(z.namelist())!=6 or len(set(z.namelist()))!=6 or z.testzip():raise ValueError('REPAIR_ADMIN_MEMBERS')\n"
         " for i in z.infolist():\n  n=i.filename\n  if n not in {'read_retry.py','transport_reads.py','test_read_retry.py','test_transport_reads.py','guest_admin_runner.py','admin_test_inventory.json'} or i.is_dir() or i.flag_bits&1 or stat.S_IFMT(i.external_attr>>16) not in (0,stat.S_IFREG):raise ValueError('REPAIR_ADMIN_SCOPE')\n z.extractall(p)")


def v12_2_regression(campaign,out,ssh,owner,watch,policy,key):
    """V12.2 new admin tests and actual SSH-disconnect probe (continue_owned.py:135-192 logic) on this fresh server."""
    from lifecycle import identity
    from budget import money
    from transport_reads import transport_class
    from job_proof import closed_archive
    from admin_revalidation import SafetyStop
    stop_at=owner['allocation_monotonic_ns']/1e9+policy['lease_seconds']-220
    def check():
        if watch.poll() is not None:raise SafetyStop('LEASE_WATCHDOG_LOST')
    spec=importlib.util.spec_from_file_location('v12_3_regression_transport',CONTROLLER)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure('A')
    ReadsTransport=transport_class(m,float('inf'),check)
    provider=campaign.Provider(str(CLI),out/'v12_3_control_api')
    def control(required_seconds,phase_deadline=None):
        check();left=stop_at-time.monotonic()
        if left<required_seconds+650:raise SafetyStop('V12_3_WINDOW_FULL_A_AND_CLEANUP_REQUIRED')
        budget=min(24,left) if phase_deadline is None else min(24,left,phase_deadline-time.monotonic())
        if budget<=0:raise TimeoutError('UNCHANGED_PROBE_RPC_DEADLINE')
        row=identity(provider.call('show','instance',owner['instance_id'],timeout=budget),owner)
        check()
        if phase_deadline is not None and time.monotonic()>=phase_deadline:raise TimeoutError('UNCHANGED_PROBE_RPC_DEADLINE')
        if (row['actual_status']!='running' or row['intended_status']!='running' or row.get('public_ipaddr')!=owner['public_ipaddr']
            or {r.get('HostPort') for r in row.get('ports',{}).get('22/tcp',[])}!={str(owner['direct_ssh_port'])}
            or money(row['dph_total'])>money(owner['observed_rate_usd'])):raise SafetyStop('V12_3_ACTUAL_MAPPING_OR_RATE_DRIFT')
    def prepare(t,auth,guest,io):
        t.guest=guest;t.remote_created=True;t.identity_verified=True;t.ssh_argv=ssh
        t.start_ns=owner['allocation_monotonic_ns'];t.started_utc=owner['allocation_start_utc']
        t.handoff=lambda:policy['lease_seconds']-220;t.stop_control_check=check;t.control=control
        return t
    base=dict(owner,ssh_host=owner['public_ipaddr'],ssh_port=owner['direct_ssh_port'],known_hosts_file=str(out/'known_hosts'))
    payload=V12_2/'admin_payload.zip'
    # 1. New administrative regression (24 new functions + 6 affected V12 files) before any A command.
    admin_io=out/'v12_3_admin_job';admin_io.mkdir()
    admin_guest='/workspace/vast_budget_admin_v12_3_'+owner['run_id']
    admin_auth=dict(base,run_id=owner['run_id']+'_v12_3_admin')
    campaign.save(out/'v12_3_admin_started.json',dict(instance_id=owner['instance_id'],payload_sha256=sha(payload),guest=admin_guest))
    control(90+96+40)
    campaign.command(admin_io,ssh+[shlex.join([PY,'-B','-c',MKDIR,admin_guest,str(owner['instance_id'])])],'mkdir',15,watch=watch)
    admin=prepare(ReadsTransport(admin_auth,str(CLI),key,admin_io),admin_auth,admin_guest,admin_io)
    admin.evidence_job_role='ADMIN_TESTS';admin.evidence_code_sha256=sha(payload)
    admin.upload(payload,'repair_admin.zip','repair_admin_upload',25)
    campaign.command(admin_io,ssh+[shlex.join([PY,'-B','-c',EXTRACT,admin_guest,admin.evidence_code_sha256])],'extract',15,watch=watch)
    observed=admin.run_remote_job([PY,'-B',admin_guest+'/guest_admin_runner.py','/workspace/vast_budget_admin_'+owner['run_id'],str(owner['instance_id'])],
                                  sha(V12_2/'guest_admin_runner.py'),timeout_seconds=90)
    admin.recover_final()
    campaign.save(out/'v12_3_admin_closed_originals.json',dict(owner=admin_auth,folder=str(admin_io),code_sha256=admin.evidence_code_sha256,
                                                              proof=closed_archive(admin_io,admin_auth,admin.evidence_code_sha256)))
    result=campaign.read(admin_io/'recovered/repair_result.json');campaign.save(out/'v12_3_admin_result.json',result)
    if observed['state']!='EXITED_SUCCESS' or result.get('passed') is not True:raise ValueError('V12_3_NEW_ADMIN_REGRESSION_FAILED_NO_A_STARTED')
    # 2. Actual SSH client termination while a detached writer keeps running (V12.2 probe_runner, 60 s writer).
    io=out/'v12_3_disconnect_probe';io.mkdir()
    guest='/workspace/vast_budget_probe_v12_3_'+owner['run_id']
    probe_auth=dict(base,run_id=owner['run_id']+'_v12_3_probe')
    campaign.command(io,ssh+[shlex.join([PY,'-B','-c',MKDIR,guest,str(owner['instance_id'])])],'mkdir',15,watch=watch)
    campaign.save(out/'v12_3_probe_started.json',dict(instance_id=owner['instance_id'],guest=guest))
    class Probe(ReadsTransport):
        def py(self,script_name,args,name,timeout=30,phase_deadline=None,required_seconds=None):
            if script_name!='guest_disconnect_launch.py':return super().py(script_name,args,name,timeout,phase_deadline,required_seconds)
            self.control(90+96+8)
            return self.run([*ssh,shlex.join([PY,'-B','-',*map(str,args)])],name,8,input=(V12_2/'disconnect_launch.py').read_bytes())
    t=prepare(Probe(probe_auth,str(CLI),key,io),probe_auth,guest,io)
    t.evidence_job_role='ADMIN_PROBE';t.evidence_code_sha256=sha(payload)
    for n in ('read_retry.py','test_read_retry.py','probe_runner.py'):t.upload(V12_2/n,n,'repair_upload_'+n,20)
    observed=t.run_remote_job([PY,'-B',guest+'/probe_runner.py'],sha(V12_2/'probe_runner.py'),timeout_seconds=90,disconnect_probe=True)
    t.recover_final()
    campaign.save(out/'v12_3_probe_closed_originals.json',dict(owner=probe_auth,folder=str(io),code_sha256=t.evidence_code_sha256,
                                                              proof=closed_archive(io,probe_auth,t.evidence_code_sha256)))
    result=campaign.read(io/'recovered/repair_result.json')
    if observed['state']!='EXITED_SUCCESS' or result.get('passed') is not True:raise ValueError('V12_3_ADMIN_AND_DISCONNECT_NOT_PASS')
    events=[json.loads(r) for r in (io/'events.jsonl').read_bytes().splitlines()]
    if not any(e.get('event')=='JOB_STATE_OBSERVED' and e.get('state')=='RUNNING' for e in events):raise ValueError('ACTUAL_LIVE_JOB_AFTER_SSH_DISCONNECTION_NOT_OBSERVED')
    campaign.save(out/'v12_3_disconnect_verified.json',dict(instance_id=owner['instance_id'],job_observation=observed,intentional_client_termination=True,
                                                           actual_running_after_disconnect=True,scope='ADMIN_PROBE_ONLY_NOT_A320',repair_tests=result))


def install_all():
    """Attach every V12.3 point; returns the V12 campaign module. Idempotent per process."""
    import authority;authority.install()
    import closure;closure.install()
    import campaign
    if getattr(campaign,'v12_3_installed',False):return campaign
    from reads import ReadRetryProvider
    from transport_reads import transport_class
    campaign.Provider=ReadRetryProvider
    def wrap(module):
        package_v2.patch_controller(module)
        module.Transport=transport_class(module,float('inf'),lambda:None)
    campaign.importlib=transport_loader_shim(wrap)
    original=campaign.remote_admin
    def remote_admin(out,ssh,scp_prefix,owner,watch,policy):
        fingerprint(campaign,out,ssh,owner,watch)
        original(out,ssh,scp_prefix,owner,watch,policy)
        v12_2_regression(campaign,out,ssh,owner,watch,policy,str(KEY))
    campaign.remote_admin=remote_admin
    package_v2.install_campaign(campaign)
    package_v2.install_recovery()
    process_bridge.install_dispatch()
    campaign.v12_3_installed=True
    return campaign


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--approval',required=True,type=Path)
    parser.add_argument('--approval-sha256',required=True)
    args=parser.parse_args(argv)
    verify_seal()
    campaign=install_all()
    package_gate=package_v2.preflight(campaign,CONTROLLER)  # local files only; before approval use or any Provider call
    from authority import require_paid_approval,claim_paid_approval
    require_paid_approval(args.approval,args.approval_sha256)  # BEFORE every Provider call/reserve/rental
    from budget import Ledger,charge_total,money
    from admin_revalidation import SafetyStop
    policy=campaign.read(V12/'policy.json');campaign.source_preflight(policy)
    policy.update(_paid_approval_path=str(args.approval.resolve()),_paid_approval_sha256=args.approval_sha256)
    admission=PRIVATE/('v12_4_admission_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    finite=campaign.read(V12/'finite_policy.json')
    finite.update(lease_seconds=1800,v12_new_window=True,paid_approval_path=policy['_paid_approval_path'],paid_approval_sha256=args.approval_sha256)
    campaign.before_any_rental(CLI,KEY,finite,admission)
    campaign.save(admission/'v12_4_package_gate.json',package_gate)
    claim_paid_approval(args.approval,args.approval_sha256)
    provider=campaign.Provider(CLI,admission/'api');ledger=Ledger(policy['ledger_path'])
    if provider.instances() or provider.volumes():raise SafetyStop('V12_3_EXPECTED_EMPTY_BASELINE_NO_OTHER_RESOURCE_ACTIONS')
    display,count=charge_total(provider.charges())
    balance=ledger.append(dict(action='OBSERVE',historical_bound=str(display+money('.002')*count+money('.020')),reason='V12_4_PRELEASE_FRESH_CHARGES',observed_utc=campaign.utc()))
    if balance['active'] or balance['cap']!=money('2') or balance['remaining']<money('.20'):raise SafetyStop('V12_3_FRESH_BUDGET_BOUNDARY')
    B=Path(policy['B_stage_closeout'])
    if sha(B)!=policy['B_stage_closeout_sha256']:raise SafetyStop('B_SUCCESS_HISTORY_DRIFT')
    close_path=campaign.stage(policy,'A',provider,ledger,KEY,B_close=B)
    close=campaign.read(close_path)
    print(json.dumps(dict(stage_closeout=str(close_path),passed=close['passed'],failure=close['failure'],budget_settled=close['budget_settled'])))
    return 0 if close['passed'] else 2


if __name__=='__main__':raise SystemExit(main())
