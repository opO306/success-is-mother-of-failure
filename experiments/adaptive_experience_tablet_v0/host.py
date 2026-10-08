"""Read-only qualifications outside the unchanged environment identity."""
import copy
import math
from experiments.adaptive_execution_v1 import environment as ENV


def describe(env, *, quota_observation='UNKNOWN', core_classes='UNKNOWN', provenance='UNKNOWN'):
    return dict(env=copy.deepcopy(env),quota_observation=quota_observation,core_classes=core_classes,
                provenance=provenance,cache='UNKNOWN',numa='UNKNOWN',isa='UNKNOWN')


def qualified(info):
    env=info['env']; cpus=env.get('allowed_cpus')
    if env.get('env_id')!=ENV.env_id(env): raise ValueError('ENV_ID_INTEGRITY')
    if env.get('platform')!='linux': raise ValueError('PLATFORM_NOT_QUALIFIED_V0')
    if info.get('core_classes')!='HOMOGENEOUS' or info.get('provenance') in (None,'','UNKNOWN'):
        raise ValueError('CORE_CLASS_ATTESTATION_REQUIRED')
    if not isinstance(cpus,list) or not cpus or any(type(c) is not int or c<0 for c in cpus) or len(set(cpus))!=len(cpus):
        raise ValueError('CPU_AFFINITY_INVALID')
    cores=env.get('core_of_cpu',{})
    if any(not isinstance(cores.get(str(c)),str) or not cores[str(c)].strip() for c in cpus):
        raise ValueError('CORE_IDENTIFICATION_REQUIRED')
    quota=env.get('cpu_quota')
    if quota is None:
        if info.get('quota_observation')!='OBSERVED_UNLIMITED': raise ValueError('QUOTA_OBSERVATION_REQUIRED')
    elif (type(quota) not in (int,float) or not math.isfinite(quota) or quota<=0
          or info.get('quota_observation')!='OBSERVED_FINITE'):
        raise ValueError('QUOTA_OBSERVATION_INVALID')
    return copy.deepcopy(env)


def compare(past, current):
    """Model equality has descriptive value only, never performance authority."""
    return dict(same_model=past.get('cpu_model')==current.get('cpu_model'),
                same_environment=past.get('env_id')==current.get('env_id'),
                changed=[key for key in ('platform','os_release','python','mpmath_version','mpmath_backend',
                         'cpu_model','allowed_cpus','core_of_cpu','cpu_quota') if past.get(key)!=current.get(key)])
