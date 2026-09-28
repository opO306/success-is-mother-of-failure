"""C1-B1 ④-4c-8: shell-17 hard-case certificate under the ④-4c-6 contract.

The certificate contract is c1b1_hard_case_certificate unchanged: build(),
verify_certificate() and check_outgoing_coverage() already take the domain,
partition and block length as arguments. That module is not edited, because
the shell-18 certificate fixture pins its source hash. This driver only binds
shell 17's original domain, runs the stages the designer listed, and records
per-stage cost:

  build -> verify (fresh object) -> JSON round trip + verify (stored form)
        -> fresh coverage over the existing layers + shell 18 + shell 17

Per-stage CPU time is the children's CPU time (resource.RUSAGE_CHILDREN) on
POSIX. Pool workers are reaped when each stage's executor shuts down, so the
delta covers that stage. It is None where resource is unavailable (Windows).
"""
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json
import os
import time

from a_numeric import FixedPoint
from a_reference import c1b1_hard_case_certificate as CT
from a_reference import c1b1_hard_case_checker as H
from a_reference import c1b1_hard_case_search as G
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-hard-case-certificate-shell17-v1'
SHELL = 17
SHELL18_CERTIFICATE = 'a_reference/fixtures/c1b1_hard_case_certificate_v1.json'
# Same partition policy as shell 18 and the ④-4c-7 survey (so rows can be compared one to one).
BLOCK_POINTS = CT.SHELL_18_BLOCK_LENGTH
SUPERBLOCKS = CT.SHELL_18_SUPERBLOCKS


def _children_cpu():
    try:
        import resource
    except ImportError:
        return None
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime+r.ru_stime


def _stage(record, name, fn, workers):
    cpu0, t0 = _children_cpu(), time.perf_counter()
    out = fn()
    wall, cpu1 = time.perf_counter()-t0, _children_cpu()
    cpu = None if cpu0 is None else cpu1-cpu0
    record.append({'stage': name, 'wall_seconds': wall, 'children_cpu_seconds': cpu, 'workers': workers,
                   'parallel_efficiency': None if cpu is None or workers < 2 else cpu/(wall*workers)})
    print(f'[{time.strftime("%H:%M:%S")}] {name}: {wall:.1f}s wall'
          + ('' if cpu is None else f', {cpu:.1f}s children CPU'), flush=True)
    return out


def domain():
    _, lo, hi, _, _ = G.load_shell(SHELL)
    return {'kind': 'axis_lattice_interval', 'axis': 0, 'lo': lo, 'hi': hi}


def layers():
    """Existing coverage layers, rebuilt exactly as c1b1_hard_case_certificate.example_report does."""
    original = json.loads((ROOT/'a_reference/fixtures/c1b1_rounding_regions_v1.json').read_text(encoding='utf-8'))
    legacy = [R.certify_finite_points(original['finite_acceptance']['domain']['points'], bits=256)]
    for c in original['analytic_and_singleton_certificates']:
        d = c['domain']
        legacy.append(R.certify_finite_points(d['points'], bits=c['bits']) if d['kind'] == 'finite_points' else
                      R.certify_axis_zero_region(d['axis'], d['lo'], d['hi'], bits=c['bits']))
    from a_reference import c1b1_half_ulp_boundaries as HB
    boundary_fixture = json.loads((ROOT/'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json').read_text(encoding='utf-8'))
    boundaries = [(HB.certify_axis_domain(g['certificate']['domain']['axis'], g['certificate']['domain']['lo'],
                                          g['certificate']['domain']['hi']), g['certificate']['domain'])
                  for g in boundary_fixture['groups'] if g['certificate']['status'] == 'certified']
    families_report = json.loads((ROOT/'a_reference/fixtures/c1b1_family_certificates_v1.json').read_text(encoding='utf-8'))
    families = tuple((g['certificate'], g['expected_domain']) for g in families_report['groups'])
    shell18 = json.loads((ROOT/SHELL18_CERTIFICATE).read_text(encoding='utf-8'))
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0), (10, 0, 0), (1, 0, 0),
                    momentum_profile=FixedPoint(96, 80))
    return run, legacy, boundaries, families, (shell18['certificate'], shell18['expected_domain'])


def _digest(name):
    return sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def example_report(workers=6):
    CT.foundation_guard()
    dom = domain()
    stages = []
    ranges = H.blocks(dom['lo'], dom['hi'], BLOCK_POINTS, SUPERBLOCKS)
    cert = _stage(stages, 'build', lambda: CT.build(ranges, dom, BLOCK_POINTS, workers=workers), workers)
    _stage(stages, 'verify', lambda: CT.verify_certificate(cert, dom, workers=workers), workers)
    wire = json.loads(json.dumps(T.serial(cert), separators=(',', ':')))
    _stage(stages, 'verify_stored_json', lambda: CT.verify_certificate(wire, dom, workers=workers), workers)
    run, legacy, boundaries, families, shell18 = layers()
    coverage = _stage(stages, 'coverage_with_shell18_and_shell17_reverified',
                      lambda: CT.check_outgoing_coverage(run, F(2), legacy, boundaries, families,
                                                         (shell18, (wire, dom)), workers=workers), workers)
    return {'version': VERSION, 'status': 'certified', 'global_4_4b': 'NotCertified', 'shell_index': SHELL,
            'certificate': wire, 'expected_domain': dom, 'coverage': coverage, 'stages': stages,
            'host': {'os': os.name, 'cpu_count': os.cpu_count(), 'workers': workers},
            'source_sha256': {name: _digest(name) for name in (
                'a_reference/c1b1_hard_case_certificate.py', 'a_reference/c1b1_hard_case_certificate_shell17.py',
                'a_reference/c1b1_hard_case_checker.py', 'a_reference/c1b1_hard_case_search.py')},
            'prior_fixture_sha256': {SHELL18_CERTIFICATE: _digest(SHELL18_CERTIFICATE)}}


if __name__ == '__main__':
    import sys
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    out = json.dumps(T.serial(example_report(workers=workers)), separators=(',', ':'))+'\n'
    Path(sys.argv[1]).write_text(out, encoding='utf-8')
