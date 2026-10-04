"""Bounded, exclusive local five-point run; no calculator research or motion."""
import argparse
import datetime
import shutil
import subprocess
import time
from pathlib import Path
from electronic_pilot.frontend_reference_v0.audit import read, write, sha
from .interface import GRID, GUARDS, analyze

DOC = Path('docs/active/h2_force_v0')
RAW = Path('runs/h2_force_v0_20261004')
PYTHON = '/home/otherside123/.venvs/h2-reference-pilot/bin/python'
DEFINITIONS = Path('C:/Users/zun24/.codex/worktrees/h2-qz-cause-v0/성공은 실패의 어머니/runs/h2_adversarial_v0/definitions_v1/basis_definitions.json')


def linux(path):
    p = Path(path).resolve().as_posix()
    return '/mnt/' + p[0].lower() + p[2:]


def verify(bindings):
    bad = [p for p, h in bindings.items() if not Path(p).is_file() or sha(p) != h]
    if bad:
        raise ValueError('protected hash mismatch: ' + repr(bad))


def prepare():
    if DOC.exists() or RAW.exists():
        raise ValueError('exclusive capture already exists')
    old = Path('docs/active/h2_r04_jc_v1/evidence')
    prior = read(old/'protocol.json')
    protected = {**prior['protected_sha256'], **prior['implementation_sha256'],
                 **read(old/'energy_seal.json')['bound_sha256'],
                 **read(old/'final_seal.json')['bound_sha256']}
    for entry in read(old/'raw_inventory.json')['entries']:
        protected[entry['path']] = entry['sha256']
    for p in old.glob('*.json'):
        protected[p.as_posix()] = sha(p)
    verify(protected)
    preflight = Path('runs/h2_force_preflight_v2_20261004.log')
    text = preflight.read_text(encoding='utf-8')
    if 'passed' not in text or 'failed' in text or 'error' in text:
        raise ValueError('fresh preflight missing or failed')
    RAW.mkdir(parents=True)
    DOC.mkdir(parents=True)
    shutil.copyfile(DEFINITIONS, RAW/'basis_definitions.json')
    source = {p.as_posix(): sha(p) for p in Path('electronic_pilot/h2_force_v0').glob('*.py')}
    source.update({p.as_posix(): sha(p) for p in Path('tests/h2_force_v0').glob('*.py')})
    source[preflight.as_posix()] = sha(preflight)
    for p in ('electronic_pilot/adversarial_v0/cardinal.py', 'electronic_pilot/ao_micro_v0/reuse.py',
              'electronic_pilot/numerical_cause/core.py', 'electronic_pilot/solver.py',
              'electronic_pilot/ao_micro_v0/protocol.json', RAW/'basis_definitions.json', DEFINITIONS):
        source[str(p)] = sha(p)
    environment = subprocess.run(['wsl', '-e', PYTHON, '-c',
        'import sys,numpy,scipy,pyscf; print(sys.version); print(numpy.__version__,scipy.__version__,pyscf.__version__)'],
        capture_output=True, text=True, check=True).stdout
    git = {}
    for name, command in (
        ('HEAD', ['git', 'rev-parse', 'HEAD']), ('branch', ['git', 'branch', '--show-current']),
        ('status', ['git', 'status', '--porcelain']),
        ('remote', ['git', 'ls-remote', 'origin', 'refs/heads/master', 'refs/heads/codex/h2-representation-pilot1'])):
        git[name] = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    protocol = dict(sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), git=git,
        R_bohr=list(GRID), h_bohr='0.1', basis='cc-pV5Z', guards=GUARDS,
        physical='clamped two protons / two electrons / nonrelativistic Coulomb / full spatial singlet / EBO=Ee+1/R',
        calculator='unchanged canonical_ao + Cholesky + AO_and_MO_integral_reuse + singlet_matrix + eigh evr roots0,1',
        arithmetic='IEEE binary64; no rigorous enclosure', threads=1, python=PYTHON, environment=environment,
        point_timeout_seconds=300, timeout_scope='operational cap only; no retry or new geometry',
        success=['all five numerical guards accepted', 'E14<E13', 'E14<E15', 'F13>0', 'F15<0'],
        F14_tolerance=None, failure='STOP on first refused point; later points NOT_EVALUATED; no estimated energies',
        cost='five fresh sequential processes; GNU time process RSS/wall; outer campaign wall includes WSL startup and capture',
        continuity='sampled structure only; no new jump threshold or global continuity claim',
        performance_acceptance='no dynamics budget specified; cost measured only',
        freeze_status='ELECTRONIC_CALC_STACK_V0 / EXPLORATORY / NOT CERTIFIED / NOT PRODUCTION APPROVED',
        backlog=['Gaussian/QZ FAIL and unresolved numerical issues', 'B2 independent JC NOT IMPLEMENTED',
                 'H-He+ indefinite S', 'General SPD', 'JC asymmetric intended root', 'reference uncertainty',
                 'AO/MO rigorous bounds', 'H2SOLV overall certification', 'representation generalization'],
        forbidden=['calculator side audits except actual blocker', 'nuclear motion', 'adaptive representation', 'merge', 'rebase', 'push'],
        protected_sha256=protected, implementation_sha256=source)
    write(DOC/'protocol.json', protocol)
    write(DOC/'protocol_seal.json', dict(sha256=sha(DOC/'protocol.json'), sealed_before_energy=True))
    print('SEALED', sha(DOC/'protocol.json'), 'protected', len(protected), flush=True)


def execute():
    if (DOC/'results.json').exists() or (RAW/'execution_start.json').exists():
        raise ValueError('exclusive execution; no rerun')
    protocol = read(DOC/'protocol.json')
    if sha(DOC/'protocol.json') != read(DOC/'protocol_seal.json')['sha256']:
        raise ValueError('protocol changed')
    verify(protocol['protected_sha256'])
    verify(protocol['implementation_sha256'])
    write(RAW/'execution_start.json', dict(protocol_sha256=sha(DOC/'protocol.json'), before_energies=True))
    rows = []
    began = time.perf_counter()
    issue = None
    for r in GRID:
        output = RAW/('R' + r)
        process = RAW/('process_R' + r)
        process.mkdir()
        command = ['wsl', '-e', '/usr/bin/time', '-f',
                   'wall_seconds=%e\npeak_rss_kib=%M\nuser_seconds=%U\nsystem_seconds=%S',
                   '-o', linux(process/'native.time'), '/usr/bin/timeout', '300', '/usr/bin/env',
                   'OMP_NUM_THREADS=1', 'OPENBLAS_NUM_THREADS=1', 'MKL_NUM_THREADS=1',
                   '/bin/sh', '-c', 'cd "$1" && exec "$2" -m electronic_pilot.h2_force_v0.worker --R "$3" --output "$4" --definitions "$5"',
                   'h2force', linux(Path.cwd()), PYTHON, r, linux(output), linux(RAW/'basis_definitions.json')]
        start = time.perf_counter()
        with (process/'stdout').open('xb') as out, (process/'stderr').open('xb') as err:
            p = subprocess.run(command, stdout=out, stderr=err)
        measured = {}
        if (process/'native.time').exists():
            for line in (process/'native.time').read_text().splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    measured[key] = float(value)
        metadata = dict(argv=command, exit=p.returncode, outer_wall_seconds=time.perf_counter()-start, measurement=measured)
        write(process/'process.json', metadata)
        if p.returncode or not (output/'result.json').exists():
            row = dict(R_decimal=r, R_bohr=float(r), accepted=False, failure_stage='process_failure',
                       total_energy_hartree=None, numerical_guard_status='REFUSED', process=metadata)
        else:
            row = read(output/'result.json')
            row['process'] = metadata
        rows.append(row)
        write(DOC/('point_R' + r + '.json'), row)
        print('POINT', r, row['numerical_guard_status'], row['total_energy_hartree'], flush=True)
        if not row['accepted']:
            break
    total = time.perf_counter()-began
    try:
        verify(protocol['protected_sha256'])
        verify(protocol['implementation_sha256'])
    except ValueError as exc:
        issue = str(exc)
    result = analyze(rows)
    if issue:
        result.update(classification=['H2_FORCE_VERTICAL_SLICE_BLOCKED'], first_blocker=dict(reason='provenance_mismatch', detail=issue))
    result.update(points=rows, total_execution_wall_seconds=total,
        native_process_wall_sum_seconds=sum(x['process']['measurement'].get('wall_seconds', 0) for x in rows),
        native_peak_rss_kib=max((x['process']['measurement'].get('peak_rss_kib', 0) for x in rows), default=0),
        postcheck_protected_count=len(protocol['protected_sha256']), protected_unchanged=issue is None,
        performance='measured static cost; next dynamics budget and scaling NOT_EVALUATED',
        nuclear_motion_implemented=False, JC_runs=0, extra_geometries=0)
    write(DOC/'results.json', result)
    inventory = {p.as_posix(): sha(p) for p in RAW.rglob('*') if p.is_file()}
    inventory.update({p.as_posix(): sha(p) for p in DOC.glob('*.json')})
    write(DOC/'execution_seal.json', dict(bound_sha256=inventory, source_unchanged=issue is None))
    print(result['classification'], 'STOP / no nuclear motion', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=('prepare', 'execute'))
    {'prepare': prepare, 'execute': execute}[p.parse_args().stage]()
