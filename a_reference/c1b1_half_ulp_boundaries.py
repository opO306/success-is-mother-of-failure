"""Half-ulp boundary inverse exclusion, not a global C1-B1 certificate.

Count before enumerating. Huge boundary families remain explicit obligations.
All coordinates, targets, and comparisons are exact rational intervals.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
import json

from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_rounding_completeness as D
from a_numeric import FixedPoint

VERSION = 'c1b1-half-ulp-boundaries-v1'
BOUNDARY_BUDGET = 64                 # work limit; never enlarges region budget
CANDIDATE_BUDGET = 64
INVERSE_STEPS = 64
INVERSE_WIDTH = Q(1, 8)               # raw input units, not physical bohr
PHYSICAL_ENCLOSURE_BITS = 512


def _ceil(x):
    return -(-x.numerator//x.denominator)


def _floor(x):
    return x.numerator//x.denominator


@dataclass(frozen=True)
class _Problem:
    domain: dict
    scope: str
    point: object
    slope: object
    error: object
    direct: object


def _axis_problem(domain):
    A.proof_guard()
    domain = R.axis_domain(domain['axis'], domain['lo'], domain['hi'])
    lo, hi, axis = domain['lo'], domain['hi'], domain['axis']
    a, b = sorted((abs(lo)*B.UX, abs(hi)*B.UX))
    cache = {}
    def point(n):
        n = B.exact(n)
        if not lo <= n <= hi:
            raise O.NotCertified('inverse point outside declared domain')
        if n not in cache:
            radius = abs(n)*B.UX
            derivative = C._model(radius*radius, PHYSICAL_ENCLOSURE_BITS, True)[1]
            sign = -1 if n > 0 else 1
            values = tuple(sign*Q(x, 1 << PHYSICAL_ENCLOSURE_BITS)*20/B.UP for x in derivative)
            cache[n] = (min(values), max(values))
        return cache[n]
    def slope():
        ddv = A.axis_derivatives(a, b)[1]
        iv = -ddv*(20*B.UX/B.UP)
        return iv.lo, iv.hi
    def error(bits):
        return A.axis_impulse_error(a, b, bits)/B.UP
    def direct(n, bits):
        raw = [0, 0, 0]
        raw[axis] = n
        proof = R.certify_finite_points((tuple(raw),), bits=bits)
        return {'bits': bits, 'margin_lower': proof['common_margin_lower']/B.UP,
                'endpoint_error_upper': proof['common_endpoint_error_upper']/B.UP,
                'point_certificate': proof}
    return _Problem(domain, 'declared_axis_lattice_domain_only', point, slope, error, direct)


def _inventory(problem, bits):
    A.precision_guard(bits)
    lo, hi = problem.domain['lo'], problem.domain['hi']
    slope = problem.slope()
    if not 0 < slope[0] <= slope[1]:
        raise O.NotCertified('strict increasing direction not proved')
    left, right = problem.point(Q(lo)), problem.point(Q(hi))
    error = B.exact(problem.error(bits))
    if error <= 0:
        raise O.NotCertified('positive common endpoint error required')
    # Twice the evaluator error leaves a common strict safety margin.
    forbidden = 2*error
    first = _ceil(left[0]-forbidden-Q(1, 2))
    last = _floor(right[1]+forbidden-Q(1, 2))
    inner_first = _ceil(left[1]-forbidden-Q(1, 2))
    inner_last = _floor(right[0]+forbidden-Q(1, 2))
    exact_count = (first, last) == (inner_first, inner_last)
    return {'domain': problem.domain, 'scope': problem.scope, 'bits': bits,
            'monotonic_direction': 'strictly_increasing', 'slope_interval': slope,
            'I_min_enclosure_ulps': left, 'I_max_enclosure_ulps': right,
            'ulp_span_enclosure': (right[0]-left[1], right[1]-left[0]),
            'endpoint_error_upper_ulps': error, 'forbidden_radius_ulps': forbidden,
            'half_ulp_index_range': (first, last), 'boundary_count': max(0, last-first+1),
            'boundary_count_exact': exact_count, 'lattice_point_count': hi-lo+1,
            'actual_trajectory_membership': 'not_claimed'}


def _inverse(problem, target):
    """Closed bracket of the clipped inverse; no approximate scalar root."""
    left, right = Q(problem.domain['lo']), Q(problem.domain['hi'])
    if problem.point(left)[0] >= target:
        return (left, left)
    if problem.point(right)[1] <= target:
        return (right, right)
    for _ in range(INVERSE_STEPS):
        if right-left <= INVERSE_WIDTH:
            return left, right
        middle = (left+right)/2
        lower, upper = problem.point(middle)
        if upper <= target:
            left = middle
        elif lower >= target:
            right = middle
        else:
            # Ambiguous physical enclosure: retain the current bracket.
            # Candidate counting, rather than an invented side, handles it.
            return left, right
    if right-left > INVERSE_WIDTH:
        raise O.NotCertified('inverse bisection work limit reached')
    return left, right


def _candidate_interval(lower_inverse, upper_inverse):
    left, right = lower_inverse[0], upper_inverse[1]
    return (_ceil(left), _floor(right))


def _direct_until_margin(problem, n, bits, error):
    attempts = []
    for p in (128 << k for k in range(8)):
        if p < bits:
            continue
        try:
            proof = problem.direct(n, p)
            if (proof['bits'] == p and 0 <= proof['endpoint_error_upper'] < proof['margin_lower']
                    and proof['margin_lower'] > error):
                return proof, tuple(attempts)
            attempts.append(p)
        except O.NotCertified:
            attempts.append(p)
    raise O.NotCertified('candidate margin not closed; common error may need refinement')


def _construct(problem, bits, *, boundary_budget=BOUNDARY_BUDGET, candidate_budget=CANDIDATE_BUDGET):
    summary = _inventory(problem, bits)
    result = {'version': VERSION, 'kind': 'HalfUlpBoundaryExclusionCertificate', **summary,
              'status': 'not_certified', 'boundary_budget': boundary_budget,
              'candidate_budget': candidate_budget, 'records': (), 'candidate_integers': None,
              'candidate_lattice_point_count': None, 'global_4_4b': 'NotCertified'}
    if not summary['boundary_count_exact']:
        return {**result, 'reason': 'endpoint_enclosures_do_not_fix_boundary_indices'}
    if summary['boundary_count'] > boundary_budget:
        return {**result, 'reason': 'symbolic_boundary_family_required'}
    records, candidates = [], set()
    first, last = summary['half_ulp_index_range']
    for k in range(first, last+1):
        h, radius = Q(k)+Q(1, 2), summary['forbidden_radius_ulps']
        lower_inverse = _inverse(problem, h-radius)
        upper_inverse = _inverse(problem, h+radius)
        first_n, last_n = _candidate_interval(lower_inverse, upper_inverse)
        count = max(0, last_n-first_n+1)
        if count > candidate_budget or len(candidates)+count > candidate_budget:
            return {**result, 'records': tuple(records), 'reason': 'candidate_work_limit',
                    'blocked_boundary_index': k, 'blocked_candidate_count': count}
        integers = tuple(range(first_n, last_n+1))
        candidates.update(integers)
        records.append({'half_ulp_index': k, 'target_band_ulps': (h-radius, h+radius),
                        'lower_inverse_bracket': lower_inverse, 'upper_inverse_bracket': upper_inverse,
                        'forbidden_preimage_outer': (lower_inverse[0], upper_inverse[1]),
                        'candidate_integers': integers, 'candidate_count': count,
                        'disposition': 'excluded_no_integer' if not integers else 'direct_candidates'})
    point_proofs = []
    for n in sorted(candidates):
        try:
            proof, attempts = _direct_until_margin(problem, n, bits, summary['endpoint_error_upper_ulps'])
        except O.NotCertified:
            return {**result, 'records': tuple(records), 'candidate_integers': tuple(sorted(candidates)),
                    'candidate_lattice_point_count': len(candidates),
                    'reason': 'candidate_margin_requires_common_precision_refinement',
                    'blocked_candidate': n, 'point_precision_cap': 16384}
        point_proofs.append({'input_raw': n, 'proof': proof, 'unsuccessful_bits': attempts})
    margin = min((p['proof']['margin_lower'] for p in point_proofs), default=radius if records else 2*summary['endpoint_error_upper_ulps'])
    margin = min(margin, summary['forbidden_radius_ulps'])
    return {**result, 'status': 'certified', 'reason': None, 'records': tuple(records),
            'candidate_integers': tuple(sorted(candidates)), 'candidate_lattice_point_count': len(candidates),
            'direct_point_proofs': tuple(point_proofs), 'common_margin_lower_ulps': margin,
            'max_decision_bits': max([bits]+[p['proof']['bits'] for p in point_proofs])}


def certify_axis_domain(axis, lo, hi):
    problem = _axis_problem(R.axis_domain(axis, lo, hi))
    attempted = []
    for bits in (256 << k for k in range(7)):
        result = _construct(problem, bits)
        attempted.append(bits)
        if result.get('reason') != 'candidate_margin_requires_common_precision_refinement':
            return {**result, 'common_precision_attempts': tuple(attempted)}
    return {**result, 'reason': 'candidate_margin_not_certified_at_precision_cap',
            'common_precision_attempts': tuple(attempted)}


def _verify_inverse(problem, bracket, target):
    left, right = bracket
    lo, hi = problem.domain['lo'], problem.domain['hi']
    if not lo <= left <= right <= hi:
        raise O.NotCertified('inverse bracket outside domain')
    if left > lo and problem.point(left)[1] > target:
        raise O.NotCertified('inverse lower endpoint does not bound the root')
    if right < hi and problem.point(right)[0] < target:
        raise O.NotCertified('inverse upper endpoint does not bound the root')


def _verify(problem, certificate):
    """Check final inequalities independently of the bisection search path."""
    summary = _inventory(problem, certificate['bits'])
    if certificate['version'] != VERSION or certificate['kind'] != 'HalfUlpBoundaryExclusionCertificate' or certificate['status'] != 'certified':
        raise O.NotCertified('only a complete boundary certificate can be checked')
    if (certificate['global_4_4b'] != 'NotCertified' or certificate['boundary_budget'] != BOUNDARY_BUDGET
            or certificate['candidate_budget'] != CANDIDATE_BUDGET):
        raise O.NotCertified('global scope or fixed work limits changed')
    if any(certificate[k] != v for k, v in summary.items()):
        raise O.NotCertified('domain, direction, error or inventory changed')
    if not summary['boundary_count_exact'] or summary['boundary_count'] > BOUNDARY_BUDGET:
        raise O.NotCertified('boundary enumeration not complete within fixed work budget')
    first, last = summary['half_ulp_index_range']
    records = certificate['records']
    if tuple(r['half_ulp_index'] for r in records) != tuple(range(first, last+1)):
        raise O.NotCertified('half-ulp boundary omitted, duplicated or reordered')
    all_candidates = set()
    for record in records:
        h, radius = Q(record['half_ulp_index'])+Q(1, 2), summary['forbidden_radius_ulps']
        if record['target_band_ulps'] != (h-radius, h+radius):
            raise O.NotCertified('forbidden band changed')
        _verify_inverse(problem, record['lower_inverse_bracket'], h-radius)
        _verify_inverse(problem, record['upper_inverse_bracket'], h+radius)
        lower, upper = record['lower_inverse_bracket'][0], record['upper_inverse_bracket'][1]
        a, b = _candidate_interval(record['lower_inverse_bracket'], record['upper_inverse_bracket'])
        count = max(0, b-a+1)
        if count > CANDIDATE_BUDGET:
            raise O.NotCertified('candidate budget exceeded')
        integers = tuple(range(a, b+1))
        if (record['forbidden_preimage_outer'] != (lower, upper) or record['candidate_integers'] != integers
                or record['candidate_count'] != count
                or record['disposition'] != ('direct_candidates' if count else 'excluded_no_integer')):
            raise O.NotCertified('candidate integer omitted or preimage changed')
        all_candidates.update(integers)
    if len(all_candidates) > CANDIDATE_BUDGET or certificate['candidate_integers'] != tuple(sorted(all_candidates)) or certificate['candidate_lattice_point_count'] != len(all_candidates):
        raise O.NotCertified('candidate union changed')
    proofs = certificate['direct_point_proofs']
    if tuple(p['input_raw'] for p in proofs) != tuple(sorted(all_candidates)):
        raise O.NotCertified('direct candidate certificate omitted')
    for p in proofs:
        A.precision_guard(p['proof']['bits'])
        rebuilt = problem.direct(p['input_raw'], p['proof']['bits'])
        if rebuilt != p['proof'] or not (0 <= rebuilt['endpoint_error_upper'] < rebuilt['margin_lower'] and rebuilt['margin_lower'] > summary['endpoint_error_upper_ulps']):
            raise O.NotCertified('direct precision certificate changed')
    margin = min((p['proof']['margin_lower'] for p in proofs), default=summary['forbidden_radius_ulps'])
    margin = min(margin, summary['forbidden_radius_ulps'])
    maximum = max([summary['bits']]+[p['proof']['bits'] for p in proofs])
    if (certificate['common_margin_lower_ulps'] != margin or certificate['max_decision_bits'] != maximum
            or not summary['endpoint_error_upper_ulps'] < margin):
        raise O.NotCertified('common margin or precision changed')
    return problem.domain


def verify_certificate(certificate, expected_domain):
    """Expected domain comes from the coverage obligation, not this certificate."""
    try:
        return _verify(_axis_problem(expected_domain), certificate)
    except (KeyError, TypeError, ValueError) as error:
        raise O.NotCertified(f'invalid boundary certificate: {error}') from error


def check_outgoing_coverage(run, p_cap, legacy_certificates, boundary_obligations):
    """Compose checked domains against fresh geometry, preserving every gap.

    Each boundary obligation is (certificate, externally expected domain).
    The old uniform/finite/zero APIs remain unchanged.
    """
    legacy_certificates, boundary_obligations = tuple(legacy_certificates), tuple(boundary_obligations)
    if len(legacy_certificates)+len(boundary_obligations) > R.MAX_REGIONS:
        raise O.NotCertified('fixed 64-region budget exceeded')
    previous = R.check_outgoing_coverage(run, p_cap, legacy_certificates)
    domains = [R.verify_region(c) for c in legacy_certificates]
    domains.extend(verify_certificate(c, expected) for c, expected in boundary_obligations)
    gaps = []
    for required in previous['required_intervals']:
        axis, (lo, hi) = required['axis'], required['raw_interval']
        covered = []
        for domain in domains:
            if domain['kind'] == 'axis_lattice_interval' and domain['axis'] == axis:
                covered.append((domain['lo'], domain['hi']))
            elif domain['kind'] == 'finite_points':
                covered.extend((q[axis], q[axis]) for q in domain['points']
                               if all(q[k] == 0 for k in range(3) if k != axis))
        gaps.extend({**required, 'raw_interval': gap} for gap in R._gaps(lo, hi, covered))
    return {'version': VERSION, 'status': 'not_certified' if gaps else 'certified',
            'scope': previous['scope'], 'global_4_4b': 'NotCertified', 'region_budget': 64,
            'used_regions': len(domains), 'required_intervals': previous['required_intervals'],
            'uncovered_intervals': tuple(gaps), 'tail': D.certify_zero_tail() if not gaps else None}


def example_report():
    root = Path(__file__).resolve().parents[1]
    prior_path = root/'a_reference/fixtures/c1b1_rounding_regions_v1.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    for path, expected in prior['source_sha256'].items():
        if sha256((root/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise O.NotCertified('prior group proof provenance changed')
    groups = []
    for group in prior['groups']:
        if group['common_precision_certified']:
            continue
        domain = group['domain']
        proof = certify_axis_domain(domain['axis'], domain['lo'], domain['hi'])
        if proof['status'] == 'certified':
            verify_certificate(proof, domain)
        groups.append({'shell_index': group['shell_index'], 'certificate': proof})
    legacy = [R.certify_finite_points(prior['finite_acceptance']['domain']['points'], bits=256)]
    for previous in prior['analytic_and_singleton_certificates']:
        domain = previous['domain']
        if domain['kind'] == 'finite_points':
            legacy.append(R.certify_finite_points(domain['points'], bits=previous['bits']))
        else:
            legacy.append(R.certify_axis_zero_region(domain['axis'], domain['lo'], domain['hi'], bits=previous['bits']))
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0),
                    (10, 0, 0), (1, 0, 0), momentum_profile=FixedPoint(96, 80))
    obligations = tuple((g['certificate'], g['certificate']['domain']) for g in groups
                        if g['certificate']['status'] == 'certified')
    coverage = check_outgoing_coverage(run, Q(2), legacy, obligations)
    return {'version': VERSION, 'status': 'not_certified', 'global_4_4b': 'NotCertified',
            'region_budget': 64, 'boundary_work_budget': BOUNDARY_BUDGET,
            'candidate_work_budget': CANDIDATE_BUDGET, 'groups': tuple(groups),
            'outgoing_coverage': coverage,
            'prior_fixture_sha256': sha256(prior_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            'certified_group_count': sum(g['certificate']['status'] == 'certified' for g in groups),
            'symbolic_family_group_count': sum(g['certificate'].get('reason') == 'symbolic_boundary_family_required' for g in groups),
            'physical_executor_modified': False, 'frozen_D_valid_modified': False,
            'source_sha256': {'a_reference/c1b1_half_ulp_boundaries.py': sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}}


if __name__ == '__main__':
    import sys
    output = json.dumps(T.serial(example_report()), indent=2)+'\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
