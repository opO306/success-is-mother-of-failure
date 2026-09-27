"""Multi-output proof regions, separate from complete outgoing coverage.

The old uniform-output certifier and the physical executor are unchanged.
An explicit finite domain is not a claim about actual trajectory membership.
"""
from fractions import Fraction as Q
from hashlib import sha256
import json

from a_numeric import FixedPoint
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_reachable_geometry as G
from a_reference import c1b1_rounding_completeness as D
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_axis_decision_bounds as A

VERSION = 'c1b1-rounding-regions-v1'
MAX_REGIONS = 64


def _domain(kind, **fields):
    return {'kind': kind, **fields}


def finite_domain(points):
    points = tuple(tuple(q) for q in points)
    if not points or len(set(points)) != len(points):
        raise O.NotCertified('nonempty distinct explicit inputs required')
    for q in points:
        if len(q) != 3 or any(type(x) is not int or abs(x) > (1 << 96)-1 for x in q):
            raise O.NotCertified('legal exact relative raw tuples required')
        if sum(x*x for x in q)*B.UX**2 < C.R_MIN2:
            raise O.NotCertified('input outside frozen physical domain')
    return _domain('finite_points', points=tuple(sorted(points)))


def axis_domain(axis, lo, hi):
    if type(axis) is not int or axis not in (0, 1, 2):
        raise O.NotCertified('coordinate axis required')
    if any(type(x) is not int or abs(x) > (1 << 96)-1 for x in (lo, hi)):
        raise O.NotCertified('legal relative grid endpoints required')
    if lo > hi or lo <= 0 <= hi or min(abs(lo), abs(hi))*B.UX < 20:
        raise O.NotCertified('one signed outer axis interval required')
    return _domain('axis_lattice_interval', axis=axis, lo=lo, hi=hi)


def _canonical(domain):
    if domain['kind'] == 'finite_points':
        return finite_domain(domain['points'])
    if domain['kind'] == 'axis_lattice_interval':
        return axis_domain(domain['axis'], domain['lo'], domain['hi'])
    raise O.NotCertified('unknown input domain')


def domain_hash(domain):
    return sha256(json.dumps(_canonical(domain), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _point_enclosures(domain, bits):
    values = []
    for raw in domain['points']:
        q = tuple(x*B.UX for x in raw)
        _, dv, inv = C._model(sum(x*x for x in q), bits, True)
        ratio = C._mul(C._neg(dv), inv, bits)
        components = []
        for x in q:
            ends = tuple(Q(y, 1 << bits)*x*B.H/2 for y in ratio) if x else (Q(0), Q(0))
            components.append((min(ends), max(ends)))
        values.append(tuple(components))
    return tuple(values)


def _finite_obligations(enclosures, outputs):
    margins, errors = [], []
    if len(enclosures) != len(outputs) or not outputs:
        raise O.NotCertified('one result for every explicit input required')
    for intervals, raw in zip(enclosures, outputs):
        if len(intervals) != 3 or len(raw) != 3:
            raise O.NotCertified('three impulse components required')
        for (lo, hi), n in zip(intervals, raw):
            if type(n) is not int or not -(1 << 95) <= n < (1 << 95) or lo > hi:
                raise O.NotCertified('invalid result or enclosure')
            margin = min(lo-(Q(n)-Q(1, 2))*B.UP, (Q(n)+Q(1, 2))*B.UP-hi)
            if margin <= 0:
                raise O.NotCertified('strict rounding-boundary separation not proved')
            margins.append(margin)
            errors.append(hi-lo)
    delta, epsilon = min(margins), max(errors)
    if not 0 <= epsilon < delta:
        raise O.NotCertified('common endpoint error is not below common margin')
    return delta, epsilon


def _header(domain, bits, method):
    return {'version': VERSION, 'status': 'certified', 'scope': 'declared_input_set_only',
            'domain': domain, 'domain_sha256': domain_hash(domain), 'bits': bits,
            'method': method, 'actual_trajectory_membership': 'not_claimed'}


def certify_finite_points(points, *, bits=128):
    """One region, one common precision; enumerate every declared member."""
    A.proof_guard()
    A.precision_guard(bits)
    domain = finite_domain(points)
    values = _point_enclosures(domain, bits)
    profile = FixedPoint(96, 80)
    outputs = tuple(tuple(profile.from_exact((lo+hi)/2) for lo, hi in row) for row in values)
    delta, epsilon = _finite_obligations(values, outputs)
    return {**_header(domain, bits, 'exhaustive_finite_domain'), 'enclosures': values,
            'outputs': outputs, 'common_margin_lower': delta, 'common_endpoint_error_upper': epsilon,
            'input_count': len(domain['points']), 'distinct_output_count': len(set(outputs))}


def _axis_obligations(domain, bits):
    a, b = sorted((abs(domain['lo'])*B.UX, abs(domain['hi'])*B.UX))
    dv, ddv = A.axis_derivatives(a, b)
    # Exact cancellation q/R=sign(q) in the PHYSICAL function only.
    impulse = -dv*(B.H/2)
    if domain['hi'] < 0:
        impulse = -impulse
    epsilon = A.axis_impulse_error(a, b, bits)
    delta = B.UP/2-impulse.magnitude
    if not 0 <= epsilon < delta:
        raise O.NotCertified('axis zero-region margin/error obligation not closed')
    return {'physical_impulse_interval': (impulse.lo, impulse.hi),
            'physical_derivative_intervals': ((dv.lo, dv.hi), (ddv.lo, ddv.hi)),
            'common_margin_lower': delta, 'common_endpoint_error_upper': epsilon}


def certify_axis_zero_region(axis, lo, hi, *, bits=256):
    """Prove all lattice points without enumerating or splitting the interval."""
    A.proof_guard()
    A.precision_guard(bits)
    domain = axis_domain(axis, lo, hi)
    result = _axis_obligations(domain, bits)
    return {**_header(domain, bits, 'analytic_axis_zero'), **result,
            'input_count': hi-lo+1, 'output': (0, 0, 0)}


def verify_region(certificate):
    """Re-establish physical foundations, then check exact proof obligations.

    This is a proof checker, not an independent implementation of the PES.
    Domain changes, omitted results and forged margins cannot pass it.
    """
    A.proof_guard()
    try:
        bits = certificate['bits']
        A.precision_guard(bits)
        domain = _canonical(certificate['domain'])
        if certificate['version'] != VERSION or certificate['status'] != 'certified' or certificate['scope'] != 'declared_input_set_only':
            raise O.NotCertified('wrong proof version, scope or status')
        if domain_hash(domain) != certificate['domain_sha256']:
            raise O.NotCertified('input domain changed')
        if certificate['method'] == 'exhaustive_finite_domain' and domain['kind'] == 'finite_points':
            values = _point_enclosures(domain, bits)
            if values != certificate['enclosures']:
                raise O.NotCertified('point evaluator enclosures changed')
            delta, epsilon = _finite_obligations(values, certificate['outputs'])
            expected = {'common_margin_lower': delta, 'common_endpoint_error_upper': epsilon,
                        'input_count': len(domain['points']),
                        'distinct_output_count': len(set(certificate['outputs']))}
        elif certificate['method'] == 'analytic_axis_zero' and domain['kind'] == 'axis_lattice_interval':
            expected = {**_axis_obligations(domain, bits), 'input_count': domain['hi']-domain['lo']+1,
                        'output': (0, 0, 0)}
        else:
            raise O.NotCertified('method/domain mismatch')
        if any(certificate[key] != value for key, value in expected.items()):
            raise O.NotCertified('proof obligation or count changed')
    except (KeyError, TypeError, ValueError) as error:
        raise O.NotCertified(f'malformed or invalid region proof: {error}') from error
    return domain


def _gaps(lo, hi, intervals):
    cursor, gaps = lo, []
    for left, right in sorted(intervals):
        left, right = max(left, lo), min(right, hi)
        if left > right or right < cursor:
            continue
        if left > cursor:
            gaps.append((cursor, left-1))
        cursor = max(cursor, right+1)
    if cursor <= hi:
        gaps.append((cursor, hi))
    return tuple(gaps)


def check_outgoing_coverage(run, p_cap, certificates):
    """Fresh conservative geometry; no interpolation or trajectory replay."""
    certificates = tuple(certificates)
    if len(certificates) > MAX_REGIONS:
        raise O.NotCertified('fixed 64-region budget exceeded')
    domains = tuple(verify_region(c) for c in certificates)
    geometry, projection = G.certify_outgoing_reachable(run, p_cap)
    missing, required = [], []
    for index, shell in enumerate(geometry['shells']):
        constraint = projection['shells'][index]
        axis, parts = T._axis_intervals(constraint['root_box'], shell, constraint)
        covered = []
        for domain in domains:
            if domain['kind'] == 'axis_lattice_interval' and domain['axis'] == axis:
                covered.append((domain['lo'], domain['hi']))
            elif domain['kind'] == 'finite_points':
                covered.extend((q[axis], q[axis]) for q in domain['points']
                               if all(q[k] == 0 for k in range(3) if k != axis))
        for lo, hi in parts:
            required.append({'shell_index': index, 'axis': axis, 'raw_interval': (lo, hi)})
            for gap in _gaps(lo, hi, covered):
                missing.append({'shell_index': index, 'axis': axis, 'raw_interval': gap})
    tail = D.certify_zero_tail() if not missing else None
    return {'version': VERSION, 'status': 'not_certified' if missing else 'certified',
            'scope': 'this_initial_state_outgoing_projection_only', 'region_budget': MAX_REGIONS,
            'used_regions': len(certificates), 'required_intervals': tuple(required),
            'uncovered_intervals': tuple(missing), 'tail': tail,
            'global_initial_state_family_completeness': 'not_claimed'}


def study_axis_group(axis, lo, hi, *, bits=256):
    """Classify the unresolved analytic obligations without changing domains."""
    A.precision_guard(bits)
    domain = axis_domain(axis, lo, hi)
    a, b = sorted((abs(lo)*B.UX, abs(hi)*B.UX))
    dv, ddv = A.axis_derivatives(a, b)
    # On either signed branch dJ/dq=-20 V''(|q|).
    slope = -ddv*(B.H/2)
    increasing = slope.lo > 0
    decreasing = slope.hi < 0
    separation = (slope.lo if increasing else -slope.hi if decreasing else Q(0))*B.UX
    impulse = -dv*(B.H/2) if hi > 0 else dv*(B.H/2)
    error = A.axis_impulse_error(a, b, bits)
    margin = B.UP/2-impulse.magnitude
    return {'domain': domain, 'declared_lattice_point_count': hi-lo+1,
            'actual_visited_point_count': 'not_proved',
            'V_prime_interval': (dv.lo, dv.hi), 'V_second_interval': (ddv.lo, ddv.hi),
            'impulse_interval': (impulse.lo, impulse.hi),
            'monotonicity': 'strictly_increasing' if increasing else 'strictly_decreasing' if decreasing else 'not_proved',
            'adjacent_impulse_separation_lower': separation,
            'interior_extrema': 'excluded' if increasing or decreasing else 'not_proved',
            'zero_crossing': 'excluded' if impulse.lo > 0 or impulse.hi < 0 else 'not_proved',
            'common_endpoint_error_upper': error, 'error_bound_bits': bits,
            'common_rounding_margin_lower': margin if margin > 0 else None,
            'common_precision_certified': bool(0 <= error < margin),
            'reflection_proof_reusable': True,
            'blocking_obligation': None if 0 <= error < margin else 'lattice_rounding_boundary_margin_not_proved'}


def example_report():
    """65-member acceptance case, all 29 groups, and truthful coverage gaps."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    diagnosis_path = root/'a_reference/fixtures/c1b1_rounding_diagnosis_v1.json'
    diagnosis = json.loads(diagnosis_path.read_text(encoding='utf-8'))
    for path, expected in diagnosis['source_sha256'].items():
        actual = sha256((root/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if actual != expected:
            raise O.NotCertified('diagnosis source provenance changed')
    points = tuple(tuple(int(Q(x)/B.UX) for x in witness['q'])
                   for witness in diagnosis['uniform_cover_obstruction']['witnesses'])
    finite = certify_finite_points(points, bits=256)
    groups, additional = [], []
    for original in diagnosis['connected_groups']:
        lo, hi = original['raw_interval']
        study = study_axis_group(0, lo, hi)
        study.update({'shell_index': original['shell_index'],
                      'original_classification': original['classification'],
                      'original_record_indices': tuple(original['record_indices'])})
        if lo == hi:
            certificate = certify_finite_points(((lo, 0, 0),))
            study['common_rounding_margin_lower'] = certificate['common_margin_lower']
            study['common_precision_certified'] = True
            study['certified_bits'] = certificate['bits']
            study['blocking_obligation'] = None
            additional.append(certificate)
        elif study['common_precision_certified']:
            certificate = certify_axis_zero_region(0, lo, hi)
            study['certified_bits'] = certificate['bits']
            additional.append(certificate)
        groups.append(study)
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0),
                    (10, 0, 0), (1, 0, 0), momentum_profile=FixedPoint(96, 80))
    coverage = check_outgoing_coverage(run, Q(2), (finite, *additional))
    files = ('a_reference/c1b1_rounding_regions.py', 'a_reference/c1b1_axis_decision_bounds.py',
             'a_reference/c1b1_two_atom.py', 'a_numeric/exp.py')
    return {'version': VERSION, 'status': coverage['status'], 'cell_budget_unchanged': 64,
            'diagnosis_sha256': sha256(diagnosis_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            'finite_acceptance': finite, 'analytic_and_singleton_certificates': tuple(additional),
            'groups': tuple(groups), 'outgoing_coverage': coverage,
            'source_sha256': {p: sha256((root/p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in files},
            'global_initial_state_family_completeness': 'not_claimed',
            'frozen_D_valid_modified': False, 'physical_executor_modified': False}


if __name__ == '__main__':
    import sys
    from pathlib import Path
    output = json.dumps(T.serial(example_report()), indent=2)+'\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
