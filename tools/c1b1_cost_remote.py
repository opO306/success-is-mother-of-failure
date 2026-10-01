"""Same-node cost bootstrap; preserve preflight failures and all warm-up/measured outputs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tarfile
import time
import traceback


def run(archive, expected_sha, destination, result_archive):
    destination = Path(destination)
    if os.name != 'posix':
        raise ValueError('remote bootstrap is Linux-only')
    if destination.exists():
        raise ValueError('new deployment directory required; never overwrite evidence')
    logs = destination/'deployment_logs'
    exit_code = 1
    try:
        if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != expected_sha:
            raise ValueError('uploaded archive hash mismatch')
        with tarfile.open(archive) as tf:
            names = set()
            for member in tf.getmembers():
                name = member.name;p = PurePosixPath(name)
                if not member.isfile() or p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name or name.casefold() in names:
                    raise ValueError('unsafe or duplicate archive entry')
                names.add(name.casefold())
            destination.mkdir(parents=True)
            tf.extractall(destination,filter='data')
        logs.mkdir()
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('package_check',destination/'package_check.py')
        checker = importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        verified = checker.verify(destination)
        (logs/'package_verified.json').write_text(json.dumps(verified,indent=2)+'\n')
        print('REMOTE PACKAGE VERIFIED',json.dumps(verified),flush=True)
        code = destination/'code'
        out = code/'runs/c1b1_kdk20_yoshida40_cost_v1'
        env = os.environ.copy()
        env.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                   MPMATH_NOGMPY='1',C1B1_REMOTE_BENCHMARK='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
        environment = dict(start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),python=sys.version,
                           platform=platform.platform(),affinity=sorted(os.sched_getaffinity(0)),gpu_compute=False,
                           lscpu=subprocess.check_output(['lscpu','-J'],text=True),
                           cpu_slots=subprocess.check_output(['lscpu','-e=CPU,CORE,SOCKET,MAXMHZ'],text=True),
                           meminfo=Path('/proc/meminfo').read_text().splitlines()[:3])
        (logs/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
        venv = destination/'venv'
        subprocess.run([sys.executable,'-m','venv',str(venv)],check=True,timeout=60)
        python = str(venv/'bin/python')
        with (logs/'dependencies.log').open('w') as log:
            subprocess.run([python,'-m','pip','install','mpmath==1.3.0','pytest==8.4.2'],env=env,
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        # Resource parsing and the execution seal are checked before numerical tests/campaign.
        probe = subprocess.check_output([python,'-c',
            "from c1b1_integrator_benchmark.study import load;from c1b1_o1.model import parse;import mpmath as m;assert len(parse())==14;print(load()['phase_one_case']);from c1b1_cost_benchmark import load as cost_load;assert cost_load()[0]['precision']==60;print(m.libmp.BACKEND)"],
            cwd=code,env=env,text=True)
        (logs/'resource_probe.txt').write_text(probe)
        tests = ['tests/test_c1b1_integrator_benchmark.py','tests/test_c1b1_o1.py','tests/test_c1b1_o1_diagnostic.py','tests/test_c1b1_cost_benchmark.py']
        with (logs/'related_tests.log').open('w') as log:
            tested = subprocess.run([python,'-m','pytest',*tests,'-q',f'--junitxml={logs}/related_tests.xml'],
                                    cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        (logs/'related_tests.exit').write_text(str(tested.returncode)+'\n')
        if tested.returncode:
            raise ValueError('related tests failed')
        print('REMOTE PREFLIGHT PASS',flush=True)
        with (logs/'campaign.log').open('w') as log:
            campaign = subprocess.run([python,'-u','-m','c1b1_cost_benchmark','campaign'],
                                     cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=3300)
        exit_code = campaign.returncode
        print('REMOTE CAMPAIGN EXIT',exit_code,flush=True)
    except BaseException:
        logs.mkdir(parents=True,exist_ok=True)
        (logs/'failure.txt').write_text(traceback.format_exc())
        traceback.print_exc()
    finally:
        logs.mkdir(parents=True,exist_ok=True)
        (logs/'exit.json').write_text(json.dumps(dict(exit=exit_code,end_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))+'\n')
        out = destination/'code/runs/c1b1_kdk20_yoshida40_cost_v1'
        artifacts = {}
        paths = list(logs.rglob('*')) + (list(out.rglob('*')) if out.exists() else [])
        for path in paths:
            if path.is_file():
                relative = 'deployment_logs/'+path.relative_to(logs).as_posix() if path.is_relative_to(logs) else 'observations/'+path.relative_to(out).as_posix()
                artifacts[relative] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
        (logs/'artifact_manifest.json').write_text(json.dumps(artifacts,indent=2)+'\n')
        with tarfile.open(result_archive,'w:gz') as tf:
            tf.add(logs,arcname='remote_results/deployment_logs')
            if out.exists():
                tf.add(out,arcname='remote_results/observations')
        print('REMOTE EVIDENCE READY',len(artifacts),flush=True)
    return exit_code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive');parser.add_argument('sha256');parser.add_argument('destination');parser.add_argument('results')
    args = parser.parse_args()
    raise SystemExit(run(args.archive,args.sha256,args.destination,args.results))
