"""Administrative observations, not physics or signing authority. Missing readiness is never permission."""
import json
import hashlib
from pathlib import Path
from decimal import Decimal, InvalidOperation
import subprocess

def decode(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('DUPLICATE_API_KEY:'+key)
            result[key]=value
        return result
    def invalid(value):raise ValueError('NONFINITE_API_JSON:'+value)
    data=json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    if not isinstance(data,dict):raise ValueError('API_OBJECT_REQUIRED')
    return data

def inspect(record,approval,role):
    if role not in ('initial','restart','control','final','guardian_initial','guardian_observe'):
        raise ValueError('EXPLICIT_OBSERVATION_ROLE_REQUIRED')
    if not isinstance(record,dict):raise ValueError('API_OBJECT_REQUIRED')
    country=record.get('country') or str(record.get('geolocation','')).rsplit(',',1)[-1].strip()
    if (type(record.get('id')) is not int or type(record.get('machine_id')) is not int
            or record['id']!=approval['instance_id'] or record['machine_id']!=approval['machine_id']
            or country!=approval['country']):raise ValueError('CORE_INSTANCE_MACHINE_COUNTRY_MISMATCH')
    try:rate=Decimal(str(record.get('dph_total')))
    except (InvalidOperation,ValueError):raise ValueError('OBSERVED_RATE_INVALID') from None
    if not rate.is_finite() or rate<0:raise ValueError('OBSERVED_RATE_INVALID')
    cap=Decimal(str(approval.get('hourly_cap_usd','0.25')))
    if cap not in (Decimal('0.25'),Decimal('0.28')):raise ValueError('HOURLY_CAP_NOT_APPROVED_PROFILE')
    if cap==Decimal('0.28'):
        if (approval.get('instance_id')!=52763685 or approval.get('machine_id')!=3448 or approval.get('country')!='NO'
            or approval.get('explicit_user_approval') is not True or approval.get('exclusive') is not True
            or not approval.get('admin_target_protocol_sha256')):raise ValueError('NO_HOURLY_EXCEPTION_APPROVAL_REQUIRED')
        protocol=Path(__file__).resolve().parent.parent/'target_protocol.json'
        if hashlib.sha256(protocol.read_bytes()).hexdigest()!=approval['admin_target_protocol_sha256']:
            raise ValueError('NO_CURRENT_PROTOCOL_RAW_PIN')
        authority=decode(protocol.read_bytes())
        if (authority.get('explicit_user_approval') is not True or authority.get('exclusive_stop_authorized') is not True
            or any(authority.get(k)!=approval.get(k) for k in ('instance_id','machine_id','country','hourly_cap_usd'))):
            raise ValueError('NO_CURRENT_PROTOCOL_AUTHORITY_MISMATCH')
    within=rate<=cap and rate*600/3600<=Decimal('0.05')
    if role not in ('final','guardian_observe') and not within:raise ValueError('PRICE_CAP')
    actual,intended=record.get('actual_status'),record.get('intended_status')
    if actual in ('exited','stopped') and intended=='stopped':state='STOPPED'
    elif actual in ('exited','stopped') and intended=='running':state='STARTING'
    elif actual=='running' and intended=='running':state='RUNNING'
    elif actual=='running' and intended=='stopped':state='STOPPING'
    else:raise ValueError('UNKNOWN_OR_ERROR_STATE')
    adopt=approval.get('allocation_mode')=='ADOPT_RUNNING'
    if adopt and (approval.get('schema')!='HUMAN_PAID_ADMIN_NO_52763685_V1' or approval.get('scope')!='ADMIN_SIMULATION_AND_ACTUAL_TRANSPORT_STOP_ONLY'
                  or approval.get('explicit_user_approval') is not True or approval.get('exclusive') is not True):raise ValueError('EXPLICIT_RUNNING_ADOPTION_REQUIRED')
    if role=='initial' and state!=('RUNNING' if adopt else 'STOPPED'):raise ValueError('EXCLUSIVE_ACTUAL_AND_INTENDED_STOPPED_REQUIRED')
    if role in ('control','guardian_initial') and state!='RUNNING':raise ValueError('RUNNING_INTENT_REQUIRED')
    ready=False
    if (role in ('restart','control') or (role=='initial' and adopt)) and state=='RUNNING':
        fields=dict(ssh_host=approval['api_ssh_host'],ssh_port=approval['api_ssh_port'],public_ipaddr=approval['ssh_host'])
        missing=False
        for key,wanted in fields.items():
            observed=record.get(key)
            if observed is None:missing=True
            elif observed!=wanted:raise ValueError('EXPLICIT_CONNECTION_MISMATCH:'+key)
        ports=record.get('ports')
        if ports is None:missing=True
        elif not isinstance(ports,dict):raise ValueError('PORT_MAPPING_OBJECT_REQUIRED')
        else:
            mapping=ports.get('22/tcp')
            if mapping is None or mapping==[]:missing=True
            elif not isinstance(mapping,list) or any(not isinstance(p,dict) for p in mapping):
                raise ValueError('SSH22_MAPPING_LIST_REQUIRED')
            else:
                observed={p.get('HostPort') for p in mapping}
                if observed!={str(approval['ssh_port'])}:raise ValueError('EXPLICIT_SSH22_PORT_MISMATCH')
        ready=not missing
        if (role=='control' or (role=='initial' and adopt)) and not ready:raise ValueError('RUNNING_CONNECTION_NOT_READY')
    return dict(state=state,connection_ready=ready,rate_within_cap=within,
                observed_hourly_usd=str(rate),actual_status=actual,intended_status=intended)

class CheckedCli:
    """Thin guard for existing guardian/fallback I/O; sends only exact leased show/stop commands."""
    def __init__(self,path,instance,approval,initial_role='guardian_observe'):
        if int(instance)!=approval['instance_id']:raise ValueError('CLI_LEASE_ID_MISMATCH')
        self.path,self.instance,self.approval=path,str(instance),approval
        self.timeout_seconds=12
        if initial_role not in ('guardian_initial','guardian_observe'):raise ValueError('CLI_ROLE_REQUIRED')
        self.role=initial_role
    def call(self,*args,decode_result=True):
        result=subprocess.run([self.path,'--raw','--retry','1',*args,self.instance],capture_output=True,timeout=self.timeout_seconds)
        if result.returncode:raise OSError('CONTROL_CLI_FAILURE')
        if not decode_result:return True
        record=decode(result.stdout)
        state=inspect(record,self.approval,self.role)
        if state['state']=='STARTING':raise ValueError('EXITED_WITH_RUNNING_INTENT_IS_NOT_STOPPED')
        self.role='guardian_observe'
        return record
    def show(self):return self.call('show','instance')
    def stop(self):
        self.role='guardian_observe'
        return self.call('stop','instance',decode_result=False)
