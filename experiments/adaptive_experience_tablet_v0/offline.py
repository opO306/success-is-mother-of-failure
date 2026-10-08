"""Source-bound offline gate. CLI refuses execution without a fresh external lease.

No network client, rental, restart, signature/private key or calculator entrypoint.
The existing outside-guest guardian must enforce recovery/termination deadlines.
"""
import argparse
import copy
import hashlib
import os
import platform
import subprocess
import sys
import time
import tracemalloc
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from experiments.adaptive_execution_real_learning_pilot_v0.common import canonical,digest,raw_hash,write_new,ROOT
from experiments.evidence_canonicalization_v0.fingerprints import parse_bytes

HERE=Path(__file__).resolve().parent


def read(path): return parse_bytes(Path(path).read_bytes())
def protocol_hash(): return raw_hash(HERE/'protocol.json')


def check_sources():
    for name in ('protocol_seal.json','preservation_manifest.json','code_seal.json'):
        for relative,wanted in read(HERE/name)['files'].items():
            path=(ROOT/relative).resolve()
            if not path.is_relative_to(ROOT.resolve()) or raw_hash(path)!=wanted:
                raise ValueError('SOURCE_SEAL_INTEGRITY:'+relative)
    return raw_hash(HERE/'code_seal.json')


def validate_status(status,code,expected):
    if (status.get('status')!='PASS' or status.get('code_sha256')!=code or status.get('protocol_sha256')!=protocol_hash()
            or status.get('tests')!=expected or any(status.get(k)!=0 for k in ('failed','errors','skipped','physics_calls','gpu_calls'))
            or status.get('benchmark_complete') is not True): raise ValueError('TABLET_OFFLINE_GATE_REFUSED')


def authorize(ticket,armed,*,instance,code,now=None):
    now=datetime.now(timezone.utc) if now is None else now
    def age(value):
        parsed=datetime.fromisoformat(value)
        if parsed.tzinfo is None: raise ValueError('UTC_TIMESTAMP_REQUIRED')
        return (now-parsed).total_seconds()
    if (platform.system()!='Linux' or ticket.get('gate')!='ADAPTIVE_EXPERIENCE_TABLET_CPU_ROUTE_V0'
            or ticket.get('scope')!='OFFLINE_ONLY' or ticket.get('explicit_user_approval') is not True
            or not ticket.get('approval_reference') or ticket.get('code_sha256')!=code
            or ticket.get('protocol_sha256')!=protocol_hash() or str(ticket.get('instance_id'))!=str(instance)
            or ticket.get('physics_calls')!=0 or ticket.get('gpu_calls')!=0
            or armed.get('status')!='ARMED' or armed.get('outside_guest') is not True
            or any(ticket.get(k)!=armed.get(k) for k in ('instance_id','machine_id','country','approval_reference'))
            or armed.get('guardian_sha256')!=raw_hash(ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py')
            or type(armed.get('deadline_seconds')) is not int or not 1<=armed['deadline_seconds']<=420
            or armed.get('confirmation_seconds')!=180
            or ticket.get('armed_sha256')!=digest(armed) or ticket.get('allocation_seconds')!=600):
        raise ValueError('FRESH_EXTERNAL_OFFLINE_APPROVAL_REQUIRED')
    rate=Decimal(str(armed.get('hourly_usd')))
    if not rate.is_finite() or not 0<=rate<=Decimal('0.25') or rate*600/3600>Decimal('0.05'):
        raise ValueError('PRICE_CAP_REFUSED')
    allocation_age=age(ticket['allocation_start_utc']); armed_age=age(armed['armed_utc'])
    if not 0<=armed_age<=allocation_age<300: raise ValueError('INSUFFICIENT_REMAINING_OFFLINE_BUDGET')
    # Guardian's 420s starts at ARMED; reject if confirmation could exceed total 600s.
    if allocation_age-armed_age+armed['deadline_seconds']+180>600:
        raise ValueError('GUARDIAN_LEASE_MUST_BE_NARROWED_TO_ALLOCATION_START')
    return ticket


def benchmark(env,experience_loader):
    from .catalog import Tablet
    from . import routes,host
    rules=read(HERE/'protocol.json')['benchmark']; results=[]
    request=dict(N=14,T=1000,start_p=163,actual_p=163,goal='WALL_MIN',
                 physics=env['contracts']['physics'],numeric=env['contracts']['numeric'],source_sha256='SYNTHETIC_INDEX_ONLY')
    def samples(call):
        walls=[]; cpus=[]; peaks=[]
        for _ in range(rules['repeats']):
            tracemalloc.start(); wall=time.perf_counter_ns(); cpu=time.process_time_ns()
            try:
                result=call(); cpus.append(time.process_time_ns()-cpu); walls.append(time.perf_counter_ns()-wall)
                _,peak=tracemalloc.get_traced_memory(); peaks.append(peak)
            finally: tracemalloc.stop()
        return dict(wall_median_ns=sorted(walls)[len(walls)//2],wall_max_ns=max(walls),
                    process_cpu_median_ns=sorted(cpus)[len(cpus)//2],traced_peak_delta_bytes=max(peaks))
    for count in rules['sizes']:
        tracemalloc.start()
        try:
            entries=[dict(profile_id=f'{i:064x}',reference_id=f'{i:064x}',session_sha256=f'{i:064x}',
                          key=dict(request,source_sha256=f'SYNTHETIC:{i}'),repeats={'SERIAL':5,'W6':5},
                          env_id='SYNTHETIC',cpu_model='SYNTHETIC') for i in range(count)]
            table=object.__new__(Tablet); table._index=dict(schema='TABLET_V0_INDEX',entries=entries,refused=[])
            table._build_buckets(); _,peak=tracemalloc.get_traced_memory()
        finally: tracemalloc.stop()
        key=entries[count//2]['key']; measured=samples(lambda:table.search(key))
        results.append(dict(records=count,index_bytes=len(canonical(table._index)),build_traced_peak_bytes=peak,
                            lookup=measured,lookup_target_met=measured['wall_median_ns']<=rules['index_lookup_median_ns_target']))
    env=copy.deepcopy(env); env.update(platform='linux',allowed_cpus=[2,7,11,19,23,31],cpu_quota=6,
                core_of_cpu={str(c):f'0:{i}' for i,c in enumerate([2,7,11,19,23,31])})
    from experiments.adaptive_execution_v1 import environment as ENV
    env['env_id']=ENV.env_id(env)
    info=host.describe(env,quota_observation='OBSERVED_FINITE',core_classes='HOMOGENEOUS',provenance='SYNTHETIC_OFFLINE_BENCHMARK')
    route_cost=samples(lambda:routes.candidates(request,info))
    selected_cost=samples(experience_loader)
    import psutil
    cpu_model=None
    try:
        cpu_model=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    except (OSError,StopIteration): pass
    return dict(scope='SYNTHETIC_INDEX_AND_MOCK_ROUTES; SELECTED_HISTORICAL_EVIDENCE_REREAD',repeats=rules['repeats'],
                host=dict(platform=platform.platform(),python=platform.python_version(),cpu_model=cpu_model,
                          affinity=sorted(os.sched_getaffinity(0)),quota='EXTERNAL_LEASE_ONE_CPU',
                          process_rss_bytes=psutil.Process().memory_info().rss),
                index_growth=results,route_generation=route_cost,selected_evidence_validation=selected_cost,
                memory_scope='tracemalloc Python heap peak, not aggregate native RSS or transient process-tree peak',
                physics_calls=0,gpu_calls=0,complete=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--authorization',required=True,type=Path)
    parser.add_argument('--armed',required=True,type=Path); parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(); code=check_sources(); ticket=read(args.authorization); armed=read(args.armed)
    authorize(ticket,armed,instance=os.environ.get('CONTAINER_ID'),code=code)
    args.out.mkdir(parents=True,exist_ok=False); write_new(args.out/'authorization_used.json',ticket)
    import resource
    import psutil
    from experiments.adaptive_execution_real_learning_pilot_v0.resources import Watch
    from experiments.adaptive_execution_real_learning_pilot_v0.bridge import deadline,cpu_clock
    start=time.monotonic_ns(); first=cpu_clock()
    resource.setrlimit(resource.RLIMIT_CPU,(120,120)); resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0)); os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    def monitor():
        members=[psutil.Process(),*psutil.Process().children(recursive=True)]; rss=0; live=0
        for member in members:
            try:
                rss+=member.memory_info().rss
                if member.pid!=os.getpid(): t=member.cpu_times(); live+=int((t.user+t.system)*10**9)
            except psutil.NoSuchProcess: pass
        now=cpu_clock()
        if rss>512*1024**2 or sum(now[k]-first[k] for k in now)+live>120*10**9: raise ValueError('RESOURCE_CAP_STOP')
        if not args.armed.exists() or digest(read(args.armed))!=digest(armed): raise ValueError('EXTERNAL_GUARDIAN_BINDING_LOST')
    watch=Watch(time.monotonic()+120,monitor); watch.start()
    try:
        with deadline(120):
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                     EVIDENCE_PHYSICS_GUARD_REPORT=str(args.out.resolve()/'physics_guard.json'))
            with (args.out/'tests.log').open('xb') as log:
                proc=subprocess.run([sys.executable,'-m','pytest',*read(HERE/'protocol.json')['offline']['test_files'],'-q',
                     '-p','no:cacheprovider','-p','experiments.evidence_canonicalization_v0.physics_guard',
                     '--junitxml='+str(args.out.resolve()/'junit.xml')],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=95)
            cases=ET.parse(args.out/'junit.xml').getroot().findall('.//testcase')
            failed=sum(x.find('failure') is not None for x in cases); errors=sum(x.find('error') is not None for x in cases)
            skipped=sum(x.find('skipped') is not None for x in cases); expected=read(HERE/'code_seal.json')['expected_tests']
            guard=read(args.out/'physics_guard.json')
            if proc.returncode or len(cases)!=expected or failed or errors or skipped or guard.get('blocked_attempts'):
                raise ValueError('TEST_GATE_STOP')
            from .catalog import Tablet
            from experiments.adaptive_execution_real_learning_pilot_v0.governance import Roots
            original=ROOT/'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/run_20261008_approved_3/recovered/output_actual'
            tablet=Tablet(args.out/'tablet',original,Roots(**read(original/'manager/roots.json')))
            entry=tablet.register('A','b775509603dc3f07e578ccce4aea11021cee013c7eea8feb8268f01a8e91482f','manager/events/event_000000.json')
            result=benchmark(read(original/'A/session.json')['env'],lambda:tablet.load(entry))
            result['reference_bytes']=(tablet.directory/'references'/f"{entry['reference_id']}.json").stat().st_size
            write_new(args.out/'benchmark.json',result); monitor(); check_sources()
            end=cpu_clock(); wall=time.monotonic_ns()-start; cpu=sum(end[k]-first[k] for k in end)
            if max(wall,cpu)>120*10**9: raise ValueError('TOTAL_BUDGET_STOP')
            status=dict(status='PASS',tests=len(cases),failed=failed,errors=errors,skipped=skipped,wall_ns=wall,cpu_ns=cpu,
                        physics_calls=0,gpu_calls=0,code_sha256=code,protocol_sha256=protocol_hash(),benchmark_complete=True,
                        cost_goal_met=all(row['lookup_target_met'] for row in result['index_growth']))
            validate_status(status,code,expected); write_new(args.out/'status.json',status)
            return 0
    except BaseException as error:
        write_new(args.out/'status.json',dict(status='STOP',reason=str(error),code_sha256=code,protocol_sha256=protocol_hash()))
        return 2
    finally: watch.close()


if __name__=='__main__': raise SystemExit(main())
