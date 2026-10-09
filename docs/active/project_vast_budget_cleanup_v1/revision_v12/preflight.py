"""Administrative pre-rental recovery prerequisites; no provider mutations."""
from pathlib import Path
import hashlib, json, shutil, subprocess, time


def require_tools(cli, key, *, which=shutil.which, run=subprocess.run, transfer_mode="PROVIDER_RSYNC"):
    paths={'vastai':str(Path(cli).resolve())}
    if not Path(paths['vastai']).is_file() or not Path(key).is_file() or not Path(str(key)+'.pub').is_file():
        raise ValueError('CLI_KEY_PUBLIC_KEY_REQUIRED_BEFORE_RENT')
    if transfer_mode not in ('SCP_O','PROVIDER_RSYNC'):raise ValueError('UNKNOWN_TRANSFER_MODE')
    for name in (('ssh','scp') if transfer_mode=='SCP_O' else ('ssh','scp','rsync')):
        found=which(name)
        if not found or not Path(found).is_file():
            raise ValueError('MISSING_RECOVERY_TOOL_BEFORE_RENT:'+name)
        paths[name]=str(Path(found).resolve())
    versions={}
    for name,args in [('vastai',['--version']),('ssh',['-V']),*((('rsync',['--version']),) if transfer_mode=='PROVIDER_RSYNC' else ())]:
        result=run([paths[name],*args],capture_output=True,timeout=8)
        raw=result.stdout+result.stderr
        if result.returncode!=0 or not raw.strip():raise ValueError('RECOVERY_TOOL_VERSION_FAILED:'+name)
        versions[name]=raw.decode('utf-8',errors='replace')[:4096]
    public=Path(str(key)+'.pub').read_text(encoding='utf-8').strip().split()
    if len(public)<2 or public[0] not in ('ssh-ed25519','ssh-rsa'):
        raise ValueError('SSH_PUBLIC_KEY_CONTENT_REQUIRED')
    return dict(status='LOCAL_TOOLS_PRESENT_NOT_REMOTE_TRANSPORT_VERIFIED',paths=paths,versions=versions,
        hashes={name:hashlib.sha256(Path(path).read_bytes()).hexdigest() for name,path in paths.items()},
        public_key_sha256=hashlib.sha256(Path(str(key)+'.pub').read_bytes()).hexdigest())


def require_finite_policy(policy):
    if policy.get('schema')!='FINITE_SETUP_CLOSURE_V2':raise ValueError('FINITE_POLICY_SCHEMA')
    for name,maximum in [('lease_seconds',3600),('recovery_seconds',180),('cleanup_seconds',220),('recovery_attempts',3)]:
        value=policy.get(name)
        if type(value) is not int or not 0<value<=maximum:raise ValueError('FINITE_POLICY_BOUND:'+name)
    if policy['lease_seconds'] not in (1200,1800,3600) or policy['cleanup_seconds']!=220:
        raise ValueError('FINITE_POLICY_MUST_MATCH_FROZEN_LEASE_AND_RESERVED_CLEANUP')
    if policy['recovery_seconds']+policy['cleanup_seconds']>=policy['lease_seconds']:
        raise ValueError('NO_FINITE_EXECUTION_WINDOW')
    if policy['lease_seconds']==1800:
        from execution_authority import require_paid_approval
        if policy.get('v12_new_window') is not True:raise ValueError('V12_FRESH_TIME_APPROVAL_REQUIRED')
        require_paid_approval(policy['paid_approval_path'],policy['paid_approval_sha256'])
    if policy['lease_seconds']==3600:
        require_time_extension(policy)
    if policy['lease_seconds']==2400:
        if hashlib.sha256(Path(policy['cap_time_amendment_path']).read_bytes()).hexdigest()!=policy.get('cap_time_amendment_sha256') or policy.get('cap_time_amendment_sha256')!='163e9ae386d68559e0e19423f0cdb968a7dc9d3c0af2e98327559c146e71d751':raise ValueError('EXACT_APPROVED_TIME_EXTENSION_REQUIRED')
    consent=policy.get('prelease_setup_loss_consent')
    if not isinstance(consent,dict) or consent.get('accepted') is not True:
        raise ValueError('NO_PRELEASE_FINITE_SETUP_DISCARD_CONSENT_NO_RENT')
    raw=Path(consent['raw_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=consent.get('raw_sha256'):
        raise ValueError('FINITE_CONSENT_RAW_DRIFT')
    if consent.get('scope')!='SETUP_NAMED_CREATED_ONLY_NO_UNKNOWN_NO_IMPORTANT_RAW' or consent.get('named_files')!=['runtime_setup.log','runtime_ready']:
        raise ValueError('FINITE_CONSENT_SCOPE')
    return True


def before_any_rental(cli,key,policy,out,*,which=shutil.which,run=subprocess.run):
    """Called before importing/entering any legacy create path."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    try:
        tools=require_tools(cli,key,which=which,run=run,transfer_mode=policy.get('transfer_mode','PROVIDER_RSYNC'))
        require_finite_policy(policy)
        record=dict(status='LOCAL_PREFLIGHT_ACCEPTED_REMOTE_COMMAND_STILL_UNCONFIRMED',tools=tools,
                    policy_sha256=hashlib.sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest())
    except Exception as error:
        record=dict(status='REFUSED_BEFORE_ANY_PROVIDER_CALL',error=repr(error),created_instances=0)
        with (out/'preflight_refused.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
        raise
    with (out/'preflight_accepted.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
    return record

def require_time_extension(policy):
    raw=Path(policy['time_extension_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=policy['time_extension_sha256']:raise ValueError('TIME_EXTENSION_RAW_DRIFT')
    packet=json.loads(raw)
    if (packet.get('accepted') is not True or packet.get('instance_id')!=55040957 or packet.get('machine_id')!=53859 or packet.get('requested_absolute_maximum_seconds')!=3600 or not packet.get('actual_human_answer')):raise ValueError('ACTUAL_SAME_SERVER_TIME_EXTENSION_NOT_APPROVED')
