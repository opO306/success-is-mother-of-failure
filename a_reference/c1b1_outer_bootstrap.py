"""Finite-shell induction and analytic tail; never changes A or D_valid.

See docs/current/C1B1_OUTER_BOOTSTRAP_AND_TAIL_V1.md for the derivation and
the distinction between finite FX execution and an analytic asymptote.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as Q
from functools import lru_cache
from math import factorial

from a_numeric import FixedPoint
from a_reference import ar2_lang2024 as L
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_outer_bound as B

VERSION = 'c1b1-outer-bootstrap-tail-v1'
ALPHA = B.H/B.MU
D = B.sqrt_up(Q(3))*B.UX
U = B.sqrt_up(Q(3))*B.UP/2
PROFILE = {'position':'FX(96,48)', 'momentum':'FX(96,80)', 'dt':B.H, 'drift':'v2'}
EXECUTION_SCOPE = {
    'transition_scope':'exact_rounding_map_on_successful_reference_steps',
    'reference_decision_within_precision_cap':'not_proved_for_future_steps',
}


class NotCertified(ValueError):
    """A sufficient proof obligation did not close; not a physics failure."""
    reason = 'outer_bound_not_certified'


def _norm2(v):
    return sum((x*x for x in v), Q(0))


def _dot(a,b):
    return sum((x*y for x,y in zip(a,b)), Q(0))


def _vector(v):
    if len(v) != 3:
        raise ValueError('three exact components required')
    return tuple(map(B.exact,v))


def _sqrt_down(x):
    hi = B.sqrt_up(x)
    return hi if hi*hi == x else hi-Q(1,2**B.BITS)


def radius_squared_increment(q,delta):
    q,delta = _vector(q),_vector(delta)
    return 2*_dot(q,delta)+_norm2(delta)


def residence_steps(width_squared,g_min):
    width_squared,g_min = B.exact(width_squared),B.exact(g_min)
    if width_squared < 0 or g_min <= 0:
        raise NotCertified('positive radial progress is required')
    ratio = width_squared/g_min
    return -(-ratio.numerator//ratio.denominator)


def _model_guard():
    if L.parameter_fingerprint() != B.FINGERPRINT:
        raise NotCertified('frozen model fingerprint mismatch')
    if (L.WORLD_RETARDATION is not True or C.AR40_MASS_ME != 2*B.MU
        or C.SPECIES_MASS.get('Ar40') != 2*B.MU):
        raise NotCertified('live model configuration differs from proved retardation/mass')


def _state(run):
    _model_guard()
    if (type(run.pos) is not FixedPoint or type(run.mom) is not FixedPoint
        or (run.pos.width,run.pos.frac_bits)!=(96,48)
        or (run.mom.width,run.mom.frac_bits)!=(96,80)
        or B.exact(run.dt)!=B.H or run.drift!='v2'
        or len(run.atoms)!=2):
        raise NotCertified('execution profile mismatch')
    for atom in run.atoms:
        if atom.species!='Ar40' or len(atom.r)!=3 or len(atom.p)!=3:
            raise NotCertified('two Ar40 three-component atoms required')
        for prof,values in ((run.pos,atom.r),(run.mom,atom.p)):
            if any(type(v) is not int or not prof.lo<=v<=prof.hi for v in values):
                raise NotCertified('raw state outside execution profile')
    q = C.relative(run.pos,*run.atoms)
    pi,pj = (C.exact(run.mom,a.p) for a in run.atoms)
    p = tuple((y-x)/2 for x,y in zip(pi,pj))
    snapshot = tuple((a.species,a.r,a.p) for a in run.atoms)
    return q,p,snapshot


def _jump(run,atoms):
    di,dj = (C.exact(run.pos,C.displacement(run.pos,run.mom,a,B.H)) for a in atoms)
    return tuple(y-x for x,y in zip(di,dj)),(di,dj)


@dataclass(frozen=True)
class ForceEnvelope:
    """For all R>=20, |V'(R)| <= sum c_k/R^k, c_k>0, k>1.

    Exact published coefficients; no sampling or finite EXP error floor.
    exp(-lambda R) <= m!/(lambda R)^m follows from its positive series.
    """
    terms: tuple = field(init=False)

    def __post_init__(self):
        _model_guard()
        terms = {}
        def add(k,c):
            if c:
                if k<=1 or c<0:
                    raise NotCertified('nonintegrable or negative envelope term')
                terms[k] = terms.get(k,Q(0))+c
        def exp_term(c,lam,power):
            m = max(0,power+10)
            add(m-power,abs(c)*factorial(m)/lam**m)
        # All numerator/denominator coefficients are positive in the frozen g.
        aa,bb = (Q(1),)+L.RET_A,(Q(1),)+L.RET_B
        if any(x<=0 for x in aa+bb):
            raise NotCertified('retardation polynomial positivity not proved')
        lead = bb[-1]
        for name,(short,(eta,cs,kadd)) in L.COMPONENTS.items():
            for lam,coefs in short.values():
                for power,c in coefs.items():
                    exp_term(lam*c,lam,power)
                    exp_term(power*c,lam,power-1)
            for k,c in cs.items():
                n = 2*k+kadd
                if name=='BO' and k==min(cs):
                    # d(R^-6 A/B): denominator B >= B6 R^6.
                    for j,aj in enumerate(aa):
                        add(13-j,abs(c)*(6+j)*aj/lead)
                        for ell,bl in enumerate(bb[1:],1):
                            add(19-j-ell,abs(c)*aj*ell*bl/lead**2)
                elif not (name=='REL' and k==min(cs)):
                    add(2*k+1,2*k*abs(c))
                # Damping correction, including the special REL cancellation.
                for j in range(n+1):
                    coef = abs(c)*eta**j/factorial(j)
                    power = j-2*k
                    exp_term(eta*coef,eta,power)
                    exp_term(power*coef,eta,power-1)
        object.__setattr__(self,'terms',tuple(sorted(terms.items())))

    def value(self,r):
        r = B.exact(r)
        if r<20:
            raise NotCertified('force envelope requires R >= 20')
        return sum((c/r**k for k,c in self.terms),Q(0))

    def integral(self,r):
        r = B.exact(r)
        if r<20:
            raise NotCertified('tail integral requires R >= 20')
        return sum((c*r**(1-k)/(k-1) for k,c in self.terms),Q(0))


@lru_cache(maxsize=128)
def _covered_shell(a,b):
    # Geometric subdivision avoids a wide interval's dependency explosion.
    cells = []
    left = a
    while left<b:
        right = min(b,left*Q(5,4))
        cells.append(B.Shell.prove(left,right))
        left = right
    return _CoveredShell(a,b,tuple(cells))


@dataclass(frozen=True)
class _CoveredShell:
    a: Q
    b: Q
    cells: tuple

    @property
    def radial(self):
        return tuple(B.Iv(min(s.radial[k].lo for s in self.cells),
                          max(s.radial[k].hi for s in self.cells)) for k in range(4))

    @property
    def force(self):
        return min(max(s.force for s in self.cells),ForceEnvelope().value(self.a))

    @property
    def third_directional(self):
        return max(s.third_directional for s in self.cells)


def _shell_induction(a,b,p0_hi,p0_lo,w0,p_cap,n_cap,width_squared):
    """Scalar induction, also valid for a propagated entry enclosure."""
    c = b+ALPHA*p_cap+D
    if c>=Q(2**48):
        raise NotCertified('relative guard radius exceeds position profile range')
    domain = _covered_shell(a,c)
    k = B.H*domain.force/2+U
    if p0_hi+2*n_cap*k>p_cap:
        raise NotCertified('momentum induction budget did not close')
    p_floor = max(Q(0),p0_lo-2*n_cap*k)
    loss = max(Q(0),2*c*k+D*p_cap-ALPHA*p_floor**2)
    w_floor = w0-n_cap*loss
    half_w_floor = w_floor-c*k
    g_min = 2*ALPHA*half_w_floor-2*c*D
    if g_min<=0:
        raise NotCertified('strict outward radial induction did not close')
    count = residence_steps(width_squared,g_min)
    if count>n_cap:
        raise NotCertified('residence induction budget did not close')
    step = B.step_budget(domain,p_cap)
    totals = {key:{term:count*value for term,value in step[key].items()}
              for key in ('energy_hartree','angular_bohr_momentum')}
    return {**EXECUTION_SCOPE,'a':a,'b':b,'guard_b':c,'p_cap':p_cap,'induction_budget':n_cap,
            'max_steps':count,'g_min':g_min,'w_floor':w_floor,
            'half_w_floor':half_w_floor,'w_loss_per_step':loss,'p_floor':p_floor,
            'half_kick_cap':k,'force_cap':domain.force,
            'guard_cells':tuple((s.a,s.b) for s in domain.cells),
            'step_budget':step,**totals}


def _check_overflow(run,count,half_kick_sum):
    """Absolute component margins for all steps; center-of-mass need not be zero."""
    pos_limit = Q(run.pos.hi,2**48)
    mom_limit = Q(run.mom.hi,2**80)
    safe_tail_steps = []
    for atom in run.atoms:
        for r0,p0 in zip(C.exact(run.pos,atom.r),C.exact(run.mom,atom.p)):
            pc = abs(p0)+2*half_kick_sum
            dx = B.H*pc/C.AR40_MASS_ME+B.UX/2
            used = abs(r0)+count*dx
            if pc>mom_limit or used>pos_limit:
                raise NotCertified('absolute profile overflow margin did not close')
            safe_tail_steps.append((pos_limit-used)//dx)
    return min(safe_tail_steps)


def certify_shell(run,a,b,p_cap,n_cap):
    """Prove exact-map escape to R>=b, conditional on reference step decisions.

    Explicit caller search budgets p_cap/n_cap are NOT premises: the induction,
    residence closure, guard shell, cache and overflow conditions are checked.
    Insufficient budgets yield NotCertified, never guessed acceptance. Future
    rounding decisions within C.MAX_PRECISION_BITS are not certified here.
    """
    a,b,p_cap = map(B.exact,(a,b,p_cap))
    if type(n_cap) is not int or n_cap<=0:
        raise TypeError('positive integer induction budget required')
    q,p,snapshot = _state(run)
    r2 = _norm2(q)
    if not (20<=a<b and a*a<=r2<b*b and p_cap>0):
        raise NotCertified('initial state must be in a finite outer shell [a,b)')
    try:
        j = C.impulse(q,B.H/2,run.mom)
        if run.J_cache is not None and run.J_cache!=j:
            raise NotCertified('initial impulse cache mismatch')
        jump,_ = _jump(run,C._kick(run.mom,run.atoms,j))
    except C.ReferenceUndecided as error:
        raise NotCertified('initial impulse precision refused') from error
    except C.ExecutorLimitExceeded as error:
        raise NotCertified(f'initial executor limit exceeded: {error}') from error
    if radius_squared_increment(q,jump)<=0:
        raise NotCertified('initial stored drift does not increase R squared')
    p0_hi,p0_lo = B.sqrt_up(_norm2(p)),_sqrt_down(_norm2(p))
    w0 = _dot(q,p)
    record = _shell_induction(a,b,p0_hi,p0_lo,w0,p_cap,n_cap,b*b-r2)
    _check_overflow(run,n_cap,n_cap*record['half_kick_cap'])
    return {'version':VERSION,'evidence':'analytic_finite_shell_induction',
            'scope':'outgoing_shell_handoff_R_ge_b','profile':dict(PROFILE),
            'initial_state':snapshot,'model_fingerprint':B.FINGERPRINT,
            'angular_scope':'finite_shell_only',
            'attainability':'not_proved',**record}


def zero_impulse_radius():
    """First radius 20*2^j satisfying the strict global norm bound h F < u_p."""
    env = ForceEnvelope()
    radius = Q(20)
    while B.H*env.value(radius)>=B.UP:
        radius *= 2
        if radius>=2**47:
            raise NotCertified('zero-impulse radius outside finite position profile')
    return radius


def _remaining_position_steps(run,displacements):
    limits = []
    for atom,delta in zip(run.atoms,displacements):
        for raw,dx in zip(atom.r,delta):
            r0 = Q(raw,2**48)
            if dx>0:
                limits.append((Q(run.pos.hi,2**48)-r0)//dx)
            elif dx<0:
                limits.append((r0-Q(run.pos.lo,2**48))//(-dx))
    if not limits or min(limits)<1:
        raise NotCertified('tail position overflow or stored drift stall')
    return min(limits)


def certify_tail(run):
    """Executor zero-kick tail + continuous tail from the SAME entry state.

    Does not assert an infinite finite-width execution, global trajectory
    shadowing, a total scattering-angle bound, or an infinite uniform L bound.
    """
    q,p,snapshot = _state(run)
    r2 = _norm2(q)
    radius = zero_impulse_radius()
    if r2<radius*radius:
        raise NotCertified('entry before the proved zero-impulse radius')
    if run.J_cache is not None and run.J_cache!=(0,0,0):
        raise NotCertified('nonzero or malformed cache in zero-impulse tail')
    jump,atom_jumps = _jump(run,run.atoms)
    if _dot(q,jump)<0 or _norm2(jump)==0:
        raise NotCertified('tail stored drift is not outward')
    g_min = radius_squared_increment(q,jump)
    r_hi,r_lo = B.sqrt_up(r2),_sqrt_down(r2)
    p_hi,p_lo = B.sqrt_up(_norm2(p)),_sqrt_down(_norm2(p))
    if r_lo-ALPHA*p_hi<L.R_MIN_BOHR:
        raise NotCertified('unrounded drift domain guard did not close')
    overflow_steps = _remaining_position_steps(run,atom_jumps)
    env = ForceEnvelope()
    integral = env.integral(r_lo)
    radial_speed = _dot(q,p)/(B.MU*r_hi)
    # R_ddot >= -F/mu; v(R)^2 >= v0^2-2 integral(F)/mu.
    margin = Q(3,4)*radial_speed**2-2*integral/B.MU
    if radial_speed<=0 or margin<=0:
        raise NotCertified('continuous radial escape margin did not close')
    v_floor = radial_speed/2
    impulse = integral/v_floor
    if impulse>=p_lo:
        raise NotCertified('continuous momentum direction margin did not close')
    force = env.value(r_lo)
    if B.H*force>=B.UP:
        raise NotCertified('strict zero-impulse inequality did not close')
    return {**EXECUTION_SCOPE,'version':VERSION,'evidence':'analytic_zero_kick_and_continuous_tail',
            'scope':'tail_from_same_actual_entry_state','profile':dict(PROFILE),
            'initial_state':snapshot,'model_fingerprint':B.FINGERPRINT,
            'R_J':radius,'entry_radius_lower':r_lo,'g_min':g_min,
            'force_envelope_terms':env.terms,'force_cap':force,
            'strict_impulse_margin':B.UP-B.H*force,
            'executor_remaining_impulse':Q(0),
            'executor_energy_tail_hartree':integral,
            'executor_modified_energy_tail_hartree':integral+B.H**2*force**2/(8*B.MU),
            'continuous_energy_change':Q(0),'continuous_tail_impulse':impulse,
            'continuous_radial_speed_floor':v_floor,'continuous_escape_margin':margin,
            'direction_error_radians':impulse/(p_lo-impulse),
            'angular_scope':'infinite_uniform_bound_not_claimed',
            'finite_FX_steps_before_position_overflow':overflow_steps,
            'asymptote_scope':'mathematical_continuation_not_infinite_FX_execution',
            'comparison_scope':'continuous_flow_restarted_at_same_entry_not_global_shadowing'}


def certify_outgoing_outer(run,p_cap):
    """Compose finite-shell summaries up to R_J and their analytic tail."""
    from a_reference.c1b1_outer_chain import certify_outgoing_outer as compose
    return compose(run,p_cap)
