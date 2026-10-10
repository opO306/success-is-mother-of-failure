"""OTHER_CPU_ROUTE_CHECK_V0: SERIAL vs W6 for the sealed A request, measured on THIS machine.

Plan: docs/active/OTHER_CPU_ROUTE_CHECK_V0_PLAN.md. Same computation path and code bytes as the Vast A resume V1
run (service.run_request FIXED_SERIAL / FIXED_W6, N14 T1000 p163, code seal ec1b50b4...). Every result must equal
the Vast results bit for bit (fingerprint below) or the run stops at once, after saving that run's record.
The Vast record is registered only into a temporary tablet inside the output directory, to obtain the v1
proposal. The judge output is recorded as a candidate only: nothing here approves or activates a profile and
nothing enters the project tablet (authority NONE).
"""
import argparse
import hashlib
import os
import platform
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.adaptive_execution_learning_v1.core import canonical, raw_hash, read, write_new  # noqa: E402

N, T, P, GOAL = 14, 1000, 163, 'WALL_MIN'
ORDER = (('SERIAL', 0), ('W6', 0), ('W6', 1), ('SERIAL', 1), ('SERIAL', 2),
         ('W6', 2), ('W6', 3), ('SERIAL', 3), ('SERIAL', 4), ('W6', 4))      # the sealed A resume V1 order
REPEATS = 5
EXPECTED_PLAN = {'SERIAL': ('CPU_SERIAL', 0), 'W6': ('CPU_PARALLEL', 6)}
PASS_FIELDS = ('outcome', 'completed_steps', 'stop', 'stop_step', 'cells', 'endpoints_key')   # checker.FIELDS
FINGERPRINT_FIELDS = PASS_FIELDS + ('endpoints_scaled', 'effective_p')
REFERENCE_SHA256 = '70897884d142404917e8f33dd6ecc6198f600d8ca7e082518c34eecc5c7bac28'   # Vast 10 runs = replay
A_CODE_SEAL = 'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'
A_CODE_SEAL_SHA256 = 'ec1b50b4f32dc8cd3334aab6c6d063f340328fc2d24e73b8b16814052e6b5d60'
TABLET_CODE_SEAL = 'experiments/adaptive_experience_tablet_v0/code_seal.json'
TABLET_CODE_SEAL_SHA256 = '10e8c73f6466746dc761efca7e8d0c0172ae4edfceed171d71efff08b3ea29ce'   # package revision 2
V1_FILES = {'experiments/adaptive_experience_tablet_v1/__init__.py':
            '174a9a8e8107f0db97d3e0e49eabf4b7ecd5f4e157288503083b306dc1288041',
            'experiments/adaptive_experience_tablet_v1/transfer.py':
            '7cbe34af0bd741629ba2e57f55d5af6abba42caf762f1e57d9d1b1a9517eda05'}
ORIGINAL = ('docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136/'
            'run_20261008_approved_3/recovered/output_actual')
PROFILE = 'b775509603dc3f07e578ccce4aea11021cee013c7eea8feb8268f01a8e91482f'
APPROVAL = 'manager/events/event_000000.json'
# Operator attestation: a single-core-class part (vendor specification), not a measurement. Laptop only (plan scope).
HOMOGENEOUS_MODELS = ('AMD Ryzen 5 4500U with Radeon Graphics',)
PER_RUN_SECONDS = 480                               # protocol per_call_seconds_max
TOTAL_SECONDS = 2400
SPREAD_MAX = (5, 4)                                 # max/min <= 1.25, compared in integers
# Report only (A resume V1 records). Cross-machine comparison uses service_wall: the Vast observation window also
# held check_seals() (about 60 ms), which this script keeps outside its clock.
VAST_MEDIANS_NS = {'service_wall': {'SERIAL': 63447635358, 'W6': 13443282925},
                   'observation': {'SERIAL': 63506288768, 'W6': 13502232290},
                   'full_request': {'SERIAL': 63513931309, 'W6': 13508699536}}
CLOCK = 'OS_MONOTONIC_AND_RUSAGE_SELF_PLUS_WAITED_CHILDREN; AROUND_RUN_REQUEST_ONLY; NO_SEAL_CHECK_OR_SAVE_INSIDE'


def _ns(seconds):
    return round(seconds * 1e9)


def fingerprint(result):
    return hashlib.sha256(canonical({k: result[k] for k in FINGERPRINT_FIELDS})).hexdigest()


def check_service(method, svc):
    """The single pass result of a clean p163 run of exactly the requested method, else ValueError."""
    if (svc.get('status') != 'DECIDED' or svc.get('final_p') != P or svc.get('p_sequence') != [P]
            or svc.get('n_passes') != 1 or len(svc.get('passes') or []) != 1):
        raise ValueError('NOT_A_CLEAN_P163_RUN')
    if svc.get('events'):
        raise ValueError('SERVICE_EVENTS')
    if (svc.get('N'), svc.get('T')) != (N, T):
        raise ValueError('REQUEST_DIFFERS')
    pz = svc['passes'][0]
    if pz.get('requested_p') != P or pz.get('start') != 'ORIGINAL_STATE':
        raise ValueError('PRECISION_OR_RESTART')
    if len(pz.get('attempts') or []) != 1:
        raise ValueError('FALLBACK_OR_RETRY')
    plan, res = pz['attempts'][0]['plan'], pz['attempts'][0]['result']
    if (plan.get('backend'), plan.get('worker_count')) != EXPECTED_PLAN[method] or plan.get('p') != P:
        raise ValueError('METHOD_DIFFERS')
    if res is None or res.get('status_class') != 'OK' or res.get('backend') != plan['backend']:
        raise ValueError('RESULT_NOT_OK')
    if res.get('executed_placement_ok') is not True or res.get('effective_p') != P:
        raise ValueError('PLACEMENT_OR_PRECISION_NOT_CONFIRMED')
    for field in PASS_FIELDS:
        if res.get(field) != pz.get(field):
            raise ValueError('ATTEMPT_PASS_DIFFER:' + field)
    return res


def check_clock(svc, wall, cpu):
    """The real inspector's clock rules (inspector.validate_record): outer clocks must cover the service's own."""
    if type(wall) is not int or type(cpu) is not int or wall <= 0 or cpu <= 0:
        raise ValueError('CLOCK_INVALID')
    if wall < _ns(svc['service_wall_s']):
        raise ValueError('OUTER_WALL_EXCLUDES_SERVICE')
    attempts = sum(_ns(a['result']['cpu_s']) for pz in svc['passes'] for a in pz['attempts'])
    if cpu + max(50_000_000, cpu // 100) < attempts:
        raise ValueError('OBSERVED_CPU_EXCLUDES_ATTEMPTS')


def _spread_ok(values):
    return max(values) * SPREAD_MAX[1] <= min(values) * SPREAD_MAX[0]


def summarize(records):
    out = {}
    for method in EXPECTED_PLAN:
        rows = sorted((r for r in records if r['method'] == method), key=lambda r: r['repeat'])
        if [r['repeat'] for r in rows] != list(range(REPEATS)):
            raise ValueError('FIVE_REPEATS_PER_METHOD_REQUIRED')
        walls, cpus = [r['wall_ns'] for r in rows], [r['cpu_ns'] for r in rows]
        service = [r['service_wall_ns'] for r in rows]
        if any(type(v) is not int or v <= 0 for v in walls + cpus + service):
            raise ValueError('CLOCK_INVALID')
        mid = REPEATS // 2
        out[method] = dict(wall_ns=walls, cpu_ns=cpus, service_wall_ns=service, wall_median_ns=sorted(walls)[mid],
                           cpu_median_ns=sorted(cpus)[mid], service_wall_median_ns=sorted(service)[mid],
                           wall_min_ns=min(walls), wall_max_ns=max(walls),
                           wall_spread_ok=_spread_ok(walls), cpu_spread_ok=_spread_ok(cpus),
                           identical=[r['fingerprint'] == REFERENCE_SHA256 for r in rows])
    out['stable'] = all(out[m]['wall_spread_ok'] and out[m]['cpu_spread_ok'] for m in EXPECTED_PLAN)
    out['pairs_identical'] = [s and w for s, w in zip(out['SERIAL']['identical'], out['W6']['identical'])]
    return out


def judged(proposal, summary):
    """The v1 judge, plus whether its answer may be used: a spread above 1.25 is not profile grade."""
    from experiments.adaptive_experience_tablet_v1 import transfer
    verdict = transfer.judge(proposal, summary['SERIAL']['wall_ns'], summary['W6']['wall_ns'], summary['pairs_identical'])
    return dict(verdict, verdict_usable=summary['stable'],
                usable_reason='STABLE' if summary['stable'] else 'SPREAD_OVER_1_25_NOT_PROFILE_GRADE')


def _check_files():
    seal = ROOT / A_CODE_SEAL
    if raw_hash(seal) != A_CODE_SEAL_SHA256:
        raise ValueError('A_CODE_SEAL_DIFFERS')
    bad = [f for f, h in read(seal)['files'].items() if raw_hash(ROOT / f) != h]
    tablet = ROOT / TABLET_CODE_SEAL
    if raw_hash(tablet) != TABLET_CODE_SEAL_SHA256:
        raise ValueError('TABLET_CODE_SEAL_DIFFERS')
    bad += [f for f, h in read(tablet)['files'].items() if raw_hash(ROOT / f) != h]
    bad += [f for f, h in V1_FILES.items() if raw_hash(ROOT / f) != h]
    if bad:
        raise ValueError('SOURCE_BYTES_DIFFER:' + ','.join(sorted(set(bad))[:5]))
    from experiments.adaptive_execution_real_learning_pilot_v0.common import check_seals
    check_seals()


def _quota_observation(env):
    try:
        quota = Path('/sys/fs/cgroup/cpu.max').read_text().split()[0]
    except (OSError, IndexError) as error:
        raise ValueError('QUOTA_UNOBSERVED') from error
    if env['cpu_quota'] is None:
        if quota != 'max':
            raise ValueError('QUOTA_UNOBSERVED')
        return 'OBSERVED_UNLIMITED'
    return 'OBSERVED_FINITE'


def preflight(out):
    """Seals, environment qualification, temporary tablet and the v1 proposal. No physics."""
    if os.name != 'posix' or not sys.platform.startswith('linux'):
        raise ValueError('LINUX_REQUIRED')
    _check_files()
    from experiments.adaptive_execution_v1 import environment as ENV
    from experiments.adaptive_execution_v1 import selector as SEL
    from experiments.adaptive_execution_real_learning_pilot_v0 import governance
    from experiments.adaptive_experience_tablet_v0 import catalog, host
    from experiments.adaptive_experience_tablet_v1 import transfer
    original = ROOT / ORIGINAL
    vast = read(original / 'A/session.json')
    if vast['code_manifest_sha256'] != A_CODE_SEAL_SHA256:
        raise ValueError('VAST_SOURCE_DIFFERS_FROM_THIS_TREE')
    for method, repeat in ORDER:
        svc = read(original / f'A/measurement/{method}_{repeat}.json')['service']
        if fingerprint(check_service(method, svc)) != REFERENCE_SHA256:
            raise ValueError('REFERENCE_PIN_DIFFERS')
    env = ENV.collect(ROOT)
    if env['platform'] != 'linux' or not SEL.cpu_verified(env):
        raise ValueError('CPU_ENVIRONMENT_NOT_VERIFIED')
    if (env['contracts']['physics'], env['contracts']['numeric']) != (vast['env']['contracts']['physics'],
                                                                     vast['env']['contracts']['numeric']):
        raise ValueError('CONTRACTS_DIFFER_FROM_VAST')
    if env['cpu_model'] not in HOMOGENEOUS_MODELS:
        raise ValueError('CORE_CLASS_NOT_ATTESTED')
    info = host.describe(env, quota_observation=_quota_observation(env), core_classes='HOMOGENEOUS',
                         provenance='LINUX_SYSFS_TOPOLOGY+CGROUP_CPU_MAX; CORE_CLASS_OPERATOR_ATTESTED_FROM_CPU_MODEL')
    shutil.copytree(original, out / 'originals')
    roots = governance.Roots(**read(out / 'originals/manager/roots.json'))
    tablet = catalog.Tablet(out / 'tablet', out / 'originals', roots)
    entry = tablet.register('A', PROFILE, APPROVAL)
    request = dict(N=N, T=T, start_p=P, actual_p=P, goal=GOAL, physics=env['contracts']['physics'],
                   numeric=env['contracts']['numeric'], source_sha256=A_CODE_SEAL_SHA256)
    hits = tablet.search(request)
    if len(hits) != 1 or hits[0] != entry:
        raise ValueError('TABLET_SEARCH_UNEXPECTED')
    proposal = transfer.propose(tablet.load(hits[0]), request, info)
    return dict(env=env, host=info, request=request, proposal=proposal, script_sha256=raw_hash(__file__),
                placements=sorted(SEL.placements(env)), boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def _cpu_ns():
    import resource
    total = 0
    for who in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN):
        r = resource.getrusage(who)
        total += _ns(r.ru_utime + r.ru_stime)
    return total


def measure(out, pre, log=print):
    from experiments.adaptive_execution_v1 import experience as EXP
    from experiments.adaptive_execution_v1 import service as SVC
    from experiments.adaptive_execution_real_learning_pilot_v0.bridge import deadline
    from experiments.adaptive_execution_real_learning_pilot_v0.resources import Watch
    store, env, begin, records = EXP.load_store(), pre['env'], time.monotonic(), []
    for method, repeat in ORDER:
        name = f'{method}_{repeat}'
        if TOTAL_SECONDS - (time.monotonic() - begin) < PER_RUN_SECONDS:
            write_new(out / 'STOP.json', dict(status='STOP', reason='TOTAL_BUDGET', before=name))
            raise TimeoutError('TOTAL_BUDGET')
        run_id = f'other_cpu_v0/{pre["boot_id"]}/{name}'
        (out / 'work' / name).mkdir(parents=True)          # cpu_pass makes its temporary directory inside
        load_before, cpu0, t0 = list(os.getloadavg()), _cpu_ns(), time.monotonic_ns()
        watch = Watch(time.monotonic() + PER_RUN_SECONDS + 30)
        watch.start()
        try:
            with deadline(PER_RUN_SECONDS):
                svc = SVC.run_request({'id': run_id, 'N': N, 'T': T, 'start': f'FIXED_START:{P}'}, 'FIXED_' + method,
                                      env, None, store, gpu=None, goal=GOAL, gate100=False, run_id=run_id,
                                      workdir=out / 'work' / name, keep_gpu_detail=False)
        except BaseException as error:
            write_new(out / f'{name}_FAILED.json', dict(status='STOP', run=name, error_type=type(error).__name__,
                                                        error=str(error)[:500], wall_ns=time.monotonic_ns() - t0))
            raise
        finally:
            watch.close()
        wall, cpu = time.monotonic_ns() - t0, _cpu_ns() - cpu0
        record = dict(method=method, repeat=repeat, run_id=run_id, wall_ns=wall, cpu_ns=cpu, clock=CLOCK,
                      loadavg_before=load_before, loadavg_after=list(os.getloadavg()), service=svc)
        problem = None
        try:
            result = check_service(method, svc)
            check_clock(svc, wall, cpu)
            record['service_wall_ns'] = _ns(svc['service_wall_s'])
            record['fingerprint'] = fingerprint(result)
        except Exception as error:                     # the raw record is saved before any stop
            problem = error
            record['check_error'] = f'{type(error).__name__}: {error}'[:500]
        write_new(out / 'runs' / f'{name}.json', record)
        if problem is not None:
            raise problem
        log(f'{name} wall={wall / 1e9:.3f}s cpu={cpu / 1e9:.3f}s identical={record["fingerprint"] == REFERENCE_SHA256}',
            flush=True)
        if record['fingerprint'] != REFERENCE_SHA256:
            raise ValueError('RESULT_DIFFERS_FROM_VAST:' + name)
        records.append(record)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--phase', required=True, choices=('preflight', 'measure'))
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    try:
        pre = preflight(args.out)
        write_new(args.out / 'preflight.json', dict(pre, hostname=platform.node(), python=sys.version))
    except BaseException as error:
        write_new(args.out / 'status.json', dict(status='STOP', stage='PREFLIGHT', error=f'{type(error).__name__}: {error}'[:500]))
        raise
    proposal = pre['proposal']
    print('preflight:', proposal['decision'], proposal.get('hint'), pre['placements'], flush=True)
    if proposal.get('decision') != 'TRY_HINT_FIRST' or proposal.get('hint') != 'W6':
        write_new(args.out / 'status.json', dict(status='STOP', stage='PROPOSAL', decision=proposal.get('decision')))
        return 3
    if args.phase == 'preflight':
        write_new(args.out / 'status.json', dict(status='PREFLIGHT_PASS', physics_runs=0))
        return 0
    try:
        records = measure(args.out, pre)
        summary = summarize(records)
        verdict = judged(proposal, summary)
    except BaseException as error:
        write_new(args.out / 'status.json', dict(status='STOP', stage='MEASURE', error=f'{type(error).__name__}: {error}'[:500]))
        raise
    write_new(args.out / 'summary.json', dict(
        status='MEASURED', authority='NONE', registered_in_project_tablet=False, script_sha256=pre['script_sha256'],
        cpu_model=pre['env']['cpu_model'], env_id=pre['env']['env_id'], clock=CLOCK, summary=summary,
        verdict=verdict, vast_medians_ns=VAST_MEDIANS_NS, elapsed_s=round(time.time() - started, 3)))
    write_new(args.out / 'status.json', dict(status='MEASURED', physics_runs=len(records)))
    print('verdict:', verdict['decision'], 'usable:', verdict['verdict_usable'], flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
