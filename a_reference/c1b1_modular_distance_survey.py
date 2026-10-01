"""Bounded, exact arithmetic survey of the 19 open positive-axis domains.

No result from this module is a certificate. Sample extrema and point CRT
bounds never enter coverage. The existing family checker is left unchanged.
"""
from collections import Counter
from fractions import Fraction as Q
from hashlib import sha256
from math import gcd, lcm
from pathlib import Path
import json

from a_reference import c1b1_fractional_phase_survey as S
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_source_binding as SA

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-exact-modular-distance-survey-v1'
PRIOR_HASHES = {
    'a_reference/fixtures/c1b1_fractional_phase_survey_v1.json': 'fb670f1d0b7c5245442e323aaa9b76e05f658b149ae3f2a304e4422d37e38d41',
    'a_reference/fixtures/c1b1_family_certificates_v1.json': '1336591ec474670e1ab6a70056d4b3454191db1fd3613e2f229d7466a5a1a1d6',
}
# Chosen before the survey: endpoints, stratified points, local neighbours,
# and valuation anchors. This is descriptive sampling, not random inference.
POLICY = {'uniform_subdivisions': 64, 'consecutive_radius': 8,
          'two_power_max': 60, 'five_power_max': 27,
          'max_points_per_domain': 205, 'error_diagnostic_bits': 4096}


def _digest(data):
    return sha256(json.dumps(T.serial(data), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _at(poly, n):
    result = 0
    for k in range(max(poly, default=0), -1, -1):
        result = result*n+poly.get(k, 0)
    return result


def valuation(n, prime):
    """Exact integer valuation, with no finite-modulus truncation."""
    if n == 0:
        return None
    n, count = abs(n), 0
    while n % prime == 0:
        n //= prime
        count += 1
    return count


def nearest_half(p, q):
    if type(p) is not int or type(q) is not int or q <= 0:
        raise ValueError('integer numerator and positive integer denominator required')
    residue = 2*p % (2*q)
    signed = residue-q
    k = (2*p-signed-q)//(2*q)
    delta, common = abs(signed), gcd(p, q)
    return {'P': p, 'Q': q, 'nearest_k': k, 'signed_delta': signed, 'delta': delta,
            'distance_ulps': Q(delta, 2*q), 'point_gcd': common,
            'reduced_delta': delta//common, 'reduced_Q': q//common,
            'exact_tie': delta == 0,
            'v2_P': valuation(p, 2), 'v2_Q': valuation(q, 2),
            'v2_reduced_P': valuation(p//common, 2),
            'v2_reduced_Q': valuation(q//common, 2),
            'reduced_Q_odd_part': (q//common) >> valuation(q//common, 2)}


def generalized_crt(congruences):
    """Combine compatible residues even when moduli share factors."""
    value, modulus = 0, 1
    for residue, other in congruences:
        if type(other) is not int or other <= 0:
            raise ValueError('positive integer CRT modulus required')
        common = gcd(modulus, other)
        if (residue-value) % common:
            raise ValueError('incompatible CRT residues')
        quotient = other//common
        step = 0 if quotient == 1 else ((residue-value)//common *
                    pow(modulus//common, -1, quotient)) % quotient
        value += modulus*step
        modulus *= quotient
        value %= modulus
    return value, modulus


def sample_points(lo, hi):
    if type(lo) is not int or type(hi) is not int or not 0 < lo <= hi:
        raise ValueError('closed positive integer interval required')
    middle = (lo+hi)//2
    points = {lo+(hi-lo)*j//POLICY['uniform_subdivisions']
              for j in range(POLICY['uniform_subdivisions']+1)}
    for anchor in (lo, middle, hi):
        radius = POLICY['consecutive_radius']
        points.update(n for n in range(anchor-radius, anchor+radius+1) if lo <= n <= hi)
    for base, maximum in ((2, POLICY['two_power_max']), (5, POLICY['five_power_max'])):
        for power in range(maximum+1):
            modulus = base**power
            n = middle-middle % modulus
            if n < lo:
                n += modulus
            if lo <= n <= hi:
                points.add(n)
    if len(points) > POLICY['max_points_per_domain']:
        raise O.NotCertified('survey sampling budget exceeded')
    return tuple(sorted(points))


def residue_counts(lo, hi, modulus):
    """Complete residue multiplicities, without visiting the lattice points."""
    if not 0 < lo <= hi or not 0 < modulus <= 1024:
        raise ValueError('invalid interval or residue inventory budget')
    return tuple((hi-r)//modulus-(lo-1-r)//modulus for r in range(modulus))


def factor_arithmetic(n, p, q, d):
    factors = (5**8, n**17, d*d)
    if factors[0]*factors[1]*factors[2] != q:
        raise ValueError('denominator factorization mismatch')
    residues = tuple(2*p % m for m in factors)
    value, modulus = generalized_crt(zip(residues, factors))
    point_lower = min(value, modulus-value)
    phase = nearest_half(p, q)
    if modulus != lcm(*factors) or phase['delta'] < point_lower:
        raise O.NotCertified('CRT point bound inconsistent')
    odd_n = n >> valuation(n, 2)
    cofactor_n = odd_n//5**valuation(odd_n, 5)
    return {'factor_names': ('5^8', 'n^17', 'D_int(n)^2'),
            'moduli': factors, 'residues_2P': residues,
            'pairwise_gcd': (gcd(factors[0], factors[1]), gcd(factors[0], factors[2]),
                             gcd(factors[1], factors[2])),
            'crt_residue': value, 'crt_modulus': modulus, 'Q_over_lcm': q//modulus,
            'crt_delta_lower': point_lower, 'bound_scope': 'this_input_only',
            'odd_multiple_parity_retained_by_factor_crt': False,
            'mod_n_residue': 2*p % n, 'mod_D_residue': 2*p % d,
            'mod_D_squared_residue': residues[2],
            'n_v2': valuation(n, 2), 'n_v5': valuation(n, 5),
            'n_remaining_cofactor_coprime_to_10': cofactor_n,
            'cofactor_is_asserted_prime': False,
            'D_v2': valuation(d, 2), 'D_v5': valuation(d, 5)}


def cleared_remainder(poly, divisor):
    """c*poly = integer quotient*divisor + integer remainder.

    The multiplier is NOT assumed invertible in any integer modulus.
    """
    remainder, quotient = {k: Q(v) for k, v in poly.items() if v}, {}
    degree = max(divisor)
    while remainder and max(remainder) >= degree:
        shift = max(remainder)-degree
        coefficient = remainder[max(remainder)]/divisor[degree]
        quotient[shift] = quotient.get(shift, Q(0))+coefficient
        for k, value in divisor.items():
            index = k+shift
            remainder[index] = remainder.get(index, Q(0))-coefficient*value
            if not remainder[index]:
                del remainder[index]
    multiplier = lcm(*(v.denominator for v in (*quotient.values(), *remainder.values())))
    return {'multiplier': multiplier,
            'quotient': {k: int(v*multiplier) for k, v in quotient.items()},
            'remainder': {k: int(v*multiplier) for k, v in remainder.items()},
            'unscaled_integer_congruence_claimed': False}


def _minimum(rows, field):
    return min(rows, key=lambda row: (row[field], row['n']))


def survey_domain(group, p, q, terms, dpoly, raw_sink=None):
    domain = group['domain']
    if R.axis_domain(domain['axis'], domain['lo'], domain['hi']) != domain or domain['lo'] <= 0:
        raise O.NotCertified('original positive-axis domain required')
    lo, hi = domain['lo'], domain['hi']
    points = sample_points(lo, hi)
    records, arithmetic = [], []
    raw_hash = sha256()
    for n in points:
        pn, qn, dn = _at(p, n), _at(q, n), _at(dpoly, n)
        row = {'n': n, **nearest_half(pn, qn)}
        factors = factor_arithmetic(n, pn, qn, dn)
        raw = {'shell_index': group['shell_index'], **row, 'arithmetic': factors}
        line = json.dumps(T.serial(raw), sort_keys=True, separators=(',', ':'))+'\n'
        raw_hash.update(line.encode())
        if raw_sink is not None:
            raw_sink.write(line)
        records.append(row)
        arithmetic.append({'n': n, **factors})
    residual = tuple(Q(x) for x in group['residual_signed_range_ulps'])
    error = A.axis_impulse_error(lo*B.UX, hi*B.UX, POLICY['error_diagnostic_bits'])/B.UP
    guard = max(abs(x) for x in residual)+error
    qmax, qmin = _at(q, hi), _at(q, lo)
    required = (2*qmax*guard).numerator//(2*qmax*guard).denominator+1
    witnesses = []
    for n in (lo, (lo+hi)//2, hi):
        interval, _ = S.residual_enclosure(n*B.UX, n*B.UX, terms)
        lower_abs = min(abs(x) for x in interval) if interval[0]*interval[1] > 0 else Q(0)
        witnesses.append({'n': n, 'signed_residual_interval_ulps': interval,
                          'residual_abs_lower_ulps': lower_abs,
                          'residual_exceeds_half_ulp': lower_abs > Q(1, 2)})
    ordered = sorted(records, key=lambda row: (row['distance_ulps'], row['n']))
    distance_bins = Counter(min(15, int(x['distance_ulps']*32)) for x in records)
    # Every original domain includes multiples of five: the fixed 5^8
    # residue-distance has minimum zero, not a positive family separation.
    five_witness = lo+(-lo) % 5
    if five_witness > hi or 2*_at(p, five_witness) % 5**8 != 0:
        raise O.NotCertified('fixed-factor zero residue witness missing')
    counts = residue_counts(lo, hi, 10)
    return {'shell_index': group['shell_index'], 'domain': domain, 'domain_hash': R.domain_hash(domain),
            'status': 'survey_only', 'lattice_point_count': hi-lo+1,
            'sample_count': len(points), 'sample_inputs_sha256': _digest(points),
            'raw_sample_rows_sha256': raw_hash.hexdigest(), 'sample_scope': 'selected_inputs_only',
            'observed_min_delta': _minimum(records, 'delta'),
            'observed_min_reduced_delta': _minimum(records, 'reduced_delta'),
            'observed_min_distance': ordered[0], 'observed_max_delta': max(x['delta'] for x in records),
            'distance_quantiles': tuple({'rank': j, 'sample': ordered[(len(ordered)-1)*j//4]} for j in range(5)),
            'distance_bin_width': Q(1, 32), 'distance_bin_counts': dict(sorted(distance_bins.items())),
            'delta_bit_length_counts': dict(sorted(Counter(x['delta'].bit_length() for x in records).items())),
            'reduced_delta_bit_length_counts': dict(sorted(Counter(x['reduced_delta'].bit_length() for x in records).items())),
            'point_gcd_bit_length_range': (min(x['point_gcd'].bit_length() for x in records),
                                          max(x['point_gcd'].bit_length() for x in records)),
            'v2_after_cancellation_counts': dict(sorted(Counter(str((x['v2_reduced_P'], x['v2_reduced_Q'])) for x in records).items())),
            'observed_min_crt_bound': _minimum(arithmetic, 'crt_delta_lower'),
            'crt_pairwise_coprime_sample_count': sum(x['pairwise_gcd'] == (1, 1, 1) for x in arithmetic),
            'max_Q_over_lcm_sampled': max(x['Q_over_lcm'] for x in arithmetic),
            'crt_sample_points_meeting_uniform_M': sum(x['crt_delta_lower'] >= required for x in arithmetic),
            'crt_meets_uniform_M_on_all_samples': all(x['crt_delta_lower'] >= required for x in arithmetic),
            'guard': {'provenance': 'pinned_signed_residual_and_shared_numeric_error_lemma',
                      'residual_interval_ulps': residual, 'numeric_error_ulps': error,
                      'execution_bits_for_diagnostic': POLICY['error_diagnostic_bits'],
                      'abs_guard_ulps': guard, 'Q_min': qmin, 'Q_max': qmax,
                      'required_uniform_M_strict': required,
                      'required_M_bits': required.bit_length(),
                      'uniform_M_over_2Qmax_strategy_impossible': required > qmin,
                      'exact_sample_counterexample_to_required_M':
                          _minimum(records, 'delta') if _minimum(records, 'delta')['delta'] < required else None},
            'point_residual_witnesses': tuple(witnesses),
            'domain_residue_inventory': {'modulus': 10, 'counts': counts, 'all_residues_present': all(counts),
                                         'all_residues_present_mod_5_power_8': hi-lo+1 >= 5**8},
            'fixed_5_power_8_residue_distance_min': {'value': 0, 'witness_n': five_witness,
                                                    'scope': 'fixed_factor_only_not_full_delta'},
            'research_class': 'shifted_phase_or_tighter_signed_bound_required' if guard >= Q(1, 2)
                              else 'denominator_normalization_or_local_guard_required' if required > qmin
                              else 'stronger_modular_family_bound_required',
            'sample_points_beating_guard': sum(x['distance_ulps'] > guard for x in records),
            'family_delta_lower_bound': None, 'family_phase_lower_bound': None,
            'new_certified_regions': 0, 'global_4_4b': 'NotCertified'}


def example_report(raw_path=None):
    K.foundation_guard()
    fixtures = {}
    for name, expected in PRIOR_HASHES.items():
        data = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
        if sha256(data).hexdigest() != expected:
            raise O.NotCertified('prior survey/certification fixture changed')
        fixtures[name] = json.loads(data)
        for source, digest in fixtures[name]['source_sha256'].items():
            if not SA.source_matches(ROOT/source, digest):
                raise O.NotCertified('prior source binding changed')
    old_survey, family = (fixtures[name] for name in PRIOR_HASHES)
    p, q, terms, _ = S.normal_form()
    independent_p, independent_q, independent_terms, dpoly = K.frozen_identity()
    if (p, q, terms) != (independent_p, independent_q, independent_terms):
        raise O.NotCertified('two exact decompositions disagree')
    groups = [g for g in old_survey['groups'] if not g['spacing_sufficient']]
    if [g['shell_index'] for g in groups] != list(range(19)) or family['remaining_family_count'] != 19:
        raise O.NotCertified('expected all 19 unchanged obligations')
    sink = None if raw_path is None else Path(raw_path).open('x', encoding='utf-8', newline='\n')
    try:
        surveyed = tuple(survey_domain(g, p, q, terms, dpoly, sink) for g in groups)
    finally:
        if sink is not None:
            sink.close()
    d_squared = {}
    for i, ci in dpoly.items():
        for j, cj in dpoly.items():
            d_squared[i+j] = d_squared.get(i+j, 0)+ci*cj
    c2, c5 = valuation(dpoly[0], 2), valuation(dpoly[0], 5)
    return {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
            'sample_policy': POLICY, 'sample_policy_sha256': _digest(POLICY),
            'sample_count': sum(g['sample_count'] for g in surveyed), 'groups': surveyed,
            'delta_identity': 'Delta=abs(2P-(2k+1)Q); d=Delta/(2Q); nearest k from modulus 2Q',
            'denominator_structure': S.denominator_structure(q),
            'factor_structure': {'D0_v2': c2, 'D0_v5': c5,
                'D0_after_2_5_removal': dpoly[0]//(2**c2*5**c5),
                'gcd_n_D_divides_D0': True,
                'reason': 'D(n)-D(0) is an integer polynomial multiple of n',
                'mod_n_identity': '2P(n) mod n = 2P(0) mod n',
                'mod_n_power_17_remainder': {k: 2*v for k, v in p.items() if k < 17},
                'cleared_mod_D': cleared_remainder({k: 2*v for k, v in p.items()}, dpoly),
                'cleared_mod_D_squared': cleared_remainder({k: 2*v for k, v in p.items()}, d_squared),
                'fixed_5_power_8_positive_family_bound': False,
                'point_crt_is_family_proof': False,
                'fixed_modulus_used_for_exact_valuations': False},
            'classification_counts': dict(Counter(g['research_class'] for g in surveyed)),
            'sampled_CRT_candidate_shells': tuple(g['shell_index'] for g in surveyed
                                                 if g['crt_meets_uniform_M_on_all_samples']),
            'new_certified_regions': 0, 'coverage_modified': False,
            'prior_coverage': {'used_regions': family['coverage']['used_regions'],
                               'region_budget': family['coverage']['region_budget'],
                               'gap_count': len(family['coverage']['uncovered_intervals']),
                               'scope': 'pinned_previous_certificate_report'},
            'precision_cap': 16384, 'family_phase_lower_bounds_proved': 0,
            'prior_fixture_sha256': PRIOR_HASHES,
            'source_sha256': {'a_reference/c1b1_modular_distance_survey.py':
                             sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}}


if __name__ == '__main__':
    import sys
    report = example_report(sys.argv[2] if len(sys.argv) == 3 else None)
    output = json.dumps(T.serial(report), indent=2)+'\n'
    if len(sys.argv) >= 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
