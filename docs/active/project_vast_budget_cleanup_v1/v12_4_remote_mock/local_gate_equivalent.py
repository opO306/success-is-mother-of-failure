"""Remote-PC (Linux/WSL) run of the A package offline gate body, without the paid-server lease checks.

Designer request (2026-10-10): "Vast 꼭 쓸거 야? 안써도 되면 로컬에서 최하영바보에서 테스트 ㄱㄱ".
Mirrors experiments/adaptive_experience_tablet_v0/offline.py main() after authorize(): same RLIMIT_CPU 120 s,
RLIMIT_AS 512 MiB, one CPU, 120 s wall deadline, resource monitor (RSS 512 MiB, CPU 120 s), the same pytest command
(protocol test files, physics guard plugin, 95 s timeout), the same tablet benchmark, check_sources and
validate_status. Removed on purpose, not faked: the ticket/armed authorization and the outside-guardian binding,
which only exist to stop a rented paid server. Result role: LOCAL_GATE_EQUIVALENT_NOT_VAST_OFFICIAL.
  python -I local_gate_equivalent.py ZIP ZIP_SHA256 DEST OUT
"""
import hashlib,json,os,subprocess,sys,time,zipfile
from pathlib import Path,PurePosixPath


def main():
    zip_path,zip_sha,dest,out=sys.argv[1],sys.argv[2],Path(sys.argv[3]).resolve(),Path(sys.argv[4]).resolve()
    if hashlib.sha256(Path(zip_path).read_bytes()).hexdigest()!=zip_sha:raise ValueError('ZIP_PIN')
    dest.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if name.startswith('/') or '..' in PurePosixPath(name).parts:raise ValueError('PATH_SCOPE')
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(z.read(name))
    sys.path.insert(0,str(dest));os.chdir(dest)
    from experiments.adaptive_experience_tablet_v0 import offline
    import xml.etree.ElementTree as ET
    code=offline.check_sources()
    out.mkdir(parents=True,exist_ok=False)
    import resource
    import psutil
    from experiments.adaptive_execution_real_learning_pilot_v0.resources import Watch
    from experiments.adaptive_execution_real_learning_pilot_v0.bridge import deadline,cpu_clock
    start=time.monotonic_ns();first=cpu_clock()
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    def monitor():
        members=[psutil.Process(),*psutil.Process().children(recursive=True)];rss=0;live=0
        for member in members:
            try:
                rss+=member.memory_info().rss
                if member.pid!=os.getpid():t=member.cpu_times();live+=int((t.user+t.system)*10**9)
            except psutil.NoSuchProcess:pass
        now=cpu_clock()
        if rss>512*1024**2 or sum(now[k]-first[k] for k in now)+live>120*10**9:raise ValueError('RESOURCE_CAP_STOP')
    record=dict(role='LOCAL_GATE_EQUIVALENT_NOT_VAST_OFFICIAL',zip_sha256=zip_sha,
                removed_checks=['ticket/armed authorization','outside guardian binding'],
                host=dict(kernel=os.uname().release,affinity=sorted(os.sched_getaffinity(0)),python=sys.version))
    watch=Watch(time.monotonic()+120,monitor);watch.start()
    try:
        with deadline(120):
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                     EVIDENCE_PHYSICS_GUARD_REPORT=str(out/'physics_guard.json'))
            with (out/'tests.log').open('xb') as log:
                proc=subprocess.run([sys.executable,'-m','pytest',*offline.read(offline.HERE/'protocol.json')['offline']['test_files'],'-q',
                     '-p','no:cacheprovider','-p','experiments.evidence_canonicalization_v0.physics_guard',
                     '--junitxml='+str(out/'junit.xml')],cwd=offline.ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=95)
            tests_done_ns=time.monotonic_ns()
            cases=ET.parse(out/'junit.xml').getroot().findall('.//testcase')
            failed=sum(x.find('failure') is not None for x in cases);errors=sum(x.find('error') is not None for x in cases)
            skipped=sum(x.find('skipped') is not None for x in cases);expected=offline.read(offline.HERE/'code_seal.json')['expected_tests']
            guard=offline.read(out/'physics_guard.json')
            if proc.returncode or len(cases)!=expected or failed or errors or skipped or guard.get('blocked_attempts'):
                raise ValueError('TEST_GATE_STOP')
            from experiments.adaptive_experience_tablet_v0.catalog import Tablet
            from experiments.adaptive_execution_real_learning_pilot_v0.governance import Roots
            original=offline.ROOT/'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/run_20261008_approved_3/recovered/output_actual'
            tablet=Tablet(out/'tablet',original,Roots(**offline.read(original/'manager/roots.json')))
            entry=tablet.register('A','b775509603dc3f07e578ccce4aea11021cee013c7eea8feb8268f01a8e91482f','manager/events/event_000000.json')
            result=offline.benchmark(offline.read(original/'A/session.json')['env'],lambda:tablet.load(entry))
            result['reference_bytes']=(tablet.directory/'references'/f"{entry['reference_id']}.json").stat().st_size
            offline.write_new(out/'benchmark.json',result);monitor();offline.check_sources()
            end=cpu_clock();wall=time.monotonic_ns()-start;cpu=sum(end[k]-first[k] for k in end)
            if max(wall,cpu)>120*10**9:raise ValueError('TOTAL_BUDGET_STOP')
            status=dict(status='PASS',tests=len(cases),failed=failed,errors=errors,skipped=skipped,wall_ns=wall,cpu_ns=cpu,
                        tests_wall_ns=tests_done_ns-start,physics_calls=0,gpu_calls=0,code_sha256=code,protocol_sha256=offline.protocol_hash(),
                        benchmark_complete=True,cost_goal_met=all(row['lookup_target_met'] for row in result['index_growth']))
            offline.validate_status({k:v for k,v in status.items() if k!='tests_wall_ns'},code,expected)
            offline.write_new(out/'status.json',dict(status,**record))
            print(json.dumps({k:status[k] for k in ('status','tests','failed','errors','skipped','wall_ns','cpu_ns','tests_wall_ns','cost_goal_met')}))
            return 0
    except BaseException as error:
        offline.write_new(out/'status.json',dict(status='STOP',reason=str(error),code_sha256=code,protocol_sha256=offline.protocol_hash(),**record))
        print(json.dumps(dict(status='STOP',reason=str(error))))
        return 2
    finally:watch.close()


if __name__=='__main__':raise SystemExit(main())
