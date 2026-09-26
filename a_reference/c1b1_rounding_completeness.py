"""Decision covers for the existing C1-B1 interval evaluator, not D_valid.

Finite step counts alone do not bound distance from half-ulp boundaries.
Tail covers below certify EVERY representable relative geometry, not samples.
"""
from fractions import Fraction as Q
from functools import lru_cache
from dataclasses import replace
from math import isqrt

from a_numeric import FixedPoint

from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_outer_bound as B

VERSION = 'c1b1-rounding-decision-v1'
RELATIVE_RADIUS_CAP = Q(2**49)  # |q_k|<2^48; sqrt(3)*2^48 < 2^49.


def _radius_interval(a,b,bits):
    lo = a*(1<<bits)
    hi = b*(1<<bits)
    return lo.numerator//lo.denominator,-(-hi.numerator//hi.denominator)


def zero_cell(a,b):
    """A whole radial cell covers all directions of the two raw positions.

    Monotone interval operations contain each point's _model enclosure. Scaling
    G=F/R by |q_k|h/2 <= b h/2 thus also bounds the actual _decide endpoints.
    """
    O._model_guard()
    a,b = B.exact(a),B.exact(b)
    if not 20<=a<b<=RELATIVE_RADIUS_CAP:
        raise O.NotCertified('finite positive outer decision cell required')
    _,dv,inv = C._model(a*a,C.START_PRECISION_BITS,True)
    point = C._mul(C._neg(dv),inv,C.START_PRECISION_BITS)
    endpoints = tuple(Q(x,1<<C.START_PRECISION_BITS)*a*B.H/2 for x in point)
    if endpoints[0]>B.UP/2 or endpoints[1]<-B.UP/2:
        raise O.NotCertified('cell contains a nonzero radial impulse; zero cover unavailable')
    bits = C.START_PRECISION_BITS
    while bits<=C.MAX_PRECISION_BITS:
        radius = _radius_interval(a,b,bits)
        arguments = []
        for shorts,eta_iv,_,_,_ in C._const_cache(bits).values():
            arguments.append(C._mul(eta_iv,radius,bits)[0])
            arguments.extend(C._mul(alpha_iv,radius,bits)[0] for alpha_iv,_,_ in shorts)
        exp_lower = Q(min(arguments),1<<bits)
        # Numerical Taylor endpoints need not be monotone across changing
        # range-reduction guards. Certify inclusion only where EVERY point
        # and parent EXP takes the same proven constant [0,1] branch.
        if exp_lower<bits*C.LN2_UPPER:
            bits *= 2
            continue
        _,derivative,inverse = C._model_R(radius,bits,True)
        ratio = C._mul(C._neg(derivative),inverse,bits)
        cap = max(abs(Q(v,1<<bits)) for v in ratio)*b*B.H/2
        if cap<B.UP/2:
            return {'a':a,'b':b,'decision_bits':bits,'ratio_interval':ratio,
                    'all_exp_shortcut':True,'minimum_exp_argument_lower':exp_lower,
                    'impulse_abs_cap':cap,'strict_half_ulp_margin':B.UP/2-cap,
                    'rounded_impulse':(0,0,0)}
        bits *= 2
    raise O.NotCertified('whole-cell zero rounding did not close within precision cap')


@lru_cache(maxsize=4)
def _tail_cover(start_bits,max_bits):
    a = O.zero_impulse_radius()
    cells = []
    while a<RELATIVE_RADIUS_CAP:
        # A narrower cover than the dynamical shells avoids dependency
        # inflation in the evaluator's rational retardation derivative.
        b = min(RELATIVE_RADIUS_CAP,a*Q(9,8))
        cells.append(zero_cell(a,b))
        a = b
    return tuple(cells)


def certify_zero_tail():
    """Uniform success of _decide for all legal FX tail geometries.

    This is a finite-width execution liveness claim, NOT infinite FX positions,
    not continuous tail force=0, and not pre-tail trajectory completeness.
    """
    O._model_guard()
    cells = tuple(dict(c) for c in _tail_cover(C.START_PRECISION_BITS,C.MAX_PRECISION_BITS))
    if max(c['decision_bits'] for c in cells)>C.MAX_PRECISION_BITS:
        raise O.NotCertified('cached tail decision proof exceeds live precision cap')
    return {'version':VERSION,'scope':'all_FX96_48_relative_geometries_in_tail',
            'profile':dict(O.PROFILE),'model_fingerprint':B.FINGERPRINT,
            'R_J':O.zero_impulse_radius(),'relative_radius_cap':RELATIVE_RADIUS_CAP,
            'max_decision_bits':max(c['decision_bits'] for c in cells),
            'precision_schedule':(C.START_PRECISION_BITS,C.MAX_PRECISION_BITS),
            'cells':cells,'all_half_kicks':(0,0,0),
            'finite_pre_tail_completeness':'not_proved',
            'attainability':'not_proved',
            'asymptote_scope':'mathematical_continuation_not_infinite_FX_execution'}


def certify_impulse_point(q):
    """Signed interval witnesses for all three decisions at one grid point."""
    O._model_guard()
    q = O._vector(q)
    limit = Q(2**48)-B.UX
    if any((x/B.UX).denominator!=1 or abs(x)>limit for x in q) or O._norm2(q)<400:
        raise O.NotCertified('represented outer relative position required')
    profile = FixedPoint(96,80)
    components = [None,None,None]
    for k,x in enumerate(q):
        if not x:
            components[k] = {'decision_bits':0,'impulse_interval':(Q(0),Q(0)),'raw':0}
    bits = C.START_PRECISION_BITS
    while bits<=C.MAX_PRECISION_BITS and any(v is None for v in components):
        _,dv,inv = C._model(O._norm2(q),bits,True)
        ratio = C._mul(C._neg(dv),inv,bits)
        for k,x in enumerate(q):
            if components[k] is not None:
                continue
            ends = tuple(Q(v,1<<bits)*x*B.H/2 for v in ratio)
            lo,hi = min(ends),max(ends)
            try:
                left,right = profile.from_exact(lo),profile.from_exact(hi)
            except C.VMHalt:
                # A coarse endpoint outside the range is not proof that the
                # enclosed exact value overflows. Refine, as the executor does.
                continue
            if left==right:
                components[k] = {'decision_bits':bits,'impulse_interval':(lo,hi),'raw':left}
        bits *= 2
    if any(c is None for c in components):
        raise O.NotCertified('point rounding separation not proved within precision cap')
    return {'version':VERSION,'scope':'this_exact_relative_position_only','q':q,
            'components':tuple(components),'rounded_impulse':tuple(c['raw'] for c in components),
            'max_decision_bits':max(c['decision_bits'] for c in components),
            'model_fingerprint':B.FINGERPRINT}


def execution_exp_cover(x,bits):
    """Enclose ALL numerical _exp_neg endpoint results on an input interval.

    Interval-execute the negative Taylor loop including every possible stopping
    iteration and every range-reduction k. No monotonicity of approximate EXP
    endpoints is assumed; exact mathematical enclosures alone are insufficient.
    """
    lo,hi=x
    if not 0<=lo<=hi:
        raise O.NotCertified('nonnegative EXP input enclosure required')
    threshold=bits*C.LN2_UPPER
    if Q(lo,1<<bits)>=threshold:
        return 0,1
    one=1<<bits
    outputs=[]
    if Q(hi,one)>=threshold:
        outputs.append((0,1))
    first=max(0,lo.bit_length()-bits+1)+8
    last=max(0,hi.bit_length()-bits+1)+8
    for k in range(first,last+1):
        # y=-end/2^k. Both floor/ceil endpoints have |y| within these bounds.
        amin=lo>>k
        amax=-(-hi//(1<<k))
        if amax>one//256:
            # A k not applicable to the largest endpoint: intersect its
            # actual bit_length branch before executing Taylor.
            top=(1<<(bits+k-8))-1
            amax=-(-min(hi,top)//(1<<k))
        if amin>amax:
            continue
        tl=th=sl=sh=(one,one)
        ends=[]
        i=0
        while True:
            i+=1
            tl=tuple(v*bound//(i*one) for v,bound in zip(tl,(amin,amax)))
            th=tuple(-(-v*bound//(i*one)) for v,bound in zip(th,(amin,amax)))
            if i&1:
                sl=(sl[0]-th[1],sl[1]-th[0])
                sh=(sh[0]-tl[1],sh[1]-tl[0])
            else:
                sl=(sl[0]+tl[0],sl[1]+tl[1])
                sh=(sh[0]+th[0],sh[1]+th[1])
            if th[0]<=1:
                # At any real stopping branch r=2*t_hi+2 <= 4.
                ends.append((sl[0]-4,sh[1]+4))
            if th[1]<=1:
                break
        low=max(0,min(v[0] for v in ends))
        high=max(v[1] for v in ends)
        for _ in range(k):
            low=(low*low)>>bits
            high=-((-high*high)>>bits)
        outputs.append((low,high))
    return min(v[0] for v in outputs),max(v[1] for v in outputs)


def _grid_radius_bounds(box,a,b):
    if (len(box)!=3 or any(len(pair)!=2 or any(type(x) is not int for x in pair)
            or pair[0]>pair[1] or max(abs(x) for x in pair)>2**96-1 for pair in box)):
        raise O.NotCertified('legal relative raw grid box required')
    low=sum((0 if x<=0<=y else min(x*x,y*y) for x,y in box),0)*B.UX**2
    high=sum((max(x*x,y*y) for x,y in box),0)*B.UX**2
    return max(a*a,low),min(b*b,high)


def certify_grid_cell(box,a,b):
    """A signed FX position cell, intersected with its induced shell guard.

    Empty intersections are discarded by proof, never by a sample. A broad
    cell may request subdivision before spending more precision. Singletons
    use the actual point witness with the complete live precision schedule.
    """
    O._model_guard()
    a,b=B.exact(a),B.exact(b)
    if not 20<=a<=b<=RELATIVE_RADIUS_CAP:
        raise O.NotCertified('induced outer radial guard required')
    box=tuple(tuple(pair) for pair in box)
    low,high=_grid_radius_bounds(box,a,b)
    if low>high:
        return {'box':box,'kind':'empty_radial_intersection'}
    if all(x==y for x,y in box):
        point=certify_impulse_point(tuple(Q(x)*B.UX for x,_ in box))
        return {'box':box,'kind':'singleton','rounded_impulse':point['rounded_impulse'],'point':point}
    profile=FixedPoint(96,80)
    bits=C.START_PRECISION_BITS
    while bits<=C.MAX_PRECISION_BITS:
        l=low*(1<<(2*bits))
        h=high*(1<<(2*bits))
        rlo=isqrt(l.numerator//l.denominator)
        rh=isqrt(h.numerator//h.denominator)
        if Q(rh*rh)<h:
            rh+=1
        _,dv,inv=C._model_R((rlo,rh),bits,True,exp_neg=execution_exp_cover)
        ratio=C._mul(C._neg(dv),inv,bits)
        components=[]
        needs_split=False
        for x,y in box:
            values=[Q(v,1<<bits)*Q(q)*B.UX*B.H/2 for v in ratio for q in (x,y)]
            lo,hi=min(values),max(values)
            try:
                left,right=profile.from_exact(lo),profile.from_exact(hi)
            except C.VMHalt:
                break
            if left!=right:
                # A one-grid-edge box cannot be tightened much spatially;
                # remove evaluator roundoff before splitting it to points.
                needs_split=hi-lo>B.UP and max(y-x for x,y in box)>1
                break
            components.append({'impulse_interval':(lo,hi),'raw':left})
        if len(components)==3:
            return {'box':box,'kind':'uniform_rounding_cell','decision_bits':bits,
                    'components':tuple(components),'rounded_impulse':tuple(c['raw'] for c in components)}
        if needs_split:
            break
        bits*=2
    raise O.NotCertified('grid cell unresolved: rounding boundary or precision cap; subdivide')


def split_grid_cell(box):
    axis=max(range(3),key=lambda k:box[k][1]-box[k][0])
    lo,hi=box[axis]
    if lo==hi:
        raise O.NotCertified('singleton cannot be subdivided')
    mid=(lo+hi)//2
    left,right=list(box),list(box)
    left[axis]=(lo,mid)
    right[axis]=(mid+1,hi)
    return tuple(left),tuple(right)


def certify_reachable_rounding(run,p_cap,*,max_cells=64):
    """Adaptive lattice cover of the existing induction's position projection.

    The scalar induction retains no direction constraint. Its position
    projection is therefore its radial guard, not the initial radial ray.
    P constraints are omitted only because impulse does not depend on P.
    Never replay, enlarge to arbitrary shells, or silently increase budgets.
    """
    if type(max_cells) is not int or max_cells<1:
        raise TypeError('positive fixed cell budget required')
    geometry=O.certify_outgoing_outer(run,p_cap)
    tail=certify_zero_tail()
    results=[]
    checked=0
    unresolved=[]
    for index,shell in enumerate(geometry['shells']):
        a,b=shell['a'],shell['guard_b']
        try:
            proof=zero_cell(a,b)
            results.append({'shell_index':index,'kind':'uniform_zero','proof':proof})
            continue
        except O.NotCertified:
            pass
        bound=min(2**96-1,int(b/B.UX))
        pending=[tuple((-bound,bound) for _ in range(3))]
        leaves=[]
        while pending and checked<max_cells:
            box=pending.pop()
            checked+=1
            try:
                leaves.append(certify_grid_cell(box,a,b))
            except O.NotCertified as error:
                if all(x==y for x,y in box):
                    unresolved.append({'shell_index':index,'box':box,'reason':str(error)})
                    break
                left,right=split_grid_cell(box)
                pending.extend((right,left))
        results.append({'shell_index':index,'kind':'adaptive_grid','leaves':tuple(leaves)})
        if pending or unresolved:
            unresolved.extend({'shell_index':index,'box':box,'reason':'fixed_cell_budget_exhausted'} for box in pending)
            unresolved.extend({'shell_index':k,'reason':'shell_not_checked'}
                              for k in range(index+1,len(geometry['shells'])))
            break
    report={'version':VERSION,'scope':'shell_induction_reachable_enclosure_projection',
            'status':'not_certified' if unresolved else 'certified',
            'rounding_decision_completeness':'not_proved' if unresolved else 'certified_for_induced_enclosure',
            'geometry_certificate':geometry,'tail_decision':tail,'shell_covers':tuple(results),
            'checked_cells':checked,'cell_budget':max_cells,'unresolved_cells':tuple(unresolved),
            'position_projection':'radial_guards_no_angular_constraint_retained_by_induction',
            'global_initial_state_family_completeness':'not_claimed'}
    if unresolved:
        error=O.NotCertified('reachable rounding cover unresolved; no complete certificate')
        error.report=report
        raise error
    return report


def certify_outgoing_decisions(run,p_cap,*,max_steps=64):
    """Combine zero covers or bounded exact replay with the uniform tail.

    No increase of max_steps on failure. Budget exhaustion is INCOMPLETE, not
    success; a checked prefix never certifies an unchecked nonzero remainder.
    Replay is a rounding proof witness, not an empirical error fit to D_valid.
    """
    if type(max_steps) is not int or max_steps<0:
        raise TypeError('nonnegative integer exact-replay budget required')
    geometry = O.certify_outgoing_outer(run,p_cap)
    tail = certify_zero_tail()
    zero_cells = []
    for s in geometry['shells']:
        try:
            zero_cells.append(zero_cell(s['a'],s['guard_b']))
        except O.NotCertified:
            break
    uniform = len(zero_cells)==len(geometry['shells'])
    witnesses,states = [],[]
    steps = 0
    failure = None
    status = 'certified' if uniform else 'incomplete_budget'
    finite = 'certified_uniform_zero_cells' if uniform else 'not_proved'
    if not uniform:
        work = replace(run)
        while True:
            q,_,state = O._state(work)
            if O._norm2(q)>=tail['R_J']**2:
                if work.J_cache is not None and work.J_cache!=(0,0,0):
                    raise O.NotCertified('tail handoff cache contradicts zero proof')
                status,finite = 'certified','certified_all_finite_transition_inputs'
                break
            try:
                witness = certify_impulse_point(q)
            except O.NotCertified as error:
                status = 'not_certified_decision'
                failure = {'kind':'point_separation_not_proved','q':q,'message':str(error)}
                break
            if work.J_cache is not None and work.J_cache!=witness['rounded_impulse']:
                raise O.NotCertified('finite replay cache contradicts point witness')
            witnesses.append(witness)
            states.append(state)
            if steps>=max_steps:
                break
            try:
                C.step(work)
            except C.ReferenceUndecided as error:
                status = 'not_certified_decision'
                failure = {'kind':'reference_undecided','transition_step':steps+1,'message':str(error)}
                break
            steps += 1
    return {'version':VERSION,'scope':'this_initial_state_outgoing_to_R_J_and_FX_tail',
            'initial_state':geometry['initial_state'],'profile':dict(O.PROFILE),
            'model_fingerprint':B.FINGERPRINT,'status':status,
            'geometry_certificate':geometry,'tail_decision':tail,
            'finite_pre_tail_completeness':finite,
            'rounding_decision_completeness':('certified_for_this_initial_state'
                if status=='certified' else 'not_proved'),
            'exact_replay_budget':max_steps,'checked_transition_steps':steps,
            'failure':failure,
            'point_witnesses':tuple(witnesses),'checked_entry_states':tuple(states),
            'zero_finite_cells':tuple(zero_cells),
            'global_initial_state_family_completeness':'not_claimed'}


def example_report():
    """Static proof examples, explicitly including an INCOMPLETE early prefix."""
    import hashlib
    from pathlib import Path
    def run_at(r):
        return C.new_run(FixedPoint(96,48),B.H,(-r/2,0,0),(-1,0,0),(r/2,0,0),(1,0,0),
                         momentum_profile=FixedPoint(96,80))
    def serial(x):
        if isinstance(x,Q):
            return str(x)
        if isinstance(x,dict):
            return {k:serial(v) for k,v in x.items()}
        if isinstance(x,(tuple,list)):
            return [serial(v) for v in x]
        return x
    root=Path(__file__).resolve().parents[1]
    files=('a_reference/c1b1_rounding_completeness.py','a_reference/c1b1_two_atom.py',
           'a_reference/c1b1_outer_bootstrap.py','a_reference/c1b1_outer_chain.py',
           'a_reference/c1b1_outer_bound.py','a_reference/ar2_lang2024.py',
           'a_numeric/profiles.py','a_numeric/exp.py')
    try:
        attempt=certify_reachable_rounding(run_at(Q(20)),Q(2),max_cells=64)
    except O.NotCertified as error:
        attempt=error.report
    attempt={key:attempt[key] for key in ('scope','status','rounding_decision_completeness',
             'checked_cells','cell_budget','unresolved_cells','shell_covers','position_projection')}
    return serial({'version':VERSION,'kind':'analytic_rounding_decision_examples_not_measurements',
                   'uniform_tail':certify_zero_tail(),
                   'late_outgoing':certify_outgoing_decisions(run_at(O.zero_impulse_radius()-Q(1,100)),Q(2),max_steps=0),
                   'early_outgoing_prefix':certify_outgoing_decisions(run_at(Q(20)),Q(2),max_steps=2),
                   'induced_enclosure_attempt':attempt,
                   'source_sha256':{f:hashlib.sha256((root/f).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for f in files}})


if __name__=='__main__':
    import json
    import sys
    from pathlib import Path
    report=example_report()
    if len(sys.argv)==2:
        Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    else:
        print(json.dumps(report,indent=2))
