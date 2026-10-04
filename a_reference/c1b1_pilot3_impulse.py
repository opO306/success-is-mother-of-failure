"""Isolated exact Pilot3 candidates. Runtime selector promotion remains gated.

World pairs are immutable; raw paths require canonical FixedPoint production
state. The original step, slow REF, Candidate B and Combined remain available.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from functools import lru_cache
from math import isqrt
from types import FunctionType
from a_numeric.profiles import _div_round,VMHalt
from . import c1b1_two_atom as C,c1b1_fast_impulse as F,c1b1_combined_arithmetic as K
from . import ar2_lang2024 as L
from .c1b1_impulse_primitives import _mul,_add,_neg,_div_small,_div_pos,_exp_neg


def pair(value):
    return value.numerator,value.denominator


def prepare_world():
    """Normalize declared constant products once, independent of M and Run."""
    return tuple((name,tuple((pair(alpha),tuple((i,pair(c),pair(c*i))
                    for i,c in coefs.items())) for alpha,coefs in short.values()),
                  pair(eta),kadd,tuple((k,pair(Ck[k]),pair(Ck[k]*2*k)) for k in sorted(Ck)))
                 for name,(short,(eta,Ck,kadd)) in L.COMPONENTS.items())


WORLD=prepare_world()
RET_A=tuple((pair(a),pair(a*(i+1))) for i,a in enumerate(L.RET_A))
RET_B=tuple((pair(b),pair(b*(i+1))) for i,b in enumerate(L.RET_B))


def const_pair(c,M):
    n,d=c;n <<= M
    return n//d,-((-n)//d)


def _scale(a,c):
    n,d=c
    if n>=0:return (a[0]*n)//d,-((-(a[1]*n))//d)
    return (a[1]*n)//d,-((-(a[0]*n))//d)


@lru_cache(maxsize=8)
def grid_constants(M):
    return tuple((name,tuple((const_pair(alpha,M),alpha,coefs) for alpha,coefs in shorts),
                  const_pair(eta,M),eta,kadd,longs) for name,shorts,eta,kadd,longs in WORLD)


from .c1b1_impulse_primitives import _inverse_table


@dataclass(frozen=True,slots=True)
class RawRelative:
    raw: tuple
    shift: int
    values: tuple

    def __post_init__(self):
        if (type(self.shift) is not int or self.shift<0 or type(self.raw) is not tuple
                or type(self.values) is not tuple or len(self.raw)!=len(self.values)
                or not all(type(v) is int for v in self.raw)
                or not all(type(v) is Q for v in self.values)):
            raise C.ContractViolation('invalid raw relative packet')
        scale=1<<self.shift
        if any(q.numerator*scale!=v*q.denominator for v,q in zip(self.raw,self.values)):
            raise C.ContractViolation('inconsistent raw relative packet')

    def __iter__(self):return iter(self.values)
    def __getitem__(self,i):return self.values[i]
    def __len__(self):return len(self.values)


def relative_raw(pos,i,j):
    signature=K.canonical_fx(pos)
    if signature is None:raise C.ContractViolation('raw relative needs canonical FixedPoint')
    if not all(pos.valid_raw(v) for a in (i,j) for v in a.r):
        raise C.ContractViolation('invalid stored raw for profile')
    raw=tuple(b-a for a,b in zip(i.r,j.r));shift=signature[1]
    return RawRelative(raw,shift,tuple(Q(v,1<<shift) for v in raw))


def radius_raw(n,shift,M):
    if type(n) is not int or type(shift) is not int or n<0 or shift<0:
        raise C.ContractViolation('invalid raw squared radius')
    e=2*(M-shift)
    if e>=0:q,rem=n<<e,0
    else:q,rem=divmod(n,1<<(-e))
    low=isqrt(q)
    return low,low+int(rem!=0 or low*low!=q)


def exact_dt_pair(dt):
    if type(dt) is Q:return dt.numerator,dt.denominator
    if type(dt) is int:return dt,1
    raise C.ContractViolation('raw impulse needs exact int/Fraction dt')


def component_interval(g,v,shift,dt,M):
    tn,td=exact_dt_pair(dt)
    a,b=g[0]*v*tn,g[1]*v*tn
    return min(a,b),max(a,b),td<<(M+shift)


def round_operands(profile,n,d):
    # Cancel exact powers of two; move no rounding operation.
    take=min(profile.frac_bits,(d & -d).bit_length()-1)
    return n<<(profile.frac_bits-take),d>>take


def decide_raw(profile,value_at):
    if K.canonical_fx(profile) is None:raise C.ContractViolation('raw impulse needs canonical FixedPoint momentum')
    M=C.START_PRECISION_BITS
    while M<=C.MAX_PRECISION_BITS:
        lo,hi,d=value_at(M)
        if d<=0 or lo>hi:raise C.ContractViolation('reversed evaluator enclosure')
        results=[]
        for n in (lo,hi):
            a,b=round_operands(profile,n,d)
            try:results.append(profile._check(_div_round(a,b)))
            except VMHalt as h:
                if h.reason!='overflow':raise
                results.append(C._Halt(h.reason))
        a,b=results
        if a==b:
            if isinstance(a,C._Halt):
                if lo<0<hi:M*=2;continue
                raise VMHalt(a.reason)
            return a
        M*=2
    raise C.ReferenceUndecided(f'not decided within {C.MAX_PRECISION_BITS} bits')


def impulse_raw(dr,dt,profile,*,prepared=False,final_integer=True):
    if type(dr) is not RawRelative:raise C.ContractViolation('raw impulse needs a prepared relative packet')
    n=sum(v*v for v in dr.raw);shift=dr.shift
    if n*C.R_MIN2.denominator < C.R_MIN2.numerator<<(2*shift):
        raise C.PhysicsDomainExceeded(f'R^2 = {float(Q(n,1<<(2*shift))):.6g} < r_min^2')
    if final_integer and K.canonical_fx(profile) is None:
        raise C.ContractViolation('raw impulse needs canonical FixedPoint momentum')
    cache={}
    def G(M):
        if M not in cache:
            radius=radius_raw(n,shift,M)
            dV,inv=(model_prepared if prepared else F._impulse_model_R_fast)(radius,M,L.WORLD_RETARDATION)
            cache[M]=_mul(_neg(dV),inv,M)
        return cache[M]
    out=[]
    for v,x in zip(dr.raw,dr.values):
        if final_integer:
            if v*exact_dt_pair(dt)[0]==0:out.append(profile._check(0));continue
            out.append(decide_raw(profile,lambda M,v=v:component_interval(G(M),v,shift,dt,M)))
        else:
            c=x*dt
            if c==0:out.append(profile.from_exact(0));continue
            def at(M,c=c):
                lo,hi=G(M);a,b=Q(lo,1<<M)*c,Q(hi,1<<M)*c
                return min(a,b),max(a,b)
            out.append(C._decide(profile,at))
    return tuple(out)


def _model_prepared_Q(R2,M,ret):
    return model_prepared(F._radius(R2,M),M,ret)


_fraction_ns=dict(F.impulse.__globals__)
_fraction_ns['_model']=_model_prepared_Q
impulse_A=FunctionType(F.impulse.__code__,_fraction_ns,'impulse_prepared_constants')


VARIANTS=('A','B','BC','BCD','ABCD')


class Runtime(K.CombinedRuntime):
    def __init__(self,run,variant='ABCD'):
        if variant not in VARIANTS:raise ValueError('unknown isolated Pilot3 variant')
        super().__init__(run)
        self.variant=variant
        self.pilot3_enabled=self.raw_drift_enabled
        if not self.pilot3_enabled:return
        from .c1b1_prepared_binding import RunBinding
        self._prepared_binding=RunBinding.build(run,'fast_pilot3:'+variant)
        ns=dict(self.function.__globals__)
        if variant=='A':ns['impulse']=impulse_A
        else:
            ns['relative']=relative_raw
            if variant=='B':ns['impulse']=F.impulse
            else:
                def selected(dr,dt,profile):
                    return impulse_raw(dr,dt,profile,prepared=variant=='ABCD',final_integer=variant in ('BCD','ABCD'))
                ns['impulse']=selected
        self.function=FunctionType(C.step.__code__,ns,'step_pilot3_'+variant)

    def _binding_mode(self):
        return 'fast_pilot3:'+self.variant


def impulse(dr,dt,profile):
    """Explicit raw packet fast path; general callers retain original Candidate B."""
    if type(dr) is RawRelative and K.canonical_fx(profile) is not None:
        from .c1b1_prepared_binding import world_binding
        world_binding()
        return impulse_raw(dr,dt,profile,prepared=True,final_integer=True)
    return F.impulse(dr,dt,profile)


def step(run):return Runtime(run).step()


def model_prepared(R: tuple, M: int, ret: bool, *, exp_neg=None):
    """Impulse-only derivative enclosure, same integer endpoints as slow REF."""
    if not 0 < R[0] <= R[1]:
        raise ValueError("fast impulse requires a positive ordered radius")
    exp_neg = _exp_neg if exp_neg is None else exp_neg
    lo, hi = R
    one = 1 << M
    pw = {0: (one, one), 1: R}
    for i in range(2, 7):
        pw[i] = _mul(pw[i - 1], R, M)
    inv = _inverse_table(lo, hi, M)

    def power(i):
        return pw[i] if i >= 0 else inv[-i]
    dV = (0, 0)
    for name, shorts, eta_iv, eta, kadd, C in grid_constants(M):
        for alpha_iv, alpha, coefs in shorts:
            E = exp_neg(_mul(alpha_iv, R, M), M)
            P = dP = (0, 0)
            for i, c, dc in coefs:
                if c[0] == 0:
                    continue
                P = _add(P, _scale(power(i), c))
                if i:
                    dP = _add(dP, _scale(power(i - 1), dc))
            dV = _add(dV, _mul(E, _add(dP, _neg(_scale(P, alpha))), M))
        x = _mul(eta_iv, R, M)
        E = exp_neg(x, M)
        piece = total = (one, one)
        done = 0
        kmin = C[0][0]
        for k, c, dk in C:
            n = 2 * k + kadd
            for i in range(done + 1, n + 1):
                piece = _div_small(_mul(piece, x, M), i)
                total = _add(total, piece)
            done = n
            T = _mul(E, total, M)
            dD = _scale(_mul(E, piece, M), eta)
            if ret and k == kmin and (name == 'BO'):
                N = Dn = (one, one)
                dN = dDn = (0, 0)
                for m, (a, da) in enumerate(RET_A):
                    N = _add(N, _scale(pw[m + 1], a))
                    dN = _add(dN, _scale(pw[m], da))
                for m, (b, db) in enumerate(RET_B):
                    Dn = _add(Dn, _scale(pw[m + 1], b))
                    dDn = _add(dDn, _scale(pw[m], db))
                g = _div_pos(N, Dn, M)
                dg = _div_pos(_add(_mul(dN, Dn, M), _neg(_mul(N, dDn, M))), _mul(Dn, Dn, M), M)
                D = _add(g, _neg(T))
                dD = _add(dD, dg)
            elif ret and k == kmin and (name == 'REL'):
                D = _neg(T)
            else:
                D = _add((one, one), _neg(T))
            dV = _add(dV, _neg(_scale(_mul(dD, power(-2 * k), M), c)))
            dV = _add(dV, _scale(_mul(D, power(-2 * k - 1), M), dk))
    return (dV, inv[1])
