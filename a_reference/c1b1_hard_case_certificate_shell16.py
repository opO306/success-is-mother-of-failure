"""C1-B1 ④-4c-10: shell-16 hard-case certificate under the ④-4c-6 contract.

Designer verdict ④-4c-10 approved certifying shell 16 after the ④-4c-9
survey: hazard 0, checker 1024/1024, brute-force misses 0, no structural
mismatch, parallel efficiency held, no memory problem, and the ④-4c-8 cost
model matched the shell-16 measurement to about 1%. The observed candidate
density increase is accepted only as an explanation for cost estimation, not
promoted to a soundness argument here.

The contract is c1b1_hard_case_certificate unchanged (same reason as
c1b1_hard_case_certificate_shell17: the shell-18 fixture pins its source
hash). This driver binds shell 16's original domain and composes fresh
coverage over the existing layers plus the shell-18, shell-17 and shell-16
certificates (all three re-verified in that stage, exactly like
c1b1_hard_case_certificate_shell17 already re-verifies shell 18).
"""
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json
import os
import time

from a_numeric import FixedPoint
from a_reference import c1b1_hard_case_certificate as CT
from a_reference import c1b1_hard_case_certificate_shell17 as S17
from a_reference import c1b1_hard_case_checker as H
from a_reference import c1b1_hard_case_search as G
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_two_atom as C

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-hard-case-certificate-shell16-v1'
SHELL = 16
CERTIFICATE_17 = 'a_reference/fixtures/c1b1_hard_case_certificate_shell17_v1.json'
# Same partition policy as shells 18/17 (so rows can be compared one to one).
BLOCK_POINTS = CT.SHELL_18_BLOCK_LENGTH
SUPERBLOCKS = CT.SHELL_18_SUPERBLOCKS


def domain():
    _, lo, hi, _, _ = G.load_shell(SHELL)
    return {'kind': 'axis_lattice_interval', 'axis': 0, 'lo': lo, 'hi': hi}


def layers():
    """Existing layers plus the shell-18 and shell-17 certificates, read from their fixtures."""
    run, legacy, boundaries, families, shell18 = S17.layers()
    shell17 = json.loads((ROOT/CERTIFICATE_17).read_text(encoding='utf-8'))
    return run, legacy, boundaries, families, shell18, (shell17['certificate'], shell17['expected_domain'])


def _digest(name):
    return sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def example_report(workers=6):
    CT.foundation_guard()
    dom = domain()
    stages = []
    ranges = H.blocks(dom['lo'], dom['hi'], BLOCK_POINTS, SUPERBLOCKS)
    cert = S17._stage(stages, 'build', lambda: CT.build(ranges, dom, BLOCK_POINTS, workers=workers), workers)
    S17._stage(stages, 'verify', lambda: CT.verify_certificate(cert, dom, workers=workers), workers)
    wire = json.loads(json.dumps(T.serial(cert), separators=(',', ':')))
    S17._stage(stages, 'verify_stored_json', lambda: CT.verify_certificate(wire, dom, workers=workers), workers)
    run, legacy, boundaries, families, shell18, shell17 = layers()
    coverage = S17._stage(
        stages, 'coverage_with_shell18_shell17_and_shell16_reverified',
        lambda: CT.check_outgoing_coverage(run, F(2), legacy, boundaries, families,
                                           (shell18, shell17, (wire, dom)), workers=workers), workers)
    return {'version': VERSION, 'status': 'certified', 'global_4_4b': 'NotCertified', 'shell_index': SHELL,
            'certificate': wire, 'expected_domain': dom, 'coverage': coverage, 'stages': stages,
            'host': {'os': os.name, 'cpu_count': os.cpu_count(), 'workers': workers},
            'source_sha256': {name: _digest(name) for name in (
                'a_reference/c1b1_hard_case_certificate.py', 'a_reference/c1b1_hard_case_certificate_shell17.py',
                'a_reference/c1b1_hard_case_certificate_shell16.py',
                'a_reference/c1b1_hard_case_checker.py', 'a_reference/c1b1_hard_case_search.py')},
            'prior_fixture_sha256': {S17.SHELL18_CERTIFICATE: _digest(S17.SHELL18_CERTIFICATE),
                                     CERTIFICATE_17: _digest(CERTIFICATE_17)}}


if __name__ == '__main__':
    import sys
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    out = json.dumps(T.serial(example_report(workers=workers)), separators=(',', ':'))+'\n'
    Path(sys.argv[1]).write_text(out, encoding='utf-8')
