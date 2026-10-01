"""Complete valuation/residue cover, with unresolved parametric CRT retained.

Analysis leaves are not certification regions. Fixed congruence compatibility
does not assert an actual small-gap input for the full variable denominator.
"""
from collections import Counter
from hashlib import sha256
from math import comb, gcd
from pathlib import Path
import json

from a_reference import c1b1_family_checker as K
from a_reference import c1b1_modular_distance_survey as M
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_outer_bootstrap as O

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-full-residue-class-survey-v1'
PRIOR = 'a_reference/fixtures/c1b1_modular_distance_survey_v1.json'
PRIOR_HASH = '3676aa17727aaeae6a2e199628ded4cb087c37b5bb86bfc2cf410f843ef62ace'
POLICY = {'max_v2_unit_digits': 8, 'max_v5_unit_digits': 4,
          'max_leaves_per_domain': 10000,
          'method': 'all valuations; all units mod 10; refine only normalized zero residues'}


def _v(n, prime):
    if not n:
        return None
    return (abs(n) & -abs(n)).bit_length()-1 if prime == 2 else M.valuation(n, prime)


def _at(poly, n, modulus=None):
    value = 0
    for k in range(max(poly, default=0), -1, -1):
        value = value*n+poly.get(k, 0)
        if modulus is not None:
            value %= modulus
    return value


def _count(lo, hi, residue, modulus):
    first = lo+(residue-lo) % modulus
    return first, 0 if first > hi else (hi-first)//modulus+1


def _info(poly, coefficient_orders, prime, n_order, scale, residue, modulus):
    orders = {k: v+k*n_order for k, v in coefficient_orders.items()}
    minimum = min(orders.values())
    if list(orders.values()).count(minimum) == 1:
        return minimum, True
    digits = _v(modulus, prime)
    probe = prime**digits
    unit_scale = scale//prime**n_order
    reduced = {k: (c//prime**coefficient_orders[k])*pow(prime, orders[k]-minimum, probe)*
               pow(unit_scale, k, probe) % probe for k, c in poly.items()}
    value = _at(reduced, residue, probe)
    return (minimum+_v(value, prime), True) if value else (minimum+digits, False)


def _shift(poly, start, step, singleton=False):
    if singleton:
        return {0: _at(poly, start)}
    result = {}
    for k, c in poly.items():
        for j in range(k+1):
            result[j] = result.get(j, 0)+c*comb(k, j)*start**(k-j)*step**j
    return {k: c for k, c in result.items() if c}


def _divide_integer(poly, divisor):
    if divisor <= 0 or any(c % divisor for c in poly.values()):
        raise O.NotCertified('normalized polynomial is not integer-valued by coefficient proof')
    return {k: c//divisor for k, c in poly.items() if c}


def _multiply(a, b):
    result = {}
    for i, x in a.items():
        for j, y in b.items():
            result[i+j] = result.get(i+j, 0)+x*y
    return {k: c for k, c in result.items() if c}


def _power(poly, exponent):
    result = {0: 1}
    for _ in range(exponent):
        result = _multiply(result, poly)
    return result


def _hash_polynomials(*polys):
    data = tuple(tuple(sorted(poly.items())) for poly in polys)
    return sha256(json.dumps(data, separators=(',', ':')).encode()).hexdigest()


def _delta_orders(p2, q2, p5, q5):
    # Nonzero delta is established separately by the existing tie checker.
    two = min(p2[0]+1, q2[0])
    if p2[1] and q2[1] and p2[0]+1 == q2[0]:
        two += 1  # both normalized terms odd, including the odd multiplier
    return two, min(p5[0], q5[0])


def fixed_crt_cover(p, q, count, common2, common5, delta2, p5, q5, required):
    """All lifts of the class parameter, all odd multipliers, fixed info only.

    For h=2j+1, z=2P'-hQ' modulo W is exactly a coset with step
    gcd(2Q',W). Integer polynomials have period dividing W. No point sample
    is used to replace the period inventory.
    """
    two_modulus = 2**(min(3, max(0, delta2-common2))+1)
    five_modulus = 5 if p5[1] and p5[0] == common5 and q5[0] > common5 else 1
    modulus = two_modulus*five_modulus
    common = 2**common2*5**common5
    classes, covered, smallest, survivor = Counter(), 0, None, None
    for residue in range(modulus):
        if residue >= count:
            break
        multiplicity = (count-1-residue)//modulus+1
        pp, qq = _at(p, residue, modulus), _at(q, residue, modulus)
        step = gcd(2*qq, modulus)
        offset = (2*pp-qq) % step
        # If 0 is in the coset, the nearest NONZERO integer is +/-step.
        distance = step if not offset else min(offset, step-offset)
        lower = common*distance
        smallest = lower if smallest is None else min(smallest, lower)
        classes[(step, offset, distance)] += multiplicity
        covered += multiplicity
        if lower < required and survivor is None:
            signed = step if not offset else offset if offset <= step-offset else offset-step
            target = signed % modulus
            period = modulus//step
            multiplier_j = 0 if period == 1 else ((2*pp-qq-target)//step *
                           pow((2*qq)//step, -1, period)) % period
            if (2*pp-(2*multiplier_j+1)*qq-signed) % modulus:
                raise O.NotCertified('fixed congruence witness inconsistent')
            survivor = {'parameter_residue': residue, 'parameter_modulus': modulus,
                        'signed_gap_compatible_with_fixed_info': common*signed,
                        'odd_multiplier_residue': 2*multiplier_j+1,
                        'actual_full_delta_witness': False,
                        'variable_moduli_checked_by_this_witness': False}
    if covered != count:
        raise O.NotCertified('fixed CRT parameter cover incomplete')
    return {'post_cancellation_moduli': (two_modulus, five_modulus),
            'parameter_period': modulus, 'covered_input_count': covered,
            'cosets': tuple((*key, n) for key, n in sorted(classes.items())),
            'whole_class_delta_lower_from_fixed_info': smallest,
            'fixed_info_excludes_small_delta': smallest >= required,
            'surviving_fixed_congruence': survivor}


def survey_domain(group, p, q, d):
    lo, hi = group['domain']['lo'], group['domain']['hi']
    required = group['guard']['required_uniform_M_strict']
    orders = {(name, prime): {k: _v(c, prime) for k, c in poly.items()}
              for name, poly in (('P', p), ('D', d)) for prime in (2, 5)}
    leaves, base_count = [], 0

    def visit(t, s, scale, ul, uh, residue, modulus):
        first, count = _count(ul, uh, residue, modulus)
        if not count:
            return
        info = {(name, prime): _info(poly, orders[name, prime], prime,
                t if prime == 2 else s, scale, residue, modulus)
                for name, poly in (('P', p), ('D', d)) for prime in (2, 5)}
        if count == 1:
            for name, poly in (('P', p), ('D', d)):
                value = _at(poly, scale*first)
                for prime in (2, 5):
                    val = _v(value, prime)
                    if val is not None:
                        info[name, prime] = val, True
        p2, p5, d2, d5 = (info[key] for key in (('P', 2), ('P', 5), ('D', 2), ('D', 5)))
        q2, q5 = (17*t+2*d2[0], d2[1]), (8+17*s+2*d5[0], d5[1])
        delta2, delta5 = _delta_orders(p2, q2, p5, q5)
        cheap_bound = 2**delta2*5**delta5
        # Refining an already sufficient divisibility proof adds no information
        # needed for this survey. Otherwise refine zero probes only.
        if count > 1 and cheap_bound < required:
            for prime, maximum in ((2, POLICY['max_v2_unit_digits']), (5, POLICY['max_v5_unit_digits'])):
                if not all(info[name, prime][1] for name in ('P', 'D')) and _v(modulus, prime) < maximum:
                    for j in range(prime):
                        visit(t, s, scale, ul, uh, residue+j*modulus, modulus*prime)
                    return
        if len(leaves) >= POLICY['max_leaves_per_domain']:
            raise O.NotCertified('analysis leaf work budget exceeded; no coverage promotion')
        common2, common5 = min(p2[0], q2[0]), min(p5[0], q5[0])
        common = 2**common2*5**common5
        # When D's 2/5 valuations are exact, Q/g=F*v with v coprime to 10.
        # For every higher modulus consisting of 2/5 powers, all odd h give
        # exactly the coset z=2P'-F (mod 2F). Every such coset contains a
        # nonzero integer |z|<=2F. This is an analytic exhaustion, not a
        # larger finite-modulus scan and not an actual full-Q gap witness.
        fixed_upper = 2**(q2[0]+1)*5**q5[0]
        full_fixed_test = {
            'raw_nonzero_compatible_gap_upper_orders': (q2[0]+1, q5[0]),
            'all_higher_2_5_moduli_same_coset_proved': d2[1] and d5[1],
            'small_gap_compatible_for_every_parameter_proved': d2[1] and d5[1] and fixed_upper < required,
            'actual_full_delta_witness': False}
        start, step = scale*first, scale*modulus
        normalized_p = _divide_integer(_shift(p, start, step, count == 1), common)
        normalized_q = _divide_integer(_shift(q, start, step, count == 1), common)
        normalized_d = _divide_integer(_shift(d, start, step, count == 1), 2**d2[0]*5**d5[0])
        unit_poly = {0: first} if count == 1 else {0: first, 1: modulus}
        scalar2, scalar5 = 17*t+2*d2[0]-common2, 8+17*s+2*d5[0]-common5
        rebuilt = _multiply(_power(unit_poly, 17), _power(normalized_d, 2))
        if {k: c*2**scalar2*5**scalar5 for k, c in rebuilt.items()} != normalized_q:
            raise O.NotCertified('normalized denominator identity mismatch')
        crt = None
        singleton_delta = None
        if count == 1:
            pn, qn = _at(p, start), _at(q, start)
            singleton_delta = abs(2*pn % (2*qn)-qn)
            lower = singleton_delta
            resolution = 'singleton_full_mod_2Q' if lower >= required else 'actual_small_delta_input'
        elif cheap_bound >= required:
            lower, resolution = cheap_bound, 'valuation_lower_bound'
        else:
            crt = fixed_crt_cover(normalized_p, normalized_q, count,
                                 common2, common5, delta2, p5, q5, required)
            lower = max(cheap_bound, crt['whole_class_delta_lower_from_fixed_info'])
            resolution = 'fixed_crt_lower_bound' if lower >= required else 'parametric_CRT_unresolved'
        leaves.append({'v2_n': t, 'v5_n': s, 'unit_residue': residue, 'unit_modulus': modulus,
            'first_n': start, 'last_n': start+(count-1)*step, 'input_count': count,
            'valuations_P2_P5_D2_D5': (p2, p5, d2, d5),
            'common_25_orders_lower': (common2, common5),
            'common_25_cancellation_exact': all(x[1] for x in (p2, p5, q2, q5)),
            'delta_divisibility_orders_lower': (delta2, delta5),
            'normalized_Q_scalar_orders': (scalar2, scalar5),
            'normalized_polynomial_sha256': _hash_polynomials(normalized_p, normalized_q, normalized_d),
            'normalized_moduli_pairwise_coprime_proved': d2[1] and d5[1],
            'full_CRT_modulus_varies_with_parameter': count > 1,
            'full_fixed_prime_power_test': full_fixed_test,
            'full_variable_modulus_feasibility': 'not_needed_for_proved_lower_bound' if lower >= required
                                                else 'actual_point' if count == 1 else 'unresolved',
            'delta_lower_for_this_whole_class': lower, 'resolution': resolution,
            'fixed_CRT_cover': crt, 'singleton_exact_delta': singleton_delta})

    for t in range(hi.bit_length()):
        s, scale = 0, 2**t
        while scale <= hi:
            ul, uh = (lo+scale-1)//scale, hi//scale
            for residue in (1, 3, 7, 9):
                _, count = _count(ul, uh, residue, 10)
                if count:
                    base_count += 1
                    visit(t, s, scale, ul, uh, residue, 10)
            s, scale = s+1, scale*5
    if sum(x['input_count'] for x in leaves) != hi-lo+1:
        raise O.NotCertified('valuation/unit cover input count mismatch')
    unresolved = [x for x in leaves if x['delta_lower_for_this_whole_class'] < required]
    return {'shell_index': group['shell_index'], 'domain': group['domain'],
            'status': 'survey_only', 'required_M': required, 'required_M_bits': required.bit_length(),
            'base_class_count': base_count, 'analysis_leaf_count': len(leaves), 'classes': tuple(leaves),
            'covered_input_count': sum(x['input_count'] for x in leaves),
            'class_cover_complete': True, 'resolution_counts': dict(Counter(x['resolution'] for x in leaves)),
            'proved_lower_bound_class_count': len(leaves)-len(unresolved),
            'unresolved_class_count': len(unresolved),
            'proved_lower_bound_input_count': sum(x['input_count'] for x in leaves if x['delta_lower_for_this_whole_class'] >= required),
            'unresolved_input_count': sum(x['input_count'] for x in unresolved),
            'unresolved_classes_with_full_fixed_power_obstruction': sum(
                x['full_fixed_prime_power_test']['small_gap_compatible_for_every_parameter_proved'] for x in unresolved),
            'actual_small_delta_inputs': tuple(x['first_n'] for x in leaves if x['resolution'] == 'actual_small_delta_input'),
            'family_lemma_candidate': not unresolved,
            'next_obligation': 'independent_lemma_checker' if not unresolved else 'parametric_variable_modulus_gap_lemma',
            'new_certified_regions': 0, 'global_4_4b': 'NotCertified'}


def example_report():
    K.foundation_guard()
    raw = (ROOT/PRIOR).read_bytes().replace(b'\r\n', b'\n')
    if sha256(raw).hexdigest() != PRIOR_HASH:
        raise O.NotCertified('prior exact-distance survey changed')
    prior = json.loads(raw)
    for name, digest in {**prior['source_sha256']}.items():
        if sha256((ROOT/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != digest:
            raise O.NotCertified('prior survey source changed')
    # Bind both older fixtures and their sources without redoing the point survey.
    inputs = {}
    for name, digest in M.PRIOR_HASHES.items():
        data = (ROOT/name).read_bytes().replace(b'\r\n', b'\n')
        if sha256(data).hexdigest() != digest:
            raise O.NotCertified('prior proof foundation changed')
        inputs[name] = json.loads(data)
        for source, expected in inputs[name]['source_sha256'].items():
            if sha256((ROOT/source).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
                raise O.NotCertified('prior foundation source changed')
    p, q, terms, d = K.frozen_identity()
    if d[0] != 2**318*5**32:
        raise O.NotCertified('gcd(n,D) fixed-factor foundation changed')
    surveyed = []
    old_survey = inputs[next(iter(M.PRIOR_HASHES))]
    for group in prior['groups'][15:19]:
        tie = old_survey['groups'][group['shell_index']]['tie_structure']
        proof = {'classes': tuple({k: x[k] for k in ('v2_n', 'v2_P', 'v2_Q')} for x in tie['classes']),
                 'leaves': tuple({'v2_n': x['v2_n'], 'residue': x['odd_u_residue'], 'modulus': x['modulus'],
                                 'v2_P': x['v2_P'], 'v2_Q': x['v2_Q']} for x in tie['refined_classes']),
                 'exceptions': ()}
        if K.check_tie_cover(proof, p, q, group['domain']['lo'], group['domain']['hi']):
            raise O.NotCertified('unexpected rational tie exceptions in shells 15..18')
        surveyed.append(survey_domain(group, p, q, d))
    return {'version': VERSION, 'status': 'survey_only', 'global_4_4b': 'NotCertified',
            'scope': 'all original inputs in shells 15..18; no additional point sampling',
            'policy': POLICY, 'groups': tuple(surveyed), 'all_class_covers_complete': True,
            'family_lemma_candidate_count': sum(g['family_lemma_candidate'] for g in surveyed),
            'actual_small_delta_input_count': sum(len(g['actual_small_delta_inputs']) for g in surveyed),
            'new_certified_regions': 0, 'coverage_modified': False,
            'prior_coverage': prior['prior_coverage'], 'precision_cap': 16384,
            'identity': 'n=2^a*5^b*u; gcd(u,10)=1; u=r+m*j, j=0..count-1',
            'normalized_denominator': 'Q/g25=2^A*5^B*u^17*D_normalized(j)^2',
            'remaining_gcd_scope': 'g25 is a proved common 2/5 factor; additional common factors are not silently discarded',
            'gcd_structure': {'D0': {'v2': 318, 'v5': 32, 'remaining_cofactor': 1},
                'P0': {'v2': _v(p[0], 2), 'v5': _v(p[0], 5),
                       'remaining_cofactor': abs(p[0])//(2**_v(p[0], 2)*5**_v(p[0], 5))},
                'gcd_n_D_divides_D0': True, 'gcd_n_P_divides_P0': True,
                'remaining_cofactor_is_asserted_prime': False,
                'complete_point_gcd_is_asserted_constant_on_class': False},
            'CRT_scope': 'fixed normalized prime-power periods exhausted; variable u^17,D_normalized^2 retain parametric conditions',
            'small_congruence_survivor_is_actual_counterexample': False,
            'prior_fixture_sha256': {PRIOR: PRIOR_HASH},
            'source_sha256': {'a_reference/c1b1_residue_class_survey.py':
                             sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()}}


def packed_report(report):
    """Lossless columnar JSON; store small multipliers instead of repeated g25."""
    result = {k: v for k, v in report.items() if k != 'groups'}
    result['class_row_fields'] = tuple(k for k in report['groups'][0]['classes'][0]
                                       if k != 'delta_lower_for_this_whole_class')
    result['fixed_CRT_row_fields'] = ('post_cancellation_moduli', 'parameter_period', 'covered_input_count',
        'cosets', 'normalized_nonzero_distance_lower', 'fixed_info_excludes_small_delta', 'surviving_fixed_congruence')
    result['fixed_survivor_row_fields'] = ('parameter_residue', 'parameter_modulus',
        'small_signed_gap_common_multiplier', 'odd_multiplier_residue', 'actual_full_delta_witness',
        'variable_moduli_checked_by_this_witness')
    result['full_fixed_prime_power_fields'] = ('raw_nonzero_compatible_gap_upper_orders',
        'all_higher_2_5_moduli_same_coset_proved', 'small_gap_compatible_for_every_parameter_proved',
        'actual_full_delta_witness')
    result['packing_rules'] = 'g=2^c2*5^c5; fixed gap=g*normalized gap; leaf lower=max(2^d2*5^d5,fixed gap), or singleton exact delta'
    groups = []
    for group in report['groups']:
        rows = []
        for row in group['classes']:
            compact = dict(row)
            compact['full_fixed_prime_power_test'] = tuple(row['full_fixed_prime_power_test'][k]
                for k in result['full_fixed_prime_power_fields'])
            common = 2**row['common_25_orders_lower'][0]*5**row['common_25_orders_lower'][1]
            if row['fixed_CRT_cover'] is not None:
                crt = dict(row['fixed_CRT_cover'])
                crt['normalized_nonzero_distance_lower'] = crt.pop('whole_class_delta_lower_from_fixed_info')//common
                if crt['surviving_fixed_congruence'] is not None:
                    witness = dict(crt['surviving_fixed_congruence'])
                    witness['small_signed_gap_common_multiplier'] = witness.pop('signed_gap_compatible_with_fixed_info')//common
                    crt['surviving_fixed_congruence'] = tuple(witness[k] for k in result['fixed_survivor_row_fields'])
                compact['fixed_CRT_cover'] = tuple(crt[k] for k in result['fixed_CRT_row_fields'])
            rows.append(tuple(compact[k] for k in result['class_row_fields']))
        groups.append({**{k: v for k, v in group.items() if k != 'classes'}, 'class_rows': tuple(rows)})
    result['groups'] = tuple(groups)
    return T.serial(result)


def unpacked_report(packed):
    """Restore exact integers and names for inspection; this grants no authority."""
    metadata = ('class_row_fields', 'fixed_CRT_row_fields', 'fixed_survivor_row_fields',
                'full_fixed_prime_power_fields', 'packing_rules', 'groups')
    result = {k: v for k, v in packed.items() if k not in metadata}
    groups = []
    for group in packed['groups']:
        leaves = []
        for values in group['class_rows']:
            if len(values) != len(packed['class_row_fields']):
                raise ValueError('packed row length mismatch')
            row = dict(zip(packed['class_row_fields'], values))
            row['full_fixed_prime_power_test'] = dict(zip(packed['full_fixed_prime_power_fields'],
                                                          row['full_fixed_prime_power_test']))
            common = 2**row['common_25_orders_lower'][0]*5**row['common_25_orders_lower'][1]
            lower = 2**row['delta_divisibility_orders_lower'][0]*5**row['delta_divisibility_orders_lower'][1]
            if row['fixed_CRT_cover'] is not None:
                crt = dict(zip(packed['fixed_CRT_row_fields'], row['fixed_CRT_cover']))
                crt['whole_class_delta_lower_from_fixed_info'] = common*crt.pop('normalized_nonzero_distance_lower')
                if crt['surviving_fixed_congruence'] is not None:
                    witness = dict(zip(packed['fixed_survivor_row_fields'], crt['surviving_fixed_congruence']))
                    witness['signed_gap_compatible_with_fixed_info'] = common*witness.pop('small_signed_gap_common_multiplier')
                    crt['surviving_fixed_congruence'] = witness
                row['fixed_CRT_cover'] = crt
                lower = max(lower, crt['whole_class_delta_lower_from_fixed_info'])
            row['delta_lower_for_this_whole_class'] = row['singleton_exact_delta'] if row['singleton_exact_delta'] is not None else lower
            leaves.append(row)
        groups.append({**{k: v for k, v in group.items() if k != 'class_rows'}, 'classes': leaves})
    result['groups'] = groups
    return result


if __name__ == '__main__':
    import sys
    output = json.dumps(packed_report(example_report()), separators=(',', ':'))+'\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
