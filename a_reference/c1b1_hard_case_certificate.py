"""C1-B1 ④-4c-6: formal certificate wrapping the shell-18 hard-case search.

Promotes the ④-4c-5 survey result (c1b1_hard_case_search / c1b1_hard_case_survey)
from survey_only to a checkable certificate with the same obligations the
rational-spacing family checker (c1b1_family_checker) already enforces:
domain binding, the frozen P/Q identity, the pinned residual+numeric-error
guard recomputed from primitives, an execution precision ceiling of
MAX_PRECISION_BITS, legal FX(96,80) momentum output, and source hash
provenance. Certificates never edit coverage themselves; this module's
check_outgoing_coverage stacks on c1b1_family_certificates.check_outgoing_coverage
and recomputes fresh coverage from whatever certificates verify.

build() takes only the superblock partition and recomputes every quantity
from c1b1_hard_case_checker primitives; it trusts no survey claim.
verify_certificate() recomputes everything again (guard, derivative bound,
crossing count, candidate set, hazard check, impulse bound) and requires the
stored values to match exactly, so a forged bound or dropped candidate is
rejected. Build and verify share _recompute_row (verification-limits type A);
the cross-implementation check is the test comparing these rows with the
generator's rows stored by the ④-4c-5 survey.
"""
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json
import re

from a_numeric import FixedPoint
from a_reference import c1b1_family_certificates as FC
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_hard_case_checker as H
from a_reference import c1b1_hard_case_search as G
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_two_atom as C

VERSION = 'c1b1-hard-case-certificate-v1'
SCOPE = 'declared_positive_axis_lattice_domain_only'
ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_HASHES = {'a_reference/c1b1_hard_case_checker.py':
                     sha256((ROOT/'a_reference/c1b1_hard_case_checker.py').read_bytes()
                            .replace(b'\r\n', b'\n')).hexdigest()}
MOMENTUM_LIMIT = F((1 << 96)-1, 2)
MOMENTUM_SCALE = 20  # I = -20 V'(R) in momentum ULPs; matches c1b1_axis_decision_bounds.
RESIDUAL_BITS = 4096
# Matches c1b1_hard_case_survey.POLICY['full_run_points'/'full_run_superblocks']; this
# module does not import the survey driver (generator/checker/certificate stay separate).
SHELL_18_BLOCK_LENGTH = 2**34+1
SHELL_18_SUPERBLOCKS = 1024
# Fail fast instead of enumerating an absurd candidate set. Any block length is
# sound (a longer block only inflates delta and the candidate set); this limit
# turns a mis-sized block into a refusal rather than an hours-long hazard scan.
MAX_CANDIDATES = 1 << 20


def _require(condition, reason):
    if not condition:
        raise O.NotCertified(reason)


def _int(x):
    _require(type(x) is int, 'exact integer required')
    return x


def _fraction(x):
    if type(x) is int:
        return F(x)
    _require(type(x) is str and re.fullmatch(r'-?\d+(?:/[1-9]\d*)?', x), 'canonical exact rational required')
    value = F(x)
    _require(str(value) == x, 'noncanonical rational')
    return value


def foundation_guard():
    """Same numeric/evaluator foundation as the family checker, plus this module's own source."""
    K.foundation_guard()
    for name, expected in FOUNDATION_HASHES.items():
        current = sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        _require(current == expected, 'hard-case checker source changed since certificate was built')


def guard_value(a, b, bits, diagnostic_bits=4096):
    """Rebuild G = max|signed residual| + numeric endpoint error, at raw shell endpoints a,b.

    `bits` is the residual Taylor/EXP enclosure precision (matches residual_bits
    in the certificate); `diagnostic_bits` is the fixed precision the numeric
    endpoint error is diagnosed at, pinned by c1b1_modular_distance_survey
    (POLICY['error_diagnostic_bits'] = 4096) and independent of the search's
    own required_bits.
    """
    p, q, terms, dpoly = K.frozen_identity()
    lo_r, hi_r = K.residual_range(F(a, 1 << 48), F(b, 1 << 48), terms, bits)
    error = K.A.axis_impulse_error(F(a, 1 << 48), F(b, 1 << 48), diagnostic_bits)/K.A.B.UP
    return max(abs(lo_r), abs(hi_r))+error, (lo_r, hi_r), error


def _recompute_row(args):
    """One superblock: one derivative bound, then quadratic blocks of `points` inputs each.

    Delegates to the checker's superblock(), the same block loop that agreed
    1024/1024 with the generator in the ④-4c-5 survey. Treating a whole
    superblock as a single quadratic block is still sound but inflates delta by
    (blocks per superblock)^3; that mistake is what this function once made.
    """
    a0, b0, guard, points = args
    p, q, terms, dpoly = K.frozen_identity()
    row = H.superblock(H.Rational(p, q), a0, b0, guard, 2, points)
    return {'range': [a0, b0], 'derivative_bound': str(row['derivative_bound']),
            'crossings': row['crossings'],
            'candidate_intervals': [list(iv) for iv in row['candidate_intervals']]}


def _candidates(rows):
    candidates = H.merged(tuple(iv) for row in rows for iv in row['candidate_intervals'])
    _require(sum(b-a+1 for a, b in candidates) <= MAX_CANDIDATES, 'candidate work limit exceeded')
    return candidates


def build(ranges, domain, points, *, momentum_scale=MOMENTUM_SCALE, workers=1):
    """Build a certificate by independently recomputing every superblock.

    `ranges` is only the superblock partition (a sequence of (a0, b0) pairs
    covering the domain contiguously) — for example from
    c1b1_hard_case_search.superblock_ranges, or read off an existing survey
    fixture's row ranges. Every other quantity (derivative bound, crossing
    count, candidate set, guard, impulse bound) is computed here from
    c1b1_hard_case_checker primitives, not taken from any prior run; nothing
    the caller supplies is trusted as a claim the way a survey row would be.

    Unlike the rational-spacing family checker, this contract has no
    precision *schedule* to search: the guard is always diagnosed at the
    fixed 4096-bit numeric-error precision pinned by
    c1b1_modular_distance_survey, and every candidate/hazard test after that
    is an exact Fraction comparison with no rounding at all. RESIDUAL_BITS
    (the residual Taylor/EXP enclosure precision) is therefore the only
    precision this certificate depends on, and it is what required_bits
    records.
    """
    p, q, terms, dpoly = K.frozen_identity()
    target = H.Rational(p, q)
    lo, hi = domain['lo'], domain['hi']
    ranges = tuple((int(a), int(b)) for a, b in ranges)
    _require(ranges and ranges[0][0] == lo and ranges[-1][1] == hi, 'ranges do not cover the declared domain')
    _require(all(ranges[i][1]+1 == ranges[i+1][0] for i in range(len(ranges)-1)),
             'superblock ranges are not contiguous')
    _require(type(points) is int and points > H.EXACT_BLOCK+1, 'block length required')
    guard, residual, error = guard_value(lo, hi, RESIDUAL_BITS)
    args = [(a0, b0, guard, points) for a0, b0 in ranges]
    if workers > 1:
        with ProcessPoolExecutor(workers) as pool:
            checked_rows = list(pool.map(_recompute_row, args, chunksize=4))
    else:
        checked_rows = [_recompute_row(a) for a in args]
    candidates = _candidates(checked_rows)
    for a, b in candidates:
        for n in range(a, b+1):
            _require(target.half_distance(n) > guard, 'hazard within guard found: not a certificate')
    qmax = H._value(q, hi)
    impulse_bound = F(sum(abs(c)*hi**k for k, c in p.items()), H._value(q, lo))+guard
    return {
        'version': VERSION, 'status': 'certified', 'scope': SCOPE, 'global_4_4b': 'NotCertified',
        'domain': domain, 'domain_hash': R.domain_hash(domain),
        'foundation_sha256': {**K.FOUNDATION_HASHES, **FOUNDATION_HASHES},
        'P': tuple(sorted(p.items())), 'Q': tuple(sorted(q.items())),
        'residual_interval': (str(residual[0]), str(residual[1])), 'numeric_error': str(error),
        'residual_bits': RESIDUAL_BITS, 'guard': str(guard),
        'required_bits': RESIDUAL_BITS, 'max_decision_bits': RESIDUAL_BITS,
        'Q_max': qmax, 'lattice_point_count': hi-lo+1, 'block_points': points,
        'superblocks': tuple(checked_rows),
        'candidate_count': sum(b-a+1 for a, b in candidates),
        'impulse_abs_upper': str(impulse_bound), 'momentum_scale': momentum_scale,
        'actual_trajectory_membership': 'not_claimed',
    }


def verify_certificate(cert, expected_domain, *, execution_limit=16384, workers=1):
    """External domain and execution ceiling are obligations, never inferred from cert.

    Every quantity (guard, derivative bound, crossing count, candidate set,
    hazard check, impulse bound) is recomputed here from c1b1_hard_case_checker
    primitives; nothing from `cert` is trusted except as a claim to re-derive
    and compare against.
    """
    try:
        foundation_guard()
        domain = R.axis_domain(expected_domain['axis'], expected_domain['lo'], expected_domain['hi'])
        _require(domain == expected_domain and domain['lo'] > 0, 'positive declared domain required')
        _require(cert['version'] == VERSION and cert['status'] == 'certified' and cert['scope'] == SCOPE
                 and cert['global_4_4b'] == 'NotCertified', 'wrong hard-case certificate contract')
        _require(cert['domain'] == domain and cert['domain_hash'] == R.domain_hash(domain), 'external domain mismatch')
        _require(cert['foundation_sha256'] == {**K.FOUNDATION_HASHES, **FOUNDATION_HASHES},
                 'foundation provenance changed')
        bits = _int(cert['required_bits'])
        K.A.precision_guard(bits)
        K.A.precision_guard(_int(execution_limit))
        _require(bits == RESIDUAL_BITS <= execution_limit <= K.A.C.MAX_PRECISION_BITS,
                 'proof precision exceeds actual execution limit')
        _require(_int(cert['max_decision_bits']) == bits and _int(cert['residual_bits']) == RESIDUAL_BITS,
                 'precision metadata changed')
        p, q, terms, dpoly = K.frozen_identity()
        p_cert = dict((_int(k), _int(v)) for k, v in cert['P'])
        q_cert = dict((_int(k), _int(v)) for k, v in cert['Q'])
        _require(p_cert == p and q_cert == q, 'frozen rational identity mismatch')
        _require(all(k >= 0 and c > 0 for k, c in q.items()), 'positive monotone Q not proved')
        lo, hi = domain['lo'], domain['hi']
        target = H.Rational(p, q)
        qmax = H._value(q, hi)
        _require(_int(cert['Q_max']) == qmax and _int(cert['lattice_point_count']) == hi-lo+1,
                 'domain endpoints/Q_max changed')

        guard, residual, error = guard_value(lo, hi, RESIDUAL_BITS)
        _require(tuple(_fraction(x) for x in cert['residual_interval']) == residual,
                 'signed residual interval changed')
        _require(_fraction(cert['numeric_error']) == error and error >= 0, 'numeric endpoint error changed')
        _require(_fraction(cert['guard']) == guard, 'signed guard changed')

        rows = cert['superblocks']
        _require(rows and rows[0]['range'][0] == lo and rows[-1]['range'][1] == hi,
                 'rows do not cover the declared domain')
        _require(all(rows[i]['range'][1]+1 == rows[i+1]['range'][0] for i in range(len(rows)-1)),
                 'superblock ranges are not contiguous')
        # The verifier's own bound, independent of whatever the certificate claims:
        # a smaller claimed bound cannot shrink the candidate set below what is
        # actually required.
        points = _int(cert['block_points'])
        _require(points > H.EXACT_BLOCK+1, 'block length required')
        args = [(entry['range'][0], entry['range'][1], guard, points) for entry in rows]
        if workers > 1:
            with ProcessPoolExecutor(workers) as pool:
                recomputed = list(pool.map(_recompute_row, args, chunksize=4))
        else:
            recomputed = [_recompute_row(a) for a in args]
        for entry, mine in zip(rows, recomputed):
            _require(entry['derivative_bound'] == mine['derivative_bound'],
                     'derivative bound does not match recomputation')
            _require(entry['crossings'] == mine['crossings'], 'crossing count mismatch')
            _require(entry['candidate_intervals'] == mine['candidate_intervals'], 'candidate set mismatch')
        candidates = _candidates(recomputed)
        _require(cert['candidate_count'] == sum(b-a+1 for a, b in candidates), 'candidate count changed')
        for a, b in candidates:
            for n in range(a, b+1):
                if target.half_distance(n) <= guard:
                    raise O.NotCertified('hazard within guard survives in candidates')

        impulse_bound = F(sum(abs(c)*hi**k for k, c in p.items()), H._value(q, lo))+guard
        _require(_fraction(cert['impulse_abs_upper']) == impulse_bound, 'impulse upper bound changed')
        _require(_int(cert['momentum_scale'])*impulse_bound < MOMENTUM_LIMIT, 'legal momentum output not proved')
        return domain
    except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError) as error:
        raise O.NotCertified(f'invalid hard-case certificate: {error}') from error


def check_outgoing_coverage(run, p_cap, legacy_certificates, boundary_obligations, family_obligations,
                            hard_case_obligations, *, workers=1):
    """Only externally checked whole domains enter fresh closed-integer coverage.

    Stacks on top of c1b1_family_certificates.check_outgoing_coverage exactly
    as that module stacks on c1b1_half_ulp_boundaries, which stacks on
    c1b1_rounding_regions: each layer only narrows the previous layer's
    uncovered_intervals using its own independently verified domains.
    """
    hard_case_obligations = tuple(hard_case_obligations)
    count = len(legacy_certificates)+len(boundary_obligations)+len(family_obligations)+len(hard_case_obligations)
    if count > R.MAX_REGIONS:
        raise O.NotCertified('fixed 64-region budget exceeded')
    previous = FC.check_outgoing_coverage(run, p_cap, legacy_certificates, boundary_obligations, family_obligations)
    domains = [verify_certificate(cert, expected, workers=workers) for cert, expected in hard_case_obligations]
    gaps = []
    for required in previous['uncovered_intervals']:
        lo, hi = required['raw_interval']
        covered = [(d['lo'], d['hi']) for d in domains if d['axis'] == required['axis']]
        gaps.extend({**required, 'raw_interval': gap} for gap in R._gaps(lo, hi, covered))
    return {**previous, 'version': VERSION, 'status': 'not_certified' if gaps else 'certified',
            'global_4_4b': 'NotCertified', 'used_regions': count,
            'uncovered_intervals': tuple(gaps), 'tail': previous['tail'] if not gaps else None}


def certify_shell_18(*, workers=1):
    """Build and immediately verify a fresh hard-case certificate for shell 18.

    Every quantity is recomputed from primitives at build time (see build()),
    so this certificate does not depend on the earlier survey_only artifact
    at all — only the domain endpoints are read from the pinned fixture via
    load_shell.
    """
    K.foundation_guard()
    _, lo, hi, _, _ = G.load_shell(18)
    domain = {'kind': 'axis_lattice_interval', 'axis': 0, 'lo': lo, 'hi': hi}
    ranges = H.blocks(lo, hi, SHELL_18_BLOCK_LENGTH, SHELL_18_SUPERBLOCKS)
    cert = build(ranges, domain, SHELL_18_BLOCK_LENGTH, workers=workers)
    verify_certificate(cert, domain, workers=workers)
    return cert, domain


def example_report(workers=1):
    """Certify shell 18, compose fresh coverage on top of the existing 11/64 layers."""
    cert, domain = certify_shell_18(workers=workers)
    original = json.loads((ROOT/'a_reference/fixtures/c1b1_rounding_regions_v1.json').read_text(encoding='utf-8'))
    legacy = [R.certify_finite_points(original['finite_acceptance']['domain']['points'], bits=256)]
    for c in original['analytic_and_singleton_certificates']:
        d = c['domain']
        legacy.append(R.certify_finite_points(d['points'], bits=c['bits']) if d['kind'] == 'finite_points' else
                      R.certify_axis_zero_region(d['axis'], d['lo'], d['hi'], bits=c['bits']))
    from a_reference import c1b1_half_ulp_boundaries as HB
    boundary_fixture = json.loads((ROOT/'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json').read_text(encoding='utf-8'))
    boundaries = []
    for g in boundary_fixture['groups']:
        if g['certificate']['status'] == 'certified':
            d = g['certificate']['domain']
            boundaries.append((HB.certify_axis_domain(d['axis'], d['lo'], d['hi']), d))
    families_report = json.loads((ROOT/'a_reference/fixtures/c1b1_family_certificates_v1.json').read_text(encoding='utf-8'))
    families = tuple((g['certificate'], g['expected_domain']) for g in families_report['groups'])
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0),
                    (10, 0, 0), (1, 0, 0), momentum_profile=FixedPoint(96, 80))
    coverage = check_outgoing_coverage(run, F(2), legacy, boundaries, families, ((cert, domain),), workers=workers)
    return {'version': VERSION, 'status': 'certified', 'global_4_4b': 'NotCertified',
            'shell_index': 18, 'certificate': cert, 'expected_domain': domain,
            'coverage': coverage,
            'source_sha256': {name: sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                              for name in ('a_reference/c1b1_hard_case_certificate.py',
                                           'a_reference/c1b1_hard_case_checker.py',
                                           'a_reference/c1b1_hard_case_search.py')}}


if __name__ == '__main__':
    import sys
    output = json.dumps(T.serial(example_report(workers=6)), indent=2)+'\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
