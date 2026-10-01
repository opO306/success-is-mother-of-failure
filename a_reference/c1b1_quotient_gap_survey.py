"""Normalized class gaps, with variable-divisor and odd quotient constraints.

Survey only. Interval overlap is an unresolved relaxation, never an existence
claim. Full small-class enumeration is distinguished from class-wide bounds.
"""
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
from math import comb, gcd
from pathlib import Path
import json

from a_reference import c1b1_residue_class_survey as V
from a_reference import c1b1_modular_distance_survey as M
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_source_binding as SA

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-normalized-quotient-gap-survey-v1'
PRIOR = 'a_reference/fixtures/c1b1_residue_class_survey_v1.json'
PRIOR_HASH = 'f209b3d32fffb2e2807f22b7099fbfcf55cc2499836437328e6b35c855368c3d'
POLICY = {'full_enumeration_max_inputs': 8, 'parameter_subdivisions': 1,
          'shell_order': (18, 17, 16, 15), 'max_classes': 15000}


def _require(condition, reason):
    if not condition:
        raise O.NotCertified(reason)


def ceil_div(a, b):
    if type(a) is not int or type(b) is not int or a <= 0 or b <= 0:
        raise ValueError('positive integer threshold and common factor required')
    return (a+b-1)//b


def _ceil(x):
    return -((-x.numerator)//x.denominator)


def _floor(x):
    return x.numerator//x.denominator


def _add(*polys):
    out = {}
    for poly in polys:
        for k, c in poly.items():
            out[k] = out.get(k, 0)+c
    return {k: c for k, c in out.items() if c}


def _scale(poly, c):
    return {k: c*v for k, v in poly.items() if c*v}


def validate_identity(p, q, divisor, cofactor, c, a, remainder):
    _require(type(c) is int and c > 0, 'positive identity multiplier required')
    _require(V._multiply(divisor, cofactor) == q, 'variable denominator factor identity mismatch')
    _require(_add(V._multiply(a, divisor), remainder) == _scale(p, 2*c),
             'cleared remainder identity mismatch')


def bernstein(poly, end, degree):
    """Exact Bernstein controls on j in [0,end], with degree elevation."""
    _require(type(end) is int and end >= 0 and max(poly, default=0) <= degree,
             'invalid polynomial range domain')
    power = {k: c*end**k for k, c in poly.items()}
    return tuple(sum((F(power.get(k, 0)*comb(i, k), comb(degree, k))
                      for k in range(i+1)), F(0)) for i in range(degree+1))


def ratio_range(numerator, denominator, end):
    """Positive denominator controls give a convex weighted ratio enclosure.

    Failure to establish positivity returns None; no sign is guessed.
    """
    degree = max(max(numerator, default=0), max(denominator, default=0))
    nn, dd = bernstein(numerator, end, degree), bernstein(denominator, end, degree)
    if min(dd) <= 0:
        return None
    values = tuple(n/d for n, d in zip(nn, dd))
    return min(values), max(values)


def quotient_lattice(a, c, cofactor):
    """For odd h: k=A-c*h*B is in the same proved coset at every j.

    This is a relaxation of the exact same-j condition, not equivalence.
    No modular inverse of c is taken.
    """
    center = _add(a, _scale(cofactor, -c))
    modulus = 0
    for value in (*_scale(cofactor, 2*c).values(),
                  *(v for k, v in center.items() if k)):
        modulus = gcd(modulus, abs(value))
    _require(modulus > 0, 'nonzero coefficient lattice modulus required')
    return center.get(0, 0) % modulus, modulus


def coset_in_interval(lo, hi, residue, modulus):
    _require(type(modulus) is int and modulus > 0, 'positive coset modulus required')
    first = lo+(residue-lo) % modulus
    count = 0 if first > hi else (hi-first)//modulus+1
    return {'first': first if count else None, 'count': count}


def range_exclusion(p, q, divisor, cofactor, c, a, remainder, count, required):
    """Exclude integer |z|<required using necessary h and k conditions.

    c*z=k*divisor+remainder, k=A-c*h*cofactor. If either relaxed
    feasible set is empty, every class input meets the normalized threshold.
    Otherwise the result makes no assertion that an input exists.
    """
    _require(type(count) is int and count > 0 and type(required) is int and required > 0,
             'positive input count and normalized threshold required')
    validate_identity(p, q, divisor, cofactor, c, a, remainder)
    end, radius = count-1, required-1
    hlo = ratio_range(_add(_scale(p, 2), {0: -radius}), q, end)
    hhi = ratio_range(_add(_scale(p, 2), {0: radius}), q, end)
    klo = ratio_range(_add(_scale(remainder, -1), {0: -c*radius}), divisor, end)
    khi = ratio_range(_add(_scale(remainder, -1), {0: c*radius}), divisor, end)
    if any(x is None for x in (hlo, hhi, klo, khi)):
        return {'resolution': 'unresolved', 'reason': 'positive_denominator_controls_unproved',
                'normalized_gap_lower': 0, 'actual_small_gap_witness': None}
    h_range = (_ceil(hlo[0]), _floor(hhi[1]))
    k_range = (_ceil(klo[0]), _floor(khi[1]))
    odd = coset_in_interval(*h_range, 1, 2)
    residue, modulus = quotient_lattice(a, c, cofactor)
    allowed = coset_in_interval(*k_range, residue, modulus)
    excluded = odd['count'] == 0 or allowed['count'] == 0
    return {'resolution': 'whole_class_lower_bound' if excluded else 'unresolved',
            'reason': 'odd_quotient_range_empty' if not odd['count'] else
                      'divisor_quotient_coset_empty' if not allowed['count'] else
                      'relaxed_same_input_constraints_overlap',
            'normalized_gap_lower': required if excluded else 0,
            'h_integer_range': h_range, 'odd_h_candidates': odd,
            'k_integer_range': k_range, 'k_coset': {'residue': residue, 'modulus': modulus},
            'k_candidates': allowed, 'h_ratio_enclosure': (hlo[0], hhi[1]),
            'k_ratio_enclosure': (klo[0], khi[1]),
            'actual_small_gap_witness': None,
            'same_j_correlation_retained_in_identity': True,
            'interval_relaxation_can_lose_same_j_correlation': True,
            'multiplier_inverse_assumed': False}


def normalized_identity(p, q, d, raw, row):
    """Transfer raw c*2P=A*D^2+R; never rename D^2 as the full Q."""
    start, count = row['first_n'], row['input_count']
    step = 2**row['v2_n']*5**row['v5_n']*row['unit_modulus']
    g = 2**row['common_25_orders_lower'][0]*5**row['common_25_orders_lower'][1]
    info = row['valuations_P2_P5_D2_D5']
    dh = 2**info[2][0]*5**info[3][0]
    shift = lambda poly: V._shift(poly, start, step, count == 1)
    pp, qq = (V._divide_integer(shift(poly), g) for poly in (p, q))
    dd = V._divide_integer(shift(d), dh)
    _require(V._hash_polynomials(pp, qq, dd) == row['normalized_polynomial_sha256'],
             'normalized class polynomial hash mismatch')
    if count > 1:
        _require(max(pp) == 22 and max(qq) == 29,
                 'linear substitution and constant cancellation changed degrees')
    divisor = V._power(dd, 2)
    unit = {0: start//(2**row['v2_n']*5**row['v5_n'])}
    if count > 1:
        unit[1] = row['unit_modulus']
    x2, x5 = row['normalized_Q_scalar_orders']
    cofactor = _scale(V._power(unit, 17), 2**x2*5**x5)
    c, aa, rr = raw['multiplier']*g, _scale(shift(raw['quotient']), dh*dh), shift(raw['remainder'])
    # Safe scalar reduction of this cleared identity only; g and M/g stay fixed.
    common = c
    for value in (*aa.values(), *rr.values()):
        common = gcd(common, abs(value))
    c, aa, rr = c//common, V._divide_integer(aa, common), V._divide_integer(rr, common)
    validate_identity(pp, qq, divisor, cofactor, c, aa, rr)
    return pp, qq, divisor, cofactor, c, aa, rr, g


def analyze_class(p, q, d, raw, row, required):
    g = 2**row['common_25_orders_lower'][0]*5**row['common_25_orders_lower'][1]
    threshold = ceil_div(required, g)
    base = {'normalized_required_gap': threshold, 'common_25_orders': row['common_25_orders_lower'],
            'input_count': row['input_count'], 'actual_small_gap_witness': None}
    if row['delta_lower_for_this_whole_class'] >= required:
        lower = ceil_div(row['delta_lower_for_this_whole_class'], g)
        return {**base, 'resolution': 'whole_class_lower_bound',
                'reason': 'prior_whole_class_lower_bound', 'normalized_gap_lower': lower}
    pp, qq, divisor, cofactor, c, aa, rr, checked_g = normalized_identity(p, q, d, raw, row)
    _require(g == checked_g, 'normalization factor mismatch')
    if row['input_count'] <= POLICY['full_enumeration_max_inputs']:
        values = []
        for j in range(row['input_count']):
            pn, qn = V._at(pp, j), V._at(qq, j)
            _require(qn > 0, 'nonpositive point denominator')
            signed = (2*pn % (2*qn))-qn
            values.append(abs(signed))
            if abs(signed) < threshold:
                h = (2*pn-signed)//qn
                _require(h % 2 == 1 and 2*pn-h*qn == signed, 'actual odd gap witness mismatch')
                step = 2**row['v2_n']*5**row['v5_n']*row['unit_modulus']
                return {**base, 'resolution': 'actual_small_gap_input', 'reason': 'exact_full_input',
                        'normalized_gap_lower': 0, 'actual_small_gap_witness':
                        {'j': j, 'n': row['first_n']+step*j, 'P_prime': pn, 'Q_prime': qn,
                         'odd_h': h, 'signed_gap': signed, 'normalized_gap': abs(signed),
                         'raw_gap': g*abs(signed), 'raw_required_M': required,
                         'full_impulse_rounding_failure_proved': False,
                         'precision_cap_exceeded_proved': False}}
        return {**base, 'resolution': 'whole_class_lower_bound', 'reason': 'complete_small_class_enumeration',
                'normalized_gap_lower': min(values)}
    result = range_exclusion(pp, qq, divisor, cofactor, c, aa, rr, row['input_count'], threshold)
    return {**base, **result, 'cleared_identity_sha256': V._hash_polynomials({0: c}, aa, rr, divisor, cofactor)}


def example_report(raw_path=None):
    K.foundation_guard()
    data = (ROOT/PRIOR).read_bytes().replace(b'\r\n', b'\n')
    _require(sha256(data).hexdigest() == PRIOR_HASH, 'prior class fixture changed')
    packed = json.loads(data)
    # Follow the complete existing source/fixture chain, without repeating the
    # old survey or promoting its flags to a new certificate.
    def bound_chain(obj):
        for name, digest in obj.get('source_sha256', {}).items():
            actual = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
            _require(SA.source_matches(ROOT/name, digest), 'prior source changed')
        parents = obj.get('prior_fixture_sha256', {})
        if isinstance(parents, str):
            legacy_parents = {
                'c1b1-half-ulp-boundaries-v1': 'a_reference/fixtures/c1b1_rounding_regions_v1.json',
                'c1b1-fractional-phase-survey-v1': 'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json',
                K.VERSION: 'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json'}
            _require(obj['version'] in legacy_parents, 'unknown legacy fixture parent')
            name = legacy_parents[obj['version']]
            parents = {name: parents}
        for name, digest in parents.items():
            actual = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
            _require(sha256(actual).hexdigest() == digest, 'prior foundation fixture changed')
            bound_chain(json.loads(actual))
    bound_chain(packed)
    prior = V.unpacked_report(packed)
    _require(sorted(POLICY['shell_order']) == [15, 16, 17, 18], 'shell inventory incomplete or repeated')
    _require([g['shell_index'] for g in prior['groups']] == [15, 16, 17, 18], 'unexpected prior shell inventory')
    p, q, _, d = K.frozen_identity()
    d_squared = V._power(d, 2)
    raw = M.cleared_remainder(_scale(p, 2), d_squared)
    validate_identity(p, q, d_squared, {17: 5**8}, raw['multiplier'], raw['quotient'], raw['remainder'])
    _require(sum(len(g['classes']) for g in prior['groups']) <= POLICY['max_classes'], 'class work budget exceeded')
    groups = []
    sink = None if raw_path is None else Path(raw_path).open('x', encoding='utf-8', newline='\n')
    try:
        for shell in POLICY['shell_order']:
            original = next(g for g in prior['groups'] if g['shell_index'] == shell)
            counts, rows, examples, witnesses = Counter(), [], {}, []
            raw_hash = sha256()
            for index, row in enumerate(original['classes']):
                result = analyze_class(p, q, d, raw, row, original['required_M'])
                detail = {'shell_index': shell, 'prior_class_index': index, **result}
                line = json.dumps(T.serial(detail), sort_keys=True, separators=(',', ':'))+'\n'
                raw_hash.update(line.encode())
                if sink is not None:
                    sink.write(line)
                counts[result['reason']] += 1
                examples.setdefault(result['reason'], detail)
                if result['actual_small_gap_witness'] is not None:
                    witnesses.append(detail)
                rows.append((index, result['resolution'], result['reason'], result['normalized_required_gap'],
                             result['normalized_gap_lower'], row['input_count'],
                             sha256(line.encode()).hexdigest()))
            unresolved = sum(x[1] == 'unresolved' for x in rows)
            actual = sum(x[1] == 'actual_small_gap_input' for x in rows)
            _require(sum(x[5] for x in rows) == original['covered_input_count'], 'class inventory count mismatch')
            groups.append({'shell_index': shell, 'domain': original['domain'], 'required_raw_M': original['required_M'],
                'raw_M_bits': original['required_M'].bit_length(), 'class_rows': rows, 'reason_counts': dict(counts),
                'normalized_required_gap_bit_range': (min(x[3].bit_length() for x in rows),
                                                       max(x[3].bit_length() for x in rows)),
                'class_count': len(rows), 'covered_input_count': original['covered_input_count'],
                'whole_class_lower_bound_count': len(rows)-unresolved-actual,
                'new_whole_class_lower_bound_count': len(rows)-unresolved-actual-original['proved_lower_bound_class_count'],
                'unresolved_class_count': unresolved, 'actual_small_gap_input_class_count': actual,
                'whole_shell_lemma_candidate': not unresolved and not actual,
                'diagnostic_examples': examples, 'actual_witnesses': witnesses,
                'raw_class_rows_sha256': raw_hash.hexdigest()})
    finally:
        if sink is not None:
            sink.close()
    return {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
        'policy': POLICY, 'groups': groups, 'class_row_fields': ('prior_class_index', 'resolution', 'reason',
            'normalized_required_gap', 'normalized_gap_lower', 'input_count', 'detail_sha256'),
        'target': 'forall integer j in class: abs((2P_prime mod 2Q_prime)-Q_prime)>=ceil(M/g)',
        'divisor_identity': 'c*2P_prime=A*D_normalized^2+R; Q_prime=B*D_normalized^2; c*z=(A-c*h*B)*D_normalized^2+R',
        'quotient_condition': 'h odd; k=A-c*h*B, k congruent A-c*B modulo 2*c*B at the same j',
        'raw_remainder_identity': raw, 'normalized_full_denominator_degrees': (22, 29),
        'raw_M_size_does_not_rank_normalized_class_difficulty': True,
        'interval_overlap_implies_actual_input': False, 'multiplier_inverse_assumed': False,
        'full_impulse_certified_by_rational_gap_alone': False,
        'class_inventory_complete': True, 'new_certified_regions': 0, 'coverage_modified': False,
        'prior_coverage': prior['prior_coverage'], 'precision_cap': 16384,
        'whole_shell_lemma_candidate_count': sum(g['whole_shell_lemma_candidate'] for g in groups),
        'actual_small_gap_input_class_count': sum(g['actual_small_gap_input_class_count'] for g in groups),
        'prior_fixture_sha256': {PRIOR: PRIOR_HASH},
        'source_sha256': {'a_reference/c1b1_quotient_gap_survey.py': sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}}


if __name__ == '__main__':
    import sys
    output = json.dumps(T.serial(example_report(sys.argv[2] if len(sys.argv) == 3 else None)), separators=(',', ':'))+'\n'
    if len(sys.argv) >= 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
