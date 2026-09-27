"""Diagnose an incomplete cover; never promote it to a certificate.

Different exact point outputs disprove a UNIFORM output cell. They do not
disprove pointwise rounding completeness, nor prove actual reachability.
The point enclosures share the reference evaluator; this is not an independent
proof of the PES implementation. No trajectory, D_valid or empirical fit.
"""
from collections import Counter
from fractions import Fraction as Q
from math import isqrt

from a_numeric import FixedPoint
from a_reference import c1b1_outer_bound as B
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_reachable_geometry as G
from a_reference import c1b1_rounding_completeness as D
from a_reference import c1b1_two_atom as C

VERSION = 'c1b1-rounding-diagnosis-v1'


def _axis_intervals(box, shell, constraint):
    """Exact intersection for coordinate-axis 1D projections only.

    Radial and dot constraints are closed. All inactive q and P0 components
    are zero, so the cross product is exactly zero. Oblique planes unsupported.
    """
    inactive = constraint['exact_zero_relative_axes']
    active = tuple(k for k in range(3) if k not in inactive)
    if len(active) != 1 or any(box[k] != (0, 0) for k in inactive):
        raise O.NotCertified('diagnosis requires a coordinate-axis 1D projection')
    axis = active[0]
    p = constraint['initial_relative_momentum']
    if any(p[k] for k in inactive):
        raise O.NotCertified('inactive initial momentum must be zero')
    if constraint['cross_initial_momentum_norm_cap'] < 0:
        raise O.NotCertified('negative cross cap')
    minimum = G._ceil(shell['a']/B.UX)
    maximum = G._floor(shell['guard_b']/B.UX)
    lo, hi = box[axis]
    if p[axis] > 0:
        lo = max(lo, G._ceil(constraint['dot_initial_momentum_lower']/(p[axis]*B.UX)))
    elif p[axis] < 0:
        hi = min(hi, G._floor(constraint['dot_initial_momentum_lower']/(p[axis]*B.UX)))
    elif constraint['dot_initial_momentum_lower'] > 0:
        return axis, ()
    intervals = []
    for a, b in ((-maximum, -minimum), (minimum, maximum)):
        left, right = max(lo, a), min(hi, b)
        if left <= right:
            intervals.append((left, right))
    return axis, tuple(intervals)


def _box_at(axis, interval):
    box = [(0, 0)]*3
    box[axis] = interval
    return tuple(box)


def _q_at(axis, raw):
    q = [Q(0)]*3
    q[axis] = raw*B.UX
    return tuple(q)


def _point_witness(axis, raw):
    point = D.certify_impulse_point(_q_at(axis, raw))
    profile = FixedPoint(96, 80)
    components = []
    for component in point['components']:
        lo, hi = component['impulse_interval']
        value = component['raw']
        if profile.from_exact(lo) != value or profile.from_exact(hi) != value:
            raise O.NotCertified('point witness endpoints do not support its raw output')
        components.append({**component,
                           'lower_half_ulp_margin': lo-(Q(value)-Q(1, 2))*B.UP,
                           'upper_half_ulp_margin': (Q(value)+Q(1, 2))*B.UP-hi})
    return {**point, 'relative_raw_axis': raw, 'components': tuple(components)}


def _enclosure(box, shell, bits):
    """The actual cell obligation at a stated precision, without subdivision."""
    low, high = D._grid_radius_bounds(box, shell['a'], shell['guard_b'])
    if low > high:
        return {'kind': 'empty_radial_intersection', 'bits': bits}
    lower, upper = low*(1 << (2*bits)), high*(1 << (2*bits))
    rlo = isqrt(lower.numerator//lower.denominator)
    rhi = isqrt(upper.numerator//upper.denominator)
    if Q(rhi*rhi) < upper:
        rhi += 1
    _, derivative, inverse = C._model_R((rlo, rhi), bits, True, exp_neg=D.execution_exp_cover)
    ratio = C._mul(C._neg(derivative), inverse, bits)
    profile = FixedPoint(96, 80)
    components = []
    for axis, (left, right) in enumerate(box):
        values = [Q(v, 1 << bits)*q*B.UX*B.H/2
                  for v in ratio for q in (left, right)]
        lo, hi = min(values), max(values)
        try:
            raw_lo, raw_hi = profile.from_exact(lo), profile.from_exact(hi)
            blocked = raw_lo != raw_hi
            halt = None
        except C.VMHalt as error:
            raw_lo = raw_hi = None
            blocked = True
            halt = error.reason
        components.append({'axis': axis, 'impulse_interval': (lo, hi),
                           'width_in_momentum_ulps': (hi-lo)/B.UP,
                           'rounded_lower': raw_lo, 'rounded_upper': raw_hi,
                           'uniform_output_condition_blocked': blocked,
                           'endpoint_halt': halt})
    return {'bits': bits, 'radius_squared_interval': (low, high),
            'ratio_interval': ratio, 'components': tuple(components),
            'blocked_axes': tuple(c['axis'] for c in components
                                  if c['uniform_output_condition_blocked'])}


def diagnose_cell(box, shell, constraint):
    """Separate proven output variation from unresolved parent overenclosure."""
    try:
        axis, intervals = _axis_intervals(box, shell, constraint)
    except O.NotCertified as error:
        return {'classification': 'unsupported_projection', 'reason': str(error)}
    if not intervals:
        return {'classification': 'empty_projection_intersection', 'axis': axis, 'parts': ()}
    parts = []
    for interval in intervals:
        left, right = interval
        try:
            endpoints = tuple(_point_witness(axis, raw) for raw in dict.fromkeys(interval))
        except O.NotCertified as error:
            parts.append({'raw_interval': interval, 'classification': 'point_precision_not_separated',
                          'reason': str(error)})
            continue
        bits = max(C.START_PRECISION_BITS, *(w['max_decision_bits'] for w in endpoints))
        parent = _enclosure(_box_at(axis, interval), shell, bits)
        outputs = tuple(w['rounded_impulse'] for w in endpoints)
        if len(set(outputs)) > 1:
            kind = 'proven_nonuniform_output'
        elif not parent['blocked_axes']:
            kind = 'uniform_cell_at_diagnostic_precision'
        else:
            kind = 'parent_enclosure_not_separated'
        parts.append({'raw_interval': interval, 'classification': kind,
                      'endpoint_witnesses': endpoints, 'cell_obligation': parent,
                      'interior_pointwise_completeness': 'not_proved'})
    kinds = tuple(p['classification'] for p in parts)
    return {'axis': axis, 'classification': kinds[0] if len(set(kinds)) == 1 else 'mixed_parts',
            'parts': tuple(parts), 'actual_trajectory_membership': 'not_proved'}


def uniform_cover_lower_bound(witnesses, box, shell, constraint):
    """Pigeonhole bound: each uniform leaf can contain at most one output.

    Validate membership and the signed rounding endpoints, not just a count
    supplied by a caller. Mathematical force enclosure validity still depends
    on the existing point evaluator, and this is only an enclosure-cover bound.
    """
    axis, intervals = _axis_intervals(box, shell, constraint)
    profile = FixedPoint(96, 80)
    outputs = set()
    points = set()
    for witness in witnesses:
        q = witness['q']
        if len(q) != 3 or any(q[k] for k in range(3) if k != axis):
            raise O.NotCertified('witness outside coordinate axis')
        raw = q[axis]/B.UX
        if raw.denominator != 1 or not any(lo <= raw <= hi for lo, hi in intervals):
            raise O.NotCertified('witness outside induced projection')
        values = []
        if len(witness['components']) != 3:
            raise O.NotCertified('three component witnesses required')
        for component in witness['components']:
            lo, hi = component['impulse_interval']
            if lo > hi or profile.from_exact(lo) != component['raw'] or profile.from_exact(hi) != component['raw']:
                raise O.NotCertified('point enclosure crosses a rounding boundary')
            values.append(component['raw'])
        output = tuple(values)
        if output != witness['rounded_impulse']:
            raise O.NotCertified('point output disagrees with component witnesses')
        outputs.add(output)
        points.add(q)
    return {'scope': 'uniform_output_leaf_cover_of_this_projection_only',
            'distinct_grid_points': len(points), 'distinct_rounded_outputs': len(outputs),
            'minimum_uniform_leaves': len(outputs),
            'actual_trajectory_lower_bound': 'not_claimed',
            'pointwise_rounding_completeness': 'not_proved'}


def _connected_groups(records):
    """Join lattice-adjacent parts with the same cause WITHIN one shell."""
    items = []
    for record in records:
        for part in record['diagnosis'].get('parts', ()):
            items.append((record['shell_index'], part['classification'],
                          part['raw_interval'], record['record_index']))
    groups = []
    for shell, cause, (lo, hi), index in sorted(items):
        if (groups and groups[-1]['shell_index'] == shell
                and groups[-1]['classification'] == cause
                and lo <= groups[-1]['raw_interval'][1]+1):
            group = groups[-1]
            group['raw_interval'] = (group['raw_interval'][0], max(hi, group['raw_interval'][1]))
            group['record_indices'].append(index)
        else:
            groups.append({'shell_index': shell, 'classification': cause,
                           'raw_interval': (lo, hi), 'record_indices': [index]})
    return tuple(groups)


def diagnose_reachable_rounding(run, p_cap, *, max_cells=64):
    """Keep the certification budget fixed; diagnostic probes cannot certify it.

    Up to 65 extra grid witnesses establish a cover-strategy obstruction, not
    extra accepted cells. This limit is fixed and separate from max_cells.
    """
    try:
        cover = D.certify_reachable_rounding(run, p_cap, max_cells=max_cells)
    except O.NotCertified as error:
        if not hasattr(error, 'report'):
            raise
        cover = error.report
    records = []
    for index, unresolved in enumerate(cover['unresolved_cells']):
        shell_index = unresolved['shell_index']
        shell = cover['geometry_certificate']['shells'][shell_index]
        constraint = cover['reachable_projection']['shells'][shell_index]
        box = unresolved.get('box', constraint['root_box'])
        records.append({'record_index': index, **unresolved, 'box': box,
                        'original_check_status': ('not_checked_shell_root' if unresolved['reason'] == 'shell_not_checked'
                            else 'not_checked_pending_cell' if unresolved['reason'] == 'fixed_cell_budget_exhausted'
                            else 'checked_but_unresolved'),
                        'diagnosis': diagnose_cell(box, shell, constraint)})
    obstruction = {'status': 'not_proved', 'witness_budget': 65}
    if cover['unresolved_cells']:
        first = cover['unresolved_cells'][0]['shell_index']
        shell = cover['geometry_certificate']['shells'][first]
        constraint = cover['reachable_projection']['shells'][first]
        box = constraint['root_box']
        try:
            axis, intervals = _axis_intervals(box, shell, constraint)
            if intervals:
                lo, hi = max(intervals, key=lambda pair: pair[1]-pair[0])
                # Even relative raw coordinates also satisfy the necessary
                # parity invariant of the symmetric zero-COM example. No
                # assertion that these grid points occur on its trajectory.
                lo, hi = -(-lo//2)*2, hi//2*2
                if lo <= hi:
                    positions = tuple(dict.fromkeys(lo+2*(((hi-lo)//2)*k//64)
                                                   for k in range(65)))
                    witnesses = tuple(_point_witness(axis, raw) for raw in positions)
                    lower = uniform_cover_lower_bound(witnesses, box, shell, constraint)
                    obstruction = {**lower, 'shell_index': first, 'witness_budget': 65,
                                   'witnesses': witnesses, 'cell_budget': max_cells,
                                   'status': ('proved_budget_obstruction'
                                              if lower['minimum_uniform_leaves'] > max_cells
                                              else 'no_budget_obstruction_proved')}
        except O.NotCertified as error:
            obstruction['reason'] = str(error)
    counts = dict(Counter(r['diagnosis']['classification'] for r in records))
    return {'version': VERSION, 'kind': 'analytic_cover_diagnosis_not_a_certificate',
            'status': cover['status'], 'rounding_decision_completeness': cover['rounding_decision_completeness'],
            'cell_budget': max_cells, 'checked_cells': cover['checked_cells'],
            'diagnostic_witness_budget': 65,
            'precision_schedule': (C.START_PRECISION_BITS, C.MAX_PRECISION_BITS),
            'initial_state': cover['geometry_certificate']['initial_state'],
            'original_reason_counts': dict(Counter(r['reason'] for r in records)),
            'classification_counts': counts, 'records': tuple(records),
            'connected_groups': _connected_groups(records),
            'uniform_cover_obstruction': obstruction,
            'cell_diagnosis_may_promote_cover': False,
            'global_initial_state_family_completeness': 'not_claimed',
            'symmetry_quotient': 'not_used_to_skip_inputs',
            'independent_evaluator_proof': 'not_claimed'}


def example_report():
    import hashlib
    from pathlib import Path
    run = C.new_run(FixedPoint(96, 48), 40, (-10, 0, 0), (-1, 0, 0),
                    (10, 0, 0), (1, 0, 0), momentum_profile=FixedPoint(96, 80))
    report = diagnose_reachable_rounding(run, Q(2), max_cells=64)
    root = Path(__file__).resolve().parents[1]
    files = ('a_reference/c1b1_rounding_diagnosis.py', 'a_reference/c1b1_rounding_completeness.py',
             'a_reference/c1b1_reachable_geometry.py', 'a_reference/c1b1_two_atom.py',
             'a_reference/c1b1_outer_bootstrap.py', 'a_reference/c1b1_outer_bound.py',
             'a_reference/c1b1_outer_chain.py', 'a_reference/ar2_lang2024.py',
             'a_numeric/profiles.py', 'a_numeric/exp.py')
    report['source_sha256'] = {f: hashlib.sha256((root/f).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                               for f in files}
    return report


def serial(value):
    if isinstance(value, Q):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(v) for v in value]
    return value


if __name__ == '__main__':
    import json
    import sys
    from pathlib import Path
    output = json.dumps(serial(example_report()), indent=2)+'\n'
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output, encoding='utf-8')
    else:
        print(output)
